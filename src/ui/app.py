from textual.app import App, ComposeResult
from textual.binding import Binding
from screens.welcome import WelcomeScreen
from screens.main_workspace import MainWorkspaceScreen

class CogniEDAApp(App):
    """CogniEDA CLI-First Research Workspace UI (Python Textual)."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "CogniEDA - Cognitive Exploratory Data Analysis"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("f1", "show_welcome", "Welcome Screen", show=True),
        Binding("f2", "show_workspace", "Main Workspace", show=True),
    ]

    def on_mount(self) -> None:
        self.install_screen(WelcomeScreen(), name="welcome")
        self.install_screen(MainWorkspaceScreen(), name="main_workspace")
        self.push_screen("welcome")

    def switch_to_main_workspace(
        self,
        mode: str = "CLEANING",
        project_name: str = "New Workspace",
        objective: str = "Define telemetry targets"
    ) -> None:
        ws = self.get_screen("main_workspace")
        ws.project_name = project_name
        ws.objective = objective
        if hasattr(ws, "switch_mode"):
            ws.switch_mode(mode)
        self.switch_screen("main_workspace")

    def switch_to_welcome(self) -> None:
        self.switch_screen("welcome")

    def action_show_welcome(self) -> None:
        self.switch_to_welcome()

    def action_show_workspace(self) -> None:
        self.switch_to_main_workspace()


if __name__ == "__main__":
    app = CogniEDAApp()
    app.run()
