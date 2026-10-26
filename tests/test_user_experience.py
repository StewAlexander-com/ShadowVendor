"""User-visible acceptance checks for report integrity and CLI feedback."""
import csv
import json
from datetime import datetime
from pathlib import Path
import sys

import pytest

import ShadowVendor as script


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 26, 12, 0, 0, tzinfo=tz)


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    from shadowvendor.config import ShadowVendorConfig
    monkeypatch.setattr(ShadowVendorConfig, "_find_config_file", lambda self: None)


def invoke(monkeypatch, text, *flags, name="switch.txt"):
    Path(name).write_text(text, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["ShadowVendor.py", "--offline", *flags, name])
    script.main()
    with (Path("output") / f"{Path(name).stem}-Devices.csv").open() as stream:
        return list(csv.DictReader(stream))


def test_unknown_vendor_agrees_across_reports(monkeypatch):
    rows = invoke(monkeypatch, "e0:fe:ed:00:00:01\n", "--siem-export")
    assert rows[0]["Vendor"] == "Unknown"
    assert "Unknown" in Path("output/vendor_summary.txt").read_text()
    events = [json.loads(line) for line in Path("output/siem/shadowvendor_siem.json").read_text().splitlines()]
    assert events[0]["vendor"] == "Unknown"


@pytest.mark.parametrize("text,headers", [
    ("0011.2233.4455\nbad-row\n00:11:22:33:44:55\n00:11:22:33:44:66\n", 0),
    ("Vlan Mac Address Type Ports\n---- ----------- ---- -----\n"
     "10 0011.2233.4455 DYNAMIC Gi1/0/1\n10 invalid DYNAMIC Gi1/0/2\n"
     "20 00:11:22:33:44:55 DYNAMIC Gi1/0/3\n20 0011.2233.4466 DYNAMIC Gi1/0/4\n", 2),
    ("Protocol Address Age (min) Hardware Addr Type Interface\n"
     "Internet 192.0.2.1 - 0011.2233.4455 ARPA Vlan10\n"
     "Internet 192.0.2.2 - invalid ARPA Vlan10\n"
     "Internet 192.0.2.3 - 00:11:22:33:44:55 ARPA Vlan20\n"
     "Internet 192.0.2.4 - 0011.2233.4466 ARPA Vlan20\n", 1),
])
def test_counts_explain_duplicates_and_rejections(monkeypatch, capsys, text, headers):
    rows = invoke(monkeypatch, text)
    output = capsys.readouterr().out
    assert len(rows) == 2
    assert "Found 3 MAC addresses (2 unique, 1 duplicate)" in output
    assert "Skipped 1 invalid data row" in output
    if headers:
        assert f"Ignored {headers} header/separator rows" in output
    # Existing last-entry-wins behavior remains unchanged.
    if headers:
        assert rows[0]["VLAN"] == "20"


@pytest.mark.parametrize("text", [
    "\n0011.2233.4455\n\n",
    "VLAN ID MAC Address Type Ports\n---- ----------- ---- -----\n10 0011.2233.4455 DYNAMIC Gi1/0/1\n",
    "Protocol Address Age (min) Hardware Addr Type Interface\nInternet 192.0.2.1 - 0011.2233.4455 ARPA Vlan10\n",
])
def test_clean_input_has_no_invalid_row_warning(monkeypatch, capsys, text):
    assert len(invoke(monkeypatch, text)) == 1
    output = capsys.readouterr().out
    assert "1 unique, 0 duplicates" in output
    assert "invalid data" not in output


def test_accounting_includes_invalid_protocol_rows(monkeypatch, capsys):
    monkeypatch.setenv("SHADOWVENDOR_LOG", "1")
    invoke(monkeypatch, "Protocol Address Age (min) Hardware Addr Type Interface\n"
           "Protocol garbage\nInternet 192.0.2.1 - 0011.2233.4455 ARPA Vlan10\n")
    assert "Skipped 1 invalid data row" in capsys.readouterr().out
    events = [json.loads(line) for line in Path("output/shadowvendor_runtime.log").read_text().splitlines()]
    stats = next(event["event_data"] for event in events if event["event_type"] == "processing_end")
    assert stats["lines_processed"] == stats["mac_addresses_found"] + stats["invalid_data_rows"] + stats["header_separator_rows"]


def test_completed_paths_include_optional_outputs(monkeypatch, capsys):
    invoke(monkeypatch, "10 0011.2233.4455 DYNAMIC Gi1/0/1\n",
           "--siem-export", "--analyze-drift", "--history-dir", "history [lab]",
           name="switch [lab].txt")
    output = capsys.readouterr().out
    assert "Files written this run:" in output
    listed = output.split("Files written this run:", 1)[1]
    for path in Path("output").rglob("*"):
        if path.is_file() and "data" not in path.parts:
            assert str(path) in listed
    for path in Path("history [lab]").iterdir():
        assert str(path) in listed


def test_output_list_does_not_advertise_stale_optional_files(monkeypatch, capsys):
    invoke(monkeypatch, "10 0011.2233.4455 DYNAMIC Gi1/0/1\n", "--siem-export", "--analyze-drift")
    capsys.readouterr()
    invoke(monkeypatch, "0011.2233.4455\n")
    output = capsys.readouterr().out.split("Files written this run:", 1)[1]
    assert "switch-Devices.csv" in output
    assert "-Ports.csv" not in output
    assert "siem" not in output
    assert "vendor_drift.csv" not in output
    assert Path("output/siem/shadowvendor_siem.json").is_file()


def test_partial_write_failure_has_an_honest_notice(monkeypatch, capsys):
    def fail_chart(*args, **kwargs):
        Path("output/vendor_distribution.html").write_text("partial")
        raise OSError("simulated full disk")
    monkeypatch.setattr(script, "create_vendor_distribution", fail_chart)
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, "0011.2233.4455\n")
    assert exc.value.code == 1
    assert Path("output/switch-Devices.csv").is_file()
    output = capsys.readouterr().out
    assert "simulated full disk" in output
    assert "Reports may be partial or from an earlier run" in output
    assert "No new reports were generated" not in output
    assert "Files written this run:" not in output


def test_archive_warning_does_not_list_an_unwritten_snapshot(monkeypatch, capsys):
    def fail_archive(*args, **kwargs):
        raise OSError("simulated archive failure")
    monkeypatch.setattr(script, "archive_vendor_summary", fail_archive)
    invoke(monkeypatch, "0011.2233.4455\n")
    output = capsys.readouterr().out
    assert "Could not archive" in output
    assert "history" not in output.split("Files written this run:", 1)[1]


@pytest.mark.parametrize("name,content", [("missing.txt", None), ("empty.txt", b""), ("binary.txt", b"\xff\xfe")])
def test_early_failures_explain_freshness(monkeypatch, capsys, name, content):
    if content is not None:
        Path(name).write_bytes(content)
    monkeypatch.setattr(sys, "argv", ["ShadowVendor.py", "--offline", name])
    with pytest.raises(SystemExit) as exc:
        script.main()
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "No new reports were generated" in output
    assert "Traceback" not in output


def test_help_is_not_reported_as_a_failed_run(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ShadowVendor.py", "--help"])
    with pytest.raises(SystemExit) as exc:
        script.main()
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "earlier run" not in output
    assert "Files written this run:" not in output


def test_invalid_rerun_preserves_reports_and_explains_freshness(monkeypatch, capsys):
    invoke(monkeypatch, "0011.2233.4455\n")
    original = Path("output/vendor_distribution.html").read_bytes()
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, "not an inventory\n")
    assert exc.value.code == 1
    assert Path("output/vendor_distribution.html").read_bytes() == original
    output = capsys.readouterr().out
    assert "No new reports were generated" in output
    assert "earlier run" in output
    assert "Files written this run:" not in output


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
def test_same_second_runs_preserve_history_and_drift_order(monkeypatch, entrypoint):
    from shadowvendor.utils import history
    from shadowvendor import analyze_file
    from shadowvendor.utils.drift_analysis import load_snapshots_from_directory
    monkeypatch.setattr(history, "datetime", FrozenDatetime)
    for i in range(12):
        text = "0011.2233.4455\n" + ("0011.2233.4466\n" if i else "")
        if entrypoint == "cli":
            invoke(monkeypatch, text, "--change-ticket", f"CHG-{i}", "--analyze-drift")
        else:
            Path("switch.txt").write_text(text)
            analyze_file("switch.txt", offline=True, history_dir="history", change_ticket=f"CHG-{i}", analyze_drift_flag=True)
    snapshots = load_snapshots_from_directory(Path("history"))
    assert len(snapshots) == 12
    assert snapshots[0].label == "vendor_summary-20261026-120000"
    assert [s.change_ticket_id for s in snapshots] == [f"CHG-{i}" for i in range(12)]
    assert snapshots[0].vendors["Unknown"][0] == 1
    assert snapshots[-1].vendors["Unknown"][0] == 2
    with Path("history/vendor_drift.csv").open() as stream:
        drift = list(csv.reader(stream))
    assert drift[3][1:] == [f"CHG-{i}" for i in range(12)]


def test_concurrent_archive_callers_keep_pairs(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from shadowvendor.utils import history
    monkeypatch.setattr(history, "datetime", FrozenDatetime)
    for i in range(16):
        Path(f"summary-{i}.txt").write_text(f"summary {i}")
    def archive(i):
        return history.archive_vendor_summary(f"summary-{i}.txt", "history", change_ticket=f"CHG-{i}")
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(archive, range(16)))
    assert len({pair[0] for pair in paths}) == 16
    for i, (summary, metadata) in enumerate(paths):
        assert summary.read_text() == f"summary {i}"
        assert json.loads(metadata.read_text())["change_ticket_id"] == f"CHG-{i}"


def test_orphan_metadata_is_not_replaced(monkeypatch):
    from shadowvendor.utils import history
    monkeypatch.setattr(history, "datetime", FrozenDatetime)
    Path("history").mkdir()
    orphan = Path("history/vendor_summary-20261026-120000.metadata.json")
    orphan.write_text('{"change_ticket_id":"KEEP"}')
    Path("summary.txt").write_text("new summary")
    summary, metadata = history.archive_vendor_summary("summary.txt", "history")
    assert summary.stem.endswith("-000001")
    assert orphan.read_text() == '{"change_ticket_id":"KEEP"}'
    assert not orphan.with_name("vendor_summary-20261026-120000.txt").exists()
    assert metadata.exists()


def test_archive_failure_cleans_only_its_own_files(monkeypatch):
    from shadowvendor.utils import history
    monkeypatch.setattr(history, "datetime", FrozenDatetime)
    Path("summary.txt").write_text("original")
    original = history.archive_vendor_summary("summary.txt", "history", change_ticket="KEEP")
    saved = [p.read_bytes() for p in original]
    actual_open = Path.open
    def fail_metadata(path, *args, **kwargs):
        if path.name.endswith("-000001.metadata.json"):
            raise PermissionError("simulated metadata denial")
        return actual_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_metadata)
    with pytest.raises(PermissionError, match="simulated"):
        history.archive_vendor_summary("summary.txt", "history")
    assert [p.read_bytes() for p in original] == saved
    assert len(list(Path("history").iterdir())) == 2
