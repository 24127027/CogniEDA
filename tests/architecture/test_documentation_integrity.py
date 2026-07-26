"""Source-backed architecture and canonical documentation integrity checks."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

DOCS_ROOT = Path("docs")
ROOT_README = Path("README.md")
PHASE_1_CANONICAL_PAGES = (
    DOCS_ROOT / "what-is-cognieda.md",
    DOCS_ROOT / "problem-and-thesis.md",
    DOCS_ROOT / "research-state-model.md",
    DOCS_ROOT / "from-question-to-discovery.md",
)
PHASE_3A_CANONICAL_PAGES = (DOCS_ROOT / "design-decisions-and-tradeoffs.md",)
PHASE_2A_CANONICAL_PAGES = (
    DOCS_ROOT / "scientific-authority.md",
    DOCS_ROOT / "protected-evaluation-context.md",
    DOCS_ROOT / "governance-and-discovery-admission.md",
    DOCS_ROOT / "from-execution-to-discovery.md",
)
PHASE_2B1_CANONICAL_PAGES = (
    DOCS_ROOT / "session-frame-and-active-context.md",
    DOCS_ROOT / "retrieval-and-context-type-safety.md",
    DOCS_ROOT / "context-reconstruction-and-continuity.md",
    DOCS_ROOT / "from-research-state-to-active-context.md",
)
PHASE_2B2_CANONICAL_PAGES = (
    DOCS_ROOT / "validity-over-time.md",
    DOCS_ROOT / "atomic-validity-propagation.md",
    DOCS_ROOT / "invalidation-and-active-retrieval.md",
    DOCS_ROOT / "from-validity-change-to-reconstructed-context.md",
)
PHASE_2B_CANONICAL_PAGES = (
    *PHASE_2B1_CANONICAL_PAGES,
    *PHASE_2B2_CANONICAL_PAGES,
)
PHASE_3B1_CANONICAL_PAGES = (
    DOCS_ROOT / "runtime-and-composition-boundary.md",
    DOCS_ROOT / "persistence-and-transaction-ownership.md",
    DOCS_ROOT / "sqlite-boundary-and-portability.md",
    DOCS_ROOT / "database-initialization-and-migrations.md",
    DOCS_ROOT / "from-runtime-composition-to-atomic-persistence.md",
)
PHASE_3B2_CANONICAL_PAGES = (
    DOCS_ROOT / "planner-boundary-and-operation-model.md",
    DOCS_ROOT / "from-user-request-to-approved-operation.md",
    DOCS_ROOT / "retrieval-strategy-and-scaling.md",
    DOCS_ROOT / "session-frame-scaling-and-resume-boundary.md",
    DOCS_ROOT / "product-surface-and-bootstrap-boundary.md",
)
CORE_EPISTEMIC_ADRS = (
    DOCS_ROOT / "decisions" / "ADR-001-first-class-research-state.md",
    DOCS_ROOT / "decisions" / "ADR-002-assumption-quarantine.md",
    DOCS_ROOT / "decisions" / "ADR-003-specialist-scientific-authority.md",
    DOCS_ROOT / "decisions" / "ADR-004-atomic-discovery-admission.md",
    DOCS_ROOT / "decisions" / "ADR-005-atomic-validity-propagation.md",
)
SQLITE_BOUNDARY_ADR = (
    DOCS_ROOT / "decisions" / "ADR-006-sqlite-supported-boundary.md"
)
PRODUCT_BOOTSTRAP_ADR = (
    DOCS_ROOT
    / "decisions"
    / "ADR-007-no-supported-cli-before-product-bootstrap.md"
)
COMPLETE_DECISION_ANATOMY_ADRS = (
    *CORE_EPISTEMIC_ADRS,
    SQLITE_BOUNDARY_ADR,
    PRODUCT_BOOTSTRAP_ADR,
)
PHASE_3A_DECISION_PAGES = (*PHASE_3A_CANONICAL_PAGES, *CORE_EPISTEMIC_ADRS)
CANONICAL_READER_PAGES = (
    *PHASE_1_CANONICAL_PAGES,
    *PHASE_3A_CANONICAL_PAGES,
    *PHASE_2A_CANONICAL_PAGES,
    *PHASE_2B_CANONICAL_PAGES,
    *PHASE_3B1_CANONICAL_PAGES,
    *PHASE_3B2_CANONICAL_PAGES,
)
CANONICAL_FOUNDATION = (ROOT_README, DOCS_ROOT / "index.md", *CANONICAL_READER_PAGES)
READER_FACING_CURRENT_STATE_PAGES = (
    DOCS_ROOT / "project-purpose.md",
    DOCS_ROOT / "roadmap.md",
    DOCS_ROOT / "architecture" / "overview.md",
    DOCS_ROOT / "architecture" / "implementation-gap-analysis.md",
    DOCS_ROOT / "architecture" / "runtime-composition.md",
    DOCS_ROOT / "architecture" / "structural-exit-status.md",
)
CHECKOUT_EVIDENCE_GUARDED_PAGES = (
    *CANONICAL_FOUNDATION,
    *CORE_EPISTEMIC_ADRS,
    SQLITE_BOUNDARY_ADR,
    PRODUCT_BOOTSTRAP_ADR,
    *READER_FACING_CURRENT_STATE_PAGES,
)

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


def test_docs_index_exposes_exact_canonical_journey() -> None:
    """The index must expose the complete concept-first canonical journey."""

    index_file = DOCS_ROOT / "index.md"
    linked_markdown: set[Path] = set()
    for _, target in _extract_markdown_links(index_file):
        if target.startswith(_EXTERNAL_SCHEMES):
            continue
        path_text, _ = _split_link_target(target)
        if not path_text or not path_text.lower().endswith(".md"):
            continue
        linked_markdown.add((index_file.parent / path_text).resolve())

    expected = {page.resolve() for page in CANONICAL_READER_PAGES}
    assert linked_markdown == expected, (
        "docs/index.md must link exactly the canonical reader journey; "
        f"expected={sorted(map(str, expected))}, "
        f"actual={sorted(map(str, linked_markdown))}"
    )


def test_reader_facing_docs_exclude_checkout_audit_evidence() -> None:
    """Canonical and current-state reader pages must exclude local audit scorekeeping."""

    forbidden_patterns = {
        "commit hash": re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])"),
        "agent attribution": re.compile(r"\b(?:Codex|Gemini)\b", re.IGNORECASE),
        "fixed test result": re.compile(
            r"\b\d+\s+(?:passed|failed|skipped)\b",
            re.IGNORECASE,
        ),
        "implementation object count": re.compile(
            r"\b\d+\s+(?:(?:SQLModel|database)\s+)?"
            r"(?:tables?|triggers?|sqlite_master\s+objects?)\b",
            re.IGNORECASE,
        ),
        "package chronology": re.compile(
            r"\b(?:Package|Wave)\s+(?:S?\d|[0-9])",
            re.IGNORECASE,
        ),
    }
    violations: list[str] = []
    for doc in CHECKOUT_EVIDENCE_GUARDED_PAGES:
        content = doc.read_text(encoding="utf-8")
        for description, pattern in forbidden_patterns.items():
            if pattern.search(content):
                violations.append(f"{doc.as_posix()}: {description}")

    assert not violations, (
        "Checkout-specific audit evidence found in canonical docs: "
        f"{violations}"
    )


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


def test_canonical_source_references_exist() -> None:
    """Inline source and test orientation paths on canonical pages must resolve."""

    violations: list[str] = []
    for doc in (*CANONICAL_READER_PAGES, *COMPLETE_DECISION_ANATOMY_ADRS):
        content = doc.read_text(encoding="utf-8")
        for reference in re.findall(r"`((?:src|tests)/[^`\n]+)`", content):
            if not Path(reference).exists():
                violations.append(f"{doc.as_posix()}: {reference}")

    assert not violations, f"Missing canonical source references: {violations}"


def test_phase_2a_canonical_pages_reject_authority_overclaims() -> None:
    """Phase 2A prose must not assign scientific authority to the wrong layer."""

    forbidden_patterns = {
        "unsafe protected input": re.compile(
            r"\bprotected (?:conclusion|discovery|evaluation|synthesis)"
            r"(?: [a-z-]+){0,3} (?:includes?|contains?|admits?) "
            r"(?:an? )?(?:Assumption|SessionFrame)s?\b",
            re.IGNORECASE,
        ),
        "governance scientific authorship": re.compile(
            r"\bgovernance (?:authors?|creates?|materializes?|rewrites?)\b",
            re.IGNORECASE,
        ),
        "application scientific rewriting": re.compile(
            r"\bapplication(?: services?| layer| code)? "
            r"(?:authors?|paraphrases?|rewrites?|normalizes?)\b",
            re.IGNORECASE,
        ),
        "concrete Data Explorer overclaim": re.compile(
            r"\b(?:concrete|production) Data Explorer "
            r"(?:is|exists as|remains) (?:implemented|available|shipped|supported)\b",
            re.IGNORECASE,
        ),
        "cross-database guarantee": re.compile(
            r"\b(?:cross-database|database-independent|all-database) "
            r"(?:atomicity|transactions?|guarantees?) "
            r"(?:is|are) (?:implemented|supported|verified|guaranteed)\b",
            re.IGNORECASE,
        ),
    }
    violations: list[str] = []
    for doc in PHASE_2A_CANONICAL_PAGES:
        content = doc.read_text(encoding="utf-8")
        for label, pattern in forbidden_patterns.items():
            if pattern.search(content):
                violations.append(f"{doc.as_posix()}: {label}")

    assert not violations, f"Scientific-authority overclaims found: {violations}"


def test_phase_2b1_canonical_pages_reject_active_context_overclaims() -> None:
    """Active-context prose must preserve authority, type, and product boundaries."""

    forbidden_patterns = {
        "SessionFrame scientific authority": re.compile(
            r"\bSessionFrame (?:is|acts as|becomes) (?:an? |the )?"
            r"(?:scientific|evaluation|conclusion) authority\b",
            re.IGNORECASE,
        ),
        "pin overrides validity": re.compile(
            r"\b(?:a |user )?pins? (?:overrides?|bypasses?|restores?|reactivates?) "
            r"(?:scientific )?(?:validity|invalidated|deprecated|lifecycle)\b",
            re.IGNORECASE,
        ),
        "raw chat as research memory": re.compile(
            r"\braw chat (?:is|becomes|serves as|functions as) "
            r"(?:durable )?research (?:memory|state)\b",
            re.IGNORECASE,
        ),
        "deferred retrieval overclaim": re.compile(
            r"\b(?:Graph Miner|semantic (?:indexing|retrieval)|"
            r"vector (?:index|retrieval|search)) (?:is|are) "
            r"(?:implemented|supported|available)\b",
            re.IGNORECASE,
        ),
        "SessionFrame-derived protected evaluation": re.compile(
            r"\bprotected (?:conclusion|evaluation|scientific|discovery|synthesis)"
            r"(?: context| bundle)? (?:is|are) "
            r"(?:derived|built|constructed|reconstructed) from "
            r"(?:a |the )?SessionFrame\b",
            re.IGNORECASE,
        ),
        "pinned invalid state active": re.compile(
            r"\b(?:invalidated|deprecated) Discovery "
            r"(?:is|becomes|remains) active (?:because|when|if)[^.]*\bpinn",
            re.IGNORECASE,
        ),
    }
    violations: list[str] = []
    for doc in PHASE_2B1_CANONICAL_PAGES:
        content = doc.read_text(encoding="utf-8")
        for label, pattern in forbidden_patterns.items():
            if pattern.search(content):
                violations.append(f"{doc.as_posix()}: {label}")

    assert not violations, f"Active-context authority overclaims found: {violations}"


def test_phase_2b2_canonical_pages_reject_validity_overclaims() -> None:
    """Validity prose must preserve history, authority, and product boundaries."""

    forbidden_patterns = {
        "invalidation as deletion": re.compile(
            r"\binvalidation (?:deletes?|erases?)\b",
            re.IGNORECASE,
        ),
        "ValidityEvent as scientific object": re.compile(
            r"\bValidityEvent (?:is|becomes|acts as) (?:an? |the )?"
            r"(?:scientific )?(?:FCO|First-Class Object|Discovery|Evidence)\b",
            re.IGNORECASE,
        ),
        "pin overrides validity": re.compile(
            r"\b(?:a |user )?pins? (?:overrides?|bypasses?|restores?|reactivates?) "
            r"(?:scientific )?(?:validity|invalidated|deprecated|lifecycle)\b",
            re.IGNORECASE,
        ),
        "Assumption replacement invalidates Discovery": re.compile(
            r"\breplac(?:ing|ement of|ed) (?:an? )?Assumption "
            r"(?:automatically |directly )?invalidates? (?:an? )?Discovery\b",
            re.IGNORECASE,
        ),
        "validity authors replacement claim": re.compile(
            r"\bvalidity propagation (?:automatically )?"
            r"(?:authors?|creates?|materializes?) (?:an? |the )?"
            r"(?:replacement )?(?:scientific )?(?:claim|Discovery)\b",
            re.IGNORECASE,
        ),
        "changed command as exact replay": re.compile(
            r"\bchanged (?:command|request)[^.\n]{0,60}"
            r"\b(?:is|becomes|counts as) (?:an? )?exact replay\b",
            re.IGNORECASE,
        ),
        "automatic refresh overclaim": re.compile(
            r"\b(?:notification|successor SessionFrame|context refresh) "
            r"(?:is|are) automatically "
            r"(?:created|delivered|performed|implemented)\b",
            re.IGNORECASE,
        ),
        "semantic-index invalidation overclaim": re.compile(
            r"\bsemantic(?:-index| index) invalidation (?:is|are) "
            r"(?:implemented|supported)\b",
            re.IGNORECASE,
        ),
        "validity-owned lease overclaim": re.compile(
            r"\bvalidity (?:uses|has|owns) (?:an? )?"
            r"(?:claim|lease|fencing token)\b",
            re.IGNORECASE,
        ),
        "cross-database guarantee": re.compile(
            r"\b(?:cross-database|database-independent|all-database) "
            r"(?:validity |transaction |concurrency )?"
            r"(?:guarantees?|behavior|atomicity) (?:is|are) "
            r"(?:implemented|supported|verified|guaranteed)\b",
            re.IGNORECASE,
        ),
    }
    violations: list[str] = []
    for doc in PHASE_2B2_CANONICAL_PAGES:
        content = doc.read_text(encoding="utf-8")
        for label, pattern in forbidden_patterns.items():
            if pattern.search(content):
                violations.append(f"{doc.as_posix()}: {label}")

    assert not violations, f"Validity-over-time overclaims found: {violations}"


def test_recent_canonical_pages_use_canonical_status_labels() -> None:
    """Status-like bold labels on the new canonical pages must use the shared vocabulary."""

    allowed = {
        "Implemented",
        "Verified on SQLite",
        "Partially implemented",
        "Design target",
        "Deferred",
        "Known deviation",
        "Unsupported",
    }
    status_terms = re.compile(
        r"implemented|verified on sqlite|design target|deferred|"
        r"known deviation|unsupported",
        re.IGNORECASE,
    )
    violations: list[str] = []
    for doc in (
        *PHASE_2B_CANONICAL_PAGES,
        *PHASE_3A_DECISION_PAGES,
        *PHASE_3B1_CANONICAL_PAGES,
        *PHASE_3B2_CANONICAL_PAGES,
        SQLITE_BOUNDARY_ADR,
        PRODUCT_BOOTSTRAP_ADR,
    ):
        content = doc.read_text(encoding="utf-8")
        emphasized = re.findall(r"\*\*([^*\n]+)\*\*", content)
        violations.extend(
            f"{doc.as_posix()}: {label!r}"
            for label in emphasized
            if status_terms.search(label) and label.removesuffix(":") not in allowed
        )

    assert not violations, f"Non-canonical implementation-status labels found: {violations}"


def test_phase_3a_docs_and_source_define_exactly_eight_fcos() -> None:
    """The source enumeration and the core decision record must expose the same eight FCOs."""

    source = Path("src/schemas/enums.py").read_text(encoding="utf-8")
    syntax_tree = ast.parse(source)
    fco_class = next(
        node
        for node in syntax_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FirstClassObjectType"
    )
    source_values = {
        statement.value.value
        for statement in fco_class.body
        if isinstance(statement, ast.Assign)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    }
    expected_values = {
        "objective",
        "data_profile",
        "assumption",
        "task",
        "hypothesis",
        "evidence",
        "discovery",
        "session_frame",
    }
    assert source_values == expected_values

    adr = CORE_EPISTEMIC_ADRS[0].read_text(encoding="utf-8")
    documented_names = set(
        re.findall(r"^\d+\. `([A-Z][A-Za-z]+)`", adr, flags=re.MULTILINE)
    )
    expected_names = {
        "Objective",
        "DataProfile",
        "Assumption",
        "Task",
        "Hypothesis",
        "Evidence",
        "Discovery",
        "SessionFrame",
    }
    assert documented_names == expected_names


def test_reconstructed_adrs_expose_complete_decision_anatomy() -> None:
    """Reconstructed ADRs must preserve rationale, limits, and redesign guidance."""

    required_headings = {
        "context",
        "problem",
        "failure mode",
        "tempting alternatives",
        "decision",
        "invariant protected",
        "current implementation",
        "tradeoffs",
        "known limitations",
        "risks",
        "revisit triggers",
        "consequences for future work",
        "related canonical concepts",
        "implementation orientation",
    }
    failures: list[str] = []
    for adr in COMPLETE_DECISION_ANATOMY_ADRS:
        content = adr.read_text(encoding="utf-8")
        headings = {
            match.group(1).strip().lower()
            for match in re.finditer(r"^##\s+(.+?)\s*$", content, flags=re.MULTILINE)
        }
        missing = sorted(required_headings - headings)
        if missing:
            failures.append(f"{adr.as_posix()}: missing headings {missing}")
        if re.search(r"^\*\*Status:\*\*\s*Accepted\b", content, flags=re.MULTILINE):
            failures.append(f"{adr.as_posix()}: uses Accepted as implementation proof")

    assert not failures, "Incomplete core decision records:\n" + "\n".join(failures)


def test_operational_docs_preserve_runtime_and_persistence_ownership() -> None:
    """Operational prose must keep composition, coordination, and writes distinct."""

    runtime = PHASE_3B1_CANONICAL_PAGES[0].read_text(encoding="utf-8")
    persistence = PHASE_3B1_CANONICAL_PAGES[1].read_text(encoding="utf-8")
    migration = PHASE_3B1_CANONICAL_PAGES[3].read_text(encoding="utf-8")

    required_runtime_patterns = {
        "runtime owns composition": re.compile(
            r"\bCogniEDARuntime\b.{0,240}\bcomposition\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "loader owns external factory seam": re.compile(
            r"\bruntime_loader\b.{0,240}\bdeployment seam\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "orchestrator is not composition root": re.compile(
            r"\borchestrator\b.{0,180}\bnot the composition root\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "bootstrap is not implemented": re.compile(
            r"\bapplication/bootstrap\b.{0,180}\bno Python implementation\b",
            re.IGNORECASE | re.DOTALL,
        ),
    }
    missing_runtime = [
        label for label, pattern in required_runtime_patterns.items() if not pattern.search(runtime)
    ]

    required_persistence_terms = {
        "domain schema",
        "repository",
        "sqlmodel model",
        "migration",
        "direct orm",
        "bypass",
        "not interchangeable",
    }
    persistence_normalized = persistence.casefold()
    missing_persistence = sorted(
        term for term in required_persistence_terms if term not in persistence_normalized
    )

    assert not missing_runtime, f"Runtime ownership is incomplete: {missing_runtime}"
    assert not missing_persistence, (
        "Persistence-layer ownership or bypass qualification is incomplete: "
        f"{missing_persistence}"
    )
    assert re.search(
        r"\bHistorical migrations? (?:are|is) immutable records?\b",
        migration,
        flags=re.IGNORECASE,
    )


def test_operational_docs_reject_backend_and_enforcement_overclaims() -> None:
    """SQLite qualification and layered enforcement must remain explicit."""

    forbidden_patterns = {
        "repository as transaction owner": re.compile(
            r"\brepositories? (?:are|act as|serve as) (?:the )?"
            r"(?:application )?transaction owners?\b",
            re.IGNORECASE,
        ),
        "db.models as domain owner": re.compile(
            r"\bdb\.models (?:owns|defines) (?:the )?"
            r"(?:domain|ontology|FCO model)\b",
            re.IGNORECASE,
        ),
        "PostgreSQL support overclaim": re.compile(
            r"\bPostgreSQL (?:is|as) (?:currently )?"
            r"(?:supported|implemented|verified)\b",
            re.IGNORECASE,
        ),
        "cross-database parity overclaim": re.compile(
            r"\bcross-database (?:parity|guarantees?|atomicity) (?:is|are) "
            r"(?:supported|implemented|verified|guaranteed)\b",
            re.IGNORECASE,
        ),
        "editable historical migration": re.compile(
            r"\bhistorical migrations? (?:may|can|should|must) be "
            r"(?:edited|rewritten|reordered)\b",
            re.IGNORECASE,
        ),
        "universal trigger protection": re.compile(
            r"\btriggers? (?:enforce|protect|guarantee) "
            r"(?:all|every|universal) (?:scientific )?(?:payloads?|invariants?)\b",
            re.IGNORECASE,
        ),
    }
    violations: list[str] = []
    for doc in (*PHASE_3B1_CANONICAL_PAGES, SQLITE_BOUNDARY_ADR):
        content = doc.read_text(encoding="utf-8")
        for label, pattern in forbidden_patterns.items():
            if pattern.search(content):
                violations.append(f"{doc.as_posix()}: {label}")

    assert not violations, f"Operational-boundary overclaims found: {violations}"


def test_phase_3b2_docs_preserve_planner_retrieval_resume_and_product_boundaries() -> None:
    """Planner coordination and product seams must not acquire false authority."""

    planner = PHASE_3B2_CANONICAL_PAGES[0].read_text(encoding="utf-8")
    workflow = PHASE_3B2_CANONICAL_PAGES[1].read_text(encoding="utf-8")
    retrieval = PHASE_3B2_CANONICAL_PAGES[2].read_text(encoding="utf-8")
    session_frame = PHASE_3B2_CANONICAL_PAGES[3].read_text(encoding="utf-8")
    product = PHASE_3B2_CANONICAL_PAGES[4].read_text(encoding="utf-8")

    required_terms = {
        "Planner boundary": (
            planner,
            (
                "It does not own scientific truth",
                "NON-BLOCKING DOCUMENTED DEBT",
                "direct durable mutation bypass",
                "commit_planner_operations",
            ),
        ),
        "approval workflow": (
            workflow,
            (
                "raw user request",
                "durable PlannerOperation or execution approval",
                "repository-current revalidation",
                "commit or fail closed",
            ),
        ),
        "retrieval boundary": (
            retrieval,
            (
                "Ranking may choose among admissible candidates",
                "default `LexicalScorer`",
                "request `objective_id` not used as a filter",
                "request `session_frame_id` not independently bound",
                "Graph Miner",
            ),
        ),
        "SessionFrame boundary": (
            session_frame,
            (
                "database-global",
                "`session_id`, `user_id`, or `objective_id`",
                "LangGraph default `MemorySaver`",
                "not complete restart-safe product continuity",
            ),
        ),
        "product boundary": (
            product,
            (
                "in-process application runtime",
                "does not yet have a supported product process",
                "contains orientation only",
                "minimum coherent product boundary",
            ),
        ),
    }
    missing = [
        f"{label}: {term}"
        for label, (content, terms) in required_terms.items()
        for term in terms
        if re.sub(r"\s+", " ", term.casefold())
        not in re.sub(r"\s+", " ", content.casefold())
    ]
    assert not missing, f"Phase 3B-2 boundary statements are incomplete: {missing}"

    combined = "\n".join(
        page.read_text(encoding="utf-8") for page in PHASE_3B2_CANONICAL_PAGES
    )
    forbidden_patterns = {
        "Planner scientific authorship": re.compile(
            r"\bPlanner nodes? (?:author|create|materialize)s? "
            r"(?:`?Evidence`?|`?Discover(?:y|ies)`?)\b",
            re.IGNORECASE,
        ),
        "Planner scientific transaction ownership": re.compile(
            r"\bPlanner nodes? (?:are|serve as|act as) (?:the )?"
            r"(?:scientific )?transaction owners?\b",
            re.IGNORECASE,
        ),
        "implemented scaffold path": re.compile(
            r"\b(?:answer|suggestion|result review|conflict review|project closure)"
            r"(?: path| workflow)?\b[^.\n]{0,80}\b(?:is|are|remains?) "
            r"\*\*Implemented\*\*",
            re.IGNORECASE,
        ),
        "implemented semantic or Graph Miner path": re.compile(
            r"\b(?:semantic retrieval|vector retrieval|Graph Miner)\b"
            r".{0,100}\*\*Implemented\*\*",
            re.IGNORECASE | re.DOTALL,
        ),
        "fully scoped SessionFrame": re.compile(
            r"\bSessionFrame\b.{0,100}\bfully "
            r"(?:user|session|Objective|branch)[-\s]scoped\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "durable in-memory checkpoint": re.compile(
            r"\bMemorySaver\b.{0,100}\b(?:durable|restart-safe)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "runtime advertised as product process": re.compile(
            r"\bCogniEDARuntime\b.{0,100}\b(?:is|provides) (?:a )?"
            r"(?:CLI|HTTP API|worker|daemon)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "implemented bootstrap directory": re.compile(
            r"\bapplication/bootstrap\b.{0,100}\b(?:is|provides) "
            r"(?:an? )?(?:implemented|production) bootstrap\b",
            re.IGNORECASE | re.DOTALL,
        ),
    }
    violations = [
        label for label, pattern in forbidden_patterns.items() if pattern.search(combined)
    ]
    assert not violations, f"Phase 3B-2 authority overclaims found: {violations}"


def test_phase_3a_decisions_preserve_core_epistemic_boundaries() -> None:
    """Decision prose must state the core anti-laundering boundaries explicitly."""

    content = "\n".join(
        page.read_text(encoding="utf-8") for page in PHASE_3A_DECISION_PAGES
    )
    required_patterns = {
        "Assumptions excluded from conclusions": re.compile(
            r"\bAssumptions?\b.{0,120}\b(?:must not|cannot)\b.{0,120}"
            r"\b(?:conclusions?|concludes?|inference premises?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "Evidence stops before interpretation": re.compile(
            r"\bEvidence without interpretation\b|"
            r"\bEvidence admission\b.{0,160}\bstops? before interpretation\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "GeneratedView is not Discovery": re.compile(
            r"\bGeneratedView\b.{0,120}\bnot Discovery\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "parent Tasks produce no Discovery": re.compile(
            r"\bParent Tasks?\b.{0,120}\b(?:do not|cannot)\b.{0,80}"
            r"\b(?:Hypotheses|Hypothesis|Discoveries|Discovery)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "governance does not author claims": re.compile(
            r"\bGovernance\b.{0,160}\b(?:does not|cannot|must not|not)\b.{0,80}"
            r"\b(?:author|revise|rewrite)\w*\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "application copies the exact proposal": re.compile(
            r"\bapplication\b.{0,160}\b(?:copies|materializes)\b.{0,120}\bexact\w*\b|"
            r"\bexact proposal-copy\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "invalidation retains history": re.compile(
            r"\bInvalidation\b.{0,120}\b(?:never|does not|must not)\b.{0,60}"
            r"\bdelet\w*\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "SessionFrame cannot override validity": re.compile(
            r"\b(?:SessionFrame|pin)\b.{0,160}\b(?:cannot|does not|must not)\b"
            r".{0,100}\b(?:validity|scientific authority|inactive object)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    }
    missing = [
        label for label, pattern in required_patterns.items() if not pattern.search(content)
    ]
    assert not missing, f"Core epistemic boundaries are not explicit: {missing}"


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
        DOCS_ROOT / "index.md",
        *CANONICAL_READER_PAGES,
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
            r"implementation status|current implementation|current maturity|"
            r"current product maturity|final verdict",
            doc.read_text(encoding="utf-8"),
            flags=re.IGNORECASE,
        )
    ]
    assert not missing, f"Major documents omit implementation status: {missing}"
