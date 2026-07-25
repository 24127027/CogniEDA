"""Automated architecture and documentation integrity test suite for Package S4."""

from __future__ import annotations

import re
from pathlib import Path

DOCS_ROOT = Path("docs")
ROOT_README = Path("README.md")
SOURCE_ROOT = Path("src")


def _extract_markdown_links(file_path: Path) -> list[tuple[str, str]]:
    """Extract (link_text, link_target) tuples from a markdown file."""
    content = file_path.read_text(encoding="utf-8")
    content_no_code = re.sub(r"```[\s\S]*?```", "", content)
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    return pattern.findall(content_no_code)


def test_internal_markdown_links_resolve() -> None:
    """All internal markdown links in docs/ and root README.md must resolve to existing files."""
    doc_files = list(DOCS_ROOT.rglob("*.md")) + [ROOT_README]
    missing_links: list[str] = []

    for doc_file in doc_files:
        links = _extract_markdown_links(doc_file)
        for text, target in links:
            if target.startswith(("http://", "https://", "mailto:", "file://")):
                continue
            clean_target = target.split("#")[0]
            if not clean_target:
                continue

            resolved_path = (doc_file.parent / clean_target).resolve()

            if not resolved_path.exists():
                missing_links.append(
                    f"{doc_file.as_posix()}: link [{text}]({target}) "
                    f"resolves to missing path {resolved_path.as_posix()}"
                )

    assert not missing_links, (
        "Broken internal documentation links found:\n" + "\n".join(missing_links)
    )


def test_docs_index_links_all_canonical_documents() -> None:
    """docs/index.md must link to every canonical document in docs/."""
    index_file = DOCS_ROOT / "index.md"
    assert index_file.exists(), "docs/index.md must exist"

    index_content = index_file.read_text(encoding="utf-8")
    unindexed_docs: list[str] = []

    for doc in DOCS_ROOT.rglob("*.md"):
        rel_path = doc.relative_to(DOCS_ROOT).as_posix()
        if rel_path == "index.md":
            continue

        if rel_path not in index_content and doc.name not in index_content:
            unindexed_docs.append(rel_path)

    assert not unindexed_docs, f"Canonical documents missing from docs/index.md: {unindexed_docs}"


def test_unsupported_cli_or_service_claims_are_absent_from_canonical_docs() -> None:
    """Canonical docs must not describe product CLI, REST API, or worker daemon as implemented."""
    forbidden_claims = [
        "cognieda run --cli",
        "python -m cognieda.cli",
        "cognieda-service",
        "production HTTP REST API daemon running on port",
    ]
    violations: list[str] = []

    for doc in DOCS_ROOT.rglob("*.md"):
        content = doc.read_text(encoding="utf-8")
        for claim in forbidden_claims:
            if claim in content:
                violations.append(f"{doc.as_posix()}: contains forbidden product claim {claim!r}")

    assert not violations, f"Unsupported CLI/service claims found in documentation: {violations}"


def test_one_canonical_roadmap_exists() -> None:
    """Only docs/roadmap.md must serve as the single canonical roadmap."""
    roadmap_file = DOCS_ROOT / "roadmap.md"
    assert roadmap_file.exists(), "docs/roadmap.md must exist as canonical roadmap"

    other_roadmaps = [
        p.as_posix()
        for p in DOCS_ROOT.rglob("*.md")
        if "roadmap" in p.name.lower() and p != roadmap_file
    ]
    assert not other_roadmaps, f"Duplicate roadmap files found: {other_roadmaps}"


def test_explicit_status_markers_in_major_documents() -> None:
    """Major canonical documentation files must include explicit status markers."""
    major_docs = [
        DOCS_ROOT / "project-purpose.md",
        DOCS_ROOT / "roadmap.md",
        DOCS_ROOT / "architecture" / "overview.md",
        DOCS_ROOT / "architecture" / "research-state-model.md",
        DOCS_ROOT / "architecture" / "scientific-specialist-contracts.md",
        DOCS_ROOT / "architecture" / "context-type-safety.md",
        DOCS_ROOT / "architecture" / "bounded-contexts.md",
        DOCS_ROOT / "architecture" / "runtime-composition.md",
        DOCS_ROOT / "architecture" / "persistence-and-transactions.md",
        DOCS_ROOT / "architecture" / "validity-and-invalidation.md",
        DOCS_ROOT / "architecture" / "retrieval-and-session-frame.md",
        DOCS_ROOT / "architecture" / "migrations.md",
        DOCS_ROOT / "architecture" / "module-responsibilities.md",
        DOCS_ROOT / "architecture" / "structural-exit-status.md",
    ]
    status_markers = {
        "[Implemented]",
        "[Verified on SQLite]",
        "[Partially Implemented]",
        "[Design Target]",
        "[Deferred]",
        "[Known Deviation]",
        "[Unsupported]",
    }

    missing_markers: list[str] = []
    for doc in major_docs:
        assert doc.exists(), f"Major document missing: {doc.as_posix()}"
        content = doc.read_text(encoding="utf-8")
        if not any(marker in content for marker in status_markers):
            missing_markers.append(doc.as_posix())

    assert not missing_markers, (
        f"Major documents missing explicit status markers: {missing_markers}"
    )
