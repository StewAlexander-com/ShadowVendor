"""
OUI Manager - MAC Address Database Handler

Implements a robust vendor lookup system with:
1. Smart caching:
   - Memory cache for speed
   - Disk cache for persistence
   - Automatic cache cleanup
2. Rate-limited API access:
   - Multiple service fallbacks
   - Exponential backoff
   - Request batching
3. Error handling:
   - Failed lookup tracking
   - Service rotation on failures
   - Atomic file operations

The manager maintains data integrity through careful state management
and handles network issues gracefully to prevent data loss.
"""

import json
import requests
import datetime
import os
import re
import time
from pathlib import Path
from typing import Dict, Set, Optional, List
from rich import print
from rich.progress import Progress
from .parsing import format_mac_address

class OUIManager:
    FAILED_LOOKUP_TTL = 300  # Seconds; transient failures must recover without manual cleanup.

    def __init__(self, oui_file: str = None, offline: bool = False):
        """Initialize the OUI manager with pre-seeded cache and API fallback.

        Args:
            oui_file: Optional path to a pre-seeded OUI file.
            offline: When True, disables external API lookups and uses cache only.
        """
        self.oui_file = oui_file
        self.offline = offline
        self.cache = {}
        self.failed_lookups = set()
        self._failed_at = {}
        self._file_metadata = None
        
        # Setup user cache directory
        self.output_dir = Path("output")
        self.data_dir = self.output_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.data_dir / "oui_cache.json"
        self.failed_lookups_file = self.data_dir / "failed_lookups.json"
        
        # Load pre-seeded cache first
        self.load_preseeded_cache()
        
        # Then load user cache (this may override some pre-seeded entries)
        if self.cache_file.exists():
            self.load_cache()
            
        # Load failed lookups
        if self.failed_lookups_file.exists():
            self.load_failed_lookups()
            
        # API configuration
        self.api_services = [
            {
                'name': 'macvendors',
                'url': 'https://api.macvendors.com/{oui}',
                'headers': {},
                'rate_limit': 2.0,
                'last_call': 0
            },
            {
                'name': 'maclookup',
                'url': 'https://api.maclookup.app/v2/macs/{oui}',
                'headers': {},
                'rate_limit': 1.0,
                'last_call': 0
            }
        ]
        self.current_service_index = 0

    def _load_oui_file(self):
        """Load OUI database from file."""
        if not self.oui_file or not os.path.exists(self.oui_file):
            return
            
        try:
            with open(self.oui_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        oui = self._normalize_oui(parts[0]) or parts[0].strip()
                        vendor = parts[1].strip()
                        if oui and vendor:
                            self.cache[oui] = vendor
        except Exception as e:
            print(f"Error loading OUI file: {e}")
            
    def get_file_metadata(self) -> dict:
        """Get metadata about the OUI file."""
        if not self.oui_file or not os.path.exists(self.oui_file):
            return None
            
        if self._file_metadata is None:
            try:
                stat = os.stat(self.oui_file)
                self._file_metadata = {
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'path': self.oui_file
                }
            except Exception as e:
                print(f"Error getting file metadata: {e}")
                self._file_metadata = None
                
        return self._file_metadata
        
    def clear_cache(self):
        """Clear the OUI cache."""
        self.cache.clear()
        self.failed_lookups.clear()
        self._failed_at.clear()
        self._file_metadata = None
        
    def load_preseeded_cache(self):
        """Load manufacturer data using the same normalization as live lookups."""
        self._load_oui_file()
        if self.oui_file and os.path.exists(self.oui_file):
            print(f"Loaded {len(self.cache)} entries from pre-seeded OUI cache")

    def load_cache(self):
        """Load user's cached vendor lookups."""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                user_cache = json.load(f)
                # Update cache with user lookups (may override pre-seeded entries)
                if isinstance(user_cache, dict):
                    # Preserve extended-prefix records even though lookups use /24.
                    self.cache.update(user_cache)
                    for key, vendor in user_cache.items():
                        oui = self._normalize_oui(key)
                        if oui and isinstance(vendor, str) and vendor:
                            self.cache[oui] = vendor
        except (json.JSONDecodeError, IOError):
            pass

    def save_cache(self):
        """Save only user-added cache entries with atomic write for cross-platform safety."""
        try:
            # Use atomic write pattern: write to temp file, then rename
            # This prevents corruption on Windows/Linux/Mac if process is interrupted
            temp_file = self.cache_file.with_suffix('.tmp')
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())  # Force write to disk (Unix/Windows)
                except (AttributeError, OSError):
                    pass  # fsync not available on all platforms
            # Atomic rename (works on Unix and Windows)
            temp_file.replace(self.cache_file)
        except (IOError, OSError, PermissionError) as e:
            # Fallback: direct write if atomic rename fails
            try:
                with self.cache_file.open('w', encoding='utf-8') as f:
                    json.dump(self.cache, f, indent=2)
            except (IOError, OSError, PermissionError):
                pass  # Silently fail if cache can't be saved

    def load_failed_lookups(self):
        """Read timed failures; legacy untimed lists are expired, not permanent bans."""
        self.failed_lookups = set()
        self._failed_at = {}
        try:
            with self.failed_lookups_file.open(encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                now = time.time()
                for key, timestamp in saved.items():
                    oui = self._normalize_oui(key)
                    if (oui and isinstance(timestamp, (int, float))
                            and 0 <= now - timestamp < self.FAILED_LOOKUP_TTL):
                        self.failed_lookups.add(oui)
                        self._failed_at[oui] = timestamp
        except (json.JSONDecodeError, OSError):
            pass

    def _recent_failure(self, oui):
        timestamp = self._failed_at.get(oui)
        if timestamp is not None and 0 <= time.time() - timestamp < self.FAILED_LOOKUP_TTL:
            return True
        self.failed_lookups.discard(oui)
        self._failed_at.pop(oui, None)
        return False

    def _remember_failure(self, oui):
        self.failed_lookups.add(oui)
        self._failed_at[oui] = time.time()
        self.save_failed_lookups()

    def save_failed_lookups(self):
        """Save failed lookups with atomic write for cross-platform safety."""
        try:
            # Use atomic write pattern: write to temp file, then rename
            # This prevents corruption on Windows/Linux/Mac if process is interrupted
            temp_file = self.failed_lookups_file.with_suffix('.tmp')
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(self._failed_at, f)
                f.flush()
                try:
                    os.fsync(f.fileno())  # Force write to disk (Unix/Windows)
                except (AttributeError, OSError):
                    pass  # fsync not available on all platforms
            # Atomic rename (works on Unix and Windows)
            temp_file.replace(self.failed_lookups_file)
        except (IOError, OSError, PermissionError) as e:
            # Fallback: direct write if atomic rename fails
            try:
                with self.failed_lookups_file.open('w', encoding='utf-8') as f:
                    json.dump(self._failed_at, f)
            except (IOError, OSError, PermissionError):
                pass  # Silently fail if failed lookups can't be saved

    @staticmethod
    def _normalize_oui(value):
        compact = re.sub(r"[.:-]", "", value.strip()).upper()
        if not re.fullmatch(r"[0-9A-F]{6}", compact):
            return None
        return ":".join(compact[i:i + 2] for i in range(0, 6, 2))

    def _normalize_mac(self, mac: str) -> str:
        normalized = format_mac_address(mac)
        return normalized[:8].upper() if normalized else None

    def _rate_limit(self, service):
        """Implement rate limiting for API calls."""
        current_time = time.time()
        time_since_last_call = current_time - service['last_call']
        if time_since_last_call < service['rate_limit']:
            sleep_time = service['rate_limit'] - time_since_last_call
            time.sleep(sleep_time)
        service['last_call'] = time.time()

    def get_vendor(self, mac: str) -> str:
        """
        Look up vendor for MAC address using cache first, then API.
        
        1. Try pre-seeded cache (Wireshark manufacturers database)
        2. Try user cache (previous API lookups)
        3. If not found and not previously failed, try API lookup
        """
        if not mac:
            return None

        oui = self._normalize_mac(mac)
        
        if oui is None:
            return None

        # A valid cache entry always wins over a previous failure.
        if oui in self.cache:
            return self.cache[oui]

        # Offline misses are not evidence that a vendor lookup has failed.
        if self.offline or self._recent_failure(oui):
            return None

        # Try API lookup
        original_service_index = self.current_service_index
        retries = 0
        max_retries = len(self.api_services) * 2

        while retries < max_retries:
            service = self.api_services[self.current_service_index]
            
            try:
                self._rate_limit(service)
                url = service['url'].format(oui=oui)
                response = requests.get(url, headers=service['headers'], timeout=5)
                
                if response.status_code == 200:
                    if service['name'] == 'maclookup':
                        data = response.json()
                        vendor = data.get('company', 'Unknown')
                    else:
                        vendor = response.text.strip()

                    if vendor and vendor != "Unknown":
                        # Cache the result
                        self.cache[oui] = vendor
                        self.save_cache()
                        return vendor
                        
                elif response.status_code == 429:  # Rate limit
                    service['rate_limit'] *= 1.5  # Increase backoff
                    
                elif response.status_code == 404:  # Not found
                    self._remember_failure(oui)
                    return None

            except (requests.RequestException, json.JSONDecodeError):
                pass  # Try next service

            self.current_service_index = (self.current_service_index + 1) % len(self.api_services)
            retries += 1

            if self.current_service_index == original_service_index:
                time.sleep(1)  # Wait before retry cycle

        # If all retries failed
        self._remember_failure(oui)
        return None

    def batch_lookup_vendors(self, macs: List[str], progress: Progress = None) -> Dict[str, str]:
        """Look up every address; a progress display never controls the work."""
        results = {}
        unknown_macs = []
        for mac in macs:
            oui = self._normalize_mac(mac) if mac else None
            if oui is None:
                results[mac] = "Unknown"
            elif oui in self.cache:
                results[mac] = self.cache[oui]
            elif self._recent_failure(oui):
                results[mac] = "Unknown"
            else:
                unknown_macs.append(mac)

        task_id = None
        if unknown_macs and progress is not None:
            task_id = progress.add_task(
                f"[cyan]Looking up vendors for {len(unknown_macs)} MAC addresses...",
                total=len(unknown_macs),
            )
        for mac in unknown_macs:
            results[mac] = self.get_vendor(mac)
            if task_id is not None:
                progress.advance(task_id)
        return results
