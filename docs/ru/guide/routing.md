# Роутинг и обработчики

## Иерархия роутеров

`Dispatcher` — корневой роутер. Роутеры отдельных функций могут содержать обработчики и дочерние роутеры.

```python
from pyromax import Dispatcher, Router

dispatcher = Dispatcher()
admin = Router(name="admin")
dispatcher.include_router(admin)
```

`include_routers(*routers)` подключает несколько роутеров. Нельзя повторно подключить роутер, подключить его к себе или создать цикл.

## Наблюдатели событий

У каждого роутера есть observers:

- `message`, `edited_message`, `reply_to_message`, `forward_message`, `message_removed`;
- `message_reaction`, `message_added_reaction`, `message_deleted_reaction`;
- `error`.
- доменные события `message_read`, `typing`, `presence`, `message_delete` и `chat_update`.
- lifecycle-события `disconnect` и `unsupported_client_version`.

Обработчики проверяются в порядке регистрации. Обычно первое совпадение поглощает событие, а `skip()` явно продолжает распространение до следующего подходящего обработчика.

`soft_propagate` управляет строгостью dependency injection, а не распространением события между обработчиками. При стандартном `soft_propagate=False` Pyromax выбрасывает `AnnotationError` в обоих случаях:

- у параметра handler отсутствует аннотация;
- параметр аннотирован, но соответствующего аннотации значения нет в DI/workflow-контексте.

При `soft_propagate=True` допускаются оба случая, а соответствующему параметру передаётся `None`:

```python
@dispatcher.message(soft_propagate=True)
async def optional_dependency(message: Message, service: "OptionalService") -> None:
    # Если OptionalService отсутствует в DI-контексте, service будет равен None.
    ...
```

Используйте этот параметр, только если handler намеренно допускает отсутствующие зависимости. Несмотря на историческое название, он не передаёт update следующему handler.

`Dispatcher(concurrent_task_dispatch=True, concurrent_task_count=100)` обрабатывает независимые события параллельно с ограничением числа задач. Последовательная обработка остаётся режимом по умолчанию, когда важен порядок.

Передайте dispatcher через `MaxApi(dispatcher=dispatcher)`, если lifecycle handlers должны видеть disconnect или unsupported-version во время инициализации. На время polling те же listeners устанавливаются автоматически.

`Dispatcher(raw_update_mode=RawUpdateMode.ALL_RESPONSES)` передаёт protocol errors и ошибки translation во внешние update middleware. Подробнее: [версии и устойчивость](resilience.md#raw-protocol-responses).

## Потеря соединения

Потеря соединения оформлена как обычное событие диспетчера. Обработчик можно зарегистрировать на `Dispatcher` или любом вложенном `Router`:

```python
from pyromax.models import DisconnectEvent


@dispatcher.disconnect()
async def disconnected(event: DisconnectEvent) -> None:
    print(
        f"Connection lost: {event.exception}; "
        f"reconnect={event.reconnect}; delay={event.delay}"
    )
```

Событие отправляется после закрытия сбойного соединения и перед попыткой переподключения. Для него работают те же фильтры, вложенные роутеры, middleware и dependency injection, что и для остальных событий. Исключения обработчиков проходят через `dispatcher.error` и не отменяют reconnect. Поля `reconnect` и `delay` берутся из `ExtraConfig.reconnect` и `ExtraConfig.reconnect_delay`.

## Неподдерживаемая версия клиента

`client.unsupported-version` доступен как типизированное событие. Handler может выбрать конкретную версию для следующей reconnect-попытки:

```python
from pyromax import MaxApi
from pyromax.models import UnsupportedClientVersionEvent


@dispatcher.unsupported_version()
async def unsupported_version(
    event: UnsupportedClientVersionEvent,
    api: MaxApi,
) -> None:
    if "26.35.1" in event.available_versions:
        await api.set_app_version("26.35.1", reconnect=False)
```

Если handler не поменял версию, lifecycle автоматически выберет другую из `event.available_versions`. После version-event та же ошибка приходит в `dispatcher.disconnect`, а затем начинается reconnect.

Если ошибка может возникнуть во время автоматического подключения внутри `await MaxApi(...)`, передайте dispatcher в конструктор клиента:

```python
api = await MaxApi(dispatcher=dispatcher)
await dispatcher.start_polling(api)
```

`dispatcher=` используется только как источник lifecycle-listeners. `MaxApi` не назначает переданный объект своим dispatcher, не запускает через него polling и не создаёт эксклюзивную связь между объектами. Поэтому один экземпляр `Dispatcher` можно передать нескольким клиентам; при каждом событии listener получает именно тот `MaxApi`, который его отправил. Если аргумент не указан, поведение остаётся прежним: lifecycle-listeners подключаются при входе в `start_polling()`.

## Регистрация обработчика

```python
from pyromax.models import Message


@dispatcher.message(from_me=True)
async def echo(message: Message) -> None:
    await message.reply(message.text or "")
```

По умолчанию message observer игнорирует сообщения текущего аккаунта. Для их обработки передайте `from_me=True`.

## Внедрение зависимостей по типам

Каждый параметр обработчика должен иметь аннотацию. Resolver ищет значения среди данных dispatcher, filters, middleware, FSM и `MaxApi.workflow_data`.

```python
from pyromax import MaxApi
from pyromax.models import Message


@dispatcher.message()
async def inspect(message: Message, api: MaxApi) -> None:
    await api.set_presence(True)
```

Поддерживаются forward references. Глобальные зависимости можно передать при создании клиента:

```python
class Database:
    pass


api = await MaxApi(workflow_data={Database: Database()})


@dispatcher.message()
async def save(message: Message, database: Database) -> None:
    ...
```

Для зависимостей на время обработки события обычно лучше использовать middleware.
