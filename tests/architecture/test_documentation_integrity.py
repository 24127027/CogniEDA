"""Source-backed architecture and documentation integrity checks for Package S4."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

DOCS_ROOT = Path("docs")
ROOT_README = Path("README.md")

_EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "file://", "data:")
_PHANTOM_IMPLEMENTATION_REFERENCES = {
    "src/application/bootstrap/runtime.py",
    "src/application/evaluation/control_service.py",
    "src/agents/executor/data_explorer/agent.py",
    "`EvaluationControlService`",
    "`EvidenceAdmissionService`",
    "`ProposalDecisionService`",
}


def _tracked_markdown_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", "*.md"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _extract_markdown_links(file_path: Path) -> list[tuple[str, str]]:
    content = file_path.read_text(encoding="utf-8")
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"`[^`\n]+`", "", content)
    return re.findall(r"!?\[([^\]]*)\]\(([^)]+)\)", content)


def _github_slug(heading: str) -> str:
    heading = re.sub(r"<[^>]+>", "", heading)
    heading = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", heading)
    heading = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
    heading = re.sub(r"[`*_~]", "", heading).strip().lower()
    heading = re.sub(r"[^\w\s-]", "", heading, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", heading).strip("-")


def _heading_anchors(file_path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is None:
            continue
        base = _github_slug(match.group(1))
        occurrence = counts.get(base, 0)
        counts[base] = occurrence + 1
        anchors.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return anchors


def _split_link_target(target: str) -> tuple[str, str]:
    target = target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    path_text, separator, fragment = target.partition("#")
    return unquote(path_text), unquote(fragment) if separator else ""


def test_all_tracked_markdown_relative_links_and_anchors_resolve() -> None:
    """Every tracked Markdown file must have valid local targets and heading anchors."""

    failures: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    repository_root = Path.cwd().resolve()

    for markdown_file in _tracked_markdown_files():
        for text, target in _extract_markdown_links(markdown_file):
            if target.startswith(_EXTERNAL_SCHEMES):
                continue
            path_text, fragment = _split_link_target(target)
            target_path = (
                repository_root / path_text.lstrip("/")
                if path_text.startswith("/")
                else markdown_file.parent / path_text
            )
            if not path_text:
                target_path = markdown_file
            target_path = target_path.resolve()
            if not target_path.exists():
                failures.append(
                    f"{markdown_file.as_posix()}: [{text}]({target}) -> missing "
                    f"{target_path.as_posix()}"
                )
                continue
            if fragment and target_path.suffix.lower() == ".md":
                anchors = anchor_cache.setdefault(target_path, _heading_anchors(target_path))
                if fragment.lower() not in anchors:
                    failures.append(
                        f"{markdown_file.as_posix()}: [{text}]({target}) -> missing "
                        f"anchor #{fragment} in {target_path.as_posix()}"
                    )

    assert not failures, "Broken local Markdown links or anchors:\n" + "\n".join(failures)


def test_docs_index_links_all_canonical_documents() -> None:
    """docs/index.md must link to every document in the canonical docs tree."""

    index_file = DOCS_ROOT / "index.md"
    index_content = index_file.read_text(encoding="utf-8")
    unindexed = [
        doc.relative_to(DOCS_ROOT).as_posix()
        for doc in DOCS_ROOT.rglob("*.md")
        if doc != index_file
        and doc.relative_to(DOCS_ROOT).as_posix() not in index_content
        and doc.name not in index_content
    ]
    assert not unindexed, f"Canonical documents missing from docs/index.md: {unindexed}"


def test_canonical_docs_do_not_name_phantom_implementation_surfaces() -> None:
    """Known false S4 source paths and class names must not return as implementation claims."""

    violations: list[str] = []
    canonical_files = [ROOT_README, *DOCS_ROOT.rglob("*.md")]
    for doc in canonical_files:
        content = doc.read_text(encoding="utf-8")
        for reference in _PHANTOM_IMPLEMENTATION_REFERENCES:
            if reference in content:
                violations.append(f"{doc.as_posix()}: {reference}")
    assert not violations, f"Phantom implementation references found: {violations}"


def test_unsupported_cli_or_service_claims_are_absent_from_canonical_docs() -> None:
    """Canonical docs must not advertise an implemented product process."""

    forbidden_claims = {
        "cognieda run --cli",
        "python -m cognieda.cli",
        "cognieda-service",
        "production HTTP REST API daemon running on port",
    }
    violations = [
        f"{doc.as_posix()}: {claim}"
        for doc in DOCS_ROOT.rglob("*.md")
        for claim in forbidden_claims
        if claim in doc.read_text(encoding="utf-8")
    ]
    assert not violations, f"Unsupported CLI/service claims found: {violations}"


def test_one_canonical_roadmap_exists() -> None:
    """Only docs/roadmap.md serves as the canonical roadmap."""

    roadmap_file = DOCS_ROOT / "roadmap.md"
    assert roadmap_file.exists()
    duplicates = [
        path.as_posix()
        for path in DOCS_ROOT.rglob("*.md")
        if "roadmap" in path.name.lower() and path != roadmap_file
    ]
    assert not duplicates, f"Duplicate roadmap files found: {duplicates}"


def test_major_documents_distinguish_implementation_status() -> None:
    """Major pages must state implementation status or a reviewed verdict explicitly."""

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
        *DOCS_ROOT.joinpath("workflows").glob("*.md"),
    ]
    missing = [
        doc.as_posix()
        for doc in major_docs
        if not re.search(
            r"implementation status|current implementation|final verdict|package 7 readiness",
            doc.read_text(encoding="utf-8"),
            flags=re.IGNORECASE,
        )
    ]
    assert not missing, f"Major documents omit implementation status: {missing}"
