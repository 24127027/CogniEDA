from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal

class CogniEDAHeader(Static):
    """Header component for CogniEDA interface."""

    def __init__(self, mode: str = "CLEANING", project_name: str = "Customer Churn", **kwargs):
        kwargs.setdefault("id", "app-header")
        super().__init__(**kwargs)
        self.mode = mode
        self.project_name = project_name

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(f"[bold #00E5FF]CogniEDA[/]  [bold white]{self.project_name}[/]", id="header-brand")
            
            badge_class = "header-mode-badge-research" if self.mode == "RESEARCH" else "header-mode-badge"
            yield Static(f"[{badge_class}]MODE : {self.mode}[/]", id="header-mode")
            
            yield Static("[dim]• Research Console[/]", id="header-console")
            yield Static("[bold white]👤 Hoang Nhi[/]", id="header-user")

    def update_mode(self, new_mode: str) -> None:
        self.mode = new_mode
        mode_widget = self.query_one("#header-mode", Static)
        badge_class = "header-mode-badge-research" if new_mode == "RESEARCH" else "header-mode-badge"
        mode_widget.update(f"[{badge_class}]MODE : {new_mode}[/]")
