# Backend layers and extension

Pyromax splits the MAX connection into four replaceable layers. A fifth, high-level method layer presents domain operations to `MaxApi`.

## Built-in implementations

### Transport

`WebSocketTransport` carries Web traffic and supports URL, proxy, origin, user-agent header, and maximum frame size. `SocketTransport` carries Desktop/Android traffic over an optional TLS connection and supports a proxy. Transports only move encoded values; they do not interpret Envelope requests.

### Encoding

`JsonEncoding` maps dictionaries to JSON text for WebSocket. `MsgPackDictEncoding` maps dictionaries to framed MessagePack bytes for socket clients and handles supported compression formats. `NoEncoding` passes values through and is mainly an extension tool. `SocketEncoding` additionally exposes header size and payload-length decoding so the transport remains unaware of message framing.

### Protocol

`EnvelopeProtocol` creates request/response correlation around the transport, applies encoding, runs the response reader, exposes `send()` and `get_updates()`, and cancels pending requests when closed.

### Mapper

`EnvelopeMapperV11` translates domain operations to Envelope V11 payloads and responses back to models. Its mixins cover messages and polls, chats and membership, contacts and sessions, profile/folders/presence, files, and authentication. It owns authorization and keepalive state, reconnection lifecycle, object binding/caches, update translation, and optional telemetry.

## Extension contracts

Custom implementations derive from `BaseTransport`, `BaseEncoding`, `BaseMaxProtocol`, or `BaseMapper`. Constructors receive the complete `ExtraConfig`, which lets cooperating layers share configuration. Async transport, protocol, and mapper classes use the project's asynchronous initialization convention.

Registration decorators associate a name with a class:

```python
from pyromax.encoding import BaseEncoding
from pyromax.encoding.registry import register_encoding


@register_encoding("AcmeEncoding")
class AcmeEncoding(BaseEncoding[dict, bytes, bytes, dict]):
    def encode(self, data: dict, *args, **kwargs) -> bytes:
        ...

    def decode(self, data: bytes, *args, **kwargs) -> dict:
        ...
```

Equivalent decorators are `register_transport`, `register_protocol`, and `register_mapper`.

!!! warning "Registry integration in 0.9"
    Registration alone does not make a backend selectable by `MaxApi`. The current configuration resolver maps known config classes to the built-in registry enums. A full custom stack must also provide config models and extend `from_config_to_registry()`, `from_registry_to_config()`, and, when appropriate, `CONFIG_SETS`. These are currently version-coupled extension points rather than a stable third-party plugin API.

## Implementing a mapper

A mapper must implement lifecycle (`start`, `stop`, readiness and auth-flow hooks), update listening/translation, file transfer, required domain primitives, and `call_method`. The generic parameters describe its protocol and file model. In practice, extending `EnvelopeMapperV11` is less work when the wire protocol remains Envelope V11:

```python
from pyromax.mapping.envelope.v11.Mapper import Mapper
from pyromax.mapping.registry import register_mapper


@register_mapper("AcmeEnvelopeV11")
class AcmeEnvelopeMapper(Mapper):
    async def custom_operation(self, value: str) -> None:
        # Compose existing mapper methods or add an immutable Envelope method.
        ...
```

Subclassing a mixin directly is not recommended: `Mapper` assembles all mixins and the shared lifecycle state they expect. A custom mapper also needs a corresponding mapper configuration and resolver mapping before `MaxApi` can construct it.

## Compatibility rules

- Transport values must match the encoding output/input types.
- Socket transports require `SocketEncoding` framing support.
- Protocol request and response types must match the mapper.
- Mapper device support must agree with its user-agent model and method registry.
- Shutdown implementations must cancel readers/keepalive tasks and resolve or cancel pending requests.

Keep extension code pinned to the Pyromax minor/patch version until the registry/configuration extension API is declared stable.
