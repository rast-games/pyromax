# Версии и устойчивость

## Каталог версий приложения

`VersionApi` (alias `VersionCatalog`) загружает встроенный каталог Android-версий MAX и fingerprints. Необязательный удалённый JSON-object может дополнить или заменить записи:

```python
from pyromax import VersionApi

catalog = await VersionApi("https://example.test/max-versions.json").load()
version = catalog.recommended()
fingerprint = catalog.resolve(version)
```

`add(version, fingerprint, override=False)` добавляет локальную запись. `resolve()` выбрасывает `VersionNotFoundError` для неизвестной версии; повторное добавление — `VersionAlreadyExistsError`, если не задан `override=True`.

## Настройка версии

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

- `app_version` задаёт сообщаемую версию приложения;
- `app_fingerprint` принимает готовый `ApkBuildFingerprint`;
- `version_api` или alias `catalog` задаёт каталог (нельзя передавать оба);
- `strict_fingerprint_pair=True` требует наличия версии в каталоге;
- при стандартном `False` неизвестная версия может работать без fingerprint.

Версию можно просматривать и менять во время работы:

```python
print(api.app_version)
print(await api.get_available_app_versions())
await api.set_app_version("26.24.0")
await api.set_random_app_version(exclude=("26.23.0",))
```

Оба setter по умолчанию переподключают клиент; `reconnect=False` применяет значение без немедленного reconnect.

## Lifecycle-события

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


# Так будут видны lifecycle-события уже во время инициализации.
api = await MaxApi(dispatcher=dp)
await dp.start_polling(api)
```

Восстановлением управляют `reconnect`, `reconnect_delay`, `relogin`. При `autochange_app_version_if_current_unsupported=True` клиент выбирает другую версию каталога, если MAX отклонил текущую.

## Circuit breakers

Transport/API failures используют независимые `CircuitBreakerConfig` внутри `EnvelopeMapperConfigV11.circuit_breakers`:

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

После достижения threshold circuit открывается. По окончании cooldown допускается ровно один half-open probe; повторная ошибка увеличивает задержку до максимума. `wait_when_open=True` ждёт доступности, `False` приводит к `CircuitBreakerOpenError`. `enabled=False` отключает breaker категории.

Cancellation не считается dependency failure: shutdown остаётся быстрым, а отменённый probe не портит состояние circuit.

## Сырые protocol responses в middleware { #raw-protocol-responses }

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

В `ALL_RESPONSES` raw errors и непереводимые responses доходят до update outer middleware, но не вызывают domain handlers. Стандартный `TRANSLATED_ONLY` фильтрует их как раньше.
