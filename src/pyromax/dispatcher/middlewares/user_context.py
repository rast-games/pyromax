from typing import Any
from collections.abc import Callable, Awaitable


from ..middlewares.base import BaseMiddleware
from ..event import ResolvedUpdate, MaxObject
from .event_resolvers import EventContext, EVENT_STRUCTURE_RESOLVERS

EVENT_CONTEXT_KEY = "event_context"


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[MaxObject, dict[Any, Any]], Awaitable[Any]],
        event: MaxObject,
        data: dict[Any, Any],
    ) -> Any:
        """Process an event through the user context middleware.

        :param handler: Handler to invoke.
        :type handler: Callable[[MaxObject, dict[Any, Any]], Awaitable[Any]]
        :param event: Incoming event to process.
        :type event: MaxObject
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        resolved_update = data.get(ResolvedUpdate)
        if resolved_update is None:
            return await handler(event, data)
        data[EVENT_CONTEXT_KEY] = self.resolve_event_context(event=resolved_update)
        return await handler(event, data)

    @staticmethod
    def resolve_event_context(
        event: MaxObject,
    ) -> EventContext:

        """Resolve event context.

        :param event: Incoming event to process.
        :type event: MaxObject
        :returns: The resulting EventContext value.
        :rtype: EventContext
        """
        typeof_update = type(event)
        resolver = EVENT_STRUCTURE_RESOLVERS.get(typeof_update)
        if resolver is None:
            return EventContext()
        return resolver(event)
