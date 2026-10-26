"""
SIEM Export Utilities for ShadowVendor

This module standardizes ShadowVendor results into SIEM-friendly CSV and JSONL
formats that can be ingested by systems like Elastic, Splunk, or other SIEMs.

Design goals:
- Do not change existing outputs or behavior.
- Depend only on in-memory `devices` data and the OUI manager.
- Produce simple, flat records with consistent fields.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def _current_timestamp() -> str:
    """Return current UTC time in ISO-8601 format with 'Z' suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def export_siem_events(
    devices: Dict[str, Dict[str, str]],
    oui_manager,
    input_file: str | Path,
    site: str | None = None,
    environment: str | None = None,
    input_type: str | None = None,
    *,
    output_dir: str | Path = "output",
) -> None:
    """
    Export normalized events for SIEM ingestion with stable schema.

    Args:
        devices: Mapping of MAC -> {'vlan': str, 'port': str}.
        oui_manager: OUIManager instance used for vendor lookups.
        input_file: Original input file path.
        site: Optional site/region identifier (e.g. "DC1", "HQ", "us-east-1").
        environment: Optional environment identifier (e.g. "prod", "dev", "staging").
        input_type: Optional logical input type ("mac_list", "mac_table", "arp_table").

    Outputs (created in `output/siem/` directory):
        - output/siem/shadowvendor_siem.csv (line-delimited CSV)
        - output/siem/shadowvendor_siem.json (JSONL, one JSON object per line)

    Schema (stable, SIEM-friendly field names):
        - timestamp: UTC ISO-8601 collection time (e.g., "2025-10-31T16:23:45Z")
        - site: Site/region identifier
        - environment: Environment identifier (prod/dev/staging)
        - mac: Normalized MAC address (xx:xx:xx:xx:xx:xx)
        - vendor: Vendor name from OUI lookup
        - device_name: Device identifier (derived from MAC if not available)
        - vlan: VLAN ID or "N/A"
        - interface: Network interface/port identifier
        - input_type: Source data type (mac_list/mac_table/arp_table)
        - source_file: Original input filename
    """
    # Create dedicated SIEM output directory
    siem_dir = Path(output_dir) / "siem"
    try:
        siem_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(
            f"Cannot create SIEM output directory '{siem_dir}' (permission denied). "
            "Please check directory permissions or run with appropriate access."
        )
    except Exception as e:
        raise RuntimeError(f"Cannot create SIEM output directory '{siem_dir}': {e}")

    source_file = Path(input_file).name
    timestamp = _current_timestamp()

    csv_path = siem_dir / "shadowvendor_siem.csv"
    json_path = siem_dir / "shadowvendor_siem.json"

    # Stable schema with SIEM-friendly field names
    fieldnames = [
        "timestamp",
        "site",
        "environment",
        "mac",
        "vendor",
        "device_name",
        "vlan",
        "interface",
        "input_type",
        "source_file",
    ]

    # Write CSV (line-delimited, one record per line)
    with csv_path.open("w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        writer.writeheader()

        for mac, info in devices.items():
            vendor = oui_manager.get_vendor(mac)
            # Derive device_name from MAC if not explicitly provided
            device_name = f"device-{mac.replace(':', '-')}" if not info.get("device_name") else info.get("device_name")
            interface = info.get("port", "N/A")
            
            row = {
                "timestamp": timestamp,
                "site": site or "",
                "environment": environment or "",
                "mac": mac,
                "vendor": vendor or "Unknown",
                "device_name": device_name,
                "vlan": info.get("vlan", "N/A"),
                "interface": interface,
                "input_type": input_type or "unknown",
                "source_file": source_file,
            }
            writer.writerow(row)

    # Write JSONL (one JSON object per line, line-delimited)
    with json_path.open("w", encoding="utf-8") as f_json:
        for mac, info in devices.items():
            vendor = oui_manager.get_vendor(mac)
            device_name = f"device-{mac.replace(':', '-')}" if not info.get("device_name") else info.get("device_name")
            interface = info.get("port", "N/A")
            
            event: Dict[str, Any] = {
                "timestamp": timestamp,
                "site": site or "",
                "environment": environment or "",
                "mac": mac,
                "vendor": vendor or "Unknown",
                "device_name": device_name,
                "vlan": info.get("vlan", "N/A"),
                "interface": interface,
                "input_type": input_type or "unknown",
                "source_file": source_file,
            }
            f_json.write(json.dumps(event, ensure_ascii=False) + "\n")


