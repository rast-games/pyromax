# Backend-слои и расширение

Соединение с MAX разделено на четыре заменяемых слоя. Пятый, high-level methods, предоставляет доменные операции `MaxApi`.

## Встроенные реализации

### Transport

`WebSocketTransport` переносит Web-трафик и настраивает URL, proxy, origin, user-agent header и максимальный frame. `SocketTransport` переносит Desktop/Android-трафик через соединение с необязательными TLS и proxy. Transport переносит закодированные значения и не интерпретирует Envelope.

### Encoding

`JsonEncoding` преобразует dict в JSON для WebSocket. `MsgPackDictEncoding` преобразует dict во framed MessagePack bytes для socket и обрабатывает поддерживаемое сжатие. `NoEncoding` пропускает значения без изменения. `SocketEncoding` дополнительно сообщает размер header и длину payload, сохраняя transport независимым от framing.

### Protocol

`EnvelopeProtocol` сопоставляет requests/responses, применяет encoding, запускает reader, предоставляет `send()` и `get_updates()`, отменяет pending requests при закрытии.

### Mapper

`EnvelopeMapperV11` переводит доменные операции в Envelope V11 payloads, а ответы — в модели. Его mixins покрывают сообщения и polls, чаты и members, contacts и sessions, профиль/folders/presence, файлы и авторизацию. Mapper владеет состоянием авторизации и keepalive, reconnect lifecycle, caches/binding, переводом updates и telemetry.

## Контракты расширения

Пользовательские реализации наследуются от `BaseTransport`, `BaseEncoding`, `BaseMaxProtocol` или `BaseMapper`. Конструкторы получают полный `ExtraConfig`. Асинхронные слои используют соглашение проекта об async initialization.

Декораторы связывают имя и класс:

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

Аналогичные декораторы: `register_transport`, `register_protocol`, `register_mapper`.

!!! warning "Интеграция registry в 0.8.5"
    Одной регистрации недостаточно для выбора backend через `MaxApi`. Текущий resolver сопоставляет известные config-классы со встроенными enum registry. Полный пользовательский стек должен добавить config models и расширить `from_config_to_registry()`, `from_registry_to_config()` и при необходимости `CONFIG_SETS`. Пока это version-coupled extension points, а не стабильный plugin API.

## Пользовательский mapper

Mapper реализует lifecycle (`start`, `stop`, readiness и auth-flow hooks), updates/translation, файлы, обязательные доменные операции и `call_method`. Если wire protocol остаётся Envelope V11, проще расширить готовый mapper:

```python
from pyromax.mapping.envelope.v11.Mapper import Mapper
from pyromax.mapping.registry import register_mapper


@register_mapper("AcmeEnvelopeV11")
class AcmeEnvelopeMapper(Mapper):
    async def custom_operation(self, value: str) -> None:
        ...
```

Не рекомендуется наследоваться от отдельного mixin: `Mapper` собирает их и общее lifecycle-состояние. Для создания через `MaxApi` также потребуются mapper config и mapping в resolver.

## Совместимость

- Типы transport должны совпадать с input/output encoding.
- Socket transport требует framing от `SocketEncoding`.
- Request/response protocol должны соответствовать mapper.
- Устройства mapper должны соответствовать user-agent model и method registry.
- Shutdown обязан отменять reader/keepalive и завершать pending requests.

До стабилизации extension API фиксируйте версию Pyromax для пользовательских backend.
