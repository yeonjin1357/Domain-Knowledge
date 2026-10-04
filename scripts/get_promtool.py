"""Download one pinned official promtool release; verify its published checksum."""

import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.5.0"
ASSET = f"prometheus-{VERSION}.windows-amd64.zip"
BASE = f"https://github.com/prometheus/prometheus/releases/download/v{VERSION}"


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def main():
    destination = ROOT / ".tools" / f"prometheus-{VERSION}"
    destination.mkdir(parents=True, exist_ok=True)
    checksums = fetch(f"{BASE}/sha256sums.txt").decode("utf-8")
    expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1] == ASSET)
    archive = fetch(f"{BASE}/{ASSET}")
    actual = hashlib.sha256(archive).hexdigest()
    if actual != expected:
        raise SystemExit("Release checksum mismatch; no executable extracted")
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        members = [n for n in bundle.namelist() if n.endswith("/promtool.exe")]
        if len(members) != 1:
            raise SystemExit("Expected one promtool.exe")
        executable = bundle.read(members[0])
    (destination / "promtool.exe").write_bytes(executable)
    record = {"version": VERSION, "asset_url": f"{BASE}/{ASSET}",
              "checksum_url": f"{BASE}/sha256sums.txt", "archive_sha256": actual,
              "executable_sha256": hashlib.sha256(executable).hexdigest()}
    (destination / "provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
