# Middleware и внедрение зависимостей

Middleware оборачивает обработку события и получает следующий handler, текущее событие и изменяемый словарь данных.

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

После этого объект доступен по аннотации:

```python
@dispatcher.message()
async def handle(context: RequestContext) -> None:
    ...
```

## Внешние middleware и middleware observer

Внешнее middleware Dispatcher окружает маршрутизацию update и все routed handlers. Middleware observer относится к конкретному типу события. Цепочка входит в middleware в порядке регистрации, а выходит в обратном порядке.

## Raw Response и ошибки трансляции

По умолчанию `Dispatcher` вызывает `update.outer_middleware` только для успешно переведённых ответов. Это режим `RawUpdateMode.TRANSLATED_ONLY`.

Чтобы middleware получало все объекты `Response`, включая `ErrorResponse` и ответы, на которых упал транслятор, включите `ALL_RESPONSES`:

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

Если транслятор выбросил исключение, `ResolvedUpdate` ссылается на тот же raw-объект, что и `Update`, а `UpdateTranslationFailure` содержит исключение. Доменные handlers для такого response не вызываются. После выхода из middleware диспетчер переходит к следующему response.

## Встроенные middleware Dispatcher

По умолчанию устанавливаются:

- `ErrorsMiddleware` для передачи ошибок;
- `UserContextMiddleware` для контекста пользователя и чата;
- `FSMContextMiddleware`, если не задано `disable_fsm=True`.

Всегда вызывайте и возвращайте `await handler(event, data)`, если middleware не должно намеренно остановить распространение события.
