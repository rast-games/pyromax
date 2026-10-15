# Methods and mapper calls

Pyromax exposes the same operation at several abstraction levels. Application code should normally prefer bound models or `MaxApi`; mapper and protocol calls are intended for extensions and debugging.

## Call hierarchy

```text
Bound model helper → MaxApi mixin → BaseMaxApiMethod → Mapper method
    → immutable Envelope method → Protocol → Encoding → Transport
```

For example, `message.reply()` delegates to the bound client, while `api.send_message()` uses the same high-level method path with explicit IDs.

## Invoke a method class with `MaxApi`

`MaxApi.__call__()` accepts a `BaseMaxApiMethod` class, binds it to the client, and forwards arguments:

```python
from pyromax.methods import SendMessageMethod

message = await api(
    SendMessageMethod,
    chat_id=123456,
    text="Hello",
)
```

This is useful for generic services that receive a method class dynamically. For a fixed operation, `await api.send_message(...)` is clearer. The callable path also normalizes mapper transport/API failures into `BaseMaxApiMethodError`.

## Define an application method

A custom method can compose existing mapper operations while retaining the generic `api(Method, ...)` interface:

```python
from pyromax.methods import BaseMaxApiMethod
from pyromax.models import Message


class SendAuditMessage(BaseMaxApiMethod[Message | None]):
    async def __call__(self, chat_id: int, text: str) -> Message | None:
        if self._max_api is None:
            raise RuntimeError("Method is not bound to MaxApi")
        return await self._max_api.mapper.send_message(
            chat_id=chat_id,
            text=f"[audit] {text}",
        )


result = await api(SendAuditMessage, chat_id=123456, text="started")
```

This does not register a new wire opcode. A genuinely new MAX operation also requires mapper translation and an immutable protocol method.

## Calling the mapper directly

The concrete mapper is available as `api.mapper`:

```python
message = await api.mapper.send_message(chat_id=123456, text="Hello")
```

`EnvelopeMapperV11` implements operations grouped into message, chat, contact, user/profile, file, and authentication mixins. It also maintains authorization, reconnection, caches, object binding, update translation, and telemetry.

Direct mapper calls are useful when implementing a new `MaxApi` method or testing the mapping layer. They couple code to the selected mapper and may bypass client-level exception normalization. Do not import a private mixin merely to call it; subclass `Mapper` only when deliberately maintaining a custom backend.

`mapper.call_method(MethodClass, ...)` dispatches a known high-level method through the mapper's device-specific registry and raises when the mapper or selected device does not support it. Many public method classes already delegate directly to their corresponding mapper method, so application code rarely needs this function.

## Raw Envelope operations

`EnvelopeMapperV11.send()` and `send_raw()` accept immutable Envelope method objects. This is the lowest mapper-level API: callers work with protocol payloads and must understand opcodes, response shapes, retry behavior, authentication requirements, and mapping errors. Treat `mapping.envelope.v11.methods.immutable` and payload modules as version-coupled internals.
