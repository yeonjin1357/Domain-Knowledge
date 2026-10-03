"""Small Markdown helpers for this repository; no external dependencies."""

from collections import Counter
from pathlib import Path
import json
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
EXPLICIT_ID = re.compile(r'<a\s+id="([^"]+)"\s*>\s*</a>')
# All source links use an inline label and a destination without a title.
LINK_START = re.compile(r"\[[^\]\n]*\]\(")


def manifest():
    return json.loads((ROOT / "book.json").read_text(encoding="utf-8"))


def content_lines(text):
    """Yield numbered non-fenced lines; code examples are never executed."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if fence:
            if (match and match[1][0] == fence[0]
                    and len(match[1]) >= fence[1] and not match[2].strip()):
                fence = None
            continue
        if match:
            fence = (match[1][0], len(match[1]))
            continue
        yield number, line
    if fence:
        raise ValueError("Unclosed fenced code block")


def slug(title):
    # GitHub-style anchors for the headings used in this repository.
    title = re.sub(r"<[^>]*>", "", title)
    title = re.sub(r"[^\w\- ]", "", title.lower(), flags=re.UNICODE)
    return title.replace(" ", "-")


def headings(text):
    seen = Counter()
    for number, line in content_lines(text):
        match = HEADING.match(line)
        if match:
            base = slug(match[2])
            suffix = f"-{seen[base]}" if seen[base] else ""
            seen[base] += 1
            yield number, len(match[1]), match[2], base + suffix


def links(line):
    """Yield (destination start, end, text), respecting nested parentheses."""
    for match in LINK_START.finditer(line):
        start = match.end()
        position, depth = start, 1
        while position < len(line):
            char = line[position]
            if char == "\\":
                position += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    yield start, position, line[start:position].strip().strip("<>")
                    break
            position += 1


def local_target(source, destination):
    parts = urlsplit(destination)
    if parts.scheme or parts.netloc:
        return None
    target = (source.parent / unquote(parts.path)).resolve() if parts.path else source
    return target, unquote(parts.fragment)


def chapter_id(path):
    relative = path.relative_to(ROOT).with_suffix("").as_posix()
    return "chapter-" + relative.replace("/", "-").lower()
