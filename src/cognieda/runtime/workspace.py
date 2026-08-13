import os
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import toml

from cognieda.application.ports.llm import ModelConfig, ProviderType
from cognieda.application.ports.llm import ProviderType

@dataclass(slots=True)
class ProviderProfile:
    type: ProviderType
    model: str
    api_key_env: str
    base_url: str = ""


@dataclass(slots=True)
class ProjectConfig:
    default_provider: str
    providers: dict[str, ProviderProfile]

    @classmethod
    def load(cls, path: Path) -> "ProjectConfig":
        raw = toml.load(path) if path.exists() else {}

        providers = {
            name: ProviderProfile(
                type=cfg["type"],
                model=cfg["model"],
                api_key_env=cfg["api_key_env"],
                base_url=cfg.get("base_url", ""),
            )
            for name, cfg in raw.get("providers", {}).items()
        }

        return cls(
            default_provider=raw.get("default_provider", ""),
            providers=providers,
        )

    def resolve_model(self) -> ModelConfig:
        profile = self.providers[self.default_provider]

        api_key = os.environ.get(profile.api_key_env)
        if not api_key:
            raise ValueError(
                f"Environment variable '{profile.api_key_env}' is not set."
            )

        return ModelConfig(
            provider=profile.type,
            model_name=profile.model,
            base_url=profile.base_url,
            api_key=api_key,
        )


class Workspace:
    def __init__(
        self,
        root: Path,
        project_config: ProjectConfig,
    ) -> None:
        self.root = root
        self.project_config = project_config
        self.model_config: ModelConfig = project_config.resolve_model()

    # -------------------------------------------------------------------------
    # Workspace lifecycle
    # -------------------------------------------------------------------------

    @classmethod
    def open(cls, root: Path) -> "Workspace":
        root = cls._normalize(root)
        cls.initialize(root)

        return cls(
            root=root,
            project_config=ProjectConfig.load(
                root / ".cognieda" / "project.toml"
            ),
        )

    @classmethod
    def initialize(cls, root: Path) -> None:
        root = cls._normalize(root)

        cognieda = root / ".cognieda"

        (root / "data").mkdir(parents=True, exist_ok=True)
        (cognieda / "skills").mkdir(parents=True, exist_ok=True)
        (cognieda / "state").mkdir(parents=True, exist_ok=True)
        (cognieda / "sessions").mkdir(parents=True, exist_ok=True)

        cls._ensure_default_project_config(
            cognieda / "project.toml"
        )

        for name in (
            "agents.toml",
            "skills.toml",
            "mcp.toml",
        ):
            (cognieda / name).touch(exist_ok=True)

    @staticmethod
    def _normalize(root: Path) -> Path:
        return root.expanduser().resolve()

    # -------------------------------------------------------------------------
    # Directories
    # -------------------------------------------------------------------------

    @property
    def cognieda_dir(self) -> Path:
        return self.root / ".cognieda"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def state_dir(self) -> Path:
        return self.cognieda_dir / "state"

    @property
    def session_dir(self) -> Path:
        return self.cognieda_dir / "sessions"

    # -------------------------------------------------------------------------
    # Configuration files
    # -------------------------------------------------------------------------

    @property
    def project_config_path(self) -> Path:
        return self.cognieda_dir / "project.toml"

    @property
    def agents_config_path(self) -> Path:
        return self.cognieda_dir / "agents.toml"

    @property
    def skills_config_path(self) -> Path:
        return self.cognieda_dir / "skills.toml"

    @property
    def mcp_config_path(self) -> Path:
        return self.cognieda_dir / "mcp.toml"

    @property
    def planner_instruction_path(self) -> Path:
        return self.root / "AGENTS.md"

    # -------------------------------------------------------------------------
    # Planner instruction
    # -------------------------------------------------------------------------

    def load_planner_instruction(self) -> str:
        if not self.planner_instruction_path.exists():
            return ""

        return self.planner_instruction_path.read_text(
            encoding="utf-8"
        )

    # -------------------------------------------------------------------------
    # Agent configuration
    # -------------------------------------------------------------------------

    def load_agents_config(self) -> dict:
        return self._load_toml(self.agents_config_path)

    def save_agents_config(self, config: dict) -> None:
        self._save_toml(self.agents_config_path, config)

    # -------------------------------------------------------------------------
    # Skill configuration
    # -------------------------------------------------------------------------

    def load_skills_config(self) -> dict:
        return self._load_toml(self.skills_config_path)

    def save_skills_config(self, config: dict) -> None:
        self._save_toml(self.skills_config_path, config)

    # -------------------------------------------------------------------------
    # Generic TOML helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_toml(path: Path) -> dict:
        if not path.exists():
            return {}

        return toml.load(path)

    @staticmethod
    def _save_toml(path: Path, data: dict) -> None:
        with path.open("w", encoding="utf-8") as f:
            toml.dump(data, f)

    # -------------------------------------------------------------------------
    # Default configuration
    # -------------------------------------------------------------------------

    @staticmethod
    def _ensure_default_project_config(path: Path) -> None:
        if path.exists():
            return

        path.write_text(
            textwrap.dedent(
                """
                default_provider = "google"

                [providers.google]
                type = "google"
                model = "gemini-2.5-flash"
                api_key_env = "GOOGLE_API_KEY"

                [providers.openai]
                type = "openai"
                model = "gpt-5"
                api_key_env = "OPENAI_API_KEY"

                [providers.anthropic]
                type = "anthropic"
                model = "claude-sonnet-4"
                api_key_env = "ANTHROPIC_API_KEY"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    # -------------------------------------------------------------------------
    # TODO: Configuration editing
    #
    # These methods are temporary. Workspace should only locate files and load
    # configuration. Editing skills/agents belongs in a dedicated configuration
    # service (e.g. WorkspaceConfigurator, SkillRegistry, or AgentRegistry).
    #
    # Keep these methods here until the configuration subsystem is extracted.
    # -------------------------------------------------------------------------

    def add_skill(self, name: str, directory: str) -> None:
        config = self.load_skills_config()

        if name in config:
            raise ValueError(f"Skill '{name}' already exists.")

        config[name] = {
            "directories": directory,
        }

        self.save_skills_config(config)


    def remove_skill(self, name: str) -> None:
        config = self.load_skills_config()

        config.pop(name, None)

        self.save_skills_config(config)


    def add_worker_skill(
        self,
        worker: str,
        skill: str,
    ) -> None:
        config = self.load_agents_config()

        worker_config = config.setdefault(worker, {})
        skills = worker_config.setdefault("skills", [])

        if skill not in skills:
            skills.append(skill)

        self.save_agents_config(config)


    def remove_worker_skill(
        self,
        worker: str,
        skill: str,
    ) -> None:
        config = self.load_agents_config()

        worker_config = config.get(worker)
        if worker_config is None:
            return

        skills = worker_config.get("skills", [])

        if skill in skills:
            skills.remove(skill)

        self.save_agents_config(config)

    # -------------------------------------------------------------------------
    # TODO: Instruction loading
    #
    # Workspace should only expose filesystem paths. Reading and composing agent
    # instructions belongs to the instruction subsystem (e.g.
    # InstructionLoader/InstructionRepository). This helper remains temporarily
    # because the planner currently loads instructions directly from the workspace.
    # -------------------------------------------------------------------------
    @property
    def agent_instruction_path(self) -> Path:
        return self.root / "AGENTS.md"
    
    def load_agent_instruction(self) -> str:
        if not self.agent_instruction_path.is_file():
            return ""

        return self.agent_instruction_path.read_text(
            encoding="utf-8",
        )