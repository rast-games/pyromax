# Versions and resilience

## Application version catalog

`VersionApi` (also exported as `VersionCatalog`) loads the bundled Android MAX version/fingerprint catalog. An optional remote JSON object can extend or replace entries:

```python
from pyromax import VersionApi

catalog = await VersionApi("https://example.test/max-versions.json").load()
version = catalog.recommended()
fingerprint = catalog.resolve(version)
```

`add(version, fingerprint, override=False)` adds a local entry. `resolve()` raises `VersionNotFoundError` for an unknown version; duplicate addition raises `VersionAlreadyExistsError` unless `override=True`.

## Configure a version

```python
from pyromax import MaxApi, VersionApi
from pyromax.config import ExtraConfig
from pyromax.models import DeviceType

config = ExtraConfig(
    app_version="26.25.0",
    version_api=VersionApi(),
    strict_fingerprint_pair=True,
)
api = await MaxApi(device_type=DeviceType.Android, extra_config=config)
```

- `app_version` selects the reported application version;
- `app_fingerprint` supplies an `ApkBuildFingerprint` directly;
- `version_api` or its `catalog` alias supplies the catalog (do not pass both);
- `strict_fingerprint_pair=True` requires the selected version to exist in the catalog;
- with the default `False`, an unknown version may run without a fingerprint.

Runtime methods expose and change the active version:

```python
print(api.app_version)
print(await api.get_available_app_versions())
await api.set_app_version("26.24.0")
await api.set_random_app_version(exclude=("26.23.0",))
```

Both setters reconnect by default; use `reconnect=False` to apply the value without an immediate reconnect.

## Lifecycle events

```python
from pyromax import Dispatcher, MaxApi
from pyromax.models import DisconnectEvent, UnsupportedClientVersionEvent

dp = Dispatcher()


@dp.disconnect()
async def disconnected(event: DisconnectEvent) -> None:
    print(event.exception, event.reconnect, event.delay)


@dp.unsupported_client_version()
async def unsupported(event: UnsupportedClientVersionEvent) -> None:
    print(event.app_version, event.available_versions)


# Passing dp here makes initialization-time lifecycle events observable.
api = await MaxApi(dispatcher=dp)
await dp.start_polling(api)
```

`reconnect`, `reconnect_delay`, and `relogin` control recovery. `autochange_app_version_if_current_unsupported=True` allows the client to choose another catalog version after MAX rejects the current one.

## Circuit breakers

Transport failures and API failures have independent `CircuitBreakerConfig` values under `EnvelopeMapperConfigV11.circuit_breakers`:

```python
from pyromax.config import (
    CircuitBreakerConfig,
    EnvelopeMapperConfigV11,
    ExtraConfig,
    MappingCircuitBreakersConfig,
)

mapper = EnvelopeMapperConfigV11(
    circuit_breakers=MappingCircuitBreakersConfig(
        transport=CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
            max_cycles=5,
            backoff_factor=2.75,
            max_recovery_timeout=30,
            wait_when_open=True,
        ),
        api=CircuitBreakerConfig(enabled=True),
    )
)
api = await MaxApi(extra_config=ExtraConfig(mapper=mapper))
```

After the failure threshold, the circuit opens. Following the cooldown exactly one half-open probe is admitted; another failure increases the delay up to the configured maximum. `wait_when_open=True` waits for availability, while false produces `CircuitBreakerOpenError`. Set `enabled=False` for a category to disable its breaker.

Cancellation is not counted as a dependency failure. This lets shutdown remain responsive and prevents cancelled probes from poisoning circuit state.

## Raw protocol responses in middleware { #raw-protocol-responses }

```python
from pyromax import Dispatcher, RawUpdateMode, UpdateTranslationFailure
from pyromax.protocol import ErrorResponse, Response

dp = Dispatcher(raw_update_mode=RawUpdateMode.ALL_RESPONSES)


@dp.update.outer_middleware()
async def inspect_raw(handler, event: Response, data: dict):
    if isinstance(event, ErrorResponse):
        ...
    if failure := data.get(UpdateTranslationFailure):
        print(failure.exception)
    return await handler(event, data)
```

In `ALL_RESPONSES`, raw errors and untranslatable responses reach update outer middleware but do not invoke domain handlers. The default `TRANSLATED_ONLY` filters them as before.
