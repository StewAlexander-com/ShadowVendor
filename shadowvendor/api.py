"""
ShadowVendor Python API

This module provides a programmatic interface to ShadowVendor functionality,
enabling integration into automation scripts and other tools.

Example usage:
    from shadowvendor import analyze_file
    
    result = analyze_file(
        input_file="mac_table.txt",
        offline=True,
        siem_export=True,
        site="DC1",
        environment="prod"
    )
    
    print(f"Processed {result['device_count']} devices")
    print(f"Output files: {result['output_files']}")
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json
import shutil

from shadowvendor.core.oui_manager import OUIManager
from shadowvendor.core.parsing import read_opening_lines
from shadowvendor.utils.vendor_output_handler import (
    make_csv,
    generate_port_report,
    create_vendor_distribution,
    save_vendor_summary
)
from shadowvendor.utils.drift_analysis import analyze_drift
from shadowvendor.utils.siem_export import export_siem_events
from shadowvendor.utils.runtime_logger import get_logger
from shadowvendor.core.netvendor import (
    is_mac_address,
    is_arp_table as is_arp_table_line,
    format_mac_address
)


def analyze_file(
    input_file: Union[str, Path],
    offline: bool = False,
    history_dir: Optional[Union[str, Path]] = None,
    analyze_drift_flag: bool = False,
    site: Optional[str] = None,
    environment: Optional[str] = None,
    change_ticket: Optional[str] = None,
    siem_export: bool = False,
    output_dir: Union[str, Path] = "output",
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Analyze a network device output file and generate reports.
    
    This is the main programmatic API for ShadowVendor. It processes MAC address
    tables, ARP tables, or MAC lists and generates vendor distribution reports.
    
    Args:
        input_file: Path to input file (MAC table, ARP table, or MAC list)
        offline: If True, disable external vendor lookups (cache-only)
        history_dir: Directory for archiving vendor summaries (None = disabled)
        analyze_drift_flag: If True, run drift analysis on archived summaries
        site: Site/region identifier for SIEM/drift metadata
        environment: Environment identifier for SIEM exports
        change_ticket: Change ticket/incident ID for drift correlation
        siem_export: If True, generate SIEM-friendly CSV/JSONL exports
        output_dir: Parent of the existing "output" report subdirectory (default: "output").
            Standard reports and SIEM exports are kept together without changing cwd.
        verbose: If True, enable verbose output (requires SHADOWVENDOR_VERBOSE env var)
    
    Returns:
        Dictionary with:
            - device_count: Number of unique devices processed
            - vendor_count: Number of unique vendors found
            - output_files: List of generated output file paths
            - input_type: Detected input type ("mac_list", "mac_table", "arp_table")
            - devices: Dictionary of processed devices {mac: {vlan, port, vendor}}
    
    Raises:
        FileNotFoundError: If input_file doesn't exist
        PermissionError: If output directory cannot be created
        ValueError: If input file is empty or invalid
    
    Example:
        >>> result = analyze_file("mac_table.txt", offline=True)
        >>> print(f"Found {result['device_count']} devices")
        >>> print(f"Vendors: {result['vendor_count']}")
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    # Validate input file
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if input_path.stat().st_size == 0:
        raise ValueError(f"Input file is empty: {input_file}")
    
    # Create output directory
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(f"Cannot create output directory: {output_dir}")
    
    # Initialize logger (respects SHADOWVENDOR_LOG env var)
    logger = get_logger()
    
    # Initialize OUI manager
    oui_manager = OUIManager(offline=offline)
    
    # Process the input file
    devices = {}
    line_count = 0
    port_count = 0
    mac_count = 0
    
    with open(input_path, 'r', encoding='utf-8') as f:
        first_line, second_line = read_opening_lines(f)
        
        # Determine file type
        is_mac_list = is_mac_address(first_line)
        is_arp_table_file = not is_mac_list and (
            first_line.startswith("Protocol") or
            "Internet" in first_line or
            "Internet" in second_line or
            (second_line and is_arp_table_line(second_line))
        )
        is_mac_table = not is_mac_list and not is_arp_table_file
        
        # Log file type detection
        if is_mac_list:
            logger.log_file_type_detection("mac_list", "first_line_mac_address")
            input_type = "mac_list"
        elif is_arp_table_file:
            logger.log_file_type_detection("arp_table", "protocol_header_or_internet_keyword")
            input_type = "arp_table"
        else:
            logger.log_file_type_detection("mac_table", "default_assumption")
            input_type = "mac_table"
        
        # Reset to start of file
        f.seek(0)
        
        # Process lines
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            line_count += 1
            
            if is_mac_list:
                mac = line.lower()
                if is_mac_address(mac):
                    mac_formatted = format_mac_address(mac)
                    if mac_formatted:
                        devices[mac_formatted] = {'vlan': 'N/A', 'port': 'N/A'}
                        mac_count += 1
            elif is_arp_table_file:
                if "Protocol" in line:
                    continue
                parts = line.split(None, 5)
                if len(parts) >= 6 and parts[0] == "Internet":
                    mac = parts[3].strip()
                    interface = parts[5].strip()
                    mac_formatted = format_mac_address(mac)
                    if mac_formatted:
                        vlan = interface.replace('Vlan', '') if 'Vlan' in interface else 'N/A'
                        devices[mac_formatted] = {'vlan': vlan, 'port': 'N/A'}
                        mac_count += 1
            else:  # MAC table
                parts = line.split(None, 4)
                if len(parts) >= 4:
                    try:
                        vlan = str(int(parts[0]))
                        mac = parts[1]
                        port = parts[3]
                        mac_formatted = format_mac_address(mac)
                        if mac_formatted:
                            devices[mac_formatted] = {'vlan': vlan, 'port': port}
                            mac_count += 1
                            port_count += 1
                    except (ValueError, IndexError):
                        continue
    
    if len(devices) == 0:
        raise ValueError("No MAC addresses were processed from input file")
    
    # Enrich devices with vendor information
    vendors = set()
    for mac in devices:
        vendor = oui_manager.get_vendor(mac)
        vendor = vendor if vendor is not None else "Unknown"
        devices[mac]['vendor'] = vendor
        vendors.add(vendor)
    
    # Keep the established API report location without changing the process cwd.
    report_dir = output_path / "output"
    output_files = []
    make_csv(input_path, devices, oui_manager, output_dir=report_dir)
    output_files.append(report_dir / f"{input_path.stem}-Devices.csv")

    if is_mac_table:
        generate_port_report(str(input_path), devices, oui_manager, is_mac_table, output_dir=report_dir)
        output_files.append(report_dir / f"{input_path.stem}-Ports.csv")

    create_vendor_distribution(devices, oui_manager, input_path, output_dir=report_dir)
    output_files.append(report_dir / "vendor_distribution.html")
    save_vendor_summary(devices, oui_manager, input_path, output_dir=report_dir)
    output_files.append(report_dir / "vendor_summary.txt")

    # SIEM export (if requested)
    if siem_export:
        export_siem_events(
            devices=devices,
            oui_manager=oui_manager,
            input_file=input_path,
            site=site,
            environment=environment,
            input_type=input_type,
            output_dir=report_dir,
        )
        output_files.append(output_path / "output" / "siem" / "shadowvendor_siem.csv")
        output_files.append(output_path / "output" / "siem" / "shadowvendor_siem.json")
    
    # Archive vendor summary (if history_dir specified)
    if history_dir:
        history_path = Path(history_dir)
        try:
            history_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError(f"Cannot create history directory: {history_dir}")
        
        # Output functions create "output" subdirectory, so summary is at output_path/output/vendor_summary.txt
        summary_src = output_path / "output" / "vendor_summary.txt"
        if summary_src.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            summary_dst = history_path / f"vendor_summary-{timestamp}.txt"
            shutil.copy2(summary_src, summary_dst)
            
            # Write metadata
            metadata = {
                "run_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "site": site,
                "change_ticket_id": change_ticket,
            }
            metadata_path = history_path / f"{summary_dst.stem}.metadata.json"
            with metadata_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
    
    # Drift analysis (if requested)
    if analyze_drift_flag and history_dir:
        drift_csv = analyze_drift(Path(history_dir))
        output_files.append(Path(history_dir) / "vendor_drift.csv")
    
    # Close logger
    logger.close()
    
    return {
        "device_count": len(devices),
        "vendor_count": len(vendors),
        "output_files": [str(f) for f in output_files],
        "input_type": input_type,
        "devices": devices,  # Full device dictionary with vendor info
    }

