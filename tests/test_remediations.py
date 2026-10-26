"""Acceptance checks for the October 2026 correctness and safety fixes.

Run: python -m pytest tests/test_remediations.py -q
All network requests are blocked unless a test supplies an explicit mock.
"""
import csv
import json
import os
import re
import runpy
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from shadowvendor import analyze_file
from shadowvendor.core.oui_manager import OUIManager
from shadowvendor.utils.runtime_logger import reset_logger

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "fixtures" / "synthetic"

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith("SHADOWVENDOR_"):
            monkeypatch.delenv(key)
    from shadowvendor.config import ShadowVendorConfig
    monkeypatch.setattr(ShadowVendorConfig, "_find_config_file", lambda self: None)
    reset_logger()
    cache = tmp_path / "output" / "data"
    cache.mkdir(parents=True)
    (cache / "oui_cache.json").write_text((DATA / "vendors.json").read_text())
    def blocked(*args, **kwargs):
        pytest.fail(f"Unexpected network request: {args}")
    monkeypatch.setattr(requests, "get", blocked)
    yield
    reset_logger()

def cli(monkeypatch, filename, *flags):
    monkeypatch.setattr(sys, "argv", ["ShadowVendor.py", "--offline", str(DATA / filename), *flags])
    runpy.run_path(str(ROOT / "ShadowVendor.py"), run_name="__main__")
    with (Path("output") / f"{Path(filename).stem}-Devices.csv").open() as stream:
        return list(csv.DictReader(stream))

@pytest.mark.parametrize("filename", ["mac-table.txt", "mac-list.txt", "arp-table.txt"])
def test_cli_supported_inputs_counts_and_exports(monkeypatch, filename):
    rows = cli(monkeypatch, filename, "--siem-export", "--analyze-drift", "--site", "SYNTHETIC-LAB", "--environment", "test")
    assert len(rows) == 240
    assert len({row["MAC"] for row in rows}) == 240
    from collections import Counter
    assert Counter(row["Vendor"] or "Unknown" for row in rows) == json.loads((DATA / "expected.json").read_text())["vendor_counts"]
    events = [json.loads(line) for line in Path("output/siem/shadowvendor_siem.json").read_text().splitlines()]
    assert len(events) == 240
    assert {e["site"] for e in events} == {"SYNTHETIC-LAB"}
    assert Path("history/vendor_drift.csv").is_file()
    assert len(list(Path("history").glob("vendor_summary-*.txt"))) == 1
    assert "Plotly.newPlot" in Path("output/vendor_distribution.html").read_text()

def test_api_basic_table_counts(tmp_path):
    result = analyze_file(DATA / "mac-table.txt", offline=True, output_dir=tmp_path / "api-reports")
    assert result["device_count"] == 240
    assert result["vendor_count"] == 5
    assert all(Path(p).is_file() for p in result["output_files"])

def test_api_siem_returned_files_exist(tmp_path):
    result = analyze_file(DATA / "mac-list.txt", offline=True, output_dir=tmp_path / "api-reports", siem_export=True)
    missing = [p for p in result["output_files"] if not Path(p).is_file()]
    assert not missing, f"API advertises files that were not written: {missing}"

def test_offline_miss_does_not_hide_a_later_cache_hit():
    mac = "E0:FE:ED:00:00:01"
    assert OUIManager(offline=True).get_vendor(mac) is None
    cache_path = Path("output/data/oui_cache.json")
    cache = json.loads(cache_path.read_text())
    cache["E0:FE:ED"] = "Newly Seeded Vendor"
    cache_path.write_text(json.dumps(cache))
    assert OUIManager(offline=True).get_vendor(mac) == "Newly Seeded Vendor"

def test_offline_miss_can_retry_online(monkeypatch):
    mac = "E0:FE:ED:00:00:01"
    assert OUIManager(offline=True).get_vendor(mac) is None
    request = Mock(return_value=Mock(status_code=200, text="Recovered Vendor"))
    monkeypatch.setattr(requests, "get", request)
    manager = OUIManager(offline=False)
    assert manager.get_vendor(mac) == "Recovered Vendor"
    assert request.call_count == 1

@pytest.mark.parametrize("filename", ["headerless-mac-table.txt", "headerless-arp-table.txt"])
def test_api_does_not_drop_headerless_data(filename, tmp_path):
    result = analyze_file(DATA / filename, offline=True, output_dir=tmp_path / "api-reports")
    assert result["device_count"] == 3

def test_api_normalizes_case_before_deduplication(tmp_path):
    result = analyze_file(DATA / "case-duplicates.txt", offline=True, output_dir=tmp_path / "api-reports")
    assert result["device_count"] == 1

@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_malformed_addresses_are_rejected(entrypoint, monkeypatch, tmp_path):
    if entrypoint == "cli":
        rows = cli(monkeypatch, "malformed-mac-table.txt")
        macs = [row["MAC"] for row in rows]
    else:
        result = analyze_file(DATA / "malformed-mac-table.txt", offline=True, output_dir=tmp_path / "api-reports")
        macs = list(result["devices"])
    assert len(macs) == 1 and all(re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", mac) for mac in macs), macs

def test_batch_lookup_works_without_optional_progress(monkeypatch):
    manager = OUIManager(offline=False)
    monkeypatch.setattr(manager, "get_vendor", lambda mac: "Mock Lookup Vendor")
    assert manager.batch_lookup_vendors(["E0:FE:ED:00:00:01"]) == {"E0:FE:ED:00:00:01": "Mock Lookup Vendor"}

def test_vendor_text_cannot_end_inline_script(monkeypatch):
    # Harmless sentinel; no external destination or data access.
    marker = "</script><script>window.__shadowvendor_review_marker=1</script>"
    cache_path = Path("output/data/oui_cache.json")
    cache = json.loads(cache_path.read_text())
    cache["00:11:22"] = marker
    cache_path.write_text(json.dumps(cache))
    cli(monkeypatch, "mac-table.txt")
    assert marker not in Path("output/vendor_distribution.html").read_text(), "Unescaped vendor data can terminate the inline script"

def test_oui_file_keys_match_lookup_normalization(tmp_path):
    manuf = tmp_path / "manuf.txt"
    manuf.write_text("E0:FE:ED\tSynthetic Manuf Vendor\n")
    assert OUIManager(oui_file=str(manuf), offline=True).get_vendor("e0:fe:ed:00:00:01") == "Synthetic Manuf Vendor"

def test_html_safe_json_preserves_data_and_script_boundary():
    from html.parser import HTMLParser
    from shadowvendor.utils.vendor_output_handler import _script_json
    data = {"labels": ["A & B", "</ScRiPt><script>window.marker=1</script>", "<b>Vendor</b>", "Line\u2028break"]}
    encoded = _script_json(data)
    assert json.loads(encoded) == data
    class Scripts(HTMLParser):
        count = 0
        def handle_starttag(self, tag, attrs):
            if tag == "script":
                self.count += 1
    parser = Scripts()
    parser.feed("<script>var figure = " + encoded + ";</script>")
    assert parser.count == 1

@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_leading_blank_mac_lists(entrypoint, monkeypatch, tmp_path):
    if entrypoint == "cli":
        assert len(cli(monkeypatch, "leading-blank-mac-list.txt")) == 3
    else:
        result = analyze_file(DATA / "leading-blank-mac-list.txt", offline=True, output_dir=tmp_path / "reports")
        assert result["device_count"] == 3
        assert result["input_type"] == "mac_list"

@pytest.mark.parametrize("value", ["0011.2233.445566", "00:11:22:33:44:GG", "00:11:22:33:44:55/49", "001122334455junk"])
def test_formatters_reject_invalid_addresses(value):
    from shadowvendor.core.netvendor import format_mac_address
    assert format_mac_address(value) is None
    standalone = runpy.run_path(str(ROOT / "ShadowVendor.py"))
    assert standalone["format_mac_address"](value) is None

@pytest.mark.parametrize("directory", ["output", "reports/nested"])
def test_api_routes_every_report_without_chdir(directory, monkeypatch):
    before = Path.cwd()
    def forbid_chdir(*args):
        pytest.fail("Analysis must not change process-wide cwd")
    monkeypatch.setattr(os, "chdir", forbid_chdir)
    result = analyze_file(DATA / "mac-table.txt", offline=True, output_dir=directory, siem_export=True)
    assert Path.cwd() == before
    assert all(Path(p).is_file() for p in result["output_files"])
    assert all(Path(p).is_relative_to(Path(directory) / "output") for p in result["output_files"])

def test_port_report_uses_input_stem_for_non_txt_input(tmp_path):
    source = tmp_path / "switch.log"
    source.write_text((DATA / "mac-table.txt").read_text())
    result = analyze_file(source, offline=True, output_dir=tmp_path / "reports")
    assert all(Path(p).exists() for p in result["output_files"])
    assert any(Path(p).name == "switch-Ports.csv" for p in result["output_files"])

def test_basic_entrypoint_retains_headerless_arp(monkeypatch):
    from shadowvendor.core.netvendor import main
    monkeypatch.setattr(sys, "argv", ["shadowvendor", str(DATA / "headerless-arp-table.txt")])
    main()
    with Path("output/headerless-arp-table-Devices.csv").open() as f:
        assert len(list(csv.DictReader(f))) == 3
