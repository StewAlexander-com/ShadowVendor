#!/usr/bin/env python3
"""
Module for handling output generation in the ShadowVendor package.
This module provides functions for creating various output files:
- CSV files with device information
- Port-based reports
- Vendor distribution visualizations
- Text summaries of vendor distributions
"""

import os
import csv
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Set, Any, Union
from collections import Counter
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from pathlib import Path
from collections import defaultdict
from ..core.oui_manager import OUIManager  # Import OUIManager from core package

console = Console()


def _script_json(value):
    """Preserve JSON values while preventing HTML from ending the script element."""
    return json.dumps(value).replace("<", "\\u003c")


def make_csv(input_file: Union[Path, str], devices: Dict[str, Dict[str, str]], oui_manager: OUIManager, *, output_dir: Union[str, Path] = "output") -> None:
    """
    Creates a CSV file with device information.
    
    Args:
        input_file: Path to the input file
        devices: Dictionary of device information
        oui_manager: OUI manager instance for vendor lookups
    """
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert input_file to Path if it's a string
    if isinstance(input_file, str):
        input_file = Path(input_file)
    
    output_file = output_dir / f"{input_file.stem}-Devices.csv"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Writing device information...", total=len(devices))
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['MAC', 'Vendor', 'VLAN', 'Port'])
            
            for mac, info in devices.items():
                vendor = oui_manager.get_vendor(mac)
                # Handle None vendor (occurs in offline mode for uncached MACs)
                vendor = vendor if vendor is not None else "Unknown"
                vlan = info.get('vlan', 'N/A')
                port = info.get('port', 'N/A')
                writer.writerow([mac, vendor, vlan, port])
                progress.advance(task)
    
    console.print(f"\nDevice information written to {output_file}")
    
def generate_port_report(input_file: str, devices: Dict[str, Dict[str, str]], oui_manager, is_mac_table: bool = True, *, output_dir: Union[str, Path] = "output") -> None:
    """
    Generate a CSV report analyzing devices connected to each network port.
    
    Input:
        input_file: Path to the input file (used for output filename)
        devices: Dictionary of device information
            - Key: MAC address
            - Value: Dictionary containing 'vlan' and 'port' information
        oui_manager: OUI manager instance for vendor lookups
        is_mac_table: Boolean indicating if the data is from a MAC address table
        
    Output:
        Creates a CSV file named '{input_file}-Ports.csv' in the output directory
        with columns:
            - Port: Network port identifier
            - Total Devices: Number of devices connected to the port
            - VLANs: Comma-separated list of VLANs present on the port
            - Vendors: Comma-separated list of vendors present on the port
            - Devices: Comma-separated list of MAC addresses
            
    Example Output:
        Port,Total Devices,VLANs,Vendors,Devices
        Gi1/0/1,3,10,20,Cisco Systems;Hewlett Packard,00:11:22:33:44:55,00:11:22:33:44:66
    """
    # Create output file path
    output_file = Path(output_dir) / f"{Path(input_file).stem}-Ports.csv"
    
    # Group devices by port
    port_data = {}
    for mac, device in devices.items():
        port = device.get('port', '')
        if port not in port_data:
            port_data[port] = {
                'total_devices': 0,
                'vlans': set(),
                'vendors': set(),
                'devices': []
            }
        
        port_info = port_data[port]
        port_info['total_devices'] += 1
        port_info['vlans'].add(device.get('vlan', ''))
        vendor = oui_manager.get_vendor(mac)
        # Handle None vendor (occurs in offline mode for uncached MACs)
        vendor = vendor if vendor is not None else "Unknown"
        port_info['vendors'].add(vendor)
        port_info['devices'].append(mac)
        
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Port', 'Total Devices', 'VLANs', 'Vendors', 'Devices'])
        for port, info in port_data.items():
            writer.writerow([
                port,
                info['total_devices'],
                ','.join(sorted(info['vlans'])),
                ','.join(sorted(info['vendors'])),
                ','.join(info['devices'])
            ])

def create_vendor_distribution(devices: Dict[str, Dict[str, str]], oui_manager, input_file: Path, *, output_dir: Union[str, Path] = "output") -> None:
    """
    Creates interactive visualizations of vendor and VLAN distributions.
    
    Input:
        devices: Dictionary of device information
            - Key: MAC address
            - Value: Dictionary containing 'vlan' and 'port' information
        oui_manager: OUI manager instance for vendor lookups
        input_file: Path to the input file (used for output filename)
        
    Output:
        Creates an HTML file named 'vendor_distribution.html' in the output directory
        containing:
        1. Vendor Distribution Chart
           - Interactive pie chart showing device distribution by vendor
           - Hover information includes:
             * Device count and percentage
             * Number of VLANs present
             * Most common VLAN
             * Maximum devices in a VLAN
             
        2. VLAN Analysis Charts
           - Total devices per VLAN
           - Unique vendors per VLAN
           - Vendor distribution per VLAN
           - Top vendors per VLAN
           
    Features:
        - Interactive charts with hover information
        - Responsive layout
        - Color-coded visualizations
        - Sortable data
        - Export capabilities
    """
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print("[cyan]Creating visualizations...[/cyan]")
    
    # Process data for visualization
    vendor_counts = Counter()
    vlan_vendor_data = defaultdict(Counter)  # VLAN -> {vendor: count}
    vendor_vlan_data = defaultdict(Counter)  # Vendor -> {vlan: count}
    vlan_total_devices = Counter()  # Total devices per VLAN
    vlan_unique_vendors = Counter()  # Unique vendors per VLAN
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        # Step 1: Process device data
        data_task = progress.add_task("[cyan]Processing device data...", total=len(devices))
        
        for mac, info in devices.items():
            vendor = oui_manager.get_vendor(mac)
            # Handle None vendor (occurs in offline mode for uncached MACs)
            vendor = vendor if vendor is not None else "Unknown"
            vlan = info.get('vlan', 'N/A')
            
            # Update counters
            vendor_counts[vendor] += 1
            vlan_vendor_data[vlan][vendor] += 1
            vendor_vlan_data[vendor][vlan] += 1
            vlan_total_devices[vlan] += 1
            vlan_unique_vendors[vlan] = len(vlan_vendor_data[vlan])
            
            progress.advance(data_task)
        
        # Step 2: Create vendor distribution chart
        chart1_task = progress.add_task("[cyan]Creating vendor distribution chart...", total=100)
        
        # Create pie chart for overall vendor distribution
        fig1 = go.Figure()
        
        if vendor_counts:  # Only create pie chart if we have data
            sorted_vendors = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)
            labels = [v[0] for v in sorted_vendors]
            values = [v[1] for v in sorted_vendors]
            total_devices = sum(vendor_counts.values())
            
            # Enhanced hover text with more details
            hover_text = [
                f"Vendor: {label}<br>" +
                f"Device Count: {value:,} devices<br>" +
                f"Percentage: {(value/total_devices)*100:.1f}%<br>" +
                f"Present in {len(vendor_vlan_data[label])} VLANs<br>" +
                f"Most Common VLAN: {max(vendor_vlan_data[label].items(), key=lambda x: x[1])[0] if vendor_vlan_data[label] else 'N/A'}<br>" +
                f"Max Devices in a VLAN: {max(vendor_vlan_data[label].values()) if vendor_vlan_data[label] else 0}"
                for label, value in zip(labels, values)
            ]
            
            legend_labels = [f"{label} ({value:,})" for label, value in zip(labels, values)]
            
            fig1.add_trace(
                go.Pie(
                    labels=legend_labels,
                    values=values,
                    hovertemplate="%{customdata}<br><extra></extra>",
                    customdata=hover_text,
                    textinfo='label',
                    textposition='outside',
                    hole=0.3
                )
            )
        else:
            # Add empty state message
            fig1.add_annotation(
                text="No vendor data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=20)
            )
        
        # Update fig1 layout
        fig1.update_layout(
            title="Vendor Distribution",
            showlegend=True if vendor_counts else False,
            autosize=True,
            height=600,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        progress.update(chart1_task, completed=100)
        
        # Step 3: Create VLAN analysis charts
        chart2_task = progress.add_task("[cyan]Creating VLAN analysis charts...", total=100)
        
        # Create subplot figure
        fig2 = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Total Devices per VLAN",
                "Unique Vendors per VLAN",
                "Vendor Distribution per VLAN",
                "Top Vendors per VLAN"
            ),
            vertical_spacing=0.2,
            horizontal_spacing=0.1
        )
        
        if vlan_total_devices:  # Only create charts if we have data
            # Sort VLANs numerically
            sorted_vlans = sorted(vlan_vendor_data.keys(), key=lambda x: str(x))
            
            # 1. VLAN Device Count
            fig2.add_trace(
                go.Bar(
                    x=[f"VLAN {v}" for v in sorted_vlans],
                    y=[vlan_total_devices[vlan] for vlan in sorted_vlans],
                    name="Total Devices",
                    hovertemplate="VLAN: %{x}<br>Devices: %{y}<extra></extra>"
                ),
                row=1, col=1
            )
            
            # 2. Unique Vendors per VLAN
            fig2.add_trace(
                go.Bar(
                    x=[f"VLAN {v}" for v in sorted_vlans],
                    y=[vlan_unique_vendors[vlan] for vlan in sorted_vlans],
                    name="Unique Vendors",
                    hovertemplate="VLAN: %{x}<br>Vendors: %{y}<extra></extra>"
                ),
                row=1, col=2
            )
            
            # 3. Vendor Distribution Heatmap
            if vendor_counts:
                top_vendors = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                vendor_names = [v[0] for v in top_vendors]
                
                heatmap_data = []
                for vlan in sorted_vlans:
                    row = [vlan_vendor_data[vlan].get(vendor, 0) for vendor in vendor_names]
                    heatmap_data.append(row)
                
                fig2.add_trace(
                    go.Heatmap(
                        z=heatmap_data,
                        x=vendor_names,
                        y=[f"VLAN {v}" for v in sorted_vlans],
                        colorscale="Viridis",
                        hovertemplate="VLAN: %{y}<br>Vendor: %{x}<br>Devices: %{z}<extra></extra>"
                    ),
                    row=2, col=1
                )
            
            # 4. Top Vendors Stacked Bar
            if vendor_counts:
                for vendor, _ in top_vendors[:5]:
                    fig2.add_trace(
                        go.Bar(
                            x=[f"VLAN {v}" for v in sorted_vlans],
                            y=[vlan_vendor_data[vlan].get(vendor, 0) for vlan in sorted_vlans],
                            name=vendor,
                            hovertemplate="VLAN: %{x}<br>Vendor: %{data.name}<br>Devices: %{y}<extra></extra>"
                        ),
                        row=2, col=2
                    )
        else:
            # Add empty state messages to all subplots
            for row in [1, 2]:
                for col in [1, 2]:
                    fig2.add_annotation(
                        text="No data available",
                        xref=f"x{(row-1)*2 + col}",
                        yref=f"y{(row-1)*2 + col}",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(size=14)
                    )
        
        # Update fig2 layout
        fig2.update_layout(
            height=1000,
            showlegend=True if vlan_total_devices else False,
            margin=dict(l=50, r=50, t=100, b=50)
        )
        
        progress.update(chart2_task, completed=100)
        
        # Save visualizations to HTML
        output_file = output_dir / "vendor_distribution.html"
        
        html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Network Vendor Distribution Analysis</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    * {{
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        margin: 0;
                        padding: 30px 20px;
                        background-color: #f5f5f5;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 1400px;
                        margin: 0 auto;
                    }}
                    h1 {{
                        color: #2c3e50;
                        text-align: center;
                        margin: 0 0 40px 0;
                        padding: 20px 0;
                        font-size: 2.2em;
                        font-weight: 600;
                        letter-spacing: -0.5px;
                    }}
                    .chart-container {{
                        background-color: white;
                        padding: 35px 30px;
                        margin: 0 0 30px 0;
                        border-radius: 10px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                        transition: box-shadow 0.3s ease;
                    }}
                    .chart-container:hover {{
                        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
                    }}
                    .chart-container h2 {{
                        margin: 0 0 25px 0;
                        padding: 0;
                        color: #34495e;
                        font-size: 1.4em;
                        font-weight: 500;
                    }}
                    #vendor-distribution {{
                        width: 100%;
                        height: 600px;
                        padding: 10px 0;
                    }}
                    #vlan-analysis {{
                        width: 100%;
                        height: 1000px;
                        padding: 10px 0;
                    }}
                    @media (max-width: 768px) {{
                        body {{
                            padding: 15px 10px;
                        }}
                        h1 {{
                            font-size: 1.6em;
                            margin-bottom: 25px;
                            padding: 15px 0;
                        }}
                        .chart-container {{
                            padding: 20px 15px;
                            margin-bottom: 20px;
                        }}
                        #vendor-distribution {{
                            height: 500px;
                        }}
                        #vlan-analysis {{
                            height: 800px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Network Vendor Distribution Analysis</h1>
                    <div class="chart-container">
                        <h2>Vendor Distribution</h2>
                        <div id="vendor-distribution"></div>
                    </div>
                    <div class="chart-container">
                        <h2>VLAN Analysis</h2>
                        <div id="vlan-analysis"></div>
                    </div>
                </div>
                <script>
                    var fig1 = {_script_json(fig1.to_dict())};
                    var fig2 = {_script_json(fig2.to_dict())};
                    Plotly.newPlot('vendor-distribution', fig1.data, fig1.layout);
                    Plotly.newPlot('vlan-analysis', fig2.data, fig2.layout);
                </script>
            </body>
            </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        console.print(f"\nCreated interactive visualizations in {output_file}")

def save_vendor_summary(devices: Dict[str, Dict[str, str]], oui_manager, input_file: Path, *, output_dir: Union[str, Path] = "output") -> None:
    """
    Creates a plain text summary of vendor distribution.
    
    Input:
        devices: Dictionary of device information
            - Key: MAC address
            - Value: Dictionary containing 'vlan' and 'port' information
        oui_manager: OUI manager instance for vendor lookups
        input_file: Path to the input file (used for output filename)
        
    Output:
        Creates a text file named 'vendor_summary.txt' in the output directory
        containing:
        - Total number of devices
        - Vendor distribution table with:
          * Vendor name
          * Device count
          * Percentage of total devices
          
    Example Output:
        Network Device Vendor Summary
        +------------------+-------+------------+
        | Vendor          | Count | Percentage |
        +==================+=======+============+
        | Cisco Systems   | 150   | 30.0%      |
        | Hewlett Packard | 100   | 20.0%      |
        +------------------+-------+------------+
    """
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process vendor counts
    vendor_counts = Counter()
    for mac in devices:
        vendor = oui_manager.get_vendor(mac)
        # Handle None vendor (occurs in offline mode for uncached MACs)
        vendor = vendor if vendor is not None else "Unknown"
        vendor_counts[vendor] += 1
    
    # Calculate total devices
    total_devices = sum(vendor_counts.values())
    
    # Create output file
    output_file = output_dir / "vendor_summary.txt"
    
    # Write summary to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Network Device Vendor Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total Devices: {total_devices}\n\n")
        
        # Create table header
        f.write("Vendor Distribution:\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'Vendor':<30} {'Count':<10} {'Percentage':<10}\n")
        f.write("-" * 50 + "\n")
        
        # Write vendor data
        for vendor, count in sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_devices) * 100
            f.write(f"{vendor:<30} {count:<10} {percentage:>6.1f}%\n")
        
        f.write("-" * 50 + "\n")
    
    console.print(f"\nCreated vendor summary in {output_file}")