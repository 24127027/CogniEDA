from textual.app import ComposeResult
from textual.widgets import Static, Input, Button, Label
from textual.containers import Container, Horizontal
from textual import events

AVAILABLE_MODELS = [
    "Gemini 2.5 Pro",
    "Gemini 2.5 Flash",
    "GPT-5",
    "Claude Sonnet",
    "Local Llama 3"
]

class ModelSelectorMenu(Container):
    """Popover menu for selecting active AI model on hover/click (Requirement 6)."""

    def __init__(self, current_model: str = "Gemini 2.5 Pro", **kwargs):
        kwargs.setdefault("id", "model-menu-popup")
        super().__init__(**kwargs)
        self.current_model = current_model

    def compose(self) -> ComposeResult:
        yield Label("[bold #00E5FF]Current Model[/]", classes="field-label")
        
        for model in AVAILABLE_MODELS:
            is_active = (model == self.current_model)
            prefix = "✓ " if is_active else "  "
            cls = "model-option-btn model-option-active" if is_active else "model-option-btn"
            model_id = f"select-model-{model.replace(' ', '-').replace('.', '_').lower()}"
            yield Button(f"{prefix}{model}", id=model_id, classes=cls)

        yield Static("────────────────────────────", classes="field-label")
        yield Button("⚙ Configure Models...", id="open-config-models-btn", classes="model-option-btn")

    def on_leave(self, event: events.Leave) -> None:
        """Closes popover menu when mouse leaves menu container."""
        if self.parent and hasattr(self.parent, "close_model_menu"):
            self.parent.close_model_menu()


class ModelSelectorButton(Button):
    """Button control displaying currently selected AI model with hover popover trigger."""

    def __init__(self, label: str, **kwargs):
        kwargs.setdefault("id", "model-selector-btn")
        super().__init__(label, **kwargs)

    def on_enter(self, event: events.Enter) -> None:
        """Triggers model selection menu popover on hover."""
        if self.parent and hasattr(self.parent, "open_model_menu"):
            self.parent.open_model_menu()


class CommandBar(Container):
    """Bottom command bar with command input and AI Model Selector beside it."""

    def __init__(self, current_model: str = "Gemini 2.5 Pro", **kwargs):
        kwargs.setdefault("id", "command-bar-container")
        super().__init__(**kwargs)
        self.current_model = current_model
        self.menu_open = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="command-input-row"):
            yield Label("📎 ", classes="field-label")
            yield Input(
                placeholder="Ask something or enter a command (e.g. \\help, /finalize dataset)...",
                id="command-input"
            )
            yield ModelSelectorButton(f"{self.current_model} ▾")

    def open_model_menu(self) -> None:
        """Mounts model selection popover if not already open."""
        if not self.menu_open:
            self.mount(ModelSelectorMenu(current_model=self.current_model))
            self.menu_open = True

    def close_model_menu(self) -> None:
        """Removes model selection popover."""
        if self.menu_open:
            try:
                self.query_one("#model-menu-popup").remove()
            except Exception:
                pass
            self.menu_open = False

    def toggle_model_menu(self) -> None:
        """Toggles model menu popover state."""
        if self.menu_open:
            self.close_model_menu()
        else:
            self.open_model_menu()

    def set_model(self, model_name: str) -> None:
        """Sets active model name and updates button label."""
        self.current_model = model_name
        btn = self.query_one(ModelSelectorButton)
        btn.label = f"{model_name} ▾"
        self.close_model_menu()
