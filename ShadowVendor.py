#!/usr/bin/env python3

import os
import sys
import json
import csv
import argparse
import shutil
from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console

from shadowvendor.core.oui_manager import OUIManager
from shadowvendor.utils.vendor_output_handler import (
    make_csv,
    generate_port_report,
    create_vendor_distribution,
    save_vendor_summary
)
from shadowvendor.utils.drift_analysis import analyze_drift
from shadowvendor.utils.siem_export import export_siem_events
from shadowvendor.utils.runtime_logger import get_logger
from shadowvendor.config import load_config

from shadowvendor.core.parsing import format_mac_address, is_mac_address, read_opening_lines

console = Console()
VERBOSE = os.getenv("SHADOWVENDOR_VERBOSE", "0") in ("1", "true", "True")

def check_dependencies():
    """
    Check if required modules are installed.
    """
    required_modules = ['requests', 'plotly', 'tqdm', 'rich']
    for module in required_modules:
        try:
            __import__(module)
            console.print(f"The module '{module}' is installed.")
        except ImportError:
            console.print(f"[bold red]Error:[/bold red] Required module '{module}' is not installed.")
            console.print(f"Please install it using: pip install {module}")
            sys.exit(1)

def is_mac_address_table(line: str) -> bool:
    """
    Check if a line is from a MAC address table.
    """
    # Check for header line variations
    if any(all(word in line for word in header) for header in [
        ["Vlan", "Mac Address"],
        ["VLAN", "MAC Address"],
        ["VLAN ID", "MAC Address"]
    ]):
        return True
        
    words = line.strip().split()
    if len(words) < 2:
        return False
    try:
        vlan = int(words[0])
        if not (1 <= vlan <= 4094):
            return False
    except ValueError:
        return False
    return is_mac_address(words[1])

def parse_port_info(line: str) -> str:
    """
    Extract port information from a line.
    """
    if "Internet" in line and "ARPA" in line:
        return None
    words = line.strip().split()
    if len(words) < 2:
        return None
    port = words[-1]
    # Check for common port prefixes
    if any(port.startswith(prefix) for prefix in ['Gi', 'Fa', 'Te', 'Eth']):
        return port
    # Check if it's a simple port number
    try:
        int(port)
        return port
    except ValueError:
        return None

def main():
    """
    Main entry point for the ShadowVendor package.
    """
    # Check if required modules are installed
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="Analyze network MAC/ARP data and generate vendor distribution reports."
    )
    parser.add_argument(
        "input_file",
        help="Path to MAC address list, MAC table, or ARP table file."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable external vendor lookups and use only the local OUI cache. "
             "Uncached devices will appear as 'Unknown'."
    )
    parser.add_argument(
        "--history-dir",
        default="history",
        help="Directory to archive vendor_summary snapshots for drift analysis "
             "(default: ./history)."
    )
    parser.add_argument(
        "--analyze-drift",
        action="store_true",
        help="After archiving the latest vendor_summary snapshot, run drift analysis "
             "over all archived summaries and write vendor_drift.csv."
    )
    parser.add_argument(
        "--site",
        default=None,
        help="Optional site/region identifier tag to include in SIEM exports (e.g., DC1, HQ, us-east-1)."
    )
    parser.add_argument(
        "--environment",
        default=None,
        help="Optional environment identifier tag to include in SIEM exports (e.g., prod, dev, staging)."
    )
    parser.add_argument(
        "--change-ticket",
        default=None,
        help="Optional change ticket/incident ID for drift analysis correlation (e.g., CHG-12345, INC-67890). "
             "Stored in drift metadata for 8D/5-why incident analysis workflows."
    )
    parser.add_argument(
        "--siem-export",
        action="store_true",
        help="Export normalized CSV/JSONL events for SIEM ingestion "
             "(shadowvendor_siem.csv / shadowvendor_siem.json in output/siem/ directory). "
             "Each record includes: timestamp, site, environment, mac, vendor, device_name, vlan, interface, input_type, source_file."
    )

    args = parser.parse_args()
    input_file = args.input_file
    
    # Load configuration (config file values can be overridden by CLI args)
    config = load_config()
    
    # Apply config defaults (CLI args take precedence)
    if not args.offline:
        args.offline = config.get('offline', False)
    if args.history_dir == "history" and config.get('history_dir') != "history":
        args.history_dir = config.get('history_dir', "history")
    if not args.analyze_drift:
        args.analyze_drift = config.get('analyze_drift', False)
    if not args.site:
        args.site = config.get('site')
    if not args.environment:
        args.environment = config.get('environment')
    if not args.change_ticket:
        args.change_ticket = config.get('change_ticket')
    if not args.siem_export:
        args.siem_export = config.get('siem_export', False)
    
    # Initialize runtime logger
    logger = get_logger()
    
    # Log command-line arguments (excluding sensitive data)
    logger.log_event("command_start", {
        "input_file": str(input_file),
        "offline_mode": args.offline,
        "siem_export": args.siem_export,
        "analyze_drift": args.analyze_drift,
        "has_history_dir": bool(args.history_dir),
        "has_site": bool(args.site),
        "has_environment": bool(args.environment),
        "has_change_ticket": bool(args.change_ticket),
    })

    # Check if input file exists
    if not os.path.exists(input_file):
        logger.log_error("file_not_found", f"Input file '{input_file}' not found", {
            "input_file": str(input_file),
            "is_absolute": os.path.isabs(input_file),
            "current_directory": os.getcwd()
        })
        console.print(f"[bold red]Error:[/bold red] Input file '{input_file}' not found.")
        console.print(f"[yellow]Hint:[/yellow] Please check that the file path is correct and the file exists.")
        if not os.path.isabs(input_file):
            console.print(f"[yellow]Hint:[/yellow] You provided a relative path. Current directory: {os.getcwd()}")
        sys.exit(1)
    
    # Check if input is a directory instead of a file
    if os.path.isdir(input_file):
        logger.log_error("invalid_input", f"'{input_file}' is a directory, not a file", {
            "input_file": str(input_file)
        })
        console.print(f"[bold red]Error:[/bold red] '{input_file}' is a directory, not a file.")
        console.print(f"[yellow]Hint:[/yellow] Please provide the path to a file containing MAC addresses, ARP data, or MAC address tables.")
        sys.exit(1)
    
    # Check if file is readable
    if not os.access(input_file, os.R_OK):
        logger.log_error("permission_denied", f"Cannot read file '{input_file}'", {
            "input_file": str(input_file),
            "error_type": "read_permission"
        })
        console.print(f"[bold red]Error:[/bold red] Cannot read file '{input_file}' (permission denied).")
        console.print(f"[yellow]Hint:[/yellow] Please check file permissions or run with appropriate access.")
        sys.exit(1)
    
    # Check if file is empty
    if os.path.getsize(input_file) == 0:
        logger.log_error("empty_file", f"Input file '{input_file}' is empty", {
            "input_file": str(input_file)
        })
        console.print(f"[bold red]Error:[/bold red] Input file '{input_file}' is empty.")
        console.print(f"[yellow]Hint:[/yellow] Please provide a file containing MAC addresses, ARP data, or MAC address tables.")
        sys.exit(1)
    
    # Log processing start
    logger.log_processing_start(input_file, {
        "offline": args.offline,
        "site": args.site,
        "environment": args.environment
    })

    # Initialize OUI manager
    oui_manager = OUIManager(offline=args.offline)
    if args.offline:
        console.print(
            "[yellow]Offline mode enabled:[/yellow] external vendor lookups are disabled. "
            "Devices not present in the local cache will appear as 'Unknown'."
        )
    if VERBOSE:
        console.print(f"Loaded OUI cache with {len(oui_manager.cache)} entries")
    
    # Process the input file
    devices = {}
    line_count = 0
    port_count = 0
    mac_count = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            first_line, second_line = read_opening_lines(f)
            
            # Debug output for file type detection
            if VERBOSE:
                console.print(f"\nFile Analysis:")
                console.print(f"First line: {first_line}")
                console.print(f"Second line: {second_line}")
            
            # Check file type
            is_mac_list = is_mac_address(first_line)
            is_arp_table = not is_mac_list and (
                first_line.startswith("Protocol") or  # ARP table header
                "Internet" in first_line or           # First data line
                "Internet" in second_line             # Second line for ARP tables
            )
            is_mac_table = not is_mac_list and not is_arp_table
            
            # Log file type detection
            if is_mac_list:
                logger.log_file_type_detection("mac_list", "first_line_mac_address")
            elif is_arp_table:
                logger.log_file_type_detection("arp_table", "protocol_header_or_internet_keyword")
            else:
                logger.log_file_type_detection("mac_table", "default_assumption")
            
            if VERBOSE:
                console.print(f"\nFile Type Detection:")
                console.print(f"  is_mac_list: {is_mac_list}")
                console.print(f"  is_arp_table: {is_arp_table}")
                console.print(f"  is_mac_table: {is_mac_table}")
            
            # Reset to start of file
            f.seek(0)
            
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                line_count += 1
                
                if is_mac_list:
                    mac = line.lower()
                    if is_mac_address(mac):
                        mac_formatted = format_mac_address(mac)
                        if mac_formatted:
                            devices[mac_formatted] = {'vlan': 'N/A', 'port': 'N/A'}
                            mac_count += 1
                            if VERBOSE:
                                console.print(f"Added MAC list entry: {mac_formatted}")
                elif is_arp_table:
                    # Skip the header line
                    if "Protocol" in line:
                        continue
                        
                    # Use string split with maxsplit to preserve spacing
                    parts = line.split(None, 5)  # Split into 6 parts max
                    if VERBOSE:
                        console.print(f"\nProcessing line: {line}")
                        console.print(f"Split parts: {parts}")
                    
                    if len(parts) >= 6 and parts[0] == "Internet":
                        mac = parts[3].strip()  # Hardware address is the 4th field
                        interface = parts[5].strip()  # Interface is the last field
                        
                        if VERBOSE:
                            console.print(f"Found MAC: {mac}")
                            console.print(f"Interface: {interface}")
                        
                        mac_formatted = format_mac_address(mac)
                        if mac_formatted:
                            vlan = interface.replace('Vlan', '') if 'Vlan' in interface else 'N/A'
                            devices[mac_formatted] = {'vlan': vlan, 'port': 'N/A'}
                            mac_count += 1
                            if VERBOSE:
                                console.print(f"Added MAC: {mac_formatted} with VLAN: {vlan}")
                else:
                    # MAC table processing
                    words = line.split()
                    if len(words) >= 2:
                        mac = words[1]
                        mac_formatted = format_mac_address(mac)
                        if mac_formatted:
                            vlan = words[0] if is_mac_address_table(line) else 'N/A'
                            port = parse_port_info(line)
                            if port:
                                port_count += 1
                            devices[mac_formatted] = {'vlan': vlan, 'port': port if port else 'N/A'}
                            mac_count += 1
                            if VERBOSE:
                                console.print(f"Added MAC table entry: {mac_formatted} (VLAN: {vlan}, Port: {port if port else 'N/A'})")
    except PermissionError:
        console.print(f"[bold red]Error:[/bold red] Permission denied when reading file '{input_file}'.")
        console.print(f"[yellow]Hint:[/yellow] Please check file permissions or run with appropriate access.")
        sys.exit(1)
    except UnicodeDecodeError as e:
        console.print(f"[bold red]Error:[/bold red] Cannot decode file '{input_file}' as UTF-8 text.")
        console.print(f"[yellow]Hint:[/yellow] The file may be binary or use a different encoding. Expected text file with MAC addresses.")
        console.print(f"[yellow]Details:[/yellow] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Unexpected error reading file '{input_file}': {e}")
        console.print(f"[yellow]Hint:[/yellow] Please ensure the file is a valid text file containing MAC addresses, ARP data, or MAC address tables.")
        sys.exit(1)
    
    # Print processing summary
    console.print(f"\nProcessing Summary:")
    console.print(f"Processed {line_count} lines")
    console.print(f"Found {mac_count} MAC addresses")
    if VERBOSE:
        console.print(f"Total devices in dictionary: {len(devices)}")
    
    # Log processing end with statistics
    logger.log_processing_end({
        "lines_processed": line_count,
        "mac_addresses_found": mac_count,
        "unique_devices": len(devices),
        "ports_found": port_count,
        "file_type": "mac_list" if is_mac_list else ("arp_table" if is_arp_table else "mac_table")
    })
    
    if len(devices) == 0:
        logger.log_error("no_mac_addresses", "No MAC addresses found in input file", {
            "lines_processed": line_count,
            "file_type_detected": "mac_list" if is_mac_list else ("arp_table" if is_arp_table else "mac_table")
        })
        console.print("[bold red]Error:[/bold red] No MAC addresses were found in the input file!")
        console.print(f"[yellow]Hint:[/yellow] Please verify that '{input_file}' contains:")
        console.print("  - MAC addresses (e.g., 00:11:22:33:44:55)")
        console.print("  - ARP table output (with 'Protocol' header)")
        console.print("  - MAC address table (with 'Vlan' or 'VLAN' header)")
        console.print(f"[yellow]Hint:[/yellow] Processed {line_count} lines but found no valid MAC addresses.")
        if line_count == 0:
            console.print(f"[yellow]Note:[/yellow] The file appears to be empty or contains only whitespace.")
        sys.exit(1)
    
    # Show sample of processed devices
    if VERBOSE:
        console.print("\nSample of processed devices:")
        for i, (mac, info) in enumerate(devices.items()):
            if i >= 5:  # Show first 5 entries
                break
            console.print(f"  {mac}: {info}")
    
    # Ensure output directory exists
    try:
        os.makedirs('output', exist_ok=True)
    except PermissionError:
        console.print(f"[bold red]Error:[/bold red] Cannot create output directory 'output' (permission denied).")
        console.print(f"[yellow]Hint:[/yellow] Please check directory permissions or run with appropriate access.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Cannot create output directory 'output': {e}")
        sys.exit(1)
    
    # Generate reports
    # Use Path for cross-platform compatibility
    input_path = Path(input_file)
    output_file = Path('output') / f"{input_path.stem}-Devices.csv"
    if VERBOSE:
        console.print(f"\nWriting to CSV file: {output_file}")
    
    try:
        with output_file.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['MAC', 'Vendor', 'VLAN', 'Port'])
            for mac, info in devices.items():
                vendor = oui_manager.get_vendor(mac)
                vlan = info.get('vlan', 'N/A')
                port = info.get('port', 'N/A')
                writer.writerow([mac, vendor, vlan, port])
                if VERBOSE:
                    console.print(f"Wrote: {mac}, {vendor}, {vlan}, {port}")
    except PermissionError:
        console.print(f"[bold red]Error:[/bold red] Cannot write to output file '{output_file}' (permission denied).")
        console.print(f"[yellow]Hint:[/yellow] Please check file/directory permissions or run with appropriate access.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Cannot write to output file '{output_file}': {e}")
        sys.exit(1)
    
    # Verify the file was written
    if output_file.exists():
        logger.log_output_generation("device_csv", str(output_file), len(devices))
        if VERBOSE:
            with output_file.open('r', encoding='utf-8') as f:
                content = f.read()
                console.print(f"\nOutput file content (first few lines):")
                console.print(content[:500])  # Show first 500 characters
    else:
        logger.log_error("output_creation_failed", f"Output file '{output_file}' was not created", {
            "output_file": str(output_file)
        })
        console.print("[bold red]Error:[/bold red] Output file was not created!")
    
    # Generate additional reports
    if is_mac_table:
        generate_port_report(input_file, devices, oui_manager, is_mac_table)
    
    create_vendor_distribution(devices, oui_manager, input_file)
    save_vendor_summary(devices, oui_manager, input_file)

    # Optional SIEM export
    if args.siem_export:
        if is_mac_list:
            input_type = "mac_list"
        elif is_arp_table:
            input_type = "arp_table"
        elif is_mac_table:
            input_type = "mac_table"
        else:
            input_type = "unknown"
        try:
            export_siem_events(
                devices=devices,
                oui_manager=oui_manager,
                input_file=input_file,
                site=args.site,
                environment=args.environment,
                input_type=input_type,
            )
        except PermissionError as e:
            console.print(f"[bold red]Error:[/bold red] Cannot create SIEM export files (permission denied).")
            console.print(f"[yellow]Hint:[/yellow] Please check directory permissions for 'output/siem/' or run with appropriate access.")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] SIEM export failed: {e}")
            console.print(f"[yellow]Hint:[/yellow] Please check that the output directory is writable and you have sufficient disk space.")
            sys.exit(1)

    # Archive vendor summary for drift analysis with metadata
    # Note: args.history_dir has a default value, so it's always set
    if args.history_dir:
        history_dir = Path(args.history_dir)
        try:
            history_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            console.print(f"[bold red]Error:[/bold red] Cannot create history directory '{history_dir}' (permission denied).")
            console.print(f"[yellow]Hint:[/yellow] Please check directory permissions or run with appropriate access.")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] Cannot create history directory '{history_dir}': {e}")
            sys.exit(1)
        
        summary_src = Path("output") / "vendor_summary.txt"
        if summary_src.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            summary_dst = history_dir / f"vendor_summary-{timestamp}.txt"
            try:
                shutil.copy2(summary_src, summary_dst)
                
                # Write companion metadata file for drift analysis correlation
                metadata = {
                    "run_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "site": args.site,
                    "change_ticket_id": args.change_ticket,
                }
                metadata_path = history_dir / f"{summary_dst.stem}.metadata.json"
                with metadata_path.open("w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                
                if VERBOSE:
                    console.print(f"Archived vendor summary to [green]{summary_dst}[/green]")
                    console.print(f"Archived metadata to [green]{metadata_path}[/green]")
            except PermissionError:
                console.print(f"[bold red]Error:[/bold red] Cannot write to history directory '{history_dir}' (permission denied).")
                console.print(f"[yellow]Hint:[/yellow] Please check directory permissions or run with appropriate access.")
                sys.exit(1)
            except OSError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not archive vendor summary: {e}")
                console.print(f"[yellow]Hint:[/yellow] The vendor summary was generated but could not be archived. Check directory permissions.")
        else:
            console.print(f"[yellow]Warning:[/yellow] Vendor summary file not found at 'output/vendor_summary.txt'. Skipping archive.")

    # Optionally run drift analysis over archived summaries
    if args.analyze_drift:
        # args.history_dir has a default value, so it's always available
        try:
            drift_csv = analyze_drift(history_dir)
            console.print(f"Vendor drift analysis written to [green]{drift_csv}[/green]")
        except RuntimeError as e:
            console.print(f"[bold red]Error:[/bold red] Drift analysis failed: {e}")
            console.print(f"[yellow]Hint:[/yellow] Ensure you have archived at least one vendor summary using --history-dir before running drift analysis.")
            sys.exit(1)
        except Exception as e:
            logger.log_error("drift_analysis_failed", str(e), {
                "history_dir": str(history_dir),
                "error_type": type(e).__name__
            })
            console.print(f"[bold red]Error:[/bold red] Drift analysis failed: {e}")
            console.print(f"[yellow]Hint:[/yellow] Please check that the history directory '{history_dir}' is accessible and contains valid vendor summary files.")
            sys.exit(1)
    
    # Close logger
    logger.close()

if __name__ == "__main__":
    main()