"""Offline, standard-library helpers for the round-4 catalog and fixtures."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def local_path(name):
    path = ROOT / name
    if not isinstance(name, str) or Path(name).is_absolute() or not path.resolve().is_relative_to(ROOT):
        raise ValueError(f"path outside repository: {name}")
    return path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def pointer(value, path):
    if not path:
        return value
    if not path.startswith("/"):
        raise ValueError("expected RFC 6901 pointer")
    for part in path.split("/")[1:]:
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


class EvidenceReader:
    def __init__(self):
        self.sources = {}
        self.cache = {}

    def read(self, name):
        if name not in self.cache:
            data = local_path(name).read_bytes()
            encoding = "gzip-text" if name.endswith(".gz") else "json" if name.endswith(".json") else "text"
            info = {"path": name, "sha256": sha(data), "bytes": len(data), "encoding": encoding}
            if encoding == "gzip-text":
                data = gzip.decompress(data)
                info.update(raw_sha256=sha(data), raw_bytes=len(data))
            text = data.decode("utf-8")
            self.cache[name] = json.loads(text) if encoding == "json" else text
            self.sources[name] = info
        return self.cache[name]

    def artifact(self, manifest, key):
        data = self.read(manifest)
        artifact = data["artifacts"][key]
        path = (Path(manifest).parent / artifact["path"]).as_posix()
        self.read(path)
        source = self.sources[path]
        for actual, expected in ((source["sha256"], artifact["gzip_sha256"]),
                                 (source["raw_sha256"], artifact["raw_sha256"]),
                                 (source["bytes"], artifact["gzip_bytes"]),
                                 (source["raw_bytes"], artifact["raw_bytes"])):
            if actual != expected:
                raise ValueError(f"artifact integrity: {path}")
        source.update(manifest=manifest, artifact_key=key)
        return {"source": path, "pointer": ""}

    def extract(self, binding):
        value = pointer(self.read(binding["source"]), binding.get("pointer", ""))
        if "metric_lines" in binding:
            # Preserve complete observed exposition lines, including label sets.
            value = "\n".join(v["raw"] for v in value if v["name"] == binding["metric_lines"])
            if not value:
                raise ValueError("requested metric is absent")
        return value


def bind(source, path=""):
    return {"source": source, "pointer": path}


def write_or_check(path, content, check):
    target = local_path(path)
    if check:
        if not target.exists() or target.read_bytes() != content.encode("utf-8"):
            raise ValueError(f"generated file differs: {path}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
