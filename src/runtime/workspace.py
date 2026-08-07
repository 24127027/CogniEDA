from pathlib import Path
from dataclasses import dataclass, field

import toml

@dataclass(slots=True)
class ProjectConfig:
    values: dict[str, object] = field(default_factory=dict)

class Workspace:
    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def state_dir(self) -> Path:
        return self.root / ".cognieda" / "state"

    @property
    def session_dir(self) -> Path:
        return self.root / ".cognieda" / "sessions"
    
    def __init__(self, root: Path, config: ProjectConfig):
        self.root = root
        self.config = config

    @classmethod
    def open(cls, root: Path) -> "Workspace":
        config_path = root / ".cognieda" / "project.toml"
        if not config_path.exists():
            cls.init_workspace(root)

        config = cls.load_config(config_path)
        return cls(root=root, config=config)

    @classmethod
    def init_workspace(cls, root: Path):
        config_path = root / ".cognieda" / "project.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            config_path.write_text("", encoding="utf-8")
    
    @staticmethod
    def load_config(config_path: Path) -> ProjectConfig:
        config_data = toml.load(config_path) if config_path.exists() else {}
        return ProjectConfig(values=config_data)