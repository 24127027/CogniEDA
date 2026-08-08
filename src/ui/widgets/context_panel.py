from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, ScrollableContainer

class ResearchContextPanel(Vertical):
    """Right panel showing Active Context & Pinned Artifacts (Purely informational / static display)."""

    def __init__(
        self,
        objective: str = "Define research objective",
        data_profile: str = None,
        current_task: str = None,
        hypotheses: list = None,
        discoveries: list = None,
        evidence: list = None,
        assumptions: list = None,
        **kwargs
    ):
        kwargs.setdefault("id", "research-context-panel")
        super().__init__(**kwargs)
        self.objective = objective
        self.data_profile = data_profile
        self.current_task = current_task
        self.hypotheses = hypotheses or []
        self.discoveries = discoveries or []
        self.evidence = evidence or []
        self.assumptions = assumptions or []

    def compose(self) -> ComposeResult:
        yield Label("Active Context", classes="panel-section-title")
        yield Label("[dim]Artifacts currently available to the agent[/]", classes="section-header")
        
        with ScrollableContainer():
            # Section 1: CURRENT FOCUS
            yield Label("CURRENT FOCUS", classes="section-header")
            
            profile_display = f"[bold white]{self.data_profile}[/]" if self.data_profile else "[dim]—[/]"
            task_display = f"[bold cyan]{self.current_task}[/]" if self.current_task else "[dim]—[/]"

            yield Static(
                f"[dim]OBJECTIVE[/]\n[bold white]{self.objective}[/]\n\n"
                f"[dim]DATA PROFILE[/]\n{profile_display}\n\n"
                f"[dim]CURRENT TASK[/]\n{task_display}",
                classes="stat-box"
            )

            yield Static("────────────────────────────────────────", classes="field-label")
            
            # Section 2: PINNED ARTIFACTS (Purely informational static presentation)
            yield Label("PINNED ARTIFACTS", classes="section-header")

            # Category 1: Hypotheses
            yield Label("Hypotheses", classes="field-label")
            if self.hypotheses:
                text = "\n".join([f"  [dim]• H{i+1}:[/] {item}" for i, item in enumerate(self.hypotheses)])
                yield Static(text, classes="stat-box")
            else:
                yield Static("  [dim]—[/]", classes="stat-box")

            # Category 2: Discoveries
            yield Label("Discoveries", classes="field-label")
            if self.discoveries:
                text = "\n".join([f"  [dim]• D{i+1}:[/] {item}" for i, item in enumerate(self.discoveries)])
                yield Static(text, classes="stat-box")
            else:
                yield Static("  [dim]—[/]", classes="stat-box")

            # Category 3: Evidence
            yield Label("Evidence", classes="field-label")
            if self.evidence:
                text = "\n".join([f"  [dim]• E{i+1}:[/] {item}" for i, item in enumerate(self.evidence)])
                yield Static(text, classes="stat-box")
            else:
                yield Static("  [dim]—[/]", classes="stat-box")

            # Category 4: Assumptions
            yield Label("Assumptions", classes="field-label")
            if self.assumptions:
                text = "\n".join([f"  [dim]• A{i+1}:[/] {item}" for i, item in enumerate(self.assumptions)])
                yield Static(text, classes="stat-box")
            else:
                yield Static("  [dim]—[/]", classes="stat-box")


class CleaningContextPanel(ResearchContextPanel):
    """CleaningContextPanel reuses the same Active Context layout for consistency."""

    def __init__(self, data_profile_name: str = None, **kwargs):
        kwargs.setdefault("id", "cleaning-context-panel")
        super().__init__(data_profile=data_profile_name, **kwargs)
