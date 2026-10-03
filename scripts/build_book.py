"""Build a single readable book, with in-book links and stable anchors."""

import argparse

from doc_utils import (
    ROOT, chapter_id, content_lines, headings, links,
    local_target, manifest,
)


def render_book():
    config = manifest()
    paths = [ROOT / name for section in config["sections"] for name in section["chapters"]]
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate chapter in book.json")
    texts = {p.resolve(): p.read_text(encoding="utf-8") for p in paths}
    ids = {p: chapter_id(p) for p in texts}
    titles = {p: next(h[2] for h in headings(t) if h[1] == 1) for p, t in texts.items()}
    fragments = {p: {h[3] for h in headings(t)} for p, t in texts.items()}

    def rewrite_link(source, destination):
        target = local_target(source, destination)
        if target is None:
            return destination
        path, fragment = target
        if path in ids:
            if fragment:
                if fragment not in fragments[path]:
                    raise ValueError(f"Unknown heading: {source}: {destination}")
                return f"#{ids[path]}--{fragment}"
            return f"#{ids[path]}"
        if path in {(ROOT / "README.md").resolve(), (ROOT / "BOOK.md").resolve()}:
            if fragment:
                raise ValueError(f"Unmapped book/root fragment: {destination}")
            return "#book-top"
        # Scripts and manifest stay as repository resources, not embedded code.
        relative = path.relative_to(ROOT).as_posix()
        return relative + (f"#{fragment}" if fragment else "")

    output = [
        '<a id="book-top"></a>', "", f'# {config["title"]}', "",
        f'> 기준일: {config["as_of"]} · 분야별 원문에서 생성한 통합본 · 상세 본문 58장', "",
        "통합 모니터링 제품을 설계·구현하는 개발자를 위한 지식서입니다. 공식 자료로 확인한 설명, 가상 계산, 설계 제안을 구분합니다.", "",
        "이 파일 안에서 장 사이를 이동할 수 있습니다. 원문은 docs/에서 관리하며, 명령·쿼리 예시의 실환경 실행 검증은 별도로 필요합니다.", "",
        "## 목차", "",
    ]
    for section in config["sections"]:
        output.append(f'- **{section["title"]}**')
        for name in section["chapters"]:
            path = (ROOT / name).resolve()
            output.append(f"  - [{titles[path]}](#{ids[path]})")
    output.append("")

    for path in paths:
        path = path.resolve()
        text = texts[path]
        ordinary_lines = dict(content_lines(text))
        heading_map = {h[0]: h for h in headings(text)}
        output.extend(["---", "", f'<a id="{ids[path]}"></a>', ""])
        for number, line in enumerate(text.splitlines(), 1):
            if number not in ordinary_lines:
                output.append(line)
                continue
            if number in heading_map:
                _, level, title, fragment = heading_map[number]
                output.extend([f'<a id="{ids[path]}--{fragment}"></a>', ""])
                line = "#" * min(level + 1, 6) + " " + title
            for start, end, destination in reversed(list(links(line))):
                line = line[:start] + rewrite_link(path, destination) + line[end:]
            output.append(line)
        output.extend(["", "[통합 목차로](#book-top)", ""])
    return "\n".join(output).rstrip() + "\n", len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if BOOK.md is stale")
    args = parser.parse_args()
    content, count = render_book()
    destination = ROOT / "BOOK.md"
    if args.check:
        if not destination.exists() or destination.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: BOOK.md differs from sources; run build_book.py")
        print(f"PASS: BOOK.md matches {count} source documents")
    else:
        destination.write_text(content, encoding="utf-8", newline="\n")
        print(f"Built BOOK.md: {count} documents, {len(content.splitlines())} lines, {len(content.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    main()
