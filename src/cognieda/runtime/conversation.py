from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import replace
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.schemas.common import ImmutableCogniEDABaseModel

DEFAULT_RECENT_TURN_LIMIT = 4
DEFAULT_OLDER_LEXICAL_MATCH_LIMIT = 4
APPLICATION_MESSAGE_ORIGIN_KEY = "cognieda_message_origin"
APPLICATION_MESSAGE_ORIGIN = "application"


class ConversationTurn(ImmutableCogniEDABaseModel):
    """One complete top-level Human-to-Planner interaction."""

    turn_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...] = Field(min_length=1)


class ConversationHistory(ImmutableCogniEDABaseModel):
    """Complete ordered native message history retained by one runtime Session."""

    turns: tuple[ConversationTurn, ...] = ()

    @model_validator(mode="after")
    def _unique_turn_ids(self) -> ConversationHistory:
        turn_ids = [turn.turn_id for turn in self.turns]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError("ConversationHistory rejects duplicate ConversationTurn IDs.")
        return self

    def add_turn(self, *, messages: Iterable[ModelMessage]) -> ConversationHistory:
        """Append one complete canonical native-message turn."""

        turn = ConversationTurn(messages=tuple(messages))
        return ConversationHistory(turns=(*self.turns, turn))

    def model_messages(self) -> tuple[ModelMessage, ...]:
        """Flatten retained turns without changing their durable boundaries."""

        return tuple(message for turn in self.turns for message in turn.messages)


def complete_turn_messages(
    *,
    human_message: str,
    planner_response: str,
    native_messages: Iterable[ModelMessage] = (),
) -> tuple[ModelMessage, ...]:
    """Complete a top-level turn without duplicating native Human/Planner messages."""

    if not human_message.strip():
        raise ValueError("A ConversationTurn requires a non-empty Human request.")
    if not planner_response.strip():
        raise ValueError("A ConversationTurn requires a non-empty Planner response.")

    messages = tuple(native_messages)
    if not _contains_user_prompt(messages, human_message):
        messages = (
            ModelRequest(
                parts=[UserPromptPart(content=human_message)],
                metadata={APPLICATION_MESSAGE_ORIGIN_KEY: APPLICATION_MESSAGE_ORIGIN},
            ),
            *messages,
        )
    if _last_text_response(messages) != planner_response:
        messages = (
            *messages,
            ModelResponse(
                parts=[TextPart(content=planner_response)],
                metadata={APPLICATION_MESSAGE_ORIGIN_KEY: APPLICATION_MESSAGE_ORIGIN},
            ),
        )
    return messages


def conversation_user_text(turn: ConversationTurn) -> str:
    """Derive the first textual Human prompt from canonical messages."""

    for message in turn.messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    return part.content
    return ""


def conversation_response_text(turn: ConversationTurn) -> str:
    """Derive the final textual Planner response from canonical messages."""

    return _last_text_response(turn.messages) or ""


def prepare_effective_message_history(
    turns: Sequence[ConversationTurn],
) -> tuple[ModelMessage, ...]:
    """Derive replay history without stale run-scoped Planner instructions."""

    return tuple(
        replace(message, instructions=None)
        if isinstance(message, ModelRequest) and message.instructions is not None
        else message
        for turn in turns
        for message in turn.messages
    )


def select_conversation_context(
    history: ConversationHistory,
    latest_request: str,
    *,
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
    older_lexical_match_limit: int = DEFAULT_OLDER_LEXICAL_MATCH_LIMIT,
) -> tuple[ConversationTurn, ...]:
    """Select bounded complete turns without mutating retained history."""

    if recent_turn_limit < 1:
        raise ValueError("recent_turn_limit must be positive.")
    if older_lexical_match_limit < 0:
        raise ValueError("older_lexical_match_limit cannot be negative.")
    request_terms = _selection_terms(latest_request)
    recent_start = max(0, len(history.turns) - recent_turn_limit)
    older_match_indexes: list[int] = []
    if older_lexical_match_limit:
        for index in range(recent_start - 1, -1, -1):
            turn = history.turns[index]
            if request_terms.intersection(_selection_terms(_turn_text(turn))):
                older_match_indexes.append(index)
                if len(older_match_indexes) == older_lexical_match_limit:
                    break

    selected_indexes = sorted((*older_match_indexes, *range(recent_start, len(history.turns))))
    return tuple(history.turns[index] for index in selected_indexes)


def _contains_user_prompt(messages: Sequence[ModelMessage], content: str) -> bool:
    return any(
        isinstance(message, ModelRequest)
        and any(
            isinstance(part, UserPromptPart) and part.content == content
            for part in message.parts
        )
        for message in messages
    )


def _last_text_response(messages: Sequence[ModelMessage]) -> str | None:
    for message in reversed(messages):
        if isinstance(message, ModelResponse):
            for part in reversed(message.parts):
                if isinstance(part, TextPart):
                    return part.content
    return None


def _turn_text(turn: ConversationTurn) -> str:
    texts: list[str] = []
    for message in turn.messages:
        for part in message.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                texts.append(part.content)
            elif isinstance(part, TextPart):
                texts.append(part.content)
    return " ".join(texts)


def _selection_terms(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return {
        term
        for term in re.findall(r"\w+", normalized, flags=re.UNICODE)
        if len(term) >= 3
    }
