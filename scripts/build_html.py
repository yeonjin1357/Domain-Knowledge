"""Build a self-contained Korean reading edition, with offline Mermaid diagrams."""

import argparse
import hashlib
from html import escape
import json
import re

from markdown_it import MarkdownIt

from build_book import render_book
from doc_utils import ROOT, chapter_id, manifest

CSS = """
:root{color-scheme:light;--ink:#1c2e3c;--muted:#506271;--line:#d9e1e6;--accent:#126270}
*{box-sizing:border-box}html{scroll-behavior:auto}body{margin:0;background:#fff;color:var(--ink);font-family:'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;font-size:16px;line-height:1.85}
aside{position:fixed;inset:0 auto 0 0;width:296px;background:#f3f6f8;border-right:1px solid var(--line);padding:24px 18px;overflow:auto;z-index:5}
.brand{font-size:18px;font-weight:750;line-height:1.5;margin:0 0 8px}.edition{font-size:12px;color:var(--muted)}
input{font:inherit;font-size:14px;width:100%;border:1px solid #a3b5c0;border-radius:6px;padding:9px 11px;margin:16px 0;background:white;color:var(--ink)}
nav details{margin-bottom:12px}nav summary{font-weight:700;cursor:pointer;font-size:14px}nav ul{list-style:none;padding:0 0 0 8px;margin:6px 0}nav li{font-size:13px;line-height:1.55;padding:5px 0}nav a{text-decoration:none;color:#3c5668}nav a:hover{color:var(--accent);text-decoration:underline}
main{margin-left:296px;padding:48px 54px 100px;max-width:1360px}h1,h2,h3,h4{line-height:1.5;letter-spacing:-.025em;overflow-wrap:anywhere}h1{font-size:34px;margin-top:0}h2{font-size:29px;margin-top:32px}h3{font-size:23px;margin-top:40px}h4{font-size:19px;margin-top:32px}
p,li,td,th{overflow-wrap:anywhere}p{margin:16px 0}a{color:var(--accent);text-underline-offset:3px}a[id]{display:block;height:0;scroll-margin-top:24px}blockquote{margin:24px 0;padding:4px 18px;border-left:4px solid #81b4bd;background:#f2f7f8;color:#435967;font-size:14px}blockquote p{margin:10px 0}
.table-wrap{overflow-x:auto;margin:24px 0;border:1px solid var(--line);border-radius:6px}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.7}th,td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top;min-width:96px;text-align:left}th{background:#edf3f5;font-weight:700}tr:last-child td{border-bottom:0}tr:nth-child(even){background:#fafbfc}
code{font-family:Consolas,'SFMono-Regular',monospace;background:#eff2f4;padding:2px 4px;border-radius:3px;font-size:.92em}pre{overflow-x:auto;line-height:1.65;background:#142936;color:#e2eff5;padding:20px 22px;border-radius:7px;font-size:14px}pre code{background:none;padding:0;color:inherit;white-space:pre}
hr{border:0;border-top:2px solid var(--line);margin:64px 0 32px}strong{font-weight:750}li{margin:5px 0}.diagram{margin:28px 0;padding:20px 8px;border:1px solid var(--line);border-radius:8px}.mermaid{text-align:center;overflow:auto}.mermaid svg{max-width:100%;height:auto}.diagram details{font-size:12px;color:var(--muted);margin:12px}.diagram pre{text-align:left}.reader-note{padding:16px 20px;border:1px solid #bad4da;background:#f3f9fa;border-radius:8px;font-size:14px}.top-link{position:fixed;right:20px;bottom:18px;background:#126270;color:#fff;border-radius:24px;padding:7px 15px;text-decoration:none;font-size:13px}.mobile-menu{display:none}small{color:var(--muted)}
@media(min-width:1600px){main{margin-left:calc(296px + (100vw - 1600px)/2)}}
@media(max-width:900px){aside{position:relative;width:auto;max-height:54vh;border-bottom:1px solid var(--line);padding:18px 22px}aside nav{display:none}aside:focus-within nav,aside.open nav{display:block}.mobile-menu{display:block;font:inherit;background:white;color:var(--ink);border:1px solid #a3b5c0;padding:7px 14px;border-radius:5px;margin-top:10px}main{margin:0;padding:30px 22px 70px}h1{font-size:28px}h2{font-size:25px}h3{font-size:21px}body{font-size:15px}th,td{padding:10px;min-width:130px}}
@media print{aside,.top-link,.diagram details{display:none}main{margin:0;padding:0;max-width:none}body{font-size:10pt}h2{break-before:page}h2,h3,h4{break-after:avoid}pre{white-space:pre-wrap;background:#f4f4f4;color:#111}pre code{white-space:pre-wrap}a{color:inherit}table{font-size:9pt}.table-wrap{overflow:visible}tr{break-inside:avoid}}
"""

JS = """
const sidebar=document.querySelector('aside');
document.querySelector('.mobile-menu').addEventListener('click',()=>{sidebar.classList.toggle('open');document.querySelector('.mobile-menu').setAttribute('aria-expanded',String(sidebar.classList.contains('open')))});
document.getElementById('toc-search').addEventListener('input',e=>{const q=e.target.value.trim().toLocaleLowerCase();document.querySelectorAll('nav details').forEach(group=>{let visible=0;group.querySelectorAll('li').forEach(li=>{li.hidden=!li.textContent.toLocaleLowerCase().includes(q);if(!li.hidden)visible++});group.hidden=!visible;group.open=true})});
window.__bookErrors=[];
mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',themeVariables:{fontFamily:'Malgun Gothic, sans-serif',fontSize:'14px',primaryColor:'#eaf3f5',primaryTextColor:'#1c2e3c',primaryBorderColor:'#4c8290',lineColor:'#466778'},flowchart:{htmlLabels:false,useMaxWidth:true}});
mermaid.run({querySelector:'.mermaid'}).catch(e=>{window.__bookErrors.push(String(e))}).finally(()=>{
  document.documentElement.dataset.renderedDiagrams=String(document.querySelectorAll('.mermaid svg').length);
  document.documentElement.dataset.diagramErrors=String(window.__bookErrors.length);
  document.documentElement.dataset.missingAnchors=String([...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).length);
  document.documentElement.dataset.bookReady='true';
  document.documentElement.dataset.viewportWidth=String(innerWidth);
  document.documentElement.dataset.documentWidth=String(document.documentElement.scrollWidth);
  document.documentElement.dataset.requestedAnchorExists=String(!location.hash||Boolean(document.getElementById(decodeURIComponent(location.hash.slice(1)))));
  if(location.hash){try{document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView()}catch(e){}}
});
"""


def render_html():
    config = manifest()
    markdown, _ = render_book()
    start = markdown.index("## 목차\n")
    end = markdown.index("\n---\n", start)
    markdown = markdown[:start] + '<div class="reader-note">목차에서 장을 고르거나 브라우저의 <strong>Ctrl+F</strong>로 본문을 검색하세요. 그림과 본문은 인터넷 없이 읽을 수 있습니다. 출처와 실행 스크립트 링크는 별도 자료입니다.</div>\n' + markdown[end:]
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    original_fence = md.renderer.rules["fence"]

    def fence(tokens, idx, options, env):
        token = tokens[idx]
        if token.info.strip() == "mermaid":
            source = escape(token.content)
            return f'<figure class="diagram"><div class="mermaid">{source}</div><details><summary>그림의 원문 보기</summary><pre><code>{source}</code></pre></details></figure>\n'
        return original_fence(tokens, idx, options, env)

    md.renderer.rules["fence"] = fence
    body = md.render(markdown)
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    navigation = []
    for section in config["sections"]:
        navigation.append(f'<details open><summary>{escape(section["title"])}</summary><ul>')
        for name in section["chapters"]:
            path = ROOT / name
            title = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
            navigation.append(f'<li><a href="#{chapter_id(path)}">{escape(title)}</a></li>')
        navigation.append("</ul></details>")
    bundle = (ROOT / "assets/mermaid-11.4.1.min.js").read_bytes()
    record = json.loads((ROOT / "assets/mermaid-provenance.json").read_text())
    assert hashlib.sha256(bundle).hexdigest() == record["bundle_sha256"]
    script = bundle.decode("utf-8").replace("</script", "<\\/script")
    return (f'<!doctype html>\n<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(config["title"])} · 제{config["edition"]}판</title><style>{CSS}</style></head><body>'
            f'<aside aria-label="책 목차"><p class="brand">통합 모니터링<br>도메인 지식서</p><div class="edition">제{config["edition"]}판 · {config["detailed_chapters"]}개 상세 장 · {config["as_of"]}</div>'
            '<button class="mobile-menu" aria-expanded="false">목차 열기 / 닫기</button><label for="toc-search" class="edition">장 제목 검색</label><input id="toc-search" type="search" placeholder="예: CPU, 연결 풀, 복제" autocomplete="off">'
            f'<nav>{"".join(navigation)}</nav></aside><main id="reading-content">{body}</main><a class="top-link" href="#book-top">맨 위로</a>'
            '<!-- Mermaid 11.4.1: MIT license, assets/LICENSE-mermaid.txt. Bundle embedded for offline reading. -->'
            f'<script>{script}</script><script>{JS}</script></body></html>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = render_html()
    path = ROOT / "BOOK.html"
    if args.check:
        assert path.exists() and path.read_text(encoding="utf-8") == result, "BOOK.html differs from sources"
        print("PASS: BOOK.html matches source documents and pinned renderer")
    else:
        path.write_text(result, encoding="utf-8", newline="\n")
        print(f"Built BOOK.html: {len(result.encode('utf-8')):,} bytes; self-contained diagrams")


if __name__ == "__main__":
    main()
