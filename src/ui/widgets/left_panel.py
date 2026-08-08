from textual.app import ComposeResult
from textual.widgets import Static, Button, Tree, Label
from textual.containers import Vertical, ScrollableContainer

class DataProfilePanel(Vertical):
    """Left panel content during Cleaning Mode showing Data Profile versions & Uploaded files."""

    def __init__(self, versions: list = None, uploaded_files: list = None, active_version: str = None, **kwargs):
        kwargs.setdefault("id", "data-profile-panel")
        super().__init__(**kwargs)
        self.versions = versions or []
        self.uploaded_files = uploaded_files or []
        self.active_version = active_version

    def compose(self) -> ComposeResult:
        yield Label("DATA PROFILE", classes="section-header")
        with ScrollableContainer():
            if not self.versions:
                yield Static("[dim]No profile versions yet[/dim]", classes="file-item")
            else:
                for v in self.versions:
                    is_active = (v == self.active_version)
                    css_cls = "profile-version-item active-version" if is_active else "profile-version-item"
                    prefix = "★ " if is_active else "• "
                    yield Static(f"{prefix}{v}", classes=css_cls, id=f"ver-{v}")

            yield Label("UPLOADED FILES", classes="section-header")
            if not self.uploaded_files:
                yield Static("[dim]No files uploaded yet[/dim]", classes="file-item")
            else:
                for f in self.uploaded_files:
                    yield Static(f"📄 {f}", classes="file-item")


class InvestigationTreePanel(Vertical):
    """Left panel content during Research Mode showing Investigation Tree."""

    def __init__(self, root_name: str = "Research Investigation", branches: list = None, **kwargs):
        kwargs.setdefault("id", "investigation-tree-panel")
        super().__init__(**kwargs)
        self.root_name = root_name
        self.branches = branches or []

    def compose(self) -> ComposeResult:
        yield Label("INVESTIGATION TREE", classes="section-header")
        
        tree: Tree[str] = Tree(self.root_name, id="investigation-tree")
        tree.show_root = True
        tree.root.expand()

        if self.branches:
            for branch in self.branches:
                if isinstance(branch, dict):
                    name = branch.get("name", "Branch")
                    node = tree.root.add(name, expand=True)
                    for leaf in branch.get("leaves", []):
                        node.add_leaf(f"• {leaf}")
                else:
                    tree.root.add_leaf(f"• {branch}")

        yield tree
        yield Button("+ Add direction", id="add-direction-btn", classes="add-direction-btn")
