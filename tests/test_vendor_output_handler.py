#!/usr/bin/env python3
"""
Test cases for the vendor_output_handler module.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from shadowvendor.utils.vendor_output_handler import (
    make_csv,
    generate_port_report,
    create_vendor_distribution,
    save_vendor_summary
)
from shadowvendor.core.oui_manager import OUIManager

@pytest.fixture
def temp_output_dir(tmp_path):
    """Let pytest clean up after monkeypatch restores cwd, including on Windows."""
    return str(tmp_path)

@pytest.fixture
def sample_device_data():
    """Create sample device data for testing."""
    return [
        {
            'mac': '00:11:22:33:44:55',
            'vendor': 'Cisco',
            'vlan': '100',
            'port': 'Gi1/0/1'
        },
        {
            'mac': 'AA:BB:CC:DD:EE:FF',
            'vendor': 'HP',
            'vlan': '200',
            'port': 'Gi1/0/2'
        }
    ]

def _to_devices_dict(sample_list):
    return {item['mac']: {'vlan': item.get('vlan', 'N/A'), 'port': item.get('port', 'N/A')} for item in sample_list}

class _StubOUI:
    def __init__(self, vendor_map):
        self.vendor_map = vendor_map
    def get_vendor(self, mac):
        return self.vendor_map.get(mac, 'Unknown')

@pytest.fixture
def sample_port_data():
    """Create sample port data for testing."""
    return {
        'Gi1/0/1': {
            'total_devices': 2,
            'vlans': {'100', '200'},
            'vendors': {'Cisco', 'HP'},
            'devices': [
                {
                    'mac': '00:11:22:33:44:55',
                    'vendor': 'Cisco',
                    'vlan': '100'
                },
                {
                    'mac': 'AA:BB:CC:DD:EE:FF',
                    'vendor': 'HP',
                    'vlan': '200'
                }
            ]
        }
    }

def test_make_csv(temp_output_dir, sample_device_data, monkeypatch):
    """Test CSV file generation."""
    # Run in temp dir and use current API
    monkeypatch.chdir(temp_output_dir)
    input_file = Path('test.txt')
    devices = _to_devices_dict(sample_device_data)
    vendors = {d['mac']: d['vendor'] for d in sample_device_data}
    oui = _StubOUI(vendors)
    make_csv(input_file, devices, oui)
    
    output_file = Path('output') / f"{input_file.stem}-Devices.csv"
    assert output_file.exists()
    with open(output_file, 'r') as f:
        content = f.read()
        assert 'MAC,Vendor,VLAN,Port' in content
        assert '00:11:22:33:44:55,Cisco,100,Gi1/0/1' in content
        assert 'AA:BB:CC:DD:EE:FF,HP,200,Gi1/0/2' in content

def test_generate_port_report(temp_output_dir, sample_port_data, monkeypatch):
    """Test port report generation."""
    monkeypatch.chdir(temp_output_dir)
    # Adapt to current API: need devices dict and oui manager and input_file
    input_file = Path('test.txt')
    # Build devices dict from sample_port_data
    devices = {}
    vendor_map = {}
    for port, info in sample_port_data.items():
        for dev in info['devices']:
            devices[dev['mac']] = {'vlan': dev['vlan'], 'port': port}
            vendor_map[dev['mac']] = dev['vendor']
    oui = _StubOUI(vendor_map)
    generate_port_report(input_file, devices, oui, is_mac_table=True)
    
    output_file = Path('output') / f"{input_file.stem}-Ports.csv"
    assert output_file.exists()
    with open(output_file, 'r') as f:
        content = f.read()
        assert 'Port,Total Devices,VLANs,Vendors,Devices' in content
        assert 'Gi1/0/1,2,100,200' in content or 'Gi1/0/1,2,"100,200"' in content

def test_create_vendor_distribution(temp_output_dir, sample_device_data, monkeypatch):
    """Test vendor distribution visualization creation."""
    monkeypatch.chdir(temp_output_dir)
    input_file = Path('test.txt')
    devices = _to_devices_dict(sample_device_data)
    vendors = {d['mac']: d['vendor'] for d in sample_device_data}
    oui = _StubOUI(vendors)
    create_vendor_distribution(devices, oui, input_file)
    
    output_file = Path('output') / 'vendor_distribution.html'
    assert output_file.exists()
    with open(output_file, 'r') as f:
        content = f.read()
        assert 'plotly' in content
        assert 'Cisco' in content
        assert 'HP' in content

def test_save_vendor_summary(temp_output_dir, sample_device_data, monkeypatch):
    """Test vendor summary text file generation."""
    monkeypatch.chdir(temp_output_dir)
    input_file = Path('test.txt')
    devices = _to_devices_dict(sample_device_data)
    vendors = {d['mac']: d['vendor'] for d in sample_device_data}
    oui = _StubOUI(vendors)
    save_vendor_summary(devices, oui, input_file)
    
    output_file = Path('output') / 'vendor_summary.txt'
    assert output_file.exists()
    with open(output_file, 'r') as f:
        content = f.read()
        assert 'Network Device Vendor Summary' in content
        assert 'Cisco' in content
        assert 'HP' in content
        assert '50.0' in content  # Percentage for each vendor

def test_empty_data_handling(temp_output_dir, monkeypatch):
    """Test handling of empty data."""
    monkeypatch.chdir(temp_output_dir)
    input_file = Path('empty.txt')
    devices = {}
    oui = _StubOUI({})
    make_csv(input_file, devices, oui)
    assert (Path('output') / f"{input_file.stem}-Devices.csv").exists()
    
    # Test empty port data
    generate_port_report(input_file, {}, oui, is_mac_table=True)
    assert (Path('output') / f"{input_file.stem}-Ports.csv").exists()
    
    # Test empty vendor distribution
    create_vendor_distribution({}, oui, input_file)
    assert (Path('output') / 'vendor_distribution.html').exists()
    
    # Test empty vendor summary
    save_vendor_summary({}, oui, input_file)
    assert (Path('output') / 'vendor_summary.txt').exists()

def test_invalid_data_handling(temp_output_dir, monkeypatch):
    """Test handling of invalid data."""
    monkeypatch.chdir(temp_output_dir)
    invalid_data = [
        {
            'mac': 'invalid-mac',
            'vendor': None,
            'vlan': None,
            'port': None
        }
    ]
    input_file = Path('invalid.txt')
    vendors = {d['mac']: d.get('vendor') or 'Unknown' for d in invalid_data}
    devices = _to_devices_dict([{
        'mac': invalid_data[0]['mac'] if invalid_data[0]['mac'] else '00:00:00:00:00:00',
        'vlan': invalid_data[0]['vlan'] or 'N/A',
        'port': invalid_data[0]['port'] or 'N/A'
    }]) if invalid_data else {}
    oui = _StubOUI(vendors)
    make_csv(input_file, devices, oui)
    assert (Path('output') / f"{input_file.stem}-Devices.csv").exists()
    
    # Test invalid vendor distribution
    create_vendor_distribution(devices, oui, input_file)
    assert (Path('output') / 'vendor_distribution.html').exists()
    
    # Test invalid vendor summary
    save_vendor_summary(devices, oui, input_file)
    assert (Path('output') / 'vendor_summary.txt').exists()
