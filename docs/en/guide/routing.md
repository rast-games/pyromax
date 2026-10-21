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
- `disconnect` and `unsupported_client_version` lifecycle events.

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

Pass a dispatcher to `MaxApi(dispatcher=dispatcher)` when lifecycle handlers must observe disconnect or unsupported-version events raised during initialization. Polling installs the same listeners automatically for the rest of the client lifetime.

`Dispatcher(raw_update_mode=RawUpdateMode.ALL_RESPONSES)` exposes protocol errors and translation failures to update outer middleware. See [versions and resilience](resilience.md#raw-protocol-responses).

## Connection loss

Connection loss is a regular dispatcher event. Register its handler on the `Dispatcher` or any nested `Router`:

```python
from pyromax.models import DisconnectEvent


@dispatcher.disconnect()
async def disconnected(event: DisconnectEvent) -> None:
    print(
        f"Connection lost: {event.exception}; "
        f"reconnect={event.reconnect}; delay={event.delay}"
    )
```

The event runs after the failed connection is closed and before a reconnect attempt. It uses the same filters, nested-router traversal, middleware, and dependency injection as other router events. Handler exceptions are routed through `dispatcher.error`; they never cancel the reconnect attempt. The `reconnect` and `delay` fields come from `ExtraConfig.reconnect` and `ExtraConfig.reconnect_delay`.

## Unsupported client version

`client.unsupported-version` is exposed as a typed event. A handler can select an exact version for the next reconnect attempt:

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

If the handler does not change the version, the lifecycle automatically selects another entry from `event.available_versions`. The same exception is then sent to `dispatcher.disconnect`, followed by the reconnect attempt.

When the error may occur during the automatic connection inside `await MaxApi(...)`, pass the dispatcher to the client constructor:

```python
api = await MaxApi(dispatcher=dispatcher)
await dispatcher.start_polling(api)
```

The `dispatcher=` argument is only a source of lifecycle listeners. `MaxApi` does not appoint it as the client's dispatcher, start polling through it, or create an exclusive relationship between the objects. The same `Dispatcher` instance can therefore be passed to several clients; each listener invocation receives the `MaxApi` that emitted that event. Without this argument, behavior is unchanged: lifecycle listeners are attached when `start_polling()` begins.

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
