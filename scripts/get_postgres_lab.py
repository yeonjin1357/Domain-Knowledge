"""Extract pinned official PostgreSQL packages locally on Ubuntu 24.04 amd64.

No sudo, apt configuration change, package installation, or system service.
The HTTPS index hashes are recorded in labs/postgresql/packages.json.
"""

import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("Run in Ubuntu 24.04 amd64 (including WSL), not Windows Python")
    manifest = json.loads((ROOT / "labs/postgresql/packages.json").read_text())
    destination = ROOT / ".tools/pg18"
    archive_dir = ROOT / ".tools/pg18-archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for entry in manifest["packages"]:
        archive = archive_dir / Path(entry["Filename"]).name
        if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != entry["SHA256"]:
            url = entry["url"]
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != entry["SHA256"]:
                raise SystemExit("Package checksum mismatch: " + entry["Package"])
            archive.write_bytes(data)
        subprocess.run(["dpkg-deb", "--extract", str(archive), str(destination)], check=True)
        print(entry["Package"] + " " + entry["Version"] + ": hash verified; extracted", flush=True)
    executable = destination / "usr/lib/postgresql/18/bin/postgres"
    env = dict(os.environ, LD_LIBRARY_PATH=str(destination / "usr/lib/x86_64-linux-gnu"))
    subprocess.run([str(executable), "--version"], check=True, env=env)


if __name__ == "__main__":
    main()
