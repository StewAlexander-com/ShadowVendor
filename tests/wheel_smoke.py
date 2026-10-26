"""Check installed entry points and package data from a clean temporary directory."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile


def main():
    fixtures = Path(__file__).resolve().parent / "fixtures" / "synthetic"
    scripts = Path(sysconfig.get_path("scripts"))
    console = scripts / ("shadowvendor.exe" if os.name == "nt" else "shadowvendor")
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        cache_dir = work / "output" / "data"
        cache_dir.mkdir(parents=True)
        cache = json.loads((fixtures / "vendors.json").read_text())
        cache["E0:FE:ED"] = "Synthetic Extra Vendor"
        (cache_dir / "oui_cache.json").write_text(json.dumps(cache))
        # -I excludes the source checkout and PYTHONPATH from package resolution.
        probe = subprocess.run([
            sys.executable, "-I", "-c",
            "import shadowvendor; from importlib.resources import files; "
            "assert files('shadowvendor').joinpath('data/oui_cache.json').is_file(); "
            "print(shadowvendor.__file__)",
        ], cwd=work, check=True, capture_output=True, text=True)
        print("Installed package:", probe.stdout.strip())
        subprocess.run([
            sys.executable, "-I", "-c",
            "import os, sys; from pathlib import Path; from shadowvendor import analyze_file; "
            "before = os.getcwd(); "
            "result = analyze_file(sys.argv[1], offline=True, siem_export=True, output_dir='api-reports'); "
            "assert result['device_count'] == 240; "
            "assert all(Path(p).is_file() for p in result['output_files']); "
            "assert os.getcwd() == before",
            str(fixtures / "mac-table.txt"),
        ], cwd=work, check=True, capture_output=True, text=True, timeout=30)
        print("Passed: installed API, SIEM paths, and unchanged cwd")
        for command in ([str(console)], [sys.executable, "-I", "-m", "shadowvendor"]):
            subprocess.run(command + [str(fixtures / "mac-table.txt")], cwd=work, check=True,
                           capture_output=True, text=True, timeout=30)
            with (work / "output" / "mac-table-Devices.csv").open() as stream:
                assert len(list(csv.DictReader(stream))) == 240
            assert (work / "output" / "vendor_distribution.html").is_file()
            print("Passed:", " ".join(command))


if __name__ == "__main__":
    main()
