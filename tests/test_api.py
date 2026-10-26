"""Tests for ShadowVendor Python API."""

import pytest
import tempfile
import os
from pathlib import Path
from shadowvendor import analyze_file


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_mac_list_file(temp_dir):
    """Create a sample MAC list file."""
    test_file = temp_dir / "test_mac_list.txt"
    test_file.write_text("00:11:22:33:44:55\n00:AA:BB:CC:DD:EE\n")
    return test_file


@pytest.fixture
def sample_mac_table_file(temp_dir):
    """Create a sample MAC table file."""
    test_file = temp_dir / "test_mac_table.txt"
    content = """Vlan    Mac Address       Type        Ports
----    -----------       ----        -----
10      0011.2233.4455    DYNAMIC     Gi1/0/1
20      00:AA:BB:CC:DD:EE DYNAMIC     Gi1/0/2
"""
    test_file.write_text(content)
    return test_file


def test_analyze_file_mac_list(sample_mac_list_file, temp_dir):
    """Test analyze_file with MAC list input."""
    result = analyze_file(
        input_file=sample_mac_list_file,
        offline=True,
        output_dir=temp_dir
    )
    
    assert result['device_count'] == 2
    assert result['input_type'] == 'mac_list'
    assert len(result['output_files']) >= 3  # CSV, HTML, summary
    assert 'devices' in result
    assert len(result['devices']) == 2


def test_analyze_file_mac_table(sample_mac_table_file, temp_dir):
    """Test analyze_file with MAC table input."""
    result = analyze_file(
        input_file=sample_mac_table_file,
        offline=True,
        output_dir=temp_dir
    )
    
    assert result['device_count'] == 2
    assert result['input_type'] == 'mac_table'
    assert len(result['output_files']) >= 4  # CSV, Port CSV, HTML, summary
    assert any('Ports.csv' in f for f in result['output_files'])


def test_analyze_file_siem_export(sample_mac_list_file, temp_dir):
    """Test analyze_file with SIEM export enabled."""
    result = analyze_file(
        input_file=sample_mac_list_file,
        offline=True,
        siem_export=True,
        site="DC1",
        environment="prod",
        output_dir=temp_dir
    )
    
    assert result['device_count'] == 2
    assert any('siem' in f and 'shadowvendor_siem.json' in f for f in result['output_files'])
    assert any('siem' in f and 'shadowvendor_siem.csv' in f for f in result['output_files'])
    assert all(Path(f).is_file() for f in result['output_files'])


def test_analyze_file_history(sample_mac_list_file, temp_dir):
    """Test analyze_file with history archiving."""
    history_dir = temp_dir / "history"
    
    result = analyze_file(
        input_file=sample_mac_list_file,
        offline=True,
        history_dir=history_dir,
        site="DC1",
        change_ticket="CHG-12345",
        output_dir=temp_dir
    )
    
    assert result['device_count'] == 2
    # Check that history files were created
    history_files = list(history_dir.glob("vendor_summary-*.txt"))
    assert len(history_files) == 1
    metadata_files = list(history_dir.glob("*.metadata.json"))
    assert len(metadata_files) == 1


def test_analyze_file_file_not_found(temp_dir):
    """Test analyze_file with non-existent file."""
    with pytest.raises(FileNotFoundError):
        analyze_file(
            input_file=temp_dir / "nonexistent.txt",
            offline=True,
            output_dir=temp_dir
        )


def test_analyze_file_empty_file(temp_dir):
    """Test analyze_file with empty file."""
    empty_file = temp_dir / "empty.txt"
    empty_file.write_text("")
    
    with pytest.raises(ValueError, match="empty"):
        analyze_file(
            input_file=empty_file,
            offline=True,
            output_dir=temp_dir
        )


def test_analyze_file_no_devices(temp_dir):
    """Test analyze_file with file containing no valid MACs."""
    invalid_file = temp_dir / "invalid.txt"
    invalid_file.write_text("not a mac address\nalso not valid\n")
    
    with pytest.raises(ValueError, match="No MAC addresses"):
        analyze_file(
            input_file=invalid_file,
            offline=True,
            output_dir=temp_dir
        )
