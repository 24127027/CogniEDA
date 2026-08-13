import os
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import toml

from cognieda.application.ports.llm import ModelConfig, ProviderType
from cognieda.application.ports.llm import ProviderType
from cognieda.runtime import workspace

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
        self.model_config = self.resolve_model_config()

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def cognieda_dir(self) -> Path:
        return self.root / ".cognieda"

    @property
    def state_dir(self) -> Path:
        return self.cognieda_dir / "state"

    @property
    def session_dir(self) -> Path:
        return self.cognieda_dir / "sessions"

    @property
    def project_config_path(self) -> Path:
        return self.cognieda_dir / "project.toml"

    @property
    def agents_config_path(self) -> Path:
        return self.cognieda_dir / "agents.toml"

    @property
    def mcp_config_path(self) -> Path:
        return self.cognieda_dir / "mcp.toml"

    @property
    def skills_config_path(self) -> Path:
        return self.cognieda_dir / "skills.toml"

    @property
    def planner_agent_instruction_path(self) -> Path:
        return self.root / "AGENTS.md"

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
        cognieda_dir = root / ".cognieda"

        cognieda_dir.mkdir(parents=True, exist_ok=True)
        (root / "data").mkdir(parents=True, exist_ok=True)
        (cognieda_dir / "skills").mkdir(parents=True, exist_ok=True)

        # Initialize project.toml if it doesn't exist
        project_config_path = cognieda_dir / "project.toml"
        if not project_config_path.exists():
            default_config = textwrap.dedent(
                """\
                [model]
                provider = "google"
                """
            )

            project_config_path.write_text(
                default_config,
                encoding="utf-8",
            )

        # Initialize agents.toml, skills.toml, and mcp.toml if they don't exist
        additional_configs = ["agents.toml", "skills.toml", "mcp.toml"]
        for config_filename in additional_configs:
            file_path = cognieda_dir / config_filename
            if not file_path.exists():
                file_path.touch()

    @staticmethod
    def _normalize_root(root: Path) -> Path:
        return root.expanduser().resolve()

    @staticmethod
    def load_config(config_path: Path) -> ProjectConfig:
        config_data = toml.load(config_path) if config_path.exists() else {}

        return ProjectConfig(values=config_data)

    # TODO: Temporarily implement add/remove skill methods for workspace, 
    # but these should be moved to some where else
    def add_skill(self, name: str, directory: str) -> None:
        config = self._load_skills_config()

        if name in config:
            raise ValueError(f"Skill '{name}' already exists.")

        config[name] = {
            "directories": directory,
        }

        self._save_skills_config(config)

    def remove_skill(self, name: str) -> None:
        config = self._load_skills_config()

        config.pop(name, None)

        self._save_skills_config(config)

    def add_worker_skill(self, worker: str, skill: str) -> None:
        config = self._load_agents_config()

        worker_cfg = config.setdefault(worker, {})
        skills = worker_cfg.setdefault("skills", [])

        if skill not in skills:
            skills.append(skill)

        self._save_agents_config(config)

    def remove_worker_skill(self, worker: str, skill: str) -> None:
        config = self._load_agents_config()

        worker_cfg = config.get(worker)
        if worker_cfg is None:
            return

        skills = worker_cfg.get("skills", [])

        if skill in skills:
            skills.remove(skill)

        self._save_agents_config(config)

    def _load_agents_config(self) -> dict:
        try:
            return toml.load(self.agents_config_path)
        except FileNotFoundError:
            return {}

    def _save_agents_config(self, config: dict) -> None:
        with open(self.agents_config_path, "w", encoding="utf-8") as f:
            toml.dump(config, f)

    def _load_skills_config(self) -> dict:
        try:
            return toml.load(self.skills_config_path)
        except FileNotFoundError:
            return {}

    def _save_skills_config(self, config: dict) -> None:
        with open(self.skills_config_path, "w", encoding="utf-8") as f:
            toml.dump(config, f)

    def load_planner_agent_instruction(self) -> str:
        path = self.planner_agent_instruction_path

        if not path.is_file():
            return ""

        return path.read_text(encoding="utf-8")

    
    def _resolved_value(
        self,
        key: str,
        *environment_names: str,
    ) -> str:
        workspace_value = self.config.get(key)
        if workspace_value is not None and str(workspace_value).strip():
            return str(workspace_value).strip()

        for environment_name in environment_names:
            environment_value = os.environ.get(environment_name, "").strip()
            if environment_value:
                return environment_value

        return ""


    def _normalize_provider(self, provider: str) -> ProviderType:
        if provider == "gemini":
            return "google"
        if provider == "openai":
            return "openai"
        if provider == "google":
            return "google"
        if provider == "anthropic":
            return "anthropic"
        raise ValueError(f"Unsupported model provider: {provider}")


    def resolve_model_config(self) -> ModelConfig:
        """Resolve workspace-first model configuration without mutating process state."""

        provider = self._resolved_value("model.provider", "COGNIEDA_MODEL_PROVIDER")
        model_name = self._resolved_value("model.name", "COGNIEDA_MODEL_NAME")
        base_url = self._resolved_value(
            "model.base_url",
            "MODEL_BASE_URL",
            "COGNIEDA_OPENAI_BASE_URL",
        )
        api_key = self._resolved_value(
            "model.api_key",
            "MODEL_API_KEY",
            "COGNIEDA_OPENAI_API_KEY",
        )

        if not model_name:
            raise ValueError(
                "Model name is required in .cognieda/project.toml or COGNIEDA_MODEL_NAME."
            )
        if not api_key:
            raise ValueError(
                "Model API key is required in .cognieda/project.toml or "
                "MODEL_API_KEY (legacy fallback: COGNIEDA_OPENAI_API_KEY)."
            )
        if not provider:
            raise ValueError(
                "Model provider is required in .cognieda/project.toml or "
                "COGNIEDA_MODEL_PROVIDER."
            )

        return ModelConfig(
            provider=self._normalize_provider(provider),
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
        )
