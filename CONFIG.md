# ⚙️ ShadowVendor Configuration Guide

**Who should read this**: Automation engineers, DevOps teams, and anyone setting up recurring jobs or CI/CD pipelines that need configuration file examples and environment variable reference.

This document provides detailed configuration examples for ShadowVendor. For a quick overview, see the [Configuration section](README.md#configuration) in the README.

> **Local execution:** Configuration is read from local files and environment variables only — nothing is sent to a remote config service. ShadowVendor processes input on your machine; set `offline = true` (or `SHADOWVENDOR_OFFLINE=true`) for zero external network calls in automated jobs. See [README — Security Considerations](README.md#-security-considerations) for full privacy details.

## 📑 Table of Contents

- [Configuration File Locations](#configuration-file-locations)
- [Configuration File Formats](#configuration-file-formats)
- [Environment Variables](#environment-variables)
- [Configuration Precedence](#configuration-precedence)
- [Complete Examples](#complete-examples)

---

## Configuration File Locations

ShadowVendor checks for configuration files in the following order (first found is used):

1. **Current directory**: `./shadowvendor.conf` (or `.yaml`, `.toml`)
2. **User config**: `~/.config/shadowvendor/shadowvendor.conf`
3. **System config**: `/etc/shadowvendor/shadowvendor.conf`

**Note**: Only one configuration file is loaded. If multiple exist, the first one found (in the order above) is used.

---

## Configuration File Formats

ShadowVendor supports three configuration file formats:

### INI/ConfigParser Format (`.conf`, `.ini`)

**Default format** - No additional dependencies required.

```ini
[shadowvendor]
offline = true
history_dir = /var/lib/shadowvendor/history
site = DC1
environment = prod
siem_export = true
analyze_drift = true
change_ticket = CHG-12345
output_dir = output
```

### YAML Format (`.yaml`, `.yml`)

**Requires PyYAML**: `pip install pyyaml`

```yaml
shadowvendor:
  offline: true
  history_dir: /var/lib/shadowvendor/history
  site: DC1
  environment: prod
  siem_export: true
  analyze_drift: true
  change_ticket: CHG-12345
  output_dir: output
```

### TOML Format (`.toml`)

**Requires tomli/tomllib**: `pip install tomli` (Python < 3.11) or built-in `tomllib` (Python 3.11+)

```toml
[shadowvendor]
offline = true
history_dir = "/var/lib/shadowvendor/history"
site = "DC1"
environment = "prod"
siem_export = true
analyze_drift = true
change_ticket = "CHG-12345"
output_dir = "output"
```

---

## Environment Variables

Environment variables override configuration file values. All environment variables use the `SHADOWVENDOR_` prefix:

| Environment Variable | Description | Example |
|---------------------|-------------|---------|
| `SHADOWVENDOR_OFFLINE` | Enable offline mode (cache-only) | `SHADOWVENDOR_OFFLINE=true` |
| `SHADOWVENDOR_HISTORY_DIR` | History directory path | `SHADOWVENDOR_HISTORY_DIR=/var/lib/shadowvendor/history` |
| `SHADOWVENDOR_SITE` | Site/region identifier | `SHADOWVENDOR_SITE=DC1` |
| `SHADOWVENDOR_ENVIRONMENT` | Environment identifier | `SHADOWVENDOR_ENVIRONMENT=prod` |
| `SHADOWVENDOR_CHANGE_TICKET` | Change ticket/incident ID | `SHADOWVENDOR_CHANGE_TICKET=CHG-12345` |
| `SHADOWVENDOR_SIEM_EXPORT` | Enable SIEM export | `SHADOWVENDOR_SIEM_EXPORT=true` |
| `SHADOWVENDOR_ANALYZE_DRIFT` | Enable drift analysis | `SHADOWVENDOR_ANALYZE_DRIFT=true` |
| `SHADOWVENDOR_OUTPUT_DIR` | Output directory path | `SHADOWVENDOR_OUTPUT_DIR=output` |
| `SHADOWVENDOR_VERBOSE` | Enable verbose output | `SHADOWVENDOR_VERBOSE=1` |
| `SHADOWVENDOR_LOG` | Enable runtime logging | `SHADOWVENDOR_LOG=1` |

**Boolean values**: Use `true`/`false` (case-insensitive) or `1`/`0` for boolean environment variables.

---

## Configuration Precedence

Configuration values are resolved in the following order (highest to lowest priority):

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Configuration file**
4. **Default values** (lowest priority)

**Example**: If you set `SHADOWVENDOR_OFFLINE=true` in your environment and also pass `--offline` on the command line, the command-line argument takes precedence.

---

## Complete Examples

### Example 1: Air-Gapped Network (Offline Only)

**Use case**: Production network with no external API access.

**INI config** (`shadowvendor.conf`):
```ini
[shadowvendor]
offline = true
output_dir = /var/lib/shadowvendor/output
```

**Command**:
```bash
python3 ShadowVendor.py input_file.txt
```

**Result**: Uses only local OUI cache, no external lookups.

---

### Example 2: SIEM Integration (Production)

**Use case**: Regular scheduled runs for SIEM ingestion.

**YAML config** (`shadowvendor.yaml`):
```yaml
shadowvendor:
  site: DC1
  environment: prod
  siem_export: true
  output_dir: /var/lib/shadowvendor/output
```

**Command**:
```bash
python3 ShadowVendor.py input_file.txt
```

**Result**: Generates standard outputs + SIEM exports in `output/siem/` directory.

---

### Example 3: Change Window Tracking

**Use case**: Track vendor changes during change windows.

**INI config** (`shadowvendor.conf`):
```ini
[shadowvendor]
history_dir = /var/lib/shadowvendor/history
site = DC1
analyze_drift = true
```

**Command**:
```bash
python3 ShadowVendor.py \
  --change-ticket CHG-12345 \
  input_file.txt
```

**Result**: Archives summary with metadata, generates drift analysis CSV with change ticket correlation.

---

### Example 4: Environment Variable Override

**Use case**: Different sites/environments without changing config files.

**INI config** (`shadowvendor.conf`):
```ini
[shadowvendor]
site = DC1
environment = prod
siem_export = true
```

**Command**:
```bash
SHADOWVENDOR_SITE=DC2 \
SHADOWVENDOR_ENVIRONMENT=staging \
python3 ShadowVendor.py input_file.txt
```

**Result**: Uses `DC2` and `staging` from environment variables, overrides config file values.

---

### Example 5: Complete Workflow (All Features)

**Use case**: Full-featured analysis with all options enabled.

**TOML config** (`shadowvendor.toml`):
```toml
[shadowvendor]
offline = true
history_dir = "/var/lib/shadowvendor/history"
site = "DC1"
environment = "prod"
siem_export = true
analyze_drift = true
output_dir = "/var/lib/shadowvendor/output"
```

**Command**:
```bash
python3 ShadowVendor.py \
  --change-ticket CHG-12345 \
  input_file.txt
```

**Result**: Runs offline, generates all outputs, archives with metadata, creates drift analysis, and exports SIEM events.

---

## Configuration File Examples

Complete example configuration files are available in the repository:

- **INI format**: [`shadowvendor.conf.example`](shadowvendor.conf.example)
- **YAML format**: [`shadowvendor.yaml.example`](shadowvendor.yaml.example)

To use these examples:

```bash
# Copy example to your config location
cp shadowvendor.conf.example ~/.config/shadowvendor/shadowvendor.conf

# Edit and customize
nano ~/.config/shadowvendor/shadowvendor.conf
```

---

## Troubleshooting

### Configuration Not Loading

**Problem**: Configuration file changes aren't being applied.

**Solutions**:
1. Check file location - ensure the file is in one of the checked directories
2. Verify file format - ensure proper syntax for your chosen format
3. Check file permissions - ensure the file is readable
4. Use verbose mode - `SHADOWVENDOR_VERBOSE=1` to see which config file is loaded

### Environment Variables Not Working

**Problem**: Environment variables aren't overriding config file values.

**Solutions**:
1. Verify variable name - must use `SHADOWVENDOR_` prefix
2. Check boolean values - use `true`/`false` or `1`/`0`
3. Verify export - ensure variables are exported in your shell session
4. Check precedence - command-line arguments override environment variables

### Format-Specific Issues

**YAML**: Ensure PyYAML is installed (`pip install pyyaml`)
**TOML**: Ensure tomli is installed for Python < 3.11 (`pip install tomli`)

---

For more information, see:
- [README.md Configuration Section](README.md#configuration)
- [ADVANCED.md](ADVANCED.md) for operational best practices

