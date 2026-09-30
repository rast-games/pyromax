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
