# Changelog

## 0.8.5 — changes since 0.8

### Client lifecycle

- Client construction and connection can now be separated with `ExtraConfig(auto_connect_after_init=False)`, followed by explicit `await api.connect()`.
- Added `request_shutdown()`, `shutdown_requested`, `wait_for_shutdown()`, `wait_until_ready()`, and idempotent `stop()`.
- Graceful shutdown now stops polling and mapper tasks, waits for in-flight dispatcher work, drains queued session writes, and closes storage.
- Failed updates are isolated so one update does not terminate the polling loop.

### Configuration and backend stack

- Added `ExtraConfig`, per-layer configuration models, and Smart Init: selecting `DeviceType` fills every unspecified layer from a compatible preset, while constructor arguments override `ExtraConfig`, which overrides preset defaults.
- Added `DeviceType` and typed transport, encoding, protocol, and mapper registries.
- Added a distinct encoding layer. Web uses `JsonEncoding`; Desktop and Android use `MsgPackDictEncoding`. The old socket-envelope adapter was removed.
- Added `auto_connect_after_init` and `restore_user_agent_from_session` directives.
- Added Web, Desktop, and Android user-agent configuration models, including restoration of the original fingerprint from a session.
- Added configurable request/connect timing, telemetry, proxy, endpoint, WebSocket frame size, registration, and synchronization overrides.

### Sessions and authentication

- Added persistent asynchronous SQLite session storage and a replaceable `BaseSessionStorage` contract.
- Tokens, phone, device identity, user-agent data, and sync state are restored and updated asynchronously.
- Added modular `AuthInteractor`, `TerminalAuthInteractor`, and `AuthCallbacks` for QR, SMS, and interactive 2FA input.
- Added mapper `start_auth_flow()` / `end_auth_flow()` integration and typed generic `AuthFlow` middleware.

### Dispatcher and events

- `MaxApi(dispatcher=...)` can preload lifecycle listeners for events emitted during authentication. This does not bind the dispatcher to that client: the same dispatcher can be passed to multiple `MaxApi` instances.
- Added optional bounded concurrent dispatch with `concurrent_task_dispatch` and `concurrent_task_count`.
- Added handler `soft_propagate` (default: `False`) to control dependency-injection strictness. When enabled, a parameter receives `None` instead of raising `AnnotationError` both when it has no annotation and when its annotation has no matching value in the DI/workflow context. It does not continue the update to another handler.
- Filter-produced dependency data is preserved while handlers are checked.
- Added typed `MessageReadEvent`, `TypingEvent`, `PresenceEvent`, and `MessageDeleteEvent` translation and observers.

### Models and methods

- Chat history can optionally resolve its chat and bind returned objects to the client.
- Bound chat history and several lifecycle/error paths were corrected.
- Mapper transport errors and request cancellation handling were made more explicit.

See [configuration and sessions](guide/configuration.md), [backend layers](guide/backends.md), and [methods and mapper calls](guide/methods.md) for the new extension surface.
