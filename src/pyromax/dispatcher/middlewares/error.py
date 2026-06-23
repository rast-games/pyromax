from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from .base import BaseMiddleware
from ..event.base import SkipHandler, CancelHandler
from ..event.UpdateType import UNHANDLED, UNKNOWN_UPDATE, MaxObject
from ...models import ErrorEvent


if TYPE_CHECKING:
    from ..Router import Router

class ErrorsMiddleware(BaseMiddleware):
    def __init__(self, router: Router):
        self.router = router


    async def __call__(
            self,
            handler: Callable[[MaxObject, dict[str | type[Any], Any]], Awaitable[Any]],
            event: MaxObject,
            data: dict[str | type[Any], Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except (CancelHandler, SkipHandler):
            raise
        except Exception as e:
            err = ErrorEvent(update=event, exception=e)
            data.update({
                ErrorEvent: err
            })
            response = await self.router.notify(
                event_types=['ERROR'],
                update=err,
                data=data
            )
            if response is not UNHANDLED and response is not UNKNOWN_UPDATE:
                return response
            raise