# Middleware and dependency injection

Middleware wraps event processing. It receives the next handler, the current event, and a mutable data dictionary.

```python
from collections.abc import Awaitable, Callable
from typing import Any

from pyromax import Dispatcher
from pyromax.dispatcher.middlewares.base import BaseMiddleware
from pyromax.dispatcher.event import MaxObject


class RequestContext:
    pass


class ContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[MaxObject, dict[type[Any] | str, Any]], Awaitable[Any]],
        event: MaxObject,
        data: dict[type[Any] | str, Any],
    ) -> Any:
        data[RequestContext] = RequestContext()
        return await handler(event, data)


dispatcher = Dispatcher()
dispatcher.update.outer_middleware(ContextMiddleware())
```

The injected object is then available by annotation:

```python
@dispatcher.message()
async def handle(context: RequestContext) -> None:
    ...
```

## Outer and observer middleware

Dispatcher outer middleware surrounds update routing and all routed handlers. Observer middleware belongs to an event observer and only wraps handlers registered for that event. Middleware is executed in registration order and unwinds in reverse order around the handler.

## Raw responses and translation failures

By default, `Dispatcher` invokes `update.outer_middleware` only for responses that were translated successfully. This is the `RawUpdateMode.TRANSLATED_ONLY` mode.

Use `ALL_RESPONSES` to deliver every `Response` to middleware, including `ErrorResponse` objects and responses for which the translator raised an exception:

```python
from pyromax import Dispatcher, RawUpdateMode, UpdateTranslationFailure
from pyromax.dispatcher.event import ResolvedUpdate, Update

dispatcher = Dispatcher(raw_update_mode=RawUpdateMode.ALL_RESPONSES)


@dispatcher.update.outer_middleware()
async def raw_logger(handler, event, data):
    print("Raw response:", data[Update])

    failure = data.get(UpdateTranslationFailure)
    if failure is not None:
        print("Translation failed:", failure.exception)

    resolved = data.get(ResolvedUpdate)
    return await handler(event, data)
```

When the translator raises, `ResolvedUpdate` refers to the same raw object as `Update`, while `UpdateTranslationFailure` contains the exception. Domain handlers are not invoked for that response. After middleware returns, the dispatcher moves on to the next response.

## Built-in dispatcher middleware

By default `Dispatcher` installs:

- `ErrorsMiddleware` for error propagation;
- `UserContextMiddleware` for user/chat context;
- `FSMContextMiddleware`, unless `disable_fsm=True`.

Always call and return `await handler(event, data)` unless the middleware intentionally stops propagation.
