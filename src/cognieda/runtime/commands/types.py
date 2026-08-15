from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CommandSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str

    @property
    def display_name(self) -> str:
        return "/" + self.name.replace(".", " ")