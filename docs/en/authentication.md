# Authentication

`MaxApi` initializes transport, encoding, protocol, and mapper before authentication. In 0.8.5, the Web profile uses WebSocket, JSON, `EnvelopeProtocol`, and `EnvelopeV11`.

## Token authentication

```python
from pyromax import MaxApi
from pyromax.models import DeviceType

api = await MaxApi(
    token="YOUR_TOKEN",
    device_type=DeviceType.Web,
)
```

Use a token with the same kind of transport/device context that created it. If no token is supplied, the mapper begins an interactive authentication flow.

## QR authentication

For the Web profile, omit `token`. `TerminalAuthInteractor` prints the QR code; use `AuthCallbacks.qr_url` to display it elsewhere.

```python
async def show_qr_url(url: str) -> None:
    print("Open or render this URL and scan it in MAX:", url)


from pyromax.interaction import AuthCallbacks
from pyromax.models import DeviceType

api = await MaxApi(
    device_type=DeviceType.Web,
    auth_callbacks=AuthCallbacks(qr_url=show_qr_url),
)
```

## Phone/SMS authentication

Desktop and Android profiles use SMS authentication by default:

```python
async def get_sms_code(phone: str) -> str:
    print("Code requested for", phone)
    return input("SMS code: ")


from pyromax.interaction import AuthCallbacks
from pyromax.models import DeviceType

api = await MaxApi(
    device_type=DeviceType.Desktop,
    phone="78005553535",
    auth_callbacks=AuthCallbacks(sms_code=get_sms_code),
)
```

SMS delivery is rate-limited by MAX. Do not repeatedly request codes; the server may temporarily restrict the account. 

[//]: # (Provide a QR callback. if the selected mapper can fall back to QR authentication.)


## Registration and authentication middleware

`registration_config=RegistrationConfig(first_name=..., last_name=...)` supplies profile data when registration is required.

### AuthFlow lifecycle { #authflow-lifecycle }

When `token` is `None` and `auth_middleware_manager` is provided, `MaxApi` creates an `AuthFlow` after constructing the selected mapper, protocol, and transport. It then passes that flow through every registered auth middleware. The flow contains:

- `token`: a token supplied or discovered by middleware, initially `None`;
- `mapper`: the active mapper instance;
- `protocol`: the active protocol instance;
- `transport`: the active transport instance.

The flow returned by the middleware chain supplies the token to `mapper.initialize_client()`. Passing `token=...` directly to `MaxApi` skips the auth middleware chain.

### Create and connect the manager

Create one `AuthMiddlewareManager`, register middleware in execution order, and pass the manager to `MaxApi`:

```python
from pyromax import MaxApi
from pyromax.auth import AuthMiddlewareManager
from pyromax.models import DeviceType

auth_manager = AuthMiddlewareManager()
auth_manager.register(FirstAuthMiddleware()) # or auth_manager(FirstAuthMiddleware())
auth_manager.register(SecondAuthMiddleware()) # or auth_manager(SecondAuthMiddleware())

api = await MaxApi(
    auth_middleware_manager=auth_manager,
    device_type=DeviceType.Web,
)
```

`auth_manager(MyMiddleware())` is equivalent to `auth_manager.register(MyMiddleware())` and can also be used as a decorator.

### Type a concrete AuthFlow

`AuthFlow` is generic in this exact order:

```python
AuthFlow[MapperType, ProtocolType, TransportType]
```

For the default web stack, define an alias so the middleware, IDE, and type checker know the concrete types of `event.mapper`, `event.protocol`, and `event.transport`:

```python
import os
from collections.abc import Awaitable, Callable
from typing import Any

from pyromax.auth import AuthFlow, BaseAuthMiddleware
from pyromax.mapping import EnvelopeMapperV11
from pyromax.protocol.envelope import EnvelopeProtocol
from pyromax.transport import WebSocketTransport

WebAuthFlow = AuthFlow[
    EnvelopeMapperV11,
    EnvelopeProtocol,
    WebSocketTransport,
]


class FirstAuthMiddleware(BaseAuthMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [WebAuthFlow, dict[type[Any] | str, Any]],
            Awaitable[Any],
        ],
        event: WebAuthFlow,
        data: dict[type[Any] | str, Any],
    ) -> WebAuthFlow:
        # These attributes now have concrete static types.
        mapper: EnvelopeMapperV11 = event.mapper
        protocol: EnvelopeProtocol = event.protocol
        transport: WebSocketTransport = event.transport

        event.token = os.getenv("MAX_TOKEN")
        return await handler(event, data)
```

The middleware chain is nested in registration order: the first registered middleware runs first before the terminal handler and finishes last after it. Call `await handler(event, data)` to continue the chain. A middleware may deliberately return an `AuthFlow` without calling the handler to stop further auth middleware.

The `data` dictionary also contains the active client, mapper, protocol, and transport under their concrete runtime types. This allows shared middleware utilities to resolve backend-specific objects when necessary.

## Backend compatibility

| Transport | Device type | Protocol | Mapper |
| --- | --- | --- | --- |
| WebSocket + JSON | `DeviceType.Web` | `EnvelopeProtocol` | `EnvelopeV11` |
| Socket + MessagePack | `DeviceType.Desktop` | `EnvelopeProtocol` | `EnvelopeV11` |
| Socket + MessagePack | `DeviceType.Android` | `EnvelopeProtocol` | `EnvelopeV11` |

[//]: # (The registries are extensible, but a custom combination must implement compatible transport, protocol, and mapper contracts. Unsupported registry names raise `RuntimeError` during initialization.)
