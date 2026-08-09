from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
COMPATIBILITY_ONLY_PHRASES = (
    "retained only for link compatibility",
    "retained for link compatibility",
    "retained for compatibility",
    "path is retained for compatibility",
)


def _slug(heading: str) -> str:
    value = re.sub(r"<[^>]+>", "", heading)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = value.replace("`", "").replace("*", "").replace("_", "")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"\s+", "-", value.strip())


def _anchors(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    for heading in HEADING.findall(path.read_text(encoding="utf-8")):
        base = _slug(heading)
        occurrence = seen.get(base, 0)
        seen[base] = occurrence + 1
        anchors.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return anchors


def test_docs_have_no_compatibility_only_redirects() -> None:
    violations = [
        path.relative_to(PROJECT_ROOT)
        for path in DOCS_ROOT.rglob("*.md")
        if any(
            phrase in path.read_text(encoding="utf-8").lower()
            for phrase in COMPATIBILITY_ONLY_PHRASES
        )
    ]

    assert violations == []


def test_docs_internal_links_and_anchors_resolve() -> None:
    violations: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}

    for source in DOCS_ROOT.rglob("*.md"):
        text = source.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            raw_target = match.group(1).strip().strip("<>")
            if raw_target.startswith(("http://", "https://", "mailto:")):
                continue
            target_text, _, raw_anchor = raw_target.partition("#")
            target = source if not target_text else (source.parent / unquote(target_text)).resolve()
            line = text.count("\n", 0, match.start()) + 1
            label = f"{source.relative_to(PROJECT_ROOT)}:{line}"

            if not target.is_file():
                violations.append(f"{label}: missing {raw_target}")
                continue
            if raw_anchor:
                anchors = anchor_cache.setdefault(target, _anchors(target))
                anchor = unquote(raw_anchor).lower()
                if anchor not in anchors:
                    violations.append(f"{label}: missing anchor {raw_target}")

    assert violations == []
