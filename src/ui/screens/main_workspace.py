from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Button
from textual.containers import Container, Vertical
from widgets.header import CogniEDAHeader
from widgets.left_panel import DataProfilePanel, InvestigationTreePanel
from widgets.context_panel import ResearchContextPanel
from widgets.conversation_panel import ConversationPanel
from widgets.command_bar import CommandBar, ModelSelectorButton, AVAILABLE_MODELS

class MainWorkspaceScreen(Screen):
    """Main Research Workspace Screen (Fixed 3-column layout with Command Bar inside Center Panel)."""

    def __init__(
        self,
        mode: str = "CLEANING",
        project_name: str = "New Workspace",
        objective: str = "Define telemetry targets",
        **kwargs
    ):
        super().__init__(id="main-workspace-screen", **kwargs)
        self.mode = mode
        self.project_name = project_name
        self.objective = objective
        self.data_profile = None
        self.current_task = None
        self.hypotheses = []
        self.discoveries = []
        self.evidence = []
        self.assumptions = []

    def compose(self) -> ComposeResult:
        yield CogniEDAHeader(mode=self.mode, project_name=self.project_name, id="app-header")

        with Container(id="main-workspace-root"):
            with Container(id="left-panel-container"):
                if self.mode == "CLEANING":
                    yield DataProfilePanel(active_version=self.data_profile)
                else:
                    yield InvestigationTreePanel(root_name=self.project_name)

            # Center Panel containing Conversation and Command Bar at the bottom
            with Vertical(id="center-panel-container"):
                yield ConversationPanel()
                yield CommandBar(id="command-bar")

            # Right Panel containing purely informational Active Context
            with Container(id="right-panel-container"):
                yield ResearchContextPanel(
                    objective=self.objective,
                    data_profile=self.data_profile,
                    current_task=self.current_task,
                    hypotheses=self.hypotheses,
                    discoveries=self.discoveries,
                    evidence=self.evidence,
                    assumptions=self.assumptions
                )

    def switch_mode(self, new_mode: str) -> None:
        """Switches mode between CLEANING and RESEARCH, re-mounting left and right panels."""
        self.mode = new_mode

        if not self.is_mounted:
            return

        # Update Header
        try:
            header = self.query_one(CogniEDAHeader)
            header.update_mode(new_mode)
        except Exception:
            pass

        # Update Left Panel
        try:
            left_container = self.query_one("#left-panel-container", Container)
            left_container.remove_children()
            if new_mode == "CLEANING":
                left_container.mount(DataProfilePanel(active_version=self.data_profile))
            else:
                left_container.mount(InvestigationTreePanel(root_name=self.project_name))
        except Exception:
            pass

        # Update Right Panel
        try:
            right_container = self.query_one("#right-panel-container", Container)
            right_container.remove_children()
            right_container.mount(ResearchContextPanel(
                objective=self.objective,
                data_profile=self.data_profile,
                current_task=self.current_task,
                hypotheses=self.hypotheses,
                discoveries=self.discoveries,
                evidence=self.evidence,
                assumptions=self.assumptions
            ))
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if not btn_id:
            return

        conv = self.query_one(ConversationPanel)
        cmd_bar = self.query_one(CommandBar)

        if btn_id == "model-selector-btn":
            cmd_bar.toggle_model_menu()
        elif btn_id.startswith("select-model-"):
            for m in AVAILABLE_MODELS:
                m_slug = f"select-model-{m.replace(' ', '-').replace('.', '_').lower()}"
                if m_slug == btn_id:
                    cmd_bar.set_model(m)
                    conv.add_agent_message(f"AI Model switched to [bold #00E5FF]{m}[/].")
                    break
        elif btn_id == "add-direction-btn":
            conv.add_user_message("/add_direction New Hypothesis")
            self.hypotheses.append("New research hypothesis branch")
            conv.add_agent_message("Added hypothesis direction to research context.")
            self.switch_mode("RESEARCH")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.input.value.strip()
        event.input.value = ""
        if not val:
            return

        conv = self.query_one(ConversationPanel)
        conv.add_user_message(val)

        val_lower = val.lower()

        if val_lower == "/finalize dataset":
            self.data_profile = "dataset_clean_v1"
            conv.show_finalize_summary()
            self.switch_mode("CLEANING")
        elif val_lower == "/begin research":
            if not self.data_profile:
                self.data_profile = "dataset_clean_v1"
            self.current_task = "Hypothesis generation & feature exploration"
            conv.show_begin_research_card()
            self.switch_mode("RESEARCH")
        elif val_lower.startswith("show evidence") or val_lower.startswith("show discovery") or val_lower.startswith("show profile"):
            conv.add_agent_message(
                f"[bold #00E5FF]Command-Driven Retrieval:[/] Displaying requested artifact content for [cyan]'{val}'[/]:\n\n"
                "[dim]• Status:[/] Retrieved from workspace context."
            )
        elif val_lower in ["\\sessions", "/sessions", "sessions"]:
            conv.add_agent_message(
                "[bold #00E5FF]Session History (\\sessions):[/]\n"
                " • Session #1: Workspace initialization & context creation"
            )
        elif val_lower in ["\\welcome", "welcome", "exit"]:
            self.app.switch_to_welcome()
        else:
            conv.add_agent_message(
                f"Received command/query: [italic]{val}[/italic].\n"
                "Processing query against active workspace context..."
            )
