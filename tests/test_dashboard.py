"""Report data, escaping, and no-JavaScript fallbacks (not browser rendering)."""
from collections import Counter, defaultdict
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import pytest

from shadowvendor.utils.vendor_output_handler import create_vendor_distribution


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.scripts = []
        self.ids = []
        self.captions = 0
        self.viewport = False
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "script":
            self.scripts.append(attrs)
        if tag == "caption":
            self.captions += 1
        if tag == "meta" and attrs.get("name") == "viewport":
            self.viewport = attrs["content"] == "width=device-width, initial-scale=1"


def generate(records, filename="switch.txt"):
    devices = {str(i): {"vlan": vlan, "port": "Gi1/0/1"} for i, (vlan, vendor) in enumerate(records)}
    class Vendors:
        def get_vendor(self, mac):
            return records[int(mac)][1]
    create_vendor_distribution(devices, Vendors(), filename)
    html = Path("output/vendor_distribution.html").read_text()
    payload = re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', html, re.S).group(1)
    return html, json.loads(payload)


def test_independent_charts_preserve_inventory_counts():
    records = [("10", "Cisco")] * 3 + [("20", "Dell")] * 2 + [("10", None)]
    html, charts = generate(records)
    document = Document(html)
    assert document.viewport
    assert len(document.ids) == len(set(document.ids))
    assert len(charts) == 5
    assert len({chart["id"] for chart in charts}) == 5
    assert all(chart["id"] in document.ids for chart in charts)
    assert charts[0]["data"][0]["values"] == [3, 2, 1]
    assert charts[1]["data"][0]["x"] == ["VLAN 10", "VLAN 20"]
    assert charts[1]["data"][0]["y"] == [4, 2]
    assert charts[2]["data"][0]["y"] == [2, 1]
    assert charts[3]["data"][0]["z"] == [[3, 0, 1], [0, 2, 0]]
    assert [trace["y"] for trace in charts[4]["data"]] == [[3, 0], [0, 2], [1, 0]]
    # Traces no longer refer to quadrants in a shared plotting area.
    assert all("xaxis" not in trace and "yaxis" not in trace for chart in charts for trace in chart["data"])
    assert document.captions == 5
    assert "<noscript>" in html


def test_large_inventory_and_long_names_keep_full_data():
    names = [f"Long manufacturer name {i} with extra descriptive text" for i in range(14)]
    records = [(str(vlan), name) for vlan in range(20) for name in names]
    html, charts = generate(records)
    assert sum(charts[0]["data"][0]["values"]) == 280
    assert len(charts[0]["data"][0]["labels"]) == 14
    assert len(charts[3]["data"][0]["x"]) == 10
    assert len(charts[4]["data"]) == 5
    assert all(name in html for name in names)
    assert "other vendors are excluded" in html


@pytest.mark.parametrize("counts, outline", [
    ([3, 3, 2, 2, 2], 2),
    ([99, 1], 2),
    ([999, 1], 0),
    ([1] * 1000, 0),
])
def test_small_donut_shares_are_not_covered_by_outlines(counts, outline):
    records = [("10", f"Vendor {i}") for i, count in enumerate(counts) for _ in range(count)]
    html, charts = generate(records)
    pie = charts[0]["data"][0]
    assert pie["marker"]["line"]["width"] == outline
    assert pie["values"] == sorted(counts, reverse=True)
    assert len(pie["labels"]) == len(counts)
    assert len(pie["marker"]["colors"]) == len(counts)
    assert charts[0]["total"] == sum(counts)
    assert pie["hole"] == 0.62
    assert all(f"Vendor {i} ({count:,})" in pie["labels"] for i, count in enumerate(counts))
    assert all(f">Vendor {i}</button>" in html for i in range(len(counts)))


def test_html_data_and_filename_cannot_inject_markup():
    marker = '</script><script>window.unwanted=1</script><img src=x onerror=alert(1)>'
    html, charts = generate([("10", marker)], filename=marker + ".txt")
    document = Document(html)
    assert len(document.scripts) == 3  # JSON, library, controller
    assert marker not in html
    assert "&lt;img" in html
    assert charts[0]["data"][0]["labels"][0] == marker + " (1)"
    assert "<img src=x" not in html


@pytest.mark.parametrize("records", [[], [("N/A", None)]])
def test_empty_and_unassigned_input_remain_readable(records):
    html, charts = generate(records)
    assert 'Known VLANs</dt><dd class="metric-value">0</dd>' in html
    if not records:
        assert "No vendor data available" in html
        assert all(not chart["data"] for chart in charts)
    else:
        assert "Unassigned entries" in html
        assert charts[1]["data"][0]["x"] == ["VLAN N/A"]


def test_theme_text_contrast():
    def luminance(color):
        values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * weight for v, weight in zip(linear, [.2126, .7152, .0722]))
    for background in ["#101b25", "#192b36"]:
        for foreground in ["#f7f3e9", "#bfccd3", "#d9bd8e", "#b9dcd6"]:
            assert (luminance(foreground) + .05) / (luminance(background) + .05) >= 4.5
