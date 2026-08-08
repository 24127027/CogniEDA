from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Vertical, ScrollableContainer

class ConversationPanel(Vertical):
    """Central panel hosting analyst-agent conversation and structured output cards."""

    def __init__(self, **kwargs):
        kwargs.setdefault("id", "conversation-panel")
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="chat-scroll-area"):
            yield Static(
                "[bold green]🤖 Neural_Observer_v4[/]  [dim]System Ready[/]\n\n"
                "Workspace initialized. Neural Engine is active and ready for execution. "
                "Type a command or ask a question to begin research.",
                classes="chat-message-agent",
                id="msg-init-agent"
            )

    def add_user_message(self, text: str) -> None:
        """Appends a new user message to the scroll container."""
        scroll_area = self.query_one("#chat-scroll-area", ScrollableContainer)
        scroll_area.mount(
            Static(
                f"[bold #00E5FF]👤 Analyst[/]  [dim]Just now[/]\n\n{text}",
                classes="chat-message-user"
            )
        )
        scroll_area.scroll_end(animate=False)

    def add_agent_message(self, text: str) -> None:
        """Appends a new agent response message to the scroll container."""
        scroll_area = self.query_one("#chat-scroll-area", ScrollableContainer)
        scroll_area.mount(
            Static(
                f"[bold green]🤖 Neural_Observer_v4[/]  [dim]Just now[/]\n\n{text}",
                classes="chat-message-agent"
            )
        )
        scroll_area.scroll_end(animate=False)

    def show_finalize_summary(self) -> None:
        """Displays the structured Dataset Finalization Review card (/finalize dataset)."""
        scroll_area = self.query_one("#chat-scroll-area", ScrollableContainer)
        scroll_area.mount(
            Static(
                "[bold #00E5FF]Dataset Finalization Review[/]\n"
                "────────────────────────────────────────────────\n"
                "[bold white]Active DataProfile:[/] dataset_clean_v1\n\n"
                "[bold white]Summary:[/] Rows: 10,000 | Columns: 15 | Missing values: 0 | Duplicates: 0\n\n"
                "[bold green]Recommendations:[JSON/List][/]\n"
                " • Dataset profile generated and validated.\n"
                " • Export a cleaning report if reproducibility is required.\n\n"
                "[dim cyan]💡 Use [bold white]/begin research[/] to start the research phase.[/]",
                classes="summary-card"
            )
        )
        scroll_area.scroll_end(animate=False)

    def show_begin_research_card(self) -> None:
        """Displays the transition card when /begin research is executed."""
        scroll_area = self.query_one("#chat-scroll-area", ScrollableContainer)
        scroll_area.mount(
            Static(
                "[bold green]Research Mode Initialized[/]\n"
                "────────────────────────────────────────────────\n"
                "[bold white]Accepted DataProfile:[/] dataset_clean_v1\n\n"
                "The cleaning stage has been closed. Future analyses will use this DataProfile "
                "as the project ground truth.",
                classes="summary-card"
            )
        )
        scroll_area.scroll_end(animate=False)
