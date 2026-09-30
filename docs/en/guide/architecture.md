# Architecture

Pyromax separates user-facing behavior from wire-level details. This makes routing independent of the MAX protocol and allows backends to be replaced through registries.

```text
Application handlers
        ↑ typed data / model helpers
Dispatcher → Router → Observer → Filters → Middleware → Handler
        ↑
Mapped domain objects (Message, Chat, Contact, ...)
        ↑↓
Mapper (EnvelopeV11)
        ↑↓
Protocol (EnvelopeProtocol) → Encoding (JSON or MessagePack)
        ↑↓
Transport (websocket or socket envelope)
        ↑↓
MAX Messenger
```

## Client stack

`MaxApi` selects backend classes from transport, encoding, protocol, and mapper registries. Construction is asynchronous because session restoration, connections, and authentication may perform I/O. The mapper exposes high-level operations and translates protocol payloads into Pydantic domain models.

## Update path

1. `MaxApi.listen_updates()` returns a response translator and an asynchronous response stream.
2. `Dispatcher.start_polling()` maps every response to a resolved domain update.
3. Dispatcher outer middleware enriches the context, handles errors, and optionally creates an `FSMContext`.
4. The observer selects handlers for the event type.
5. Filters run in registration order. A `False` result rejects the handler; a dictionary merges values into handler data.
6. Middleware wraps the selected handler.
7. Parameters are resolved by their type annotations or forward-reference names.

## Public and extension layers

- Prefer `MaxApi` and bound model helpers for application code.
- Use `Router`, observers, filters, middleware, and FSM to structure behavior.
- Extend transport/protocol/mapper registries only when implementing a backend.
- Classes in `mapping.envelope.v11.payloads`, immutable method builders, and DTO translators are protocol internals and may evolve more quickly than the high-level API.

## Lifecycle and ownership

The dispatcher owns the polling loop and closes its FSM middleware when polling stops. It requests client shutdown, waits for in-flight update tasks, drains session writes, and closes the client stack. Models returned by the mapper are bound to the originating `MaxApi`; this enables methods such as `message.reply()` and `chat.history()`.
