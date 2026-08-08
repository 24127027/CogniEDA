from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label
from textual.containers import Vertical, Horizontal, Container
from widgets.header import CogniEDAHeader
from widgets.side_panels import CreateWorkspacePanel, OpenWorkspacePanel, AiEnvironmentPanel, HelpPanel

class WelcomeScreen(Screen):
    """Welcome Page screen (Entry point with static CLI command guidance)."""

    def __init__(self, **kwargs):
        super().__init__(id="welcome-screen", **kwargs)
        self.active_overlay = None

    def compose(self) -> ComposeResult:
        yield CogniEDAHeader(mode="WELCOME", project_name="")
        
        with Container(id="welcome-root"):
            with Vertical(id="welcome-center-container"):
                yield Static(
                    "Welcome back, [bold #00E5FF]Hoang Nhi[/]",
                    classes="welcome-title"
                )
                yield Static(
                    "Ready to resume your analytical workflows. CogniEDA neural engine is initialized and ready for execution.",
                    classes="welcome-subtitle"
                )

                # Available commands displayed as static guidance documentation (informational only)
                with Vertical(id="welcome-actions-grid"):
                    yield Static(
                        " [bold #00E5FF]\\create[/]   [dim]Create a new research workspace[/]",
                        classes="cli-command-hint"
                    )
                    yield Static(
                        " [bold #00E5FF]\\open[/]     [dim]Resume an existing workspace[/]",
                        classes="cli-command-hint"
                    )
                    yield Static(
                        " [bold #00E5FF]\\ai[/]       [dim]View and manage AI environment[/]",
                        classes="cli-command-hint"
                    )
                    yield Static(
                        " [bold #00E5FF]\\help[/]     [dim]Learn CogniEDA workflow[/]",
                        classes="cli-command-hint"
                    )

                yield Input(
                    placeholder="Type a command (\\create, \\open, \\ai, \\help)...",
                    id="welcome-cmd-input"
                )

    def show_overlay(self, overlay_name: str) -> None:
        """Shows specified side overlay panel, replacing any existing overlay."""
        self.hide_overlay()
        
        root = self.query_one("#welcome-root", Container)
        if overlay_name == "create":
            panel = CreateWorkspacePanel()
        elif overlay_name == "open":
            panel = OpenWorkspacePanel()
        elif overlay_name == "ai":
            panel = AiEnvironmentPanel()
        elif overlay_name == "help":
            panel = HelpPanel()
        else:
            return

        root.mount(panel)
        self.active_overlay = overlay_name

    def hide_overlay(self) -> None:
        """Removes active overlay panel."""
        if self.active_overlay:
            for panel_cls in [CreateWorkspacePanel, OpenWorkspacePanel, AiEnvironmentPanel, HelpPanel]:
                try:
                    self.query_one(panel_cls).remove()
                except Exception:
                    pass
            self.active_overlay = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles button presses from side overlay panels only."""
        btn_id = event.button.id
        if btn_id == "close-overlay-btn":
            self.hide_overlay()
        elif btn_id == "submit-create-ws-btn":
            ws_name = "New Workspace"
            ws_obj = "Define telemetry targets"
            try:
                panel = self.query_one(CreateWorkspacePanel)
                name_val = panel.query_one("#ws-name-input", Input).value.strip()
                if name_val:
                    ws_name = name_val
                obj_val = panel.query_one("#ws-objective-input", Input).value.strip()
                if obj_val:
                    ws_obj = obj_val
            except Exception:
                pass
            self.app.switch_to_main_workspace(project_name=ws_name, objective=ws_obj)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Processes input submissions without clearing form inputs unintentionally."""
        inp_id = event.input.id
        
        if inp_id == "ws-name-input":
            # Focus the objective input field on Enter without clearing name text
            try:
                panel = self.query_one(CreateWorkspacePanel)
                panel.query_one("#ws-objective-input", Input).focus()
            except Exception:
                pass
            return

        elif inp_id == "ws-objective-input":
            # Submit creation form on Enter using current non-empty values without clearing text
            ws_name = "New Workspace"
            ws_obj = "Define telemetry targets"
            try:
                panel = self.query_one(CreateWorkspacePanel)
                name_val = panel.query_one("#ws-name-input", Input).value.strip()
                if name_val:
                    ws_name = name_val
                obj_val = event.input.value.strip()
                if obj_val:
                    ws_obj = obj_val
            except Exception:
                pass
            self.app.switch_to_main_workspace(project_name=ws_name, objective=ws_obj)
            return

        elif inp_id == "welcome-cmd-input":
            val = event.input.value.strip().lower()
            event.input.value = ""
            if val in ["\\create", "create", "/create"]:
                self.show_overlay("create")
            elif val in ["\\open", "open", "/open"]:
                self.show_overlay("open")
            elif val in ["\\ai", "ai", "/ai"]:
                self.show_overlay("ai")
            elif val in ["\\help", "help", "/help"]:
                self.show_overlay("help")
            elif val in ["workspace", "start", "enter"]:
                self.app.switch_to_main_workspace()
