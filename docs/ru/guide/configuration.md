# Конфигурация и сессии

`ExtraConfig` — центральная конфигурация всего клиентского стека. Короткие аргументы `MaxApi`, например `token=`, `phone=`, `work_dir=` и `device_type=`, удобны как точечные переопределения; для повторного использования настроек и настройки отдельных слоёв используйте `ExtraConfig`.

## Полный пример

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

## Smart Init и приоритет конфигурации

Smart Init собирает совместимый клиентский стек по выбранному `DeviceType`. В обычном случае достаточно указать только устройство:

```python
from pyromax import MaxApi
from pyromax.models import DeviceType

web = await MaxApi(device_type=DeviceType.Web)
desktop = await MaxApi(device_type=DeviceType.Desktop)
android = await MaxApi(device_type=DeviceType.Android)
```

Для каждой настройки Pyromax берёт явно указанное значение с наибольшим приоритетом:

```text
Аргумент конструктора MaxApi
        ↓ переопределяет
значение из ExtraConfig
        ↓ переопределяет
стандарт Smart Init для DeviceType
```

Иными словами: **аргументы конструктора > `ExtraConfig` > стандартные значения Smart Init**.

- Прямые `token`, `password`, `phone`, `session_id`, `work_dir`, `session_name`, `auth_interactor` и `device_type` замещают соответствующие значения конфигурации.
- Явные selectors транспорта, encoding, протокола или mapper, переданные в `MaxApi`, приоритетнее слоя из `ExtraConfig` или preset.
- Явные конфигурации слоёв внутри `ExtraConfig` приоритетнее стандартов Smart Init.
- Всё, что не переопределено, заполняется из preset эффективного `DeviceType`.

Например, конфигурация ниже берёт стандартные socket, MessagePack, protocol и mapper профиля Desktop, но меняет endpoint и request timeout:

```python
config = ExtraConfig(
    transport=SocketTransportConfig(host="example.test", port=443),
    mapper=EnvelopeMapperConfigV11(
        device_type=DeviceType.Desktop,
        request_timeout=45,
    ),
)

# Значение конструктора приоритетнее device_type из ExtraConfig.
# Неуказанные слои Smart Init подберёт уже для Android.
api = await MaxApi(
    extra_config=config,
    device_type=DeviceType.Android,
)
```

!!! note
    Если кастомизация слоя не нужна, предпочтительно указывать только `DeviceType`. После ручной замены отдельных слоёв за их совместимость отвечает пользователь; для неизвестной комбинации Pyromax выводит предупреждение.

## Настройки слоёв

| Поле | Встроенные конфигурации | Назначение |
| --- | --- | --- |
| `transport` | `WebSocketTransportConfig`, `SocketTransportConfig` | Endpoint, proxy, TLS, WebSocket origin/header и максимальный размер frame. |
| `encoding` | `JsonEncodingConfig`, `MsgPackDictEncodingConfig`, `NoEncodingConfig` | Сериализация между значениями протокола и транспорта. Обычно выбирается профилем устройства. |
| `protocol` | `EnvelopeProtocolConfig` | Конфигурация протокола; сейчас публичных полей нет. |
| `mapper` | `EnvelopeMapperConfigV11` | Тип устройства, credentials, user agent, таймауты, авторизация, telemetry и регистрация. |

Preset Smart Init зависит от эффективного `mapper.device_type`:

| Устройство | Транспорт | Кодирование | Протокол | Маппер |
| --- | --- | --- | --- | --- |
| `DeviceType.Web` | WebSocket | JSON | Envelope | Envelope V11 |
| `DeviceType.Desktop` | Socket | MessagePack | Envelope | Envelope V11 |
| `DeviceType.Android` | Socket | MessagePack | Envelope | Envelope V11 |

Если задан только профиль маппера, Smart Init подберёт транспорт и остальные слои. Явная неизвестная комбинация принимается с предупреждением.

## Маппер и user agent

Основные поля `EnvelopeMapperConfigV11`:

- `device_type`, `token`, `phone`, `password` — идентичность и credentials;
- `sms_auth` по умолчанию выключен для Web и включён для Desktop/Android;
- `interactive` управляет интерактивным поведением маппера;
- `keepalive_ping_interval`, `connect_timeout`, `request_timeout` задают тайминги;
- `registration_config` содержит данные нового аккаунта;
- `use_mobile_fingerprint` и `use_telemetry` включают возможности маппера;
- `mapper_logger` заменяет logger маппера;
- `user_agent_config` задаёт Web-, Desktop- или Android-fingerprint.

User-agent config содержит device ID, locale, timezone, ОС, имя устройства, версию приложения и специфичные для устройства поля. Явно переданный объект считается пользовательским и не заменяется fingerprint из сессии.

## Директивы

Директивы меняют оркестрацию клиента, а не отдельный backend.

### `auto_connect_after_init`

По умолчанию `True`: `await MaxApi(...)` создаёт стек и сразу вызывает `connect()`. Значение `False` отделяет создание объектов от авторизации и запуска:

```python
config = ExtraConfig(auto_connect_after_init=False)
api = await MaxApi(extra_config=config)

try:
    # Здесь можно подключить интеграции или проверить слои клиента.
    await api.connect()
    await api.wait_until_ready()
finally:
    await api.stop()
```

`connect()` запускает авторизацию и маппер. Идемпотентный `stop()` запрашивает штатное завершение, останавливает маппер, записывает очередь изменений сессии и закрывает storage. Остановленный клиент можно подключить снова: `connect()` сбросит состояние shutdown.

### `restore_user_agent_from_session`

По умолчанию `True`. При найденной сессии и отсутствии явно заданного user-agent config восстанавливается сохранённый fingerprint. При `False` остаётся новая конфигурация. Смена fingerprint влияет на то, как MAX распознаёт сессию.

## Сессии и синхронизация

`work_dir` и `session_name` задают расположение стандартного `AioSqLiteSessionStorage`, а `session_id` идентифицирует аккаунт. `SessionInfo` хранит токен, телефон, устройство, user agent и sync-маркеры.

`sync=SyncOverrides(...)` выборочно переопределяет восстановленные `chats_sync`, `contacts_sync`, `drafts_sync`, `presence_sync`, `chats_count` и `config_hash`. `None` означает использование сохранённого значения.

Для другой БД реализуйте `BaseSessionStorage`: `save_session`, `load_session`, `update_session`, `delete_session`, `close`; передайте экземпляр через `session_storage`.

## Взаимодействие при авторизации

`auth_interactor` принимает `AuthInteractor`. По умолчанию `TerminalAuthInteractor` показывает QR и запрашивает SMS/2FA. Для простой настройки передайте `AuthCallbacks` в `MaxApi`; callbacks нельзя совмещать с пользовательским interactor.
