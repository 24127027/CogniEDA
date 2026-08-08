from textual.app import ComposeResult
from textual.widgets import Static, Input, Button, Label, ListView, ListItem
from textual.containers import Vertical, Horizontal, Container, ScrollableContainer

class BaseOverlayPanel(Container):
    """Base container for Welcome Screen side overlays."""
    DEFAULT_CLASSES = "overlay-panel"

    def __init__(self, title: str, panel_id: str, **kwargs):
        kwargs.setdefault("id", panel_id)
        super().__init__(**kwargs)
        self.panel_title = title

    def compose_header(self) -> ComposeResult:
        with Horizontal(classes="overlay-header-bar"):
            yield Label(f"[bold #00E5FF]{self.panel_title}[/]", classes="overlay-title")
            yield Button("✕", id="close-overlay-btn", classes="close-panel-btn")


class CreateWorkspacePanel(BaseOverlayPanel):
    """Side panel for creating a new research workspace (\create)."""

    def __init__(self, **kwargs):
        super().__init__(title="NEW WORKSPACE", panel_id="create-workspace-panel", **kwargs)

    def compose(self) -> ComposeResult:
        yield from self.compose_header()
        yield Label("WORKSPACE NAME", classes="field-label")
        yield Input(placeholder="Enter workspace name", id="ws-name-input", classes="panel-input")
        
        yield Label("OBJECTIVE", classes="field-label")
        yield Input(placeholder="Define telemetry targets", id="ws-objective-input", classes="panel-input")
        
        yield Button("CREATE", id="submit-create-ws-btn", classes="primary-action-btn")


class OpenWorkspacePanel(BaseOverlayPanel):
    """Side panel for opening/resuming existing workspaces (\open)."""

    def __init__(self, **kwargs):
        super().__init__(title="OPEN WORKSPACE", panel_id="open-workspace-panel", **kwargs)

    def compose(self) -> ComposeResult:
        yield from self.compose_header()
        yield Input(placeholder="🔍 search_workspace", id="ws-search-input", classes="panel-input")
        
        yield Label("RECENT ACTIVITY", classes="field-label")
        with ScrollableContainer():
            yield Static(
                "[bold #F1F5F9]Neural_Flux_Gamma[/]  [green]ACTIVE[/]\n"
                "[dim]Exploring tensor perturbations in LLM-60B variant.[/]\n"
                "[dim cyan]🕒 2h ago[/]",
                classes="recent-item"
            )
            yield Static(
                "[bold #F1F5F9]Data_Harvest_V2[/]  [dim]ARCHIVED[/]\n"
                "[dim]Multi-modal dataset cleaning for image-text pairs.[/]\n"
                "[dim cyan]🕒 22h ago[/]",
                classes="recent-item"
            )
            yield Static(
                "[bold #F1F5F9]Synthetic_Protocol[/]  [green]ACTIVE[/]\n"
                "[dim]Cross-chain transaction pattern analysis.[/]\n"
                "[dim cyan]🕒 1d ago[/]",
                classes="recent-item"
            )
            yield Static(
                "[bold #F1F5F9]Project_Aurora_Core[/]  [dim]ARCHIVED[/]\n"
                "[dim]Visualizing solar flare telemetry data 1998-2023.[/]\n"
                "[dim cyan]🕒 3d ago[/]",
                classes="recent-item"
            )
            yield Static(
                "[bold #F1F5F9]Genome_Map_04[/]  [dim]ARCHIVED[/]\n"
                "[dim]Mapping CRISPR mutations in plant pathogens.[/]\n"
                "[dim cyan]🕒 5d ago[/]",
                classes="recent-item"
            )

        yield Button("🔍 Browse all file systems", id="browse-filesystem-btn", classes="primary-action-btn")


class AiEnvironmentPanel(BaseOverlayPanel):
    """Side panel for viewing/configuring AI Environment (\ai)."""

    def __init__(self, **kwargs):
        super().__init__(title="AI ENVIRONMENT", panel_id="ai-environment-panel", **kwargs)

    def compose(self) -> ComposeResult:
        yield from self.compose_header()
        with ScrollableContainer():
            yield Label("CORE ENGINE", classes="field-label")
            yield Static(
                "[dim]Current Agent:[/] [bold white]Neural_Observer_v4[/]\n"
                "[dim]Current Model:[/] [bold #00E5FF]Cogni-LLM-70B[/]\n"
                "[dim]Reasoning:[/]     [bold green]• Ready[/]\n"
                "[dim]Planner:[/]       [bold white]Task-Oriented[/]",
                classes="stat-box"
            )

            yield Label("COMPUTE & RUNTIME", classes="field-label")
            yield Static(
                "[dim]Python Runtime:[/]  [white]3.11.4 (Kernel 4)[/]\n"
                "[dim]Embedding Model:[/] [white]Text-Embed-v2[/]\n"
                "[dim]Execution Mode:[/]  [bold green]SANDBOXED[/]",
                classes="stat-box"
            )

            yield Label("WORKSPACE CONTEXT", classes="field-label")
            yield Static(
                "[dim]Session:[/] [cyan]research_delta_9[/]\n"
                "[dim]Auth:[/]    [green]enterprise_verified[/]\n"
                "[dim]Data Latency:[/] [white]24ms[/]\n"
                "[dim]Workspace:[/]    [white]Global_EDA_Root[/]",
                classes="stat-box"
            )

        yield Button("Configure AI Environment ➔", id="config-ai-btn", classes="primary-action-btn")


class HelpPanel(BaseOverlayPanel):
    """Side panel for Help and CLI command guidance (\help)."""

    def __init__(self, **kwargs):
        super().__init__(title="HOW TO USE COGNIEDA", panel_id="help-panel", **kwargs)

    def compose(self) -> ComposeResult:
        yield from self.compose_header()
        with ScrollableContainer():
            yield Static(
                "[bold #00E5FF]01  Create workspace[/]\n"
                "[dim]Use \\create or \\open to initialize your research context and target telemetry.[/]\n\n"
                "[bold #00E5FF]02  Mount the dataset[/]\n"
                "[dim]Load raw CSV or parquet files into the Cleaning Workspace.[/]\n\n"
                "[bold #00E5FF]03  Dataset cleaning[/]\n"
                "[dim]Inspect data profile versions, remove missing rows/outliers, and run /finalize dataset.[/]\n\n"
                "[bold #00E5FF]04  Begin Research[/]\n"
                "[dim]Run /begin research to switch to Research Mode and start investigation tree branches.[/]\n\n"
                "[bold #00E5FF]05  Command-Driven Retrieval[/]\n"
                "[dim]Retrieve pinned objects using commands like 'show evidence payment' or 'show profile'.[/]",
                classes="stat-box"
            )
