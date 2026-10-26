"""Tests for the ShadowVendor package."""

import os
import tempfile
from pathlib import Path
import pytest
from shadowvendor.core import check_dependencies, is_mac_address, is_mac_address_table, parse_port_info
from shadowvendor.core.oui_manager import OUIManager
from shadowvendor.utils.helpers import (
    get_format_type
)
from shadowvendor.core.netvendor import (
    format_mac_address
)

@pytest.fixture
def oui_manager():
    """Create a temporary OUI manager for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["SHADOWVENDOR_DATA_DIR"] = tmpdir
        manager = OUIManager()
        yield manager

def test_is_mac_address():
    """Test MAC address validation."""
    # Standard formats
    assert is_mac_address("00:11:22:33:44:55")
    assert is_mac_address("00-11-22-33-44-55")
    assert is_mac_address("001122334455")
    assert is_mac_address("0011.2233.4455")
    
    # Vendor-specific formats
    assert is_mac_address("00:11:22:33:44:55/ff:ff:ff:ff:ff:ff")  # Juniper
    assert is_mac_address("00:11:22:33:44:55/24")  # Aruba
    assert is_mac_address("00-11-22-33-44-55/ff-ff-ff-ff-ff-ff")  # Extreme
    assert is_mac_address("00:11:22:33:44:55/ffff.ffff.ffff")  # Brocade
    
    # Invalid formats
    assert not is_mac_address("00:11:22:33:44")  # Too short
    assert not is_mac_address("00:11:22:33:44:55:66")  # Too long
    assert not is_mac_address("00:11:22:33:44:GG")  # Invalid characters
    assert not is_mac_address("00:11:22:33:44:55/gg:gg:gg:gg:gg:gg")  # Invalid mask

def test_is_mac_address_table():
    """Test MAC address table detection."""
    # Cisco formats
    assert is_mac_address_table("Vlan    Mac Address       Type        Ports")
    assert is_mac_address_table("VLAN    MAC Address       Type        Interface")
    
    # HP/Aruba formats
    assert is_mac_address_table("VLAN ID  MAC Address      Type        Port")
    assert is_mac_address_table("VLAN    MAC Address       Type        Aging")
    
    # Juniper format
    assert is_mac_address_table("VLAN    MAC Address       Type        Ports    Aging")
    
    # Extreme format
    assert is_mac_address_table("VLAN    MAC Address       Type        Ports    State")
    
    # Brocade format
    assert is_mac_address_table("VLAN    MAC Address       Type        Ports    Last Time")
    
    # Invalid formats
    assert not is_mac_address_table("Internet  10.0.0.1   1   0123.4567.89ab  ARPA")
    assert not is_mac_address_table("Invalid line")
    assert not is_mac_address_table("")

def test_parse_port_info():
    """Test port information parsing."""
    assert parse_port_info("1       0001.0001.0001   DYNAMIC     Gi1/0/1") == "Gi1/0/1"
    assert parse_port_info("1        00:01:00:01:00:01 1") == "1"
    assert parse_port_info("No port info") is None

def test_get_format_type():
    """Test format type detection."""
    assert get_format_type("Vlan    Mac Address       Type        Ports") == "cisco"
    assert get_format_type("VLAN ID  MAC Address      Port") == "hp"
    assert get_format_type("Some other format") == "generic"

def test_oui_manager_cache(tmp_path):
    """Use an explicit temporary cache, never a live lookup or developer cache."""
    import json
    cache_dir = tmp_path / "output" / "data"
    cache_dir.mkdir(parents=True)
    (cache_dir / "oui_cache.json").write_text(json.dumps({
        "00:1B:63": "Apple, Inc.", "00:0E:83": "Cisco Systems, Inc",
        "00:24:81": "Hewlett Packard", "B8:AC:6F": "Dell Inc.",
        "00:90:7F": "WatchGuard Technologies, Inc.",
    }))
    oui_manager = OUIManager(offline=True)
    # Apple, Inc.
    vendor = oui_manager.get_vendor('00:1B:63:AA:BB:CC')
    assert vendor == 'Apple, Inc.'
    # Cisco Systems, Inc
    vendor = oui_manager.get_vendor('00:0E:83:11:22:33')
    assert vendor == 'Cisco Systems, Inc'
    # Hewlett Packard
    vendor = oui_manager.get_vendor('00:24:81:44:55:66')
    assert vendor == 'Hewlett Packard'
    # Dell Inc.
    vendor = oui_manager.get_vendor('B8:AC:6F:77:88:99')
    assert vendor == 'Dell Inc.'
    # WatchGuard Technologies, Inc.
    vendor = oui_manager.get_vendor('00:90:7F:12:34:56')
    assert vendor == 'WatchGuard Technologies, Inc.'

def test_oui_manager_failed_lookups(monkeypatch):
    """Test OUI manager failed lookups handling with a MAC not in cache."""
    from unittest.mock import Mock
    monkeypatch.setattr("requests.get", Mock(return_value=Mock(status_code=404)))
    oui_manager = OUIManager()
    # Use a MAC not in the cache
    mac = 'AA:BB:CC:DD:EE:FF'
    vendor = oui_manager.get_vendor(mac)
    assert vendor is None
    # Compute the OUI in the same normalized format (e.g. 'AA:BB:CC') as get_vendor does.
    oui = mac[:8]  # e.g. 'AA:BB:CC'
    assert oui in oui_manager.failed_lookups

def test_oui_manager_file_tracking():
    """Test OUI manager file tracking functionality."""
    oui_manager = OUIManager()  # Initialize without file
    metadata = oui_manager.get_file_metadata()
    assert metadata is None  # Should be None when no file is specified
    
    # Test with a non-existent file
    oui_manager = OUIManager('nonexistent.txt')
    metadata = oui_manager.get_file_metadata()
    assert metadata is None

def test_format_mac_address():
    """Test MAC address formatting."""
    # Standard formats
    assert format_mac_address("00:11:22:33:44:55") == "00:11:22:33:44:55"
    assert format_mac_address("00-11-22-33-44-55") == "00:11:22:33:44:55"
    assert format_mac_address("001122334455") == "00:11:22:33:44:55"
    assert format_mac_address("0011.2233.4455") == "00:11:22:33:44:55"
    
    # Vendor-specific formats
    assert format_mac_address("00:11:22:33:44:55/ff:ff:ff:ff:ff:ff") == "00:11:22:33:44:55"  # Juniper
    assert format_mac_address("00:11:22:33:44:55/24") == "00:11:22:33:44:55"  # Aruba
    assert format_mac_address("00-11-22-33-44-55/ff-ff-ff-ff-ff-ff") == "00:11:22:33:44:55"  # Extreme
    assert format_mac_address("00:11:22:33:44:55/ffff.ffff.ffff") == "00:11:22:33:44:55"  # Brocade
    
    # Invalid formats
    assert format_mac_address("") is None
    assert format_mac_address("invalid") is None
    assert format_mac_address("00:11:22:33:44") is None
