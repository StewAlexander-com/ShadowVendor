"""Responsive report presentation; input parsing and export schemas stay separate."""

from html import escape
from importlib.resources import files
import json
from pathlib import Path

PALETTE = ["#b9dcd6", "#d9bd8e", "#8db4d9", "#c3a6d9", "#e4a99b", "#a7c78e",
           "#82c9d2", "#d7b3c5", "#c5c38e", "#a8b1df"]


def script_json(value):
    """Keep values intact without allowing data to end an HTML script element."""
    return json.dumps(value).replace("<", "\\u003c")


def _table(headers, rows, caption):
    headings = "".join(f'<th scope="col">{escape(str(h))}</th>' for h in headers)
    body = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            tag, attributes = ("th", ' scope="row"') if i == 0 else ("td", "")
            cells.append(f'<{tag}{attributes}>{escape(str(cell))}</{tag}>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (f'<div class="table-scroll" tabindex="0" role="region" aria-label="{escape(caption, quote=True)}">'
            f'<table><caption>{escape(caption)}</caption><thead><tr>{headings}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def render_dashboard(fig1, fig2, vendor_counts, vlan_vendor_data, input_file):
    """Split the existing five analyses into independently sized plot containers."""
    vendors = sorted(vendor_counts, key=vendor_counts.get, reverse=True)
    vlans = sorted(vlan_vendor_data, key=lambda value: str(value))
    total = sum(vendor_counts.values())
    colors = {vendor: PALETTE[i % len(PALETTE)] for i, vendor in enumerate(vendors)}
    groups = [[], [], [], []]
    for trace in fig2.to_dict()["data"]:
        trace = dict(trace)
        axis = trace.pop("xaxis", "x")
        trace.pop("yaxis", None)
        groups[int(axis[1:] or "1") - 1].append(trace)
    pie = fig1.to_dict()["data"]
    if pie:
        # A fixed outline can cover narrow wedges entirely, especially at the
        # donut's inner edge. Keep small shares visible without grouping vendors.
        outline_width = 0 if min(pie[0]["values"]) / total < 0.01 else 2
        pie[0].update(textinfo="none", hole=0.62, sort=False,
                      marker={"colors": [colors[v] for v in vendors], "line": {"color": "#192b36", "width": outline_width}})
    if groups[0]:
        groups[0][0]["marker"] = {"color": "#b9dcd6"}
        groups[1][0]["marker"] = {"color": "#d9bd8e"}
        groups[2][0].update(colorscale=[[0, "#223a47"], [0.5, "#5d9994"], [1, "#d9bd8e"]],
                            colorbar={"orientation": "v", "thickness": 10, "len": 0.75,
                                      "tickfont": {"color": "#bfccd3"}, "title": "MACs"})
        for trace in groups[3]:
            trace["marker"] = {"color": colors[trace["name"]]}
    specs = [{"id": "vendor-distribution", "kind": "pie", "data": pie, "total": total}]
    definitions = [
        ("vlan-devices", "bar", "Total devices per VLAN", "Unique parsed MAC addresses in each VLAN.",
         ["VLAN", "Devices"], [[v, sum(vlan_vendor_data[v].values())] for v in vlans]),
        ("vlan-vendors", "bar", "Unique vendors per VLAN", "Vendor labels represented in each VLAN.",
         ["VLAN", "Vendors"], [[v, len(vlan_vendor_data[v])] for v in vlans]),
        ("vlan-distribution", "heatmap", "Vendor distribution per VLAN", "Device counts for the ten most common vendors overall.",
         ["VLAN", *vendors[:10]], [[v, *[vlan_vendor_data[v].get(name, 0) for name in vendors[:10]]] for v in vlans]),
        ("vlan-top-vendors", "stack", "Top vendors per VLAN", "The five most common vendors overall; other vendors are excluded.",
         ["VLAN", *vendors[:5]], [[v, *[vlan_vendor_data[v].get(name, 0) for name in vendors[:5]]] for v in vlans]),
    ]
    cards = []
    for index, (chart_id, kind, title, description, headers, rows) in enumerate(definitions):
        specs.append({"id": chart_id, "kind": kind, "data": groups[index]})
        key = ""
        if kind == "stack":
            key = '<div class="series-key" aria-label="Toggle vendor series">' + "".join(
                f'<button type="button" disabled data-chart="{chart_id}" data-series="{i}" aria-pressed="true">'
                f'<span class="swatch" style="background:{colors[v]}"></span>{escape(v)}</button>'
                for i, v in enumerate(vendors[:5])) + '</div>'
        cards.append(f'''<section class="panel" aria-labelledby="{chart_id}-title">
          <header class="panel-heading"><span class="eyebrow">0{index + 2} / VLAN analysis</span>
            <h3 id="{chart_id}-title">{title}</h3><p>{description}</p></header>
          <div class="plot" id="{chart_id}" role="region" aria-label="{title}; data table follows"></div>{key}
          <details><summary>Read data table</summary>{_table(headers, rows, title)}</details>
        </section>''')
    legend = "".join(
        f'<tr><th scope="row"><button type="button" disabled data-chart="vendor-distribution" data-series="{i}" '
        f'aria-pressed="true"><span class="swatch" style="background:{colors[v]}"></span>{escape(v)}</button></th>'
        f'<td>{vendor_counts[v]:,}</td><td>{vendor_counts[v] / total * 100:.1f}%</td></tr>'
        for i, v in enumerate(vendors))
    vendor_table = (f'<div class="vendor-list table-scroll" tabindex="0" role="region" aria-label="Vendor counts">'
                    '<table><caption>All vendor counts. Select a vendor to toggle its chart slice.</caption>'
                    '<thead><tr><th scope="col">Vendor</th><th scope="col">MACs</th><th scope="col">Share</th></tr></thead>'
                    f'<tbody>{legend}</tbody></table></div>') if vendors else '<p class="empty">No vendor data available.</p>'
    known_vlans = sum(str(v) != "N/A" for v in vlans)
    vlan_note = "Unassigned entries appear as VLAN N/A." if "N/A" in vlans else "VLANs represented in this input."
    css = files(__package__).joinpath("dashboard.css").read_text(encoding="utf-8")
    script = files(__package__).joinpath("dashboard.js").read_text(encoding="utf-8")
    payload = script_json(specs)
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ShadowVendor · Network vendor analysis</title><style>{css}</style></head>
<body><a class="skip" href="#overview">Skip to analysis</a>
<div class="page"><header class="masthead"><a class="brand" href="#overview">ShadowVendor<span>Network visibility</span></a>
<a class="site-link" href="https://www.stewalexander.com/">Stew Alexander <span aria-hidden="true">↗</span></a></header>
<main><header class="intro"><p class="eyebrow">Inventory / Vendor intelligence</p>
<h1>Your network,<br><em>in perspective.</em></h1>
<p class="lead">Vendor distribution and VLAN composition, from one inventory snapshot.</p>
<p class="source">Source <span>{escape(Path(input_file).name)}</span></p></header>
<dl class="metrics" aria-label="Inventory summary">
<div><dt>Unique MAC addresses</dt><dd class="metric-value">{total:,}</dd><dd class="metric-note">Parsed addresses, not verified physical devices.</dd></div>
<div><dt>Vendor labels</dt><dd class="metric-value">{len(vendors):,}</dd><dd class="metric-note">Includes Unknown when a lookup is missing.</dd></div>
<div><dt>Known VLANs</dt><dd class="metric-value">{known_vlans:,}</dd><dd class="metric-note">{vlan_note}</dd></div></dl>
<p class="chart-status" id="chart-status" role="status">Charts are loading. Data tables are available below.</p>
<noscript><p class="notice">JavaScript is disabled. The data tables contain the same counts as the charts.</p></noscript>
<section class="panel overview" id="overview" aria-labelledby="overview-title" tabindex="-1">
<header class="panel-heading"><span class="eyebrow">01 / Vendor overview</span><h2 id="overview-title">Vendor distribution</h2>
<p>Share of all parsed MAC addresses. Hover over a slice for VLAN details.</p></header>
<div class="overview-grid"><div class="plot" id="vendor-distribution" role="region" aria-label="Vendor distribution chart; full counts alongside"></div>{vendor_table}</div></section>
<div class="section-heading" id="vlan-analysis"><h2>A closer look at your VLANs.</h2><p>Four views of the same inventory.</p></div>
<div class="analysis-grid">{''.join(cards)}</div></main>
<footer><strong>ShadowVendor</strong><p>Counts describe this input only. Use the device CSV to inspect individual records.</p>
<a href="https://www.stewalexander.com/">Independent thinking. Practical work.</a></footer></div>
<script id="chart-data" type="application/json">{payload}</script>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script><script>{script}</script></body></html>'''
