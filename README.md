# 🚀 ShadowVendor

![Overview](docs/images/overview.png?v=14.0.0)

**Overview Dashboard** - Interactive vendor distribution visualization:
- Hover over pie segments to see device counts, percentages, and VLAN presence
- Quickly identify dominant vendors and device diversity
- Export-ready for reports and presentations

## ⚡ TL;DR: Why You Should Care

- **Turn MAC tables into dashboards**: Transform raw network device outputs into interactive HTML visualizations and CSV reports
- **Detect new/unknown vendors**: Identify previously unseen devices and track vendor distribution changes over time
- **Export SIEM events**: Generate normalized CSV/JSONL exports for Elastic, Splunk, and other SIEMs to enable posture-change detection

**Quick start:** `python3 ShadowVendor.py input_file.txt` → Check `output/` for results

**Try it in 60 seconds:** `python3 ShadowVendor.py tests/data/test-mac-table.txt` (then open `output/vendor_distribution.html` in your browser) → See dashboards without touching your own network data

**Privacy & local execution:** ShadowVendor processes your files entirely on your machine. Input files and full MAC addresses are never uploaded. In default mode, uncached vendor lookups send only OUI prefixes (first 3 octets) to external APIs. Use `--offline` for fully air-gapped operation with zero external network calls.

## 👥 Who is This For?

- **SOC analysts**: Detect new vendors and track device changes for security monitoring
- **Network engineers**: Analyze MAC address tables and ARP data to understand network composition
- **Asset/CMDB owners**: Maintain accurate device inventories with vendor identification
- **Security architects**: Integrate posture-change detection into SIEM workflows

---

## 📖 Introduction

**ShadowVendor** is a Python tool for network administrators and cybersecurity professionals to analyze and visualize the vendor distribution of devices on a network. It processes MAC address tables and ARP data from a wide range of network devices (including Cisco, HP/Aruba, Juniper, Extreme, Brocade, and more), providing detailed insights into your network's composition.

**Runs on your machine:** ShadowVendor is not a cloud service — your network exports and full MAC addresses are processed locally and never uploaded; use `--offline` for zero external network calls.

When integrated with SIEMs (Elastic, Splunk, QRadar, etc.), ShadowVendor transforms from a static inventory tool into a **posture-change sensor** that enables proactive security monitoring and incident response.

---

## 📚 Documentation Overview

ShadowVendor includes comprehensive documentation organized by audience and use case. This README provides the essential information to get started quickly. For deeper dives, see the specialized documentation:

| Document | Purpose | Best For |
|----------|---------|----------|
| **[README.md](README.md)** (you are here) | Quick start, common workflows, basic usage | First-time users, quick reference |
| **[TUTORIAL.md](TUTORIAL.md)** | Technical deep-dive, architecture, code walkthroughs | Contributors, developers, understanding internals |
| **[ADVANCED.md](ADVANCED.md)** | Operational best practices, SIEM integration, production deployment | SOC engineers, network operations, production users |
| **[CONFIG.md](CONFIG.md)** | Configuration files, environment variables, automation setup | Automation engineers, DevOps, recurring jobs |
| **[EXECUTION_PATHS.md](EXECUTION_PATHS.md)** | Complete execution path documentation, behavior graphs | Testers, QA, understanding all execution modes |
| **[TEST_COVERAGE.md](TEST_COVERAGE.md)** | Test coverage details, testing strategy | Contributors, QA engineers |

**Navigation Guide:**
- **New to ShadowVendor?** → Start here (README.md), then try the [Quick Start](#-getting-started)
- **Want to understand how it works?** → Read [TUTORIAL.md](TUTORIAL.md) for architecture and code walkthroughs
- **Deploying to production?** → See [ADVANCED.md](ADVANCED.md) for operational best practices
- **Setting up automation?** → Check [CONFIG.md](CONFIG.md) for configuration examples
- **Contributing code?** → Review [TUTORIAL.md](TUTORIAL.md#for-contributors) for extension points and testing

---

## 📑 Table of Contents

- [✨ Features](#-features)
- [🔄 Common Workflows](#-common-workflows)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [📋 Quick Reference](#-quick-reference)
  - [Ways to Run ShadowVendor](#ways-to-run-shadowvendor)
  - [Expected Outputs](#expected-outputs)
- [📋 Detailed Usage](#-detailed-usage)
  - [Command-Line Flags](#command-line-flags)
  - [Offline Mode](#offline-mode)
  - [Historical Drift Analysis](#historical-drift-analysis)
  - [SIEM-Friendly Export](#siem-friendly-export)
  - [Windows Usage](#windows-usage)
  - [Verbose Output](#verbose-output)
  - [Runtime Logging](#runtime-logging)
  - [Configuration](#configuration)
  - [Python API](#python-api)
- [📥 Supported Input Formats](#-supported-input-formats)
- [📊 Output Details](#-output-details)
- [🌟 Success Stories & Known Deployments](#-success-stories--known-deployments)
- [🔒 Security Considerations](#-security-considerations)
- [🔧 Advanced Topics](#-advanced-topics)
  - [Technical Tutorial](#technical-tutorial)
- [🧪 Testing & Quality](#-testing--quality)
- [📈 Project Status](#-project-status)
- [🤝 Community](#-community)

---

## ✨ Features

- **Multi-vendor MAC address parsing:** Supports Cisco, HP/Aruba, Juniper, Extreme, Brocade, and more.
- **Flexible input:** Accepts MAC address lists, MAC tables, and ARP tables in various formats.
- **Vendor identification:** Uses a local IEEE OUI cache for fast, secure lookups.
- **Comprehensive reporting:** Generates CSVs, summaries, and interactive HTML dashboards.
- **VLAN and port analysis:** Extracts and visualizes VLAN and port data where available.
- **Historical drift tracking:** Archive vendor summaries and analyze trends over time with metadata correlation.
- **SIEM integration:** Export normalized CSV/JSONL events for security monitoring and posture-change detection.
- **Extensible and robust:** Easily add support for new formats; thoroughly tested with real-world data.

---

## 🔄 Common Workflows

**Basic Analysis:**
```bash
python3 ShadowVendor.py input_file.txt
```
→ Generates standard outputs: Device CSV, Port CSV (if MAC table), HTML dashboard, Vendor Summary

**Offline Analysis (air-gapped networks):**
```bash
python3 ShadowVendor.py --offline input_file.txt
```
→ Uses only local OUI cache, no external API calls

**SIEM Integration:**
```bash
python3 ShadowVendor.py \
  --siem-export \
  --site DC1 \
  --environment prod \
  input_file.txt
```
→ Generates standard outputs + SIEM-ready CSV/JSONL files

**Historical Tracking with Drift Analysis:**
```bash
python3 ShadowVendor.py \
  --history-dir history \
  --site DC1 \
  --change-ticket CHG-12345 \
  --analyze-drift \
  input_file.txt
```
→ Generates standard outputs + archives summary with metadata + creates drift analysis CSV

**Complete Workflow (all features):**
```bash
python3 ShadowVendor.py \
  --offline \
  --history-dir history \
  --analyze-drift \
  --siem-export \
  --site DC1 \
  --environment prod \
  --change-ticket CHG-12345 \
  input_file.txt
```
→ Runs offline, generates all outputs, archives with metadata, creates drift analysis, and exports SIEM events

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher (Python 3.8+ supported)
- pip (Python package installer)

### Installation

**Option 1: Install as a package (recommended for Python API usage)**
```bash
git clone https://github.com/StewAlexander-com/ShadowVendor.git
cd ShadowVendor && pip install -e .
```

**Option 2: Use standalone script (no installation required)**
```bash
git clone https://github.com/StewAlexander-com/ShadowVendor.git
cd ShadowVendor
pip install -r requirements.txt  # Install dependencies only
python3 ShadowVendor.py input_file.txt  # Run directly
```

**Runtime dependencies** will be automatically installed when you run `pip install -e .` or `pip install -r requirements.txt`. Required packages:
- `requests` (for OUI API lookups)
- `plotly` (for interactive HTML dashboards)
- `tqdm` (for progress bars)
- `rich` (for enhanced terminal output)

**Development dependencies** (for testing and security scanning):
- Install with: `pip install -r requirements-dev.txt`
- Includes: `pytest`, `pytest-cov`, and `bandit` (security scanner)
- Required for: Running tests (`pytest`), security scanning (`pytest --bandit`), and code coverage reports
- **Note**: Development dependencies are optional for end users; only needed for contributors and CI/CD pipelines

---

## 📋 Quick Reference

### Ways to Run ShadowVendor

**1. Simple Package Entry Point** (basic usage, no flags):
```bash
shadowvendor input_file.txt
# or
python3 -m shadowvendor input_file.txt
```
*Limited to basic analysis only - no advanced features*

**2. Standalone Script** (full feature set with all flags):
```bash
python3 ShadowVendor.py input_file.txt
```

**Important:** For all advanced features (offline mode, history tracking, SIEM export, drift analysis), use `python3 ShadowVendor.py`. The package entry point (`shadowvendor`) is a simple wrapper that only accepts an input file argument and does not support flags.

### Expected Outputs

ShadowVendor generates several output files in the `output/` directory:

**Output behavior:**
- **Always generated**: Device CSV, interactive HTML dashboard, vendor summary text file
- **Conditionally generated**: Port CSV (only for MAC address tables, not ARP or simple lists)
- **Optional** (with flags): SIEM exports (CSV/JSONL), historical archives, drift analysis CSV

See [Output Details](#-output-details) below for complete file descriptions.

### Typical First Run

**Quick workflow for first-time users:**

1. **Paste your network output** into a file (e.g., `my_switch.txt`):
   ```bash
   # Copy output from: show mac address-table
   # or: show arp
   # or: just a list of MAC addresses
   ```

2. **Run ShadowVendor**:
   ```bash
   python3 ShadowVendor.py my_switch.txt
   ```

3. **Open the results**:
   - **Interactive dashboard**: Open `output/vendor_distribution.html` in your browser
   - **Device list**: Check `output/my_switch-Devices.csv` for detailed device information
   - **Summary**: Read `output/vendor_summary.txt` for quick vendor counts

**That's it!** You now have a complete vendor analysis of your network data.

---

## 📋 Detailed Usage

### Command-Line Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--offline` | Disable external vendor lookups (cache-only) | `--offline` |
| `--history-dir DIR` | Directory for archiving vendor summaries (created automatically if it doesn't exist) | `--history-dir history` |
| `--analyze-drift` | Run drift analysis on archived summaries | `--analyze-drift` |
| `--site SITE` | Site/region identifier for SIEM/drift metadata | `--site DC1` |
| `--environment ENV` | Environment identifier for SIEM exports | `--environment prod` |
| `--change-ticket ID` | Change ticket/incident ID for drift correlation | `--change-ticket CHG-12345` |
| `--siem-export` | Generate SIEM-friendly CSV/JSONL exports | `--siem-export` |

**Note**: Configuration file values and environment variables can provide defaults for these flags. See [Configuration](#configuration) section below.

### Offline Mode

Use the `--offline` flag when you want to avoid any external vendor lookups (e.g., on air‑gapped networks). Devices that are not already present in the local OUI cache will appear as `Unknown`.

```bash
python3 ShadowVendor.py --offline input_file.txt
```

### Historical Drift Analysis

Track how vendor composition changes over time and correlate with change windows/incidents:

```bash
python3 ShadowVendor.py \
  --history-dir history \
  --site DC1 \
  --change-ticket CHG-12345 \
  --analyze-drift \
  input_file.txt
```

**What it does:**
- Creates the history directory if it doesn't exist
- Archives `vendor_summary.txt` to `history/vendor_summary-YYYYMMDD-HHMMSS.txt`
- Creates companion `.metadata.json` file with `run_timestamp`, `site`, `change_ticket_id`
- Generates `history/vendor_drift.csv` with metadata rows and vendor percentage trends

**SIEM Correlation:** The drift CSV metadata enables correlation with change windows and incidents, supporting 8D/5-why workflows. You can join drift data with SIEM events using `run_timestamp` and `site`, and correlate vendor mix shifts with `change_ticket_id`.

### SIEM-Friendly Export

For SIEM integration (Elastic, Splunk, etc.), generate normalized CSV and JSONL events:

```bash
python3 ShadowVendor.py \
  --siem-export \
  --site DC1 \
  --environment prod \
  input_file.txt
```

**Stable Schema** (all fields present in every record):
- `timestamp`, `site`, `environment`, `mac`, `vendor`, `device_name`, `vlan`, `interface`, `input_type`, `source_file`

**Correlation-friendly design:**
- All fields consistently named and present in every record
- MAC addresses normalized for reliable joins
- UTC ISO-8601 timestamps for time-based correlation
- Site and environment tags enable multi-site/environment dashboards

**For complete SIEM integration:** See [ADVANCED.md](ADVANCED.md#-posture-change-detection--security-monitoring) for:
- Detailed SIEM integration workflows
- Correlation rule examples (Elastic, Splunk)
- Posture-change detection strategies
- Continuous monitoring setup

### Cross-Platform Compatibility

ShadowVendor is designed to work on **Linux (Debian/Ubuntu), macOS (Intel and Apple Silicon), and Windows**. All file operations use UTF-8 encoding and cross-platform path handling for seamless operation across environments.

**Windows Usage:**
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; python3 ShadowVendor.py input_file.txt
```

Or set environment variables separately:
```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
python3 ShadowVendor.py input_file.txt
```

**Linux/macOS Usage:**
```bash
python3 ShadowVendor.py input_file.txt
```

**Cross-Platform Considerations:**
- **File paths**: All paths use `pathlib.Path` for cross-platform compatibility (handles `/` vs `\` automatically)
- **File encoding**: All file operations explicitly use UTF-8 encoding to prevent encoding issues on Windows
- **Line endings**: Python's text mode handles both CRLF (Windows) and LF (Unix) automatically
- **File locking**: Cache writes use atomic operations (write to temp file, then rename) to prevent corruption if multiple processes run simultaneously
- **API timeouts**: All network requests have 5-second timeouts to prevent hangs on slow/unreliable networks
- **Error handling**: Permission errors and file system errors are handled gracefully on all platforms

### Verbose Output

Control debug output with the `SHADOWVENDOR_VERBOSE` environment variable (only supported by `ShadowVendor.py`):

```bash
# Quiet mode (default)
python3 ShadowVendor.py input_file.txt

# Verbose mode - detailed processing information
SHADOWVENDOR_VERBOSE=1 python3 ShadowVendor.py input_file.txt
```

When verbose mode is enabled, you'll see file type detection details, per-line processing information, sample device entries, CSV writing progress, and output file content preview.

### Runtime Logging

For troubleshooting and performance analysis, ShadowVendor can log runtime behavior to a structured log file:

```bash
# Enable runtime logging
SHADOWVENDOR_LOG=1 python3 ShadowVendor.py input_file.txt
```

When enabled, a log file is created at `output/shadowvendor_runtime.log` in JSONL format (one JSON object per line). Each entry includes:
- `timestamp`: UTC ISO-8601 timestamp
- `event_type`: Type of event (e.g., "processing_start", "file_type_detection", "error")
- `event_data`: Event-specific data
- `context`: Additional context information

The logger captures key runtime events including file processing, error conditions, output generation, and performance metrics. Logging is disabled by default and has no performance impact when not enabled.

### Configuration

ShadowVendor supports configuration files and environment variables to reduce CLI flag churn in recurring jobs.

**Configuration file locations** (checked in order):
1. Current directory: `./shadowvendor.conf` (or `.yaml`, `.toml`)
2. User config: `~/.config/shadowvendor/shadowvendor.conf`
3. System config: `/etc/shadowvendor/shadowvendor.conf`

**Supported formats**: INI/ConfigParser (`.conf`, `.ini`), YAML (`.yaml`, `.yml` - requires PyYAML), TOML (`.toml` - requires tomli/tomllib)

**Example config** (`shadowvendor.conf`):
```ini
[shadowvendor]
offline = true
history_dir = /var/lib/shadowvendor/history
site = DC1
environment = prod
siem_export = true
```

**Precedence**: Command-line arguments > Environment variables > Config file > Defaults

**For complete configuration details:** See [CONFIG.md](CONFIG.md) for:
- Complete configuration file examples (INI, YAML, TOML)
- Environment variable reference
- Configuration precedence rules
- Automation setup examples

### Python API

ShadowVendor provides a programmatic Python API for integration into automation scripts and other tools:

```python
from shadowvendor import analyze_file

# Basic usage
result = analyze_file("mac_table.txt", offline=True)

print(f"Processed {result['device_count']} devices")
print(f"Found {result['vendor_count']} unique vendors")
print(f"Output files: {result['output_files']}")

# Access device data
for mac, info in result['devices'].items():
    print(f"{mac}: {info['vendor']} (VLAN: {info['vlan']})")

# With SIEM export
result = analyze_file(
    input_file="mac_table.txt",
    offline=True,
    siem_export=True,
    site="DC1",
    environment="prod"
)

# With history tracking
result = analyze_file(
    input_file="mac_table.txt",
    history_dir="history",
    analyze_drift_flag=True,
    site="DC1",
    change_ticket="CHG-12345"
)
```

**API Reference**: See `shadowvendor/api.py` for complete function signature and return value documentation. For code examples and integration patterns, see [TUTORIAL.md](TUTORIAL.md#for-contributors).

---

## 📥 Supported Input Formats

**Just paste your raw `show mac address-table` output into a file; ShadowVendor will auto-detect the format.** No heavy data cleaning required - the tool handles headers, whitespace, and various vendor formats automatically.

ShadowVendor automatically detects and parses the following formats:

### 1. Simple MAC Address List

```
00:11:22:33:44:55
00-11-22-33-44-55
001122334455
0011.2233.4455
```

### 2. MAC Address Tables (Multi-vendor)

**Cisco:**
```
Vlan    Mac Address       Type        Ports
10      0011.2233.4455    DYNAMIC     Gi1/0/1
```

**HP/Aruba:**
```
Vlan    Mac Address       Type        Ports
20      00:24:81:44:55:66 DYNAMIC     1
```

**Juniper:**
```
Vlan    Mac Address       Type        Ports
30      00:0E:83:11:22:33 DYNAMIC     ge-0/0/0
```

**Extreme:**
```
Vlan    Mac Address       Type        Ports
40      B8-AC-6F-77-88-99 DYNamic     1:1
```

**Brocade:**
```
Vlan    Mac Address       Type        Ports
50      00:11:22:33:44:55 DYNAMIC     1/1
```

### 3. ARP Tables

```
Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  192.168.1.1      -          0011.2233.4455  ARPA   Vlan10
```

**Format Detection Features:**
- Automatic file type detection based on content
- Flexible MAC parsing: Accepts colon, hyphen, dot, and mask/prefix formats
- VLAN extraction from multiple sources (column, interface, etc.)
- Port extraction for detailed switch analysis
- Header skipping and robust error handling

**Want to understand how format detection works?** See [TUTORIAL.md](TUTORIAL.md#file-type-detection) for detailed implementation and how to add support for new vendor formats.

---

## 📊 Output Details

### Standard Outputs

**Use these dashboards during change windows to confirm no unexpected vendors appear.**

![Security Dashboard](docs/images/security-dashboard.png?v=12.8)

**Security Dashboard** - Device count analysis per VLAN:
- Identify VLANs with high device concentrations for security monitoring
- Spot anomalies in device distribution across network segments
- Quick visual reference for security reviews

![Vendor Dashboard](docs/images/vendor-dashboard.png?v=12.8)

**Vendor Dashboard** - Comprehensive multi-panel VLAN analysis:
- Device counts, vendor diversity, and heatmaps
- Top vendor distributions across network segments
- Cross-VLAN vendor comparison for change validation

**Device Information CSV** (`{input_file}-Devices.csv`):
- One row per device with columns: MAC, Vendor, VLAN, Port
- Always generated

**Port Report CSV** (`{input_file}-Ports.csv`):
- Port utilization and device mapping
- Columns: Port, Total Devices, VLANs, Vendors, Device Details
- Only generated for MAC address tables (not ARP or simple lists)

**Vendor Distribution HTML** (`vendor_distribution.html`):
- Interactive dashboard with vendor distribution pie chart and VLAN analysis subplots
- Always generated

**Vendor Summary Text** (`vendor_summary.txt`):
- Plain text summary with vendor counts and percentages in formatted table
- Always generated

### Optional Outputs

**SIEM Export Files** (requires `--siem-export`, written to `output/siem/` directory):
- `siem/shadowvendor_siem.csv`: Line-delimited CSV with header
- `siem/shadowvendor_siem.json`: JSONL format (one JSON object per line)
- Both contain identical data with stable schema for SIEM correlation

**History Archive Files** (requires `--history-dir`):
- `vendor_summary-YYYYMMDD-HHMMSS.txt`: Timestamped vendor summary snapshot
- `vendor_summary-YYYYMMDD-HHMMSS.metadata.json`: Companion metadata file with:
  - `run_timestamp`: UTC ISO-8601 timestamp
  - `site`: Site/region identifier
  - `change_ticket_id`: Change ticket/incident ID

**Drift Analysis CSV** (requires `--analyze-drift`):
- `history/vendor_drift.csv`: Vendor percentage trends across all archived runs
- Includes metadata rows at top: `run_timestamp`, `site`, `change_ticket_id`
- Vendor percentage rows showing changes over time

---

## 🌟 Success Stories & Known Deployments

ShadowVendor is used in production environments for network monitoring, security posture tracking, and asset management. While specific deployment details are kept confidential, the tool has been successfully deployed in:

- **Enterprise SOC environments**: Integrated with Elastic Stack and Splunk for continuous posture-change detection across multiple data centers
- **Network operations teams**: Daily analysis of MAC address tables from Cisco, Juniper, and Aruba switches to track device inventory and vendor distribution
- **Air-gapped networks**: Offline mode enables vendor identification in isolated environments without external API dependencies
- **Change management workflows**: Historical drift analysis with change ticket correlation supports incident response and root cause analysis

**Have a success story to share?** We'd love to hear how you're using ShadowVendor! See the [Community section](#-community) for details on how to contribute your success story.

---

## 🔒 Security Considerations

ShadowVendor is designed with security in mind:
- **Read-only operation**: ShadowVendor reads text exports only and does not make changes to network devices
- **Local-first processing**: Input files and full MAC addresses never leave your machine
- **Default mode**: Uncached vendor lookups send only OUI prefixes (first 3 octets) to external APIs; all other processing stays local
- **Offline mode**: `--offline` flag enables air-gapped analysis with zero external network calls
- **Safe for production**: No device modifications, no credentials stored, no persistent connections
- **HTML dashboards**: Opening generated HTML may load Plotly from a CDN in your browser
- **Code security scanning**: Regular security scans with Bandit to detect potential vulnerabilities and code execution risks

For security teams evaluating the tool: ShadowVendor processes static text files and generates reports locally. It does not connect to network devices or modify configurations. For full network and API behavior details, see [ADVANCED.md — Network & API Behavior](ADVANCED.md#network--api-behavior). To report vulnerabilities in ShadowVendor, see [SECURITY.md](SECURITY.md).

## 🔧 Advanced Topics

### Operational Guidance

For detailed information on advanced topics and production deployment, see **[ADVANCED.md](ADVANCED.md)**:

- **Posture-Change Detection & Security Monitoring**: SIEM integration workflows, correlation rules, and continuous monitoring strategies
- **Operational Best Practices**: Vendor lookup optimization, cache management, output organization, troubleshooting, and cross-platform considerations
- **Runtime Considerations**: Performance benchmarks, network behavior, disk space planning, and error handling details

### Technical Deep-Dive

**Want to understand how ShadowVendor works under the hood?** See **[TUTORIAL.md](TUTORIAL.md)** for a comprehensive technical deep-dive covering:

- **Architecture Overview**: Modular design, component relationships, data flow
- **Execution Flow**: Step-by-step walkthrough from code execution to output generation
- **Core Components**: File type detection, MAC normalization, vendor lookup system, OUI cache management
- **For Contributors**: Extension points, adding new formats, testing strategy, debugging playbook

**Perfect for:**
- Developers who want to modify or extend ShadowVendor
- Engineers who need to understand behavior in production
- Contributors who want to add new features or formats

---

## 🧪 Testing & Quality

**TL;DR**: Comprehensive test suite (41+ tests) covering all execution paths, input formats, and features. Run `pytest -q` for quick validation. See [EXECUTION_PATHS.md](EXECUTION_PATHS.md) and [TEST_COVERAGE.md](TEST_COVERAGE.md) for details.

ShadowVendor includes a comprehensive test suite that validates all execution paths, input formats, and features to ensure reliability and correctness. The test suite uses realistic network device outputs and mock data for reproducible validation.

### Running Tests

**Quick test run:**
```bash
pytest -q
```

**Detailed test output:**
```bash
pytest -v
```

**Run specific test categories:**
```bash
# Test all execution paths (package entry, standalone script, Python API)
pytest tests/test_execution_paths.py -v

# Test core parsing and format detection
pytest tests/test_shadowvendor.py -v

# Test vendor lookup and caching
pytest tests/test_oui_manager.py -v

# Test output generation
pytest tests/test_vendor_output_handler.py -v

# Test Python API
pytest tests/test_api.py -v
```

**Test with coverage report:**
```bash
pytest --cov=shadowvendor --cov-report=html
```

### Test Coverage

**Coverage summary**: 41+ tests covering execution paths, configuration, input processing, and error handling. Test data in `tests/data/` includes realistic MAC tables, ARP tables, and MAC lists.

**What's tested:**
- ✅ Execution paths (package entry, standalone script, Python API)
- ✅ Configuration files (INI, YAML, TOML) and environment variables
- ✅ Input processing (MAC lists, MAC tables, ARP tables)
- ✅ Error handling (missing files, empty files, invalid inputs)
- ✅ Core functionality (parsing, normalization, vendor lookup)
- ✅ Output generation (CSV, HTML, port reports)

**For detailed testing documentation:**
- **[EXECUTION_PATHS.md](EXECUTION_PATHS.md)** - Complete execution path documentation
- **[TEST_COVERAGE.md](TEST_COVERAGE.md)** - Detailed test coverage summary
- **[TUTORIAL.md](TUTORIAL.md#test-strategy)** - Test strategy and debugging guide

### Security Scanning

**Bandit** is a security linter that scans Python code for common security vulnerabilities. It's included as a development dependency and can be run as part of the test suite.

**Installation:**
```bash
# Install development dependencies (includes bandit, pytest, pytest-cov)
pip install -r requirements-dev.txt
```

**Run Bandit security scanner as part of test suite:**
```bash
# Run all tests with security scan
pytest --bandit

# Run specific tests with security scan
pytest tests/test_api.py --bandit -v
```

**What Bandit checks:**
- SQL injection vulnerabilities
- Command injection risks
- Insecure use of cryptographic functions
- Hardcoded passwords and secrets
- Insecure random number generation
- Code execution vulnerabilities
- And other security anti-patterns

**Current status**: ✅ No security issues identified (with configured exclusions for intentional patterns)

**Note**: The `--bandit` flag runs the security scan before executing tests. If security issues are found, the test suite will fail before running any tests. Bandit is a **development dependency** and is not required for normal ShadowVendor usage.

### Optional Linting/Type Checks

If configured locally:
```bash
ruff check .
mypy shadowvendor
```

---

## 📈 Project Status

**TL;DR**: Actively maintained, production-ready. Latest: [v14.0.0](https://github.com/StewAlexander-com/ShadowVendor/releases/tag/v14.0.0) with complete rebranding, comprehensive testing, and enhanced documentation. Stable API and CLI since v14.0.0.

![ShadowVendor v14.0.0](https://raw.githubusercontent.com/StewAlexander-com/ShadowVendor/main/.github/og-image.png)

ShadowVendor demonstrates comprehensive software engineering practices including test-driven development (41+ tests), detailed technical documentation, security-focused design (offline mode, read-only operations), and production-ready features (SIEM integration, historical drift analysis, cross-platform compatibility).

### Latest Release: v14.0.0

**Major Release: Project Rebranding to ShadowVendor**

**Key highlights:**
- 🎉 Complete rebranding from NetVendor to ShadowVendor
- ✅ Comprehensive test suite (41+ tests covering all execution paths)
- 📚 Enhanced documentation (TUTORIAL.md, ADVANCED.md, EXECUTION_PATHS.md, TEST_COVERAGE.md)
- 🐍 Python API for programmatic usage
- ⚙️ Configuration file support (INI, YAML, TOML)
- 🧪 Test data included for quick start examples

**Recent improvements:**
- Enhanced MAC address parsing (Juniper, Aruba, Extreme, Brocade)
- Historical drift analysis with metadata correlation
- SIEM export with stable schema for posture-change detection
- Runtime logging for troubleshooting and performance analysis
- Offline mode support for air-gapped networks

### Versioning & Stability

- **SIEM schema**: Stable since v14.0.0
- **Core CLI flags**: Stable since v14.0.0 (backward compatible)
- **Python API**: Stable since v14.0.0

### Planned Features

- More vendor format support
- Additional visualization options
- Network topology mapping
- GitHub Discussions and community chat channels

---

## 🤝 Community

ShadowVendor is an open-source project, and we welcome contributions from the community!

### Getting Help & Reporting Issues

- **Report bugs or request features**: Open an [issue on GitHub](https://github.com/StewAlexander-com/ShadowVendor/issues)
- **Ask questions**: Open a GitHub issue with the "question" label for general questions and use cases
- **Security vulnerabilities**: See [SECURITY.md](SECURITY.md) — report privately via [GitHub Security Advisories](https://github.com/StewAlexander-com/ShadowVendor/security/advisories/new)

### Contributing Success Stories

We'd love to hear how you're using ShadowVendor! Share your success stories by:
- Opening a GitHub issue with your use case (anonymized as needed)
- Submitting a pull request to add your deployment to the [Success Stories section](#-success-stories--known-deployments)
- Sharing your experience in an issue thread

### Contributing Code

Contributions are welcome! To contribute:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request with a clear description of your changes

### Community Channels

- **GitHub Discussions**: See [Planned](#-project-status) section for upcoming community features
- **Community chat**: See [Planned](#-project-status) section for upcoming community features

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 👤 Author

Stewart Alexander

---

---

## 🗺️ Quick Navigation

**Common paths through the documentation:**

1. **First-time user workflow:**
   - Start here (README.md) → [Getting Started](#-getting-started) → [Quick Reference](#-quick-reference) → Try it!

2. **Production deployment workflow:**
   - README.md → [Advanced Topics](#-advanced-topics) → [ADVANCED.md](ADVANCED.md) → [CONFIG.md](CONFIG.md)

3. **Understanding internals workflow:**
   - README.md → [Advanced Topics](#-advanced-topics) → [TUTORIAL.md](TUTORIAL.md) → [How It Works](TUTORIAL.md#how-it-works)

4. **Contributing workflow:**
   - README.md → [TUTORIAL.md](TUTORIAL.md#for-contributors) → [Extension Points](TUTORIAL.md#extension-points) → [Test Strategy](TUTORIAL.md#test-strategy)

5. **Troubleshooting workflow:**
   - README.md → [TUTORIAL.md](TUTORIAL.md#troubleshooting) → [Debugging Playbook](TUTORIAL.md#debugging-playbook) → [ADVANCED.md](ADVANCED.md#-operational-best-practices)

---

**💡 Tip:** For best results, always use the latest OUI cache and keep your dependencies up to date. And remember: Networks are more fun when you know who's on them! 😄
