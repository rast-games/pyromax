# Configuration and sessions

`ExtraConfig` is the central configuration object for the complete client stack. Short constructor arguments such as `token=`, `phone=`, `work_dir=`, and `device_type=` are convenient overrides; use `ExtraConfig` when settings need to be reusable or when configuring a specific layer.

## Complete example

```python
from pyromax import MaxApi
from pyromax.config import (
    EnvelopeMapperConfigV11,
    ExtraConfig,
    WebSocketTransportConfig,
)
from pyromax.models import DeviceType, SyncOverrides

config = ExtraConfig(
    transport=WebSocketTransportConfig(
        proxy=None,
        max_size=10 * 1024 * 1024,
    ),
    mapper=EnvelopeMapperConfigV11(
        device_type=DeviceType.Web,
        token=None,
        phone=None,
        password=None,
        interactive=True,
        use_telemetry=True,
        request_timeout=30,
    ),
    work_dir=".data",
    session_name="accounts.db",
    session_id="primary-account",
    restore_user_agent_from_session=True,
    auto_connect_after_init=True,
    sync=SyncOverrides(),
)

api = await MaxApi(extra_config=config)
```

## Smart Init and configuration priority

Smart Init constructs a compatible client stack from the selected `DeviceType`. In the common case, selecting the device is enough:

```python
from pyromax import MaxApi
from pyromax.models import DeviceType

web = await MaxApi(device_type=DeviceType.Web)
desktop = await MaxApi(device_type=DeviceType.Desktop)
android = await MaxApi(device_type=DeviceType.Android)
```

For every setting, Pyromax uses the highest-priority value that was explicitly supplied:

```text
MaxApi constructor argument
        ↓ overrides
value from ExtraConfig
        ↓ overrides
Smart Init default for DeviceType
```

In other words: **constructor arguments > `ExtraConfig` > Smart Init defaults**.

- Direct `token`, `password`, `phone`, `session_id`, `work_dir`, `session_name`, `auth_interactor`, and `device_type` arguments replace their corresponding configured values.
- Explicit transport, encoding, protocol, or mapper selectors passed to `MaxApi` take precedence over the layer selected from `ExtraConfig` or a preset.
- Explicit layer configurations inside `ExtraConfig` take precedence over Smart Init defaults.
- Anything left unspecified is filled from the preset matching the effective `DeviceType`.

For example, this retains the standard Desktop socket, MessagePack, protocol, and mapper, but replaces the socket endpoint and request timeout:

```python
config = ExtraConfig(
    transport=SocketTransportConfig(host="example.test", port=443),
    mapper=EnvelopeMapperConfigV11(
        device_type=DeviceType.Desktop,
        request_timeout=45,
    ),
)

# The constructor value wins over device_type from ExtraConfig.
# The remaining unspecified layers are selected for Android by Smart Init.
api = await MaxApi(
    extra_config=config,
    device_type=DeviceType.Android,
)
```

!!! note
    Prefer selecting only `DeviceType` unless a layer really needs customization. Overriding individual layers makes you responsible for their compatibility; Pyromax warns when the resulting combination is not a known preset.

## Layer settings

| Field | Built-in configuration | Purpose |
| --- | --- | --- |
| `transport` | `WebSocketTransportConfig`, `SocketTransportConfig` | Endpoint, proxy, TLS, WebSocket origin/header, and maximum frame size. |
| `encoding` | `JsonEncodingConfig`, `MsgPackDictEncodingConfig`, `NoEncodingConfig` | Serialization between protocol values and transport values. Usually selected by the device profile. |
| `protocol` | `EnvelopeProtocolConfig` | Protocol implementation configuration. It currently has no public fields. |
| `mapper` | `EnvelopeMapperConfigV11` | Device type, credentials, user agent, timeouts, authentication mode, telemetry, and registration. |

The Smart Init preset depends on the effective `mapper.device_type`:

| Device | Transport | Encoding | Protocol | Mapper |
| --- | --- | --- | --- | --- |
| `DeviceType.Web` | WebSocket | JSON | Envelope | Envelope V11 |
| `DeviceType.Desktop` | Socket | MessagePack | Envelope | Envelope V11 |
| `DeviceType.Android` | Socket | MessagePack | Envelope | Envelope V11 |

If only a mapper profile is supplied, Smart Init selects its matching transport and the remaining layers. Explicit combinations are accepted with a warning when they do not match a known preset.

## Mapper and user-agent settings

`EnvelopeMapperConfigV11` contains the commonly adjusted runtime settings:

- `device_type`, `token`, `phone`, and `password` select identity and credentials;
- `sms_auth` defaults to false for Web and true for Desktop/Android;
- `interactive` controls interactive mapper behavior;
- `keepalive_ping_interval`, `connect_timeout`, and `request_timeout` control timing;
- `registration_config` supplies profile data for a new account;
- `use_mobile_fingerprint` and `use_telemetry` control mapper features;
- `mapper_logger` replaces the mapper logger;
- `user_agent_config` supplies a Web, Desktop, or Android fingerprint.

User-agent configuration includes device ID, locale, timezone, OS, device name, application version, and device-specific fields. Supplying it explicitly marks it as custom and prevents an automatically restored fingerprint from replacing it.

## Directives

Directives change client orchestration rather than an individual backend:

### `auto_connect_after_init`

The default is `True`, so `await MaxApi(...)` constructs the stack and immediately calls `connect()`. Set it to `False` to separate construction from authentication/startup:

```python
config = ExtraConfig(auto_connect_after_init=False)
api = await MaxApi(extra_config=config)

try:
    # Register runtime integrations or inspect api.transport/protocol/mapper here.
    await api.connect()
    await api.wait_until_ready()
finally:
    await api.stop()
```

`connect()` starts authentication and the mapper. `stop()` is idempotent, requests graceful shutdown, stops the mapper, drains queued session writes, and closes session storage. A stopped client may be connected again; `connect()` resets its shutdown state.

### `restore_user_agent_from_session`

The default is `True`. When a matching session exists and no custom user-agent config was supplied, Pyromax restores the saved device fingerprint. Set it to `False` to keep the newly generated configuration. Changing fingerprints can affect how MAX recognizes a session.

## Sessions and synchronization

`work_dir` and `session_name` locate the default `AioSqLiteSessionStorage`; `session_id` identifies an account inside it. The stored `SessionInfo` contains token, phone, device identity, user-agent configuration, and sync markers.

`sync=SyncOverrides(...)` selectively replaces restored sync values (`chats_sync`, `contacts_sync`, `drafts_sync`, `presence_sync`, `chats_count`, and `config_hash`). Leave a field as `None` to use its saved value.

Implement `BaseSessionStorage` for another database and pass its instance as `session_storage`. The asynchronous contract is `save_session`, `load_session`, `update_session`, `delete_session`, and `close`.

## Authentication interaction

`auth_interactor` accepts an `AuthInteractor`. By default, `TerminalAuthInteractor` renders QR codes and prompts for SMS and 2FA. For simple customization, pass `AuthCallbacks` to `MaxApi`; do not combine callbacks with a custom interactor.
