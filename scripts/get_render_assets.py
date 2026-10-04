"""Fetch the pinned Mermaid browser bundle and its license, without running npm."""

import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "11.4.1"
INTEGRITY = "Mb01JT/x6CKDWaxigwfZYuYmDZ6xtrNwNlidKZwkSrDaY9n90tdrJTV5Umk+wP1fZscGptmKFXHsXMDEVZ+Q6A=="


def main():
    url = f"https://registry.npmjs.org/mermaid/-/mermaid-{VERSION}.tgz"
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    assert base64.b64encode(hashlib.sha512(data).digest()).decode() == INTEGRITY
    destination = ROOT / "assets"
    destination.mkdir(exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as bundle:
        # Extract explicit regular files only; no archive paths are written.
        for member, output in [("package/dist/mermaid.min.js", f"mermaid-{VERSION}.min.js"),
                               ("package/LICENSE", "LICENSE-mermaid.txt")]:
            info = bundle.getmember(member)
            assert info.isfile()
            content = bundle.extractfile(info).read()
            (destination / output).write_bytes(content)
    record = {"version": VERSION, "url": url, "archive_sha512_base64": INTEGRITY,
              "bundle_sha256": hashlib.sha256((destination / f"mermaid-{VERSION}.min.js").read_bytes()).hexdigest()}
    (destination / "mermaid-provenance.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
