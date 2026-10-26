# Testing ShadowVendor

Install test tools, then run the isolated suite:

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest tests --bandit -q
```

Tests use temporary working directories and explicit cache fixtures. Unexpected live HTTP requests fail the test; execution-path tests supply deterministic vendor-service mocks. The cache tests exercise the current API rather than skipping tests for the former database API.

## Coverage by behavior

- `test_netvendor.py`: supported MAC representations, validation, ports, cached lookups, and failed lookups.
- `test_oui_manager.py`: legacy failure-file recovery, five-minute expiry, positive-cache precedence, offline misses, normalized cache keys, progress-independent batch results, request counts, malformed records, and invalid addresses.
- `test_vendor_output_handler.py`: device/port CSVs, chart documents, summaries, and empty/unknown data.
- `test_api.py`: input errors, device counts, history, and existence of every reported SIEM file.
- `test_execution_paths.py`: standalone CLI, installed entry-point function, API, flags, configuration, history, and exports.
- `test_remediations.py`: 240-device synthetic workflows, output schemas/counts, safe HTML script embedding, headerless input, leading blanks, malformed addresses, case deduplication, batch behavior, cache recovery, and explicit API output routing.

The synthetic fixtures in `tests/fixtures/synthetic/` contain no captured network inventory. Vendor labels are fictitious cache mappings. `expected.json` records their expected counts.

## Distribution smoke test

After installing a non-editable build with `python -m pip install .`, run:

```bash
python tests/wheel_smoke.py
```

This launches the installed console command and module from a temporary directory, checks the 240-record output, and verifies that the bundled OUI snapshot is included in the package. The basic entry points retain their file-only interface; use `ShadowVendor.py` for advanced CLI flags.

## Continuous integration and limits

The Tests workflow runs the full suite, configured Bandit scan, and installed-distribution smoke test on Linux with Python 3.9, 3.12, and 3.14, and Windows with Python 3.12. CodeQL runs separately. Inspect the checks for the exact commit rather than treating this document as evidence of a green build.

Bandit exclusions are recorded in `bandit.yaml`; a clean scan is not a claim that all vulnerabilities are absent. HTML tests verify safe script boundaries and JSON round trips. They do not replace interactive browser testing of Plotly rendering. The generated dashboard still loads Plotly from a CDN.
