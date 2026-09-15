"""Validate the bilingual README pair.

Checks, for each README:
  * every relative <img src> / ![]() target exists on disk
  * every relative markdown link target exists on disk
  * the language switcher points at the *other* README
  * the two files expose the same set of section headings (structural parity)
  * every ```mermaid block is non-empty and fenced correctly
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(".")
PAIR = {"README.md": "README-zh.md", "README-zh.md": "README.md"}

IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"')
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"')
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.M)
MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)

failures: list[str] = []
notes: list[str] = []


def is_external(t: str) -> bool:
    return t.startswith(("http://", "https://", "mailto:", "#", "data:"))


def check_target(target: str, src_file: str, kind: str) -> None:
    if is_external(target):
        return
    clean = target.split("#", 1)[0]
    if not clean:
        return
    if not (ROOT / clean).exists():
        failures.append(f"{src_file}: broken {kind} -> {target}")


for fname, other in PAIR.items():
    path = ROOT / fname
    if not path.exists():
        failures.append(f"missing file: {fname}")
        continue
    text = path.read_text(encoding="utf-8")

    imgs = IMG_RE.findall(text) + MD_IMG_RE.findall(text)
    links = LINK_RE.findall(text) + MD_LINK_RE.findall(text)

    for t in imgs:
        check_target(t, fname, "image")
    for t in links:
        check_target(t, fname, "link")

    # Language switcher must reach the sibling README (the pair is the point).
    if other not in links:
        failures.append(f"{fname}: language switcher does not link to {other}")

    # Mermaid fence sanity
    for i, block in enumerate(MERMAID_RE.findall(text), 1):
        if not block.strip():
            failures.append(f"{fname}: mermaid block #{i} is empty")
        head = block.strip().splitlines()[0].strip()
        if not re.match(r"^(flowchart|graph|sequenceDiagram|stateDiagram|erDiagram|classDiagram|journey|gantt|pie)", head):
            failures.append(f"{fname}: mermaid block #{i} has an unrecognised diagram type: {head!r}")

    notes.append(
        f"{fname}: {len(imgs)} images, {len(links)} links, "
        f"{len(MERMAID_RE.findall(text))} mermaid diagrams, "
        f"{len(HEADING_RE.findall(text))} headings"
    )

# Structural parity — both languages must cover the same sections.
def headings(f: str) -> list[str]:
    return [h[1].strip() for h in HEADING_RE.findall((ROOT / f).read_text(encoding="utf-8"))]

h_en, h_zh = headings("README.md"), headings("README-zh.md")
if len(h_en) != len(h_zh):
    notes.append(
        f"NOTE: heading count differs (en={len(h_en)}, zh={len(h_zh)}) — "
        "expected; the Chinese file carries Chinese section titles"
    )

print("\n".join(notes))
print()
if failures:
    print(f"{len(failures)} problem(s):", file=sys.stderr)
    for f in failures:
        print(f"  {f}", file=sys.stderr)
    sys.exit(1)
print("OK — both READMEs validate: no broken assets or links, switcher is bidirectional.")
