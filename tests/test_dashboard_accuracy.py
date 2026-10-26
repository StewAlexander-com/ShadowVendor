"""Hand-counted chart oracles, from documented input through exported HTML.

These check serialized chart/hover data and HTML tables, not browser rendering.
"""
from collections import Counter
import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import runpy
import sys

import pytest

from shadowvendor import analyze_file
from shadowvendor.utils.vendor_output_handler import create_vendor_distribution

ROOT = Path(__file__).resolve().parents[1]
# Independently counted from the two documented switch-table examples.
EXAMPLES = {
    "mac-table.txt": {
        "10": {"Cisco": 2, "Intel": 1},
        "20": {"Cisco": 1, "Dell": 2},
        "30": {"Dell": 1, "Apple": 2},
        "40": {"VMware": 2, "Intel": 1},
    },
    "vlan-review.txt": {
        "10": {"Cisco": 6, "Dell": 2, "Intel": 4},
        "20": {"Dell": 6, "Apple": 2},
        "30": {"Cisco": 4, "Dell": 4, "Apple": 6, "VMware": 4},
        "40": {"Cisco": 4, "VMware": 6},
    },
}
PREFIXES = {"001b54": "Cisco", "001aa0": "Dell", "001b63": "Apple",
            "000c29": "VMware", "001b21": "Intel"}


class Tables(HTMLParser):
    """Read actual rendered-text inputs, including text inside legend buttons."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.cell = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self.tables[-1].append([])
        elif tag in ("th", "td"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td"):
            self.tables[-1][-1].append("".join(self.cell).strip())
            self.cell = None


def assert_report(html, expected):
    """Compare every chart cell and table cell with an external count oracle."""
    payload = re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', html, re.S)
    charts = json.loads(payload.group(1))
    pie, devices, diversity, heatmap, stack = [chart["data"] for chart in charts]
    overall = Counter()
    for counts in expected.values():
        overall.update(counts)
    total = sum(overall.values())
    vendors = [label.rsplit(" (", 1)[0] for label in pie[0]["labels"]]
    assert dict(zip(vendors, pie[0]["values"])) == dict(overall)
    assert pie[0]["values"] == sorted(overall.values(), reverse=True)
    assert charts[0]["total"] == total
    assert f'Unique MAC addresses</dt><dd class="metric-value">{total:,}</dd>' in html
    assert f'Vendor labels</dt><dd class="metric-value">{len(overall)}</dd>' in html
    assert f'Known VLANs</dt><dd class="metric-value">{len(set(expected) - {"N/A"})}</dd>' in html
    for vendor, hover in zip(vendors, pie[0]["customdata"]):
        present = {v: counts[vendor] for v, counts in expected.items() if counts.get(vendor)}
        assert f"Device Count: {overall[vendor]:,} devices" in hover
        assert f"Percentage: {overall[vendor] / total * 100:.1f}%" in hover
        assert f"Present in {len(present)} VLANs" in hover
        assert f"Max Devices in a VLAN: {max(present.values())}" in hover
        # Ties may choose either equally common VLAN; do not encode insertion order.
        top_vlan = re.search(r"Most Common VLAN: (.*?)<br>", hover).group(1)
        assert present[top_vlan] == max(present.values())
    vlans = [label.removeprefix("VLAN ") for label in devices[0]["x"]]
    assert set(vlans) == set(expected)
    assert devices[0]["y"] == [sum(expected[v].values()) for v in vlans]
    assert "%{x}" in devices[0]["hovertemplate"] and "%{y}" in devices[0]["hovertemplate"]
    assert diversity[0]["x"] == devices[0]["x"]
    assert diversity[0]["y"] == [len(expected[v]) for v in vlans]
    assert "%{x}" in diversity[0]["hovertemplate"] and "%{y}" in diversity[0]["hovertemplate"]
    assert heatmap[0]["x"] == vendors[:10]
    assert heatmap[0]["y"] == devices[0]["x"]
    assert heatmap[0]["z"] == [[expected[v].get(name, 0) for name in vendors[:10]] for v in vlans]
    assert [trace["name"] for trace in stack] == vendors[:5]
    for trace in stack:
        assert trace["x"] == devices[0]["x"]
        assert trace["y"] == [expected[v].get(trace["name"], 0) for v in vlans]
    # Hover coordinates must resolve the same matrix/series values as the plot.
    assert "Vendor: %{x}" in heatmap[0]["hovertemplate"]
    assert "%{y}" in heatmap[0]["hovertemplate"] and "%{z}" in heatmap[0]["hovertemplate"]
    assert all("%{data.name}" in trace["hovertemplate"] and "%{y}" in trace["hovertemplate"] for trace in stack)
    tables = Tables(html).tables
    assert len(tables) == 5
    assert tables[0][1:] == [[v, f"{overall[v]:,}", f"{overall[v] / total * 100:.1f}%"] for v in vendors]
    assert tables[1][1:] == [[v, str(sum(expected[v].values()))] for v in vlans]
    assert tables[2][1:] == [[v, str(len(expected[v]))] for v in vlans]
    for table, limit in [(tables[3], 10), (tables[4], 5)]:
        assert table[0] == ["VLAN", *vendors[:limit]]
        assert table[1:] == [[v, *[str(expected[v].get(name, 0)) for name in vendors[:limit]]] for v in vlans]


@pytest.mark.parametrize("filename", EXAMPLES)
@pytest.mark.parametrize("entrypoint", ["api", "cli"])
def test_documented_inputs_match_hand_counted_charts_and_exports(filename, entrypoint, monkeypatch):
    from shadowvendor.config import ShadowVendorConfig
    monkeypatch.setattr(ShadowVendorConfig, "_find_config_file", lambda self: None)
    source = ROOT / "docs" / "examples" / filename
    expected = EXAMPLES[filename]
    # Follow the README's offline quickstart, including its bundled cache copy.
    cache = Path("output/data/oui_cache.json")
    cache.parent.mkdir(parents=True)
    cache.write_bytes((ROOT / "shadowvendor/data/oui_cache.json").read_bytes())
    # A simple independent reader checks that the hand-counted oracle still
    # describes the raw fixture, without using ShadowVendor's parsing helpers.
    raw = {}
    for line in source.read_text().splitlines()[2:]:
        vlan, mac, _, port = line.split()
        compact = mac.replace(".", "").lower()
        assert compact not in raw
        raw[compact] = (vlan, PREFIXES[compact[:6]], port)
    assert Counter((v, name) for v, name, _ in raw.values()) == Counter(
        {(v, name): count for v, counts in expected.items() for name, count in counts.items()})
    if entrypoint == "api":
        analyze_file(source, offline=True, output_dir=".")
    else:
        monkeypatch.setattr(sys, "argv", ["ShadowVendor.py", "--offline", str(source)])
        runpy.run_path(str(ROOT / "ShadowVendor.py"), run_name="__main__")
    with Path(f"output/{source.stem}-Devices.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(raw)
    assert {row["MAC"].replace(":", "").lower(): (row["VLAN"], row["Vendor"], row["Port"]) for row in rows} == raw
    assert f"Total Devices: {len(raw)}" in Path("output/vendor_summary.txt").read_text()
    assert_report(Path("output/vendor_distribution.html").read_text(), expected)


def test_top_vendor_limits_do_not_change_totals_or_hide_unknown_counts():
    # Twelve unequal vendor totals exercise truncation and a vendor appearing
    # only on an unassigned VLAN. Neither chart may silently normalize counts.
    expected = {"10": {f"Vendor {i}": 12 - i for i in range(11)},
                "20": {"Vendor 0": 3, "Vendor 10": 2}, "N/A": {"Unknown": 1}}
    records = [(vlan, vendor) for vlan, counts in expected.items()
               for vendor, count in counts.items() for _ in range(count)]
    devices = {str(i): {"vlan": v} for i, (v, _) in enumerate(records)}
    class Vendors:
        def get_vendor(self, mac):
            name = records[int(mac)][1]
            return None if name == "Unknown" else name
    create_vendor_distribution(devices, Vendors(), "uneven.txt")
    assert_report(Path("output/vendor_distribution.html").read_text(), expected)
