# Routing and handlers

## Router hierarchy

`Dispatcher` is the root router. Feature routers can contain their own handlers and child routers.

```python
from pyromax import Dispatcher, Router

dispatcher = Dispatcher()
admin = Router(name="admin")
dispatcher.include_router(admin)
```

`include_routers(*routers)` attaches several routers. A router cannot be attached twice, to itself, or in a cycle.

## Event observers

Every router exposes observers for:

- `message`, `edited_message`, `reply_to_message`, `forward_message`, and `message_removed`;
- `message_reaction`, `message_added_reaction`, and `message_deleted_reaction`;
- `error`.
- `message_read`, `typing`, `presence`, `message_delete`, and `chat_update` domain events.

Handlers are checked in registration order. The first matching handler normally consumes the event; `skip()` explicitly continues propagation to another matching handler.

`soft_propagate` controls dependency-injection strictness, not event propagation between handlers. With the default `soft_propagate=False`, Pyromax raises `AnnotationError` in either of these cases:

- a handler parameter has no annotation;
- a handler parameter is annotated, but no value matching that annotation exists in the DI/workflow context.

With `soft_propagate=True`, both cases are allowed and Pyromax passes `None` for the affected parameter:

```python
@dispatcher.message(soft_propagate=True)
async def optional_dependency(message: Message, service: "OptionalService") -> None:
    # service is None when OptionalService is absent from the DI context.
    ...
```

Use this option only when the handler intentionally accepts missing dependencies. Despite its historical name, it does not cause the update to continue to the next handler.

`Dispatcher(concurrent_task_dispatch=True, concurrent_task_count=100)` processes independent updates concurrently with a bounded task count. Sequential dispatch remains the default when ordering matters.

## Register a handler

```python
from pyromax.models import Message


@dispatcher.message(from_me=True)
async def echo(message: Message) -> None:
    await message.reply(message.text or "")
```

Message observers ignore messages sent by the current account unless `from_me=True` is passed.

## Typed dependency injection

Every handler parameter must be annotated. The resolver matches annotations against the data accumulated by the dispatcher, filters, middleware, FSM, and `MaxApi.workflow_data`.

```python
from pyromax import MaxApi
from pyromax.models import Message


@dispatcher.message()
async def inspect(message: Message, api: MaxApi) -> None:
    await api.set_presence(True)
```

Forward references are supported. Custom dependencies can be supplied globally:

```python
class Database:
    pass


api = await MaxApi(workflow_data={Database: Database()})


@dispatcher.message()
async def save(message: Message, database: Database) -> None:
    ...
```

Middleware is usually a better choice for request-scoped dependencies.
