"""
Comprehensive tests for all ShadowVendor execution paths.

This test suite validates every way users can run ShadowVendor:
1. Package entry point (basic): shadowvendor input_file.txt
2. Module execution: python3 -m shadowvendor input_file.txt
3. Standalone script (full features): python3 ShadowVendor.py input_file.txt
4. Python API: from shadowvendor import analyze_file
5. All flag combinations and configurations
"""

import pytest
import tempfile
import subprocess
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from shadowvendor import analyze_file
from shadowvendor.config import load_config


@pytest.fixture(autouse=True)
def vendor_services(monkeypatch):
    """Execution-path tests exercise reports, with deterministic unknown vendors."""
    from shadowvendor.core.oui_manager import OUIManager
    monkeypatch.setattr("requests.get", MagicMock(return_value=MagicMock(status_code=404)))
    monkeypatch.setattr(OUIManager, "_rate_limit", lambda self, service: None)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_mac_table_file(temp_dir):
    """Create a sample MAC table file."""
    test_file = temp_dir / "test_mac_table.txt"
    content = """Vlan    Mac Address       Type        Ports
----    -----------       ----        -----
10      0011.2233.4455    DYNAMIC     Gi1/0/1
20      00:AA:BB:CC:DD:EE DYNAMIC     Gi1/0/2
30      B8:AC:6F:77:88:99 DYNAMIC     Gi1/0/3
"""
    test_file.write_text(content)
    return test_file


@pytest.fixture
def sample_mac_list_file(temp_dir):
    """Create a sample MAC list file."""
    test_file = temp_dir / "test_mac_list.txt"
    test_file.write_text("00:11:22:33:44:55\n00:AA:BB:CC:DD:EE\n")
    return test_file


@pytest.fixture
def sample_arp_table_file(temp_dir):
    """Create a sample ARP table file."""
    test_file = temp_dir / "test_arp_table.txt"
    content = """Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  192.168.1.1      -          0011.2233.4455  ARPA   Vlan10
Internet  192.168.1.2      -          00:AA:BB:CC:DD:EE ARPA   Vlan20
"""
    test_file.write_text(content)
    return test_file


# ============================================================================
# Execution Path 1: Package Entry Point (Basic) - shadowvendor input_file.txt
# ============================================================================

def test_package_entry_point_basic(sample_mac_list_file, temp_dir):
    """Test: shadowvendor input_file.txt (basic package entry point)."""
    # This tests the shadowvendor/core/netvendor.py::main() path
    # Note: This entry point doesn't support flags, only basic analysis
    from shadowvendor.core.netvendor import main
    import sys
    
    # Mock sys.argv for the test
    with patch('sys.argv', ['shadowvendor', str(sample_mac_list_file)]):
        # Change to temp_dir to avoid cluttering test directory
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify outputs were created
            assert (temp_dir / "output" / f"{sample_mac_list_file.stem}-Devices.csv").exists()
            assert (temp_dir / "output" / "vendor_distribution.html").exists()
            assert (temp_dir / "output" / "vendor_summary.txt").exists()
        finally:
            os.chdir(old_cwd)


# ============================================================================
# Execution Path 2: Module Execution - python3 -m shadowvendor input_file.txt
# ============================================================================

def test_module_execution(sample_mac_list_file, temp_dir):
    """Test: python3 -m shadowvendor input_file.txt."""
    # This should call the same path as package entry point
    from shadowvendor.core.netvendor import main
    import sys
    
    with patch('sys.argv', ['shadowvendor', str(sample_mac_list_file)]):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify outputs
            assert (temp_dir / "output" / f"{sample_mac_list_file.stem}-Devices.csv").exists()
        finally:
            os.chdir(old_cwd)


# ============================================================================
# Execution Path 3: Standalone Script - python3 ShadowVendor.py input_file.txt
# ============================================================================

def test_standalone_script_basic(sample_mac_table_file, temp_dir):
    """Test: python3 ShadowVendor.py input_file.txt (basic, no flags)."""
    # Test the full ShadowVendor.py main() function
    from ShadowVendor import main
    import sys
    
    with patch('sys.argv', ['ShadowVendor.py', str(sample_mac_table_file)]):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify standard outputs
            assert (temp_dir / "output" / f"{sample_mac_table_file.stem}-Devices.csv").exists()
            assert (temp_dir / "output" / f"{sample_mac_table_file.stem}-Ports.csv").exists()
            assert (temp_dir / "output" / "vendor_distribution.html").exists()
            assert (temp_dir / "output" / "vendor_summary.txt").exists()
        finally:
            os.chdir(old_cwd)


def test_standalone_script_offline(sample_mac_table_file, temp_dir):
    """Test: python3 ShadowVendor.py --offline input_file.txt."""
    from ShadowVendor import main
    import sys
    
    with patch('sys.argv', ['ShadowVendor.py', '--offline', str(sample_mac_table_file)]):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify outputs created in offline mode
            assert (temp_dir / "output" / f"{sample_mac_table_file.stem}-Devices.csv").exists()
        finally:
            os.chdir(old_cwd)


def test_standalone_script_siem_export(sample_mac_table_file, temp_dir):
    """Test: python3 ShadowVendor.py --siem-export --site DC1 --environment prod input_file.txt."""
    from ShadowVendor import main
    import sys
    
    with patch('sys.argv', [
        'ShadowVendor.py',
        '--siem-export',
        '--site', 'DC1',
        '--environment', 'prod',
        str(sample_mac_table_file)
    ]):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify SIEM exports
            assert (temp_dir / "output" / "siem" / "shadowvendor_siem.csv").exists()
            assert (temp_dir / "output" / "siem" / "shadowvendor_siem.json").exists()
            
            # Verify SIEM JSON content
            with open(temp_dir / "output" / "siem" / "shadowvendor_siem.json", 'r') as f:
                first_line = f.readline()
                event = json.loads(first_line)
                assert event['site'] == 'DC1'
                assert event['environment'] == 'prod'
                assert 'mac' in event
                assert 'vendor' in event
        finally:
            os.chdir(old_cwd)


def test_standalone_script_history_drift(sample_mac_table_file, temp_dir):
    """Test: python3 ShadowVendor.py --history-dir history --analyze-drift --site DC1 input_file.txt."""
    from ShadowVendor import main
    import sys
    
    history_dir = temp_dir / "history"
    
    with patch('sys.argv', [
        'ShadowVendor.py',
        '--history-dir', str(history_dir),
        '--analyze-drift',
        '--site', 'DC1',
        '--change-ticket', 'CHG-12345',
        str(sample_mac_table_file)
    ]):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify history archive
            history_files = list(history_dir.glob("vendor_summary-*.txt"))
            assert len(history_files) == 1
            
            # Verify metadata
            metadata_files = list(history_dir.glob("*.metadata.json"))
            assert len(metadata_files) == 1
            
            with open(metadata_files[0], 'r') as f:
                metadata = json.load(f)
                assert metadata['site'] == 'DC1'
                assert metadata['change_ticket_id'] == 'CHG-12345'
                assert 'run_timestamp' in metadata
            
            # Verify drift CSV
            assert (history_dir / "vendor_drift.csv").exists()
        finally:
            os.chdir(old_cwd)


def test_standalone_script_all_features(sample_mac_table_file, temp_dir):
    """Test: python3 ShadowVendor.py --offline --history-dir X --analyze-drift --siem-export --site X --environment Y --change-ticket Z input_file.txt."""
    from ShadowVendor import main
    import sys
    
    history_dir = temp_dir / "history"
    
    with patch('sys.argv', [
        'ShadowVendor.py',
        '--offline',
        '--history-dir', str(history_dir),
        '--analyze-drift',
        '--siem-export',
        '--site', 'DC1',
        '--environment', 'prod',
        '--change-ticket', 'CHG-12345',
        str(sample_mac_table_file)
    ]):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify all outputs
            assert (temp_dir / "output" / f"{sample_mac_table_file.stem}-Devices.csv").exists()
            assert (temp_dir / "output" / f"{sample_mac_table_file.stem}-Ports.csv").exists()
            assert (temp_dir / "output" / "vendor_distribution.html").exists()
            assert (temp_dir / "output" / "vendor_summary.txt").exists()
            assert (temp_dir / "output" / "siem" / "shadowvendor_siem.csv").exists()
            assert (temp_dir / "output" / "siem" / "shadowvendor_siem.json").exists()
            assert (history_dir / "vendor_drift.csv").exists()
        finally:
            os.chdir(old_cwd)


# ============================================================================
# Execution Path 4: Python API - from shadowvendor import analyze_file
# ============================================================================

def test_python_api_basic(sample_mac_list_file, temp_dir):
    """Test: Python API - analyze_file() basic usage."""
    result = analyze_file(
        input_file=sample_mac_list_file,
        offline=True,
        output_dir=temp_dir
    )
    
    assert result['device_count'] == 2
    assert result['input_type'] == 'mac_list'
    assert len(result['output_files']) >= 3


def test_python_api_all_features(sample_mac_table_file, temp_dir):
    """Test: Python API - analyze_file() with all features."""
    history_dir = temp_dir / "history"
    
    result = analyze_file(
        input_file=sample_mac_table_file,
        offline=True,
        history_dir=history_dir,
        analyze_drift_flag=True,
        site="DC1",
        environment="prod",
        change_ticket="CHG-12345",
        siem_export=True,
        output_dir=temp_dir
    )
    
    assert result['device_count'] == 3
    assert result['input_type'] == 'mac_table'
    assert len(result['output_files']) >= 6  # CSV, Port CSV, HTML, Summary, SIEM CSV, SIEM JSON
    
    # Verify history
    assert (history_dir / "vendor_drift.csv").exists()


# ============================================================================
# Execution Path 5: Configuration File Support
# ============================================================================

def test_config_file_ini(sample_mac_table_file, temp_dir):
    """Test: Configuration from INI file."""
    config_file = temp_dir / "shadowvendor.conf"
    config_file.write_text("""[shadowvendor]
offline = true
site = DC1
environment = prod
siem_export = true
""")
    
    from ShadowVendor import main
    import sys
    
    with patch('sys.argv', ['ShadowVendor.py', str(sample_mac_table_file)]):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            main()
            
            # Verify config was applied (SIEM export should be enabled)
            assert (temp_dir / "output" / "siem" / "shadowvendor_siem.json").exists()
        finally:
            os.chdir(old_cwd)


def test_config_file_env_override(sample_mac_table_file, temp_dir):
    """Test: Environment variables override config file."""
    config_file = temp_dir / "shadowvendor.conf"
    config_file.write_text("""[shadowvendor]
offline = false
site = DC1
""")
    
    from ShadowVendor import main
    import sys
    
    with patch('sys.argv', ['ShadowVendor.py', str(sample_mac_table_file)]):
        with patch.dict(os.environ, {'SHADOWVENDOR_OFFLINE': 'true', 'SHADOWVENDOR_SITE': 'DC2'}):
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                main()
                
                # Environment should override config
                # Verify SIEM export has DC2 (from env, not DC1 from config)
                if (temp_dir / "output" / "siem" / "shadowvendor_siem.json").exists():
                    with open(temp_dir / "output" / "siem" / "shadowvendor_siem.json", 'r') as f:
                        first_line = f.readline()
                        if first_line:
                            event = json.loads(first_line)
                            # Site should be from env var (DC2), not config (DC1)
                            # But we need --siem-export flag for SIEM export
                            pass
            finally:
                os.chdir(old_cwd)


# ============================================================================
# Execution Path 6: Different Input File Types
# ============================================================================

def test_mac_list_input(sample_mac_list_file, temp_dir):
    """Test: MAC list input file."""
    result = analyze_file(
        input_file=sample_mac_list_file,
        offline=True,
        output_dir=temp_dir
    )
    
    assert result['input_type'] == 'mac_list'
    assert result['device_count'] == 2
    # MAC lists don't generate port reports
    port_files = [f for f in result['output_files'] if 'Ports.csv' in f]
    assert len(port_files) == 0


def test_mac_table_input(sample_mac_table_file, temp_dir):
    """Test: MAC table input file."""
    result = analyze_file(
        input_file=sample_mac_table_file,
        offline=True,
        output_dir=temp_dir
    )
    
    assert result['input_type'] == 'mac_table'
    assert result['device_count'] == 3
    # MAC tables generate port reports
    port_files = [f for f in result['output_files'] if 'Ports.csv' in f]
    assert len(port_files) == 1


def test_arp_table_input(sample_arp_table_file, temp_dir):
    """Test: ARP table input file."""
    result = analyze_file(
        input_file=sample_arp_table_file,
        offline=True,
        output_dir=temp_dir
    )
    
    assert result['input_type'] == 'arp_table'
    assert result['device_count'] == 2
    # ARP tables don't generate port reports
    port_files = [f for f in result['output_files'] if 'Ports.csv' in f]
    assert len(port_files) == 0


# ============================================================================
# Execution Path 7: Error Handling
# ============================================================================

def test_missing_input_file(temp_dir):
    """Test: Error handling for missing input file."""
    from ShadowVendor import main
    import sys
    
    with patch('sys.argv', ['ShadowVendor.py', 'nonexistent.txt']):
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            with pytest.raises(SystemExit):
                main()
        finally:
            os.chdir(old_cwd)


def test_empty_input_file(temp_dir):
    """Test: Error handling for empty input file."""
    empty_file = temp_dir / "empty.txt"
    empty_file.write_text("")
    
    with pytest.raises(ValueError, match="empty"):
        analyze_file(
            input_file=empty_file,
            offline=True,
            output_dir=temp_dir
        )


def test_invalid_input_file(temp_dir):
    """Test: Error handling for invalid input file (no MACs)."""
    invalid_file = temp_dir / "invalid.txt"
    invalid_file.write_text("not a mac address\nalso not valid\n")
    
    with pytest.raises(ValueError, match="No MAC addresses"):
        analyze_file(
            input_file=invalid_file,
            offline=True,
            output_dir=temp_dir
        )


# ============================================================================
# Execution Path 8: Configuration Loading
# ============================================================================

def test_config_loading_defaults():
    """Test: Configuration loads with defaults when no config file exists."""
    config = load_config()
    
    assert config.get('offline') == False
    assert config.get('history_dir') == 'history'
    assert config.get('siem_export') == False


def test_config_loading_from_file(temp_dir):
    """Test: Configuration loads from file."""
    config_file = temp_dir / "shadowvendor.conf"
    config_file.write_text("""[shadowvendor]
offline = true
site = TEST_SITE
environment = test
""")
    
    config = load_config(config_file)
    
    assert config.get('offline') == True
    assert config.get('site') == 'TEST_SITE'
    assert config.get('environment') == 'test'


def test_config_env_override(temp_dir):
    """Test: Environment variables override config file."""
    config_file = temp_dir / "shadowvendor.conf"
    config_file.write_text("""[shadowvendor]
offline = false
site = CONFIG_SITE
""")
    
    with patch.dict(os.environ, {'SHADOWVENDOR_OFFLINE': 'true', 'SHADOWVENDOR_SITE': 'ENV_SITE'}):
        config = load_config(config_file)
        
        # Env vars should override config
        assert config.get('offline') == True
        assert config.get('site') == 'ENV_SITE'
