"""Pytest configuration for ShadowVendor tests."""

import os
import sys
import tempfile
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Isolate caches, configuration, logs, and network access for every test."""
    import requests
    from shadowvendor.utils.runtime_logger import reset_logger
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith("SHADOWVENDOR_"):
            monkeypatch.delenv(key)
    def no_network(*args, **kwargs):
        pytest.fail("Unexpected HTTP request: supply an explicit vendor-service mock")
    monkeypatch.setattr(requests.sessions.Session, "request", no_network)
    reset_logger()
    yield
    reset_logger()

@pytest.fixture
def sample_mac_addresses():
    """Provide a list of sample MAC addresses for testing."""
    return [
        "00:11:22:33:44:55",
        "00-11-22-33-44-55",
        "001122334455",
        "0011.2233.4455",
        "invalid_mac",
        "00:11:22:33:44:GG"
    ]

@pytest.fixture
def sample_device_data():
    """Provide sample device data for testing."""
    return {
        "00:11:22:33:44:55": {
            "vlan": "1",
            "port": "Gi1/0/1",
            "vendor": "Vendor A"
        },
        "00:22:33:44:55:66": {
            "vlan": "2",
            "port": "Gi1/0/2",
            "vendor": "Vendor B"
        },
        "00:33:44:55:66:77": {
            "vlan": "1",
            "port": "Gi1/0/3",
            "vendor": "Vendor A"
        }
    }

@pytest.fixture
def sample_vendor_cache():
    """Provide sample vendor cache data for testing."""
    return {
        "001122": "Vendor A",
        "002233": "Vendor B",
        "003344": "Vendor C"
    }

@pytest.fixture
def sample_input_file(tmp_path):
    """Create a sample input file for testing."""
    file_path = tmp_path / "test_input.txt"
    content = """
Vlan    Mac Address       Type        Ports
----    -----------       ----        -----
1       0011.2233.4455   DYNAMIC     Gi1/0/1
2       0022.3344.5566   DYNAMIC     Gi1/0/2
1       0033.4455.6677   DYNAMIC     Gi1/0/3
"""
    file_path.write_text(content)
    return str(file_path)


def pytest_addoption(parser):
    """Add custom command-line options for pytest."""
    parser.addoption(
        "--bandit",
        action="store_true",
        default=False,
        help="Run Bandit security scan as part of test suite"
    )


def pytest_sessionstart(session):
    """Run Bandit security scan before tests if --bandit flag is set."""
    if session.config.getoption("--bandit"):
        run_bandit_scan()


def run_bandit_scan():
    """Run Bandit security scan and fail if issues found."""
    import subprocess
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    bandit_config_path = project_root / "bandit.yaml"
    
    # Build bandit command
    cmd = [
        sys.executable, "-m", "bandit",
        "-c", str(bandit_config_path),
        "-r", str(project_root / "shadowvendor"),
        str(project_root / "ShadowVendor.py"),
        "-f", "json"
    ]
    
    try:
        # Run Bandit scan
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        # Parse JSON output
        import json
        if result.returncode != 0 or result.stdout:
            try:
                bandit_output = json.loads(result.stdout)
                issues = bandit_output.get("results", [])
                
                # Filter out issues that are in the skip list (from config)
                skipped_tests = []
                if bandit_config_path.exists():
                    try:
                        import yaml
                        with open(bandit_config_path) as f:
                            config = yaml.safe_load(f)
                            skipped_tests = config.get("skips", [])
                    except ImportError:
                        # PyYAML not available, skip filtering
                        pass
                
                filtered_issues = [
                    issue for issue in issues
                    if issue.get("test_id") not in skipped_tests
                ]
                
                # Fail if security issues found
                if filtered_issues:
                    issue_summary = "\n".join([
                        f"  {issue.get('severity', 'UNKNOWN').upper()}: {issue.get('test_id')} - "
                        f"{issue.get('issue_text', '')} ({issue.get('filename')}:{issue.get('line_number')})"
                        for issue in filtered_issues
                    ])
                    raise pytest.UsageError(
                        f"Bandit security scan found {len(filtered_issues)} issue(s):\n{issue_summary}\n"
                        f"Fix these issues before running tests."
                    )
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, check stderr for errors
                if result.stderr:
                    raise pytest.UsageError(
                        f"Bandit scan failed:\n{result.stderr}"
                    )
                elif result.returncode != 0:
                    raise pytest.UsageError(
                        f"Bandit scan failed with return code {result.returncode}"
                    )
    except FileNotFoundError:
        raise pytest.UsageError(
            "Bandit not installed. Install with: pip install -r requirements-dev.txt"
        )
    except Exception as e:
        raise pytest.UsageError(
            f"Bandit scan error: {str(e)}"
        )
