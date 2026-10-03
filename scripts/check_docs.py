"""Check Markdown structure, local targets, anchors, and book coverage."""

from collections import Counter
import re

from doc_utils import ROOT, EXPLICIT_ID, content_lines, headings, links, local_target, manifest


def main():
    errors, documents, anchors = [], {}, {}
    files = sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)
    for path in files:
        name = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8-sig")
            if "\ufffd" in text:
                errors.append(f"{name}: Unicode replacement character")
            if "\x00" in text:
                errors.append(f"{name}: NUL character")
            ordinary = list(content_lines(text))
            hs = list(headings(text))
            if sum(h[1] == 1 for h in hs) != 1:
                errors.append(f"{name}: expected exactly one H1")
            explicit = [a for _, line in ordinary for a in EXPLICIT_ID.findall(line)]
            for duplicate, count in Counter(explicit).items():
                if count > 1:
                    errors.append(f"{name}: duplicate explicit anchor {duplicate}")
            anchors[path] = set(explicit) | {h[3] for h in hs}
            documents[path] = ordinary
            for number, line in enumerate(text.splitlines(), 1):
                if line.rstrip() != line:
                    errors.append(f"{name}:{number}: trailing whitespace")
        except (UnicodeError, ValueError) as exc:
            errors.append(f"{name}: {exc}")

    local_count, external_urls = 0, set()
    for source, lines in documents.items():
        name = source.relative_to(ROOT).as_posix()
        for number, line in lines:
            for _, _, destination in links(line):
                result = local_target(source, destination)
                if result is None:
                    if destination.startswith(("https://", "http://")):
                        external_urls.add(destination.split("#", 1)[0])
                    continue
                local_count += 1
                target, fragment = result
                if not target.is_relative_to(ROOT):
                    errors.append(f"{name}:{number}: local link outside repository: {destination}")
                elif not target.exists():
                    errors.append(f"{name}:{number}: missing target: {destination}")
                elif fragment and target.suffix == ".md" and fragment not in anchors.get(target, set()):
                    errors.append(f"{name}:{number}: missing anchor: {destination}")

    config = manifest()
    listed = [ROOT / p for s in config["sections"] for p in s["chapters"]]
    expected = set(files) - {ROOT / "README.md", ROOT / "BOOK.md"}
    if set(listed) != expected:
        errors.append(f"Manifest coverage mismatch: missing={expected - set(listed)}, extra={set(listed) - expected}")
    if len(set(listed)) != len(listed):
        errors.append("book.json: duplicate source document")
    detailed = [p for p in files if p.parent.parent == ROOT / "docs" and p.name != "README.md"]
    for path in detailed:
        text = path.read_text(encoding="utf-8")
        if len(text.splitlines()) < 35:
            errors.append(f"{path}: detailed chapter too short")
        if not re.search(r"^## .*이해 확인", text, re.MULTILINE) or "> 상태:" not in text:
            errors.append(f"{path}: missing scope/status or comprehension section")
        if path.parent.name != "cross-domain" and "https://" not in text:
            errors.append(f"{path}: missing primary-source link")
        index_text = (path.parent / "README.md").read_text(encoding="utf-8")
        if f"]({path.name})" not in index_text:
            errors.append(f"{path}: missing domain index link")
    if len(detailed) != 58:
        errors.append(f"Expected 58 detailed chapters, found {len(detailed)}; update count claims")
    if errors:
        print("\n".join(errors))
        raise SystemExit(f"FAIL: {len(errors)} documentation issues")
    print(f"PASS: {len(files)} Markdown files; {len(detailed)} detailed chapters; {local_count} local links; {len(external_urls)} distinct external URLs")
    print("Checked: UTF-8, headings, fences, local paths/anchors, manifest coverage, chapter indexing")
    print("External URLs are inventoried, not automatically revalidated by this script")


if __name__ == "__main__":
    main()
