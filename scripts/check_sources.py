"""Inventory and fetch cited primary-source URLs. HTTP success is not a fact check."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

from doc_utils import ROOT, content_lines, links


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "DomainKnowledge-SourceReview/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(8_000_000)
            kind = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            title = ""
            if "html" in kind:
                match = re.search(r"<title[^>]*>(.*?)</title>", body.decode(charset, errors="replace"), re.S | re.I)
                if match:
                    title = " ".join(unescape(re.sub("<[^>]+>", "", match[1])).split())
            return {"status": response.status, "final_url": response.url,
                    "content_type": kind, "title": title,
                    "body_bytes_up_to_limit": len(body), "body_sha256": hashlib.sha256(body).hexdigest()}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "error": str(exc.reason)}
    except (OSError, ValueError, LookupError) as exc:
        return {"status": None, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".lab-runs/source-status.json")
    args = parser.parse_args()
    inventory = {}
    for path in sorted((ROOT / "docs").rglob("*.md")):
        for _, line in content_lines(path.read_text(encoding="utf-8")):
            for _, _, url in links(line):
                if url.startswith("https://"):
                    inventory.setdefault(url.split("#", 1)[0], set()).add(path.relative_to(ROOT).as_posix())
    results = {}
    with ThreadPoolExecutor(max_workers=8) as workers:
        pending = {workers.submit(fetch, url): url for url in inventory}
        for future in as_completed(pending):
            url = pending[future]
            results[url] = dict(future.result(), cited_by=sorted(inventory[url]))
    failures = {url: entry for url, entry in results.items() if entry["status"] != 200}
    record = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "meaning": "Availability inventory only. HTTP 200 does not verify claims or anchor fragments.",
              "url_count": len(results), "http_200_count": len(results)-len(failures),
              "sources": dict(sorted(results.items()))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Fetched {len(results)} cited URLs; {len(failures)} require availability review")
    for url, entry in sorted(failures.items()):
        print(f"{entry['status']}: {url}")


if __name__ == "__main__":
    main()
