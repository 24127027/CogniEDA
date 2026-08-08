from textual.app import ComposeResult
from textual.containers import Horizontal, Grid
from textual.widgets import Static


class CogniEDAHeader(Horizontal):
    """Header component for CogniEDA interface."""

    def __init__(self, mode: str, project_name: str, **kwargs):
        kwargs.setdefault("id", "app-header")
        super().__init__(**kwargs)

        self.mode = mode
        self.project_name = project_name

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold #00E5FF]CogniEDA[/]  "
            f"[bold white]{self.project_name}[/]",
            id="header-brand",
        )

        yield Static(
            self._mode_markup(),
            id="header-mode",
        )

        yield Static(
            "[bold white]👤 Hoang Nhi[/]",
            id="header-user",
        )

    def _mode_markup(self) -> str:
        badge_class = (
            "header-mode-badge-research"
            if self.mode == "RESEARCH"
            else "header-mode-badge"
        )
        return f"[{badge_class}]MODE : {self.mode}[/]"

    def update_mode(self, new_mode: str) -> None:
        self.mode = new_mode
        self.query_one("#header-mode", Static).update(
            self._mode_markup()
        )