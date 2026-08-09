import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import toml


@dataclass(slots=True)
class ProjectConfig:
    values: dict[str, object] = field(default_factory=dict)

    def get(self, key: str, default=None):
        current = self.values

        for part in key.split("."):
            if not isinstance(current, dict):
                return default

            current = current.get(part)

            if current is None:
                return default

        return current


class Workspace:
    def __init__(self, root: Path, config: ProjectConfig):
        self.root = self._normalize_root(root)
        self.config = config

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def state_dir(self) -> Path:
        return self.root / ".cognieda" / "state"

    @property
    def session_dir(self) -> Path:
        return self.root / ".cognieda" / "sessions"

    @classmethod
    def open(cls, root: Path) -> "Workspace":
        root = cls._normalize_root(root)
        cls.init_workspace(root)
        config_path = root / ".cognieda" / "project.toml"

        config = cls.load_config(config_path)

        return cls(
            root=root,
            config=config,
        )

    @classmethod
    def init_workspace(cls, root: Path) -> None:
        root = cls._normalize_root(root)
        config_path = root / ".cognieda" / "project.toml"

        config_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        (root / "data").mkdir(parents=True, exist_ok=True)

        if not config_path.exists():
            default_config = textwrap.dedent(
                """\
                [model]
                name = "default-model"
                base_url = ""
                api_key = "local"
                """
            )

            config_path.write_text(
                default_config,
                encoding="utf-8",
            )

    @staticmethod
    def _normalize_root(root: Path) -> Path:
        return root.expanduser().resolve()

    @staticmethod
    def load_config(config_path: Path) -> ProjectConfig:
        config_data = toml.load(config_path) if config_path.exists() else {}

        return ProjectConfig(values=config_data)
