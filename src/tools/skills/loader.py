import tomllib
from pathlib import Path

from pydantic_ai_skills import SkillsCapability


def load_skills(
    path: str | Path = "config/skills.toml"
) -> dict[str, SkillsCapability]:
    """
    Load all skills defined in skills.toml.

    Example:
        {
            "planner": SkillsCapability(...),
            "graph_miner": SkillsCapability(...),
        }
    """

    skills_path = Path(path)
    if not skills_path.exists():
        raise FileNotFoundError(f"Skills configuration file not found: {skills_path}")


    with open(skills_path, "rb") as f:
        skills_config = tomllib.load(f)

    skills: dict[str, SkillsCapability] = {}
    for skill_name, skill_data in skills_config.items():
        skills[skill_name] = SkillsCapability(**skill_data)

    return skills    