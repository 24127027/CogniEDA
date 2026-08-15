from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

from .events import RuntimeEvent

EventT = TypeVar("EventT", bound=RuntimeEvent)

EventHandler = Callable[[EventT], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[
            type[RuntimeEvent],
            list[Callable[[Any], None]],
        ] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        handlers = self._handlers.get(event_type)
        if handlers is None:
            return

        try:
            handlers.remove(handler)
        except ValueError:
            return

        if not handlers:
            del self._handlers[event_type]

    def publish(self, event: RuntimeEvent) -> None:
        for handler in tuple(self._handlers[type(event)]):
            handler(event)