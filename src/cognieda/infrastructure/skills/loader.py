import tomllib
from pathlib import Path
from typing import Any

from pydantic_ai_skills import SkillsCapability


def load_skills(path: Path) -> dict[str, SkillsCapability]:
    """
    Load all skills defined in skills.toml.

    Relative directories are resolved relative to the location of
    skills.toml rather than the current working directory.
    """

    skills_path = path.resolve()

    with skills_path.open("rb") as f:
        skills_config = tomllib.load(f)

    base_dir = skills_path.parent

    skills: dict[str, SkillsCapability] = {}

    for skill_name, skill_data in skills_config.items():
        config: dict[str, Any] = dict(skill_data)

        directories = config.get("directories")
        if directories is not None:
            if isinstance(directories, str):
                directories = [directories]

            config["directories"] = [
                str((base_dir / directory).resolve())
                if not Path(directory).is_absolute()
                else str(Path(directory).resolve())
                for directory in directories
            ]

        skills[skill_name] = SkillsCapability(**config)

    return skills