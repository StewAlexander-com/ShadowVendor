<picture>
  <source media="(max-width: 600px)" srcset="docs/readme-assets/hero-mobile.svg">
  <img src="docs/readme-assets/hero.svg" alt="ShadowVendor — Make the inventory visible. MAC and ARP exports become vendor reports, VLAN views, and evidence for change reviews." width="1000">
</picture>

# ShadowVendor

**Turn network exports into a clearer picture of your device vendors.**

ShadowVendor reads saved MAC address tables, ARP tables, and MAC lists. It identifies vendors from address prefixes and produces interactive HTML charts, CSV reports, and timestamped summaries. Use those outputs to review a change window, investigate an unfamiliar vendor, or feed your SIEM.

[Try the sample](#quick-start) · [See the output](#see-the-output) · [Data boundaries](#what-stays-local) · [Documentation](#go-further)

**Scope:** analysis of saved text files. ShadowVendor does not scan your network or connect to switches. A vendor match is a clue about an address prefix, not proof of device identity, ownership, or compromise.

## From an export to evidence

<picture>
  <source media="(max-width: 600px)" srcset="docs/readme-assets/workflow-mobile.svg">
  <img src="docs/readme-assets/workflow.svg" alt="Export: save a MAC table, ARP table, or MAC list. Enrich: normalize MAC addresses and look up vendor prefixes. Review: inspect charts and CSVs, compare summaries, or ingest SIEM events." width="1000">
</picture>

| Your question | Where to look |
| --- | --- |
| Which vendors appear in this export? | Vendor distribution chart and device CSV |
| How are those entries spread across VLANs and ports? | VLAN charts and, for MAC tables, the port report |
| Has the vendor mix changed? | Archived summaries and the drift CSV |
| How can I correlate this with other events? | CSV/JSONL exports tagged with site and environment |

Drift shows changes in aggregate vendor percentages. Alert rules, collection schedules, and device-level comparisons belong in your surrounding workflow or SIEM.

## Quick start

Use **Python 3.11 or newer** for this walkthrough. Run these commands from a terminal on macOS or Linux:

```bash
git clone https://github.com/StewAlexander-com/ShadowVendor.git
cd ShadowVendor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Seed the working cache from the repository’s bundled snapshot. This first-use step keeps the sample run offline and preserves any existing cache:

```bash
mkdir -p output/data
cp -n shadowvendor/data/oui_cache.json output/data/oui_cache.json
python ShadowVendor.py --offline docs/examples/mac-table.txt
```

Open **`output/vendor_distribution.html`** in your browser. With the bundled cache, the synthetic sample produces **12 unique MAC entries, 5 vendor labels, and 4 VLANs**. The included addresses are demonstration data, not a captured network inventory.

**Two separate network boundaries:** dependency installation needs internet access; `--offline` disables vendor lookup requests during analysis. Opening the generated dashboard still loads Plotly from a CDN. CSV and text reports remain usable without that browser dependency.

<details>
<summary><strong>Windows PowerShell setup</strong></summary>

Use Python 3.11+ and run the environment’s interpreter directly; no activation-policy change is needed.

```powershell
git clone https://github.com/StewAlexander-com/ShadowVendor.git
cd ShadowVendor
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force output/data | Out-Null
if (!(Test-Path output/data/oui_cache.json)) {
    Copy-Item shadowvendor/data/oui_cache.json output/data/oui_cache.json
}
.\.venv\Scripts\python.exe ShadowVendor.py --offline docs/examples/mac-table.txt
```

Open `output/vendor_distribution.html` in your browser. The same CDN requirement applies.

</details>

## See the output

The responsive dashboard puts the vendor overview and four VLAN analyses in separate panels, with readable typography, a dark theme, and data tables alongside the charts. Panels adapt to window width and height; vendor controls let you hide or show slices and stacked series.

These screenshots show actual generated output from the [48-address simulated VLAN inventory](docs/examples/vlan-review.txt), using the bundled vendor cache. They contain **48 unique MAC addresses, 5 vendor labels, and 4 VLANs**. The records are demonstration data, not a production network capture. Chart values and tables are checked against independently counted source records in the [accuracy tests](tests/test_dashboard_accuracy.py).

<a href="docs/readme-assets/vendor-overview.png"><img src="docs/readme-assets/vendor-overview.png" alt="Themed vendor overview for 48 simulated MAC addresses: Cisco 14, Dell 12, VMware 10, Apple 8, and Intel 4." width="1000"></a>

Cisco accounts for 14 addresses (29.2%), Dell 12 (25.0%), VMware 10 (20.8%), Apple 8 (16.7%), and Intel 4 (8.3%). The vendor list scrolls; Intel's row is below the visible portion of this capture. Percentages are rounded independently.

<details>
<summary><strong>View the inventory summary</strong></summary>

<a href="docs/readme-assets/dashboard-summary.png"><img src="docs/readme-assets/dashboard-summary.png" alt="Dashboard summary: 48 unique MAC addresses, 5 vendor labels, and 4 known VLANs from vlan-review.txt." width="1000"></a>

Counts describe parsed MAC addresses, not verified physical devices. Missing vendor lookups are included under the label `Unknown`.

</details>

### Look closer at VLANs

**Where are entries concentrated?** VLANs 10, 20, 30, and 40 contain **12, 8, 18, and 10** unique MAC addresses respectively. The visible hover detail confirms VLAN 10's count of 12.

<a href="docs/readme-assets/vlan-mac-counts.png"><img src="docs/readme-assets/vlan-mac-counts.png" alt="Themed MAC-count chart: VLAN 10 has 12 addresses, VLAN 20 has 8, VLAN 30 has 18, and VLAN 40 has 10." width="800"></a>

**What makes up each total?** The stacked chart shows the vendor mix. For example, VLAN 30 contains four Cisco, four Dell, four VMware, and six Apple addresses. This view includes the five most common vendors overall; other vendors are excluded when an inventory has more than five labels.

<a href="docs/readme-assets/vlan-vendor-stack.png"><img src="docs/readme-assets/vlan-vendor-stack.png" alt="Themed stacked vendor chart with VLAN totals 12, 8, 18, and 10. Colors identify Cisco, Dell, VMware, Apple, and Intel." width="800"></a>

<details>
<summary><strong>Explore vendor diversity and the heatmap</strong></summary>

**How varied is each VLAN?** The same export contains **3, 2, 4, and 2** vendor labels across VLANs 10, 20, 30, and 40. Diversity adds context; it is not a security score.

<a href="docs/readme-assets/vlan-vendor-labels.png"><img src="docs/readme-assets/vlan-vendor-labels.png" alt="Themed vendor-diversity chart showing 3, 2, 4, and 2 labels; the tooltip confirms four vendors in VLAN 30." width="800"></a>

**Which vendor appears where?** The heatmap shows counts for the ten most common vendors overall. Dark navy represents zero and gold represents six in this example. The visible tooltip reads **VLAN 10, Apple, 0**; Intel has four addresses in the adjacent cell. Read the tooltip's vendor label to identify the selected cell.

<a href="docs/readme-assets/vlan-vendor-heatmap.png"><img src="docs/readme-assets/vlan-vendor-heatmap.png" alt="Themed vendor-by-VLAN heatmap with Cisco, Dell, VMware, Apple, and Intel columns. The visible tooltip reads VLAN 10, Apple, Devices: 0." width="800"></a>

Each chart scales its own axis. Compare values and units rather than bar heights across different charts. The smaller quickstart example has three addresses and two vendor labels in every VLAN, so its bars are correctly equal within each of those views.

</details>

<details>
<summary><strong>Reproduce these screenshots' data</strong></summary>

After the quick-start installation and bundled-cache setup:

```bash
python ShadowVendor.py --offline docs/examples/vlan-review.txt
```

Open `output/vendor_distribution.html`. This replaces the previous sample's dashboard and summary. The HTML supports hover details, vendor toggles, zoom/reset, and PNG export; the README images are static. Expand **Read data table** to inspect the underlying values. Embedded tables remain readable when JavaScript or the chart CDN is unavailable.

VLAN and port detail depends on what the input contains and the parser recognizes; missing fields appear as `N/A`. See [image provenance](docs/readme-assets/README.md) for the source and verified counts.

</details>

| Report | What it contains |
| --- | --- |
| Device CSV | Unique MAC entries with vendor, VLAN, and port |
| Port CSV | Port grouping for MAC-table inputs |
| HTML dashboard | Vendor and VLAN charts |
| Text summary | Vendor counts and percentages |
| History archive | Timestamped summary and metadata, saved by default |

<details>
<summary><strong>Where the sample files are saved</strong></summary>

```text
output/
├── mac-table-Devices.csv
├── mac-table-Ports.csv
├── vendor_distribution.html
└── vendor_summary.txt
history/
└── timestamped summaries
    and companion metadata
```

Device and port filenames use the input filename without its extension. See the [usage reference](docs/usage.md) for optional exports and archive naming.

</details>

Shared output filenames are overwritten on later runs; archive reports you need to retain. Duplicate MAC addresses collapse to one entry, so counts describe unique addresses in the supplied file.

## What stays local

<picture>
  <source media="(max-width: 600px)" srcset="docs/readme-assets/data-boundaries-mobile.svg">
  <img src="docs/readme-assets/data-boundaries.svg" alt="Local analysis reads a saved export, consults the working cache, and writes reports. In online mode a cache miss may send only the three-byte OUI prefix to MACVendors or MACLookup. Offline mode blocks that lookup. Separately, opening the HTML report loads Plotly from a CDN; CSV and text reports need no browser script." width="1000">
</picture>

Input files and full MAC addresses are processed locally. In default online mode, uncached prefixes may be sent to **MACVendors** or **MACLookup**. Use `--offline` when external vendor lookups are unwanted. An uncached prefix becomes `Unknown`.

The script reads its working cache from `output/data/oui_cache.json`; it does not automatically load the bundled snapshot. Cache age and randomized or spoofed MAC addresses limit what vendor labels can establish. Treat generated reports as network inventory data when sharing them.

## Put it to work

Replace the sample path with your own saved export. Use **`ShadowVendor.py` for these flags**; `shadowvendor` and `python -m shadowvendor` are basic file-only entry points.

**Review a change window** — keep comparable exports from the same scope together:

```bash
python ShadowVendor.py --offline \
  --history-dir history/DC1 --analyze-drift \
  --site DC1 --change-ticket CHG-12345 my-switch.txt
```

This adds the latest summary to the archive and writes `history/DC1/vendor_drift.csv`. Two or more comparable snapshots make a trend meaningful; a percentage shift alone does not explain its cause.

**Prepare SIEM ingestion** — export locally, then configure your collector separately:

```bash
python ShadowVendor.py --offline --siem-export \
  --site DC1 --environment prod my-switch.txt
```

Read `output/siem/shadowvendor_siem.csv` or `output/siem/shadowvendor_siem.json`. The `.json` file contains **JSON Lines**, one event per line. Exporting does not send events to a SIEM.

## Go further

| Next step | Guide |
| --- | --- |
| Flags, input examples, cache behavior, output details | [Usage reference](docs/usage.md) |
| Recurring jobs and configuration formats | [Configuration](CONFIG.md) |
| SIEM ingestion and operational patterns | [Advanced guide](ADVANCED.md) |
| Architecture and the Python API | [Technical tutorial](TUTORIAL.md) · [API source](shadowvendor/api.py) |
| Execution paths and existing tests | [Execution paths](EXECUTION_PATHS.md) · [Test coverage](TEST_COVERAGE.md) |

The [usage reference](docs/usage.md) records current implementation limits where older guides describe broader behavior.

## Contribute or get help

Open an [issue](https://github.com/StewAlexander-com/ShadowVendor/issues) with the command, Python version, and a sanitized input example. For a code contribution, include a focused regression test and run `python -m pytest tests` after installing `requirements-dev.txt`. See [SECURITY.md](SECURITY.md) for private vulnerability reporting.

## License and author

[MIT License](LICENSE) · Copyright © 2024–2026 Stewart Alexander.

Created by [Stewart Alexander](https://www.stewalexander.com/) — independent thinking, practical work.
