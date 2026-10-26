# ShadowVendor usage reference

[← Back to the README](../README.md)

This reference describes the repository’s standalone `ShadowVendor.py` workflow. Examples assume you are in the repository root with dependencies installed. The README recommends Python 3.11+ for new installations. Package metadata consistently declares Python 3.9+; CI covers 3.9, 3.12, and 3.14 on Linux, plus 3.12 on Windows.

## Choose an entry point

| Entry point | Behavior |
| --- | --- |
| `python ShadowVendor.py INPUT` | Full CLI: offline mode, history, drift, SIEM export, configuration |
| `shadowvendor INPUT` or `python -m shadowvendor INPUT` | Basic analysis; no advanced CLI flags |
| `from shadowvendor import analyze_file` | Python API with keyword options; inspect its returned paths |

Install the package with `python -m pip install -e .` if you need the `shadowvendor` command. The README’s direct-script walkthrough only needs `requirements.txt`.

API standard reports remain under `<output_dir>/output/` for compatibility. API SIEM exports now live alongside them in `<output_dir>/output/siem/`, and returned paths identify the files actually written. Analysis does not change the process working directory. CLI report paths remain `output/`. Both paths use the same MAC normalization; input validation rejects malformed addresses before lookup.

## Input shapes

Use UTF-8 text. The script detects the shape from the first nonblank lines. Leading blanks are accepted, and headerless MAC/ARP tables retain their first records. Remove switch prompts or unrelated preambles before the data. The included [synthetic MAC table](examples/mac-table.txt) is a reproducible example.

**MAC list** — one address per line, using colon, hyphen, dotted, or compact notation:

```text
00:1B:54:00:00:01
00-1A-A0-00-00-01
001b.6300.0001
000c29000001
```

**MAC table** — VLAN first, MAC second, port last:

```text
Vlan    Mac Address       Type        Ports
----    -----------       ----        -----
10      001b.5400.0001     DYNAMIC     Gi1/0/1
20      001a.a000.0001     DYNAMIC     Gi1/0/2
```

**ARP table** — the script recognizes Cisco-style `Protocol` / `Internet` rows:

```text
Protocol  Address       Age (min)  Hardware Addr   Type  Interface
Internet  192.0.2.1      -          001b.5400.0001  ARPA  Vlan10
```

A matching layout matters more than the switch brand. Port extraction in the standalone script recognizes `Gi`, `Fa`, `Te`, `Eth`, and integer port labels. Other labels can become `N/A`, even if the MAC and VLAN are parsed. Confirm the device CSV before relying on a port report. The tool does not validate an entire switch export against every vendor’s command syntax.

Repeated MAC addresses overwrite their earlier entry; a multi-VLAN or multi-port appearance is not retained as separate observations. Counts therefore mean unique parsed MAC addresses, not an authenticated count of physical devices.

The standalone CLI distinguishes accepted MAC entries, unique addresses, and duplicates in its processing summary. It counts recognized table headings/separators separately and warns when data rows are rejected. Check that warning and the device CSV before treating a partial input as a complete inventory.

## CLI options

Run `python ShadowVendor.py --help` for the installed script’s help.

| Option | Effect |
| --- | --- |
| `--offline` | Cache-only vendor lookup; missing prefixes become `Unknown` |
| `--history-dir DIR` | Summary archive location; defaults to `history` |
| `--analyze-drift` | Writes `vendor_drift.csv` from archived summaries |
| `--site SITE` | Site tag for SIEM events and history metadata |
| `--environment ENV` | Environment tag for SIEM events |
| `--change-ticket ID` | Change/incident reference in history metadata |
| `--siem-export` | Writes CSV and JSONL files to `output/siem/` |

The default history archive is created on successful standalone runs, even without `--analyze-drift`. Its files are named `vendor_summary-YYYYMMDD-HHMMSS.txt` and a matching `.metadata.json`. A later run in the same second adds `-000001`, `-000002`, and so on before the extension, preserving earlier summaries and their metadata. Drift reads the base snapshot before its numbered siblings. The Python API uses the same archive behavior. Metadata includes `run_timestamp`, `site`, and `change_ticket_id`. Filenames use local time; metadata timestamps are UTC. Archive names are reserved exclusively, but concurrent analyses still need separate working/output directories because the current dashboard, summary, CSVs, and cache use shared filenames.

Drift compares vendor percentages across saved summaries; it is not an alert engine or a per-device change detector. Separate history folders by site and collection scope. The CSV includes metadata rows followed by vendor percentage rows, rather than one normalized event per row.

## Cache and network behavior

The script loads `output/data/oui_cache.json` relative to the current working directory. The repository also includes `shadowvendor/data/oui_cache.json`, but the default constructor does not load that file automatically. The README copies it into place without replacing an existing working cache.

Online mode consults the cache, then may query `api.macvendors.com` or `api.maclookup.app` with the first three bytes of an address. The remaining bytes and input file are not sent by the lookup code. API requests have timeouts and retry behavior; lookup success and vendor-name freshness are not guaranteed.

Offline mode makes no external vendor lookup requests and does not persist misses as failed lookups. Positive cache entries take precedence over earlier failures. Online failures are cached for five minutes to avoid repeated requests while allowing recovery. Older `failed_lookups.json` lists have no timestamps and are treated as expired; new files map OUI prefixes to failure timestamps. Existing positive caches are retained, and loaded OUI keys are normalized consistently.

The bundled snapshot provides a starting point, not a freshness guarantee. `shadowvendor/utils/update_oui_cache.py` is an explicit network-download utility; invoking it is separate from offline analysis and can replace the working cache.

The generated HTML requests `https://cdn.plot.ly/plotly-latest.min.js` when opened. Chart rendering needs that library, but the report's data tables, styling, and counts are embedded and remain readable when JavaScript or the CDN is unavailable. Installing dependencies or updating the cache is also a separate network operation.

## Output and SIEM fields

Standard report files are under `output/`. The device CSV uses `MAC`, `Vendor`, `VLAN`, and `Port`. The port CSV is generated for MAC-table inputs. HTML and summary filenames are shared between runs; device and port filenames use the input stem.

The dashboard uses separate responsive panels for the vendor overview and four VLAN views. Panels stack on narrower windows; charts resize when their containers change, including split-pane resizing. Short windows scroll naturally. Select a vendor beside the donut or beneath the top-vendor chart to hide/show that slice or series. Full values are available in the data tables, and the Plotly toolbar retains zoom, pan, reset, and PNG export. The heatmap shows the top ten vendors overall; the top-vendor bars show the top five and exclude other vendors. Counts and CSV/text/SIEM schemas are unchanged.

Missing vendor lookups appear as `Unknown` in the device CSV, summary, and SIEM exports. Successful standalone runs finish with a list of files written during that run, including enabled SIEM exports, history files, and drift output. Optional files left by previous runs are not included in that list.

If input validation fails, existing reports are preserved and the CLI explains that no new reports were generated. If an error occurs after writing starts, it warns that files may be partial or from an earlier run. Resolve the error and rerun before using those files as a fresh inventory.

SIEM exports contain these fields in each record:

```text
timestamp, site, environment, mac, vendor, device_name,
vlan, interface, input_type, source_file
```

`timestamp` is the UTC export time, not the original observation time on the switch. `device_name` defaults to a label derived from the MAC, not a discovered hostname. `interface` comes from the parsed port; `source_file` is the input filename. Empty site/environment values and `N/A` fields are valid.

`shadowvendor_siem.json` is JSON Lines despite its extension. Ingestion, retention, correlation, and alerting are configured outside ShadowVendor. Exports include complete MAC addresses; share sanitized samples when reporting bugs.

## Configuration and diagnostics

[CONFIG.md](../CONFIG.md) covers configuration file formats and `SHADOWVENDOR_*` variables. Files are searched in the current directory, the user’s `.config/shadowvendor` directory, then `/etc/shadowvendor`. INI works with the standard library; YAML needs PyYAML. Python 3.11+ includes the TOML reader.

Environment variables override config-file values. Explicit CLI options generally override those defaults, but boolean flags only enable features; they cannot turn a configured `true` value off. Explicit `--history-dir history` is indistinguishable from the default and can be replaced by configuration. The standalone script does not honor a configurable `output_dir`; its report paths remain under `output/` in the working directory.

For diagnostic output on macOS/Linux:

```bash
SHADOWVENDOR_VERBOSE=1 python ShadowVendor.py --offline my-switch.txt
SHADOWVENDOR_LOG=1 python ShadowVendor.py --offline my-switch.txt
```

The second command writes JSONL runtime events to `output/shadowvendor_runtime.log`. On PowerShell, set `$env:SHADOWVENDOR_VERBOSE = "1"` or `$env:SHADOWVENDOR_LOG = "1"` before running the command.

## Documentation verification

The README sample and combined offline/history/SIEM workflow were exercised on macOS with Python 3.14. The Windows commands were checked for consistency with the same paths but were not executed on Windows. This is documentation validation, not a claim of full platform certification or a fresh security audit.
