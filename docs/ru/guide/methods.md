# Методы и вызовы маппера

Одна операция доступна на нескольких уровнях. В приложении обычно выбирайте bound-модель или `MaxApi`; прямые вызовы mapper/protocol предназначены для расширений и отладки.

```text
Bound model → mixin MaxApi → BaseMaxApiMethod → метод Mapper
    → immutable Envelope method → Protocol → Encoding → Transport
```

## `MaxApi.__call__()`

`MaxApi.__call__()` принимает класс `BaseMaxApiMethod`, привязывает его к клиенту и передаёт аргументы:

```python
from pyromax.methods import SendMessageMethod

message = await api(
    SendMessageMethod,
    chat_id=123456,
    text="Привет",
)
```

Это полезно сервисам, которые получают класс метода динамически. Для фиксированной операции понятнее `await api.send_message(...)`. Callable-путь также нормализует mapper transport/API errors в `BaseMaxApiMethodError`.

## Пользовательский high-level метод

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

Такой класс объединяет существующие операции, но не регистрирует новый wire opcode. Для новой операции MAX нужны перевод в маппере и immutable protocol method.

## Прямой вызов маппера

```python
message = await api.mapper.send_message(chat_id=123456, text="Привет")
```

`EnvelopeMapperV11` объединяет mixins сообщений, чатов, контактов, профиля, файлов и авторизации. Он также управляет авторизацией, reconnect/keepalive, caches, привязкой моделей, переводом updates и telemetry.

Прямые вызовы полезны при создании нового метода `MaxApi` и тестировании mapping layer, но связывают код с конкретным mapper и могут обходить нормализацию ошибок клиента. Не импортируйте приватный mixin только ради вызова; наследуйтесь от собранного `Mapper`, только если поддерживаете собственный backend.

`mapper.call_method(MethodClass, ...)` ищет известный high-level метод в registry конкретного устройства. Он выбросит исключение, если mapper или выбранное устройство его не поддерживает. Большинство публичных method-классов уже вызывает соответствующий mapper method напрямую.

## Raw Envelope

`EnvelopeMapperV11.send()` и `send_raw()` принимают immutable Envelope methods. Это низший уровень mapper API: нужно понимать opcode, payload/response, retries, авторизацию и ошибки mapping. Модули `mapping.envelope.v11.methods.immutable` и payloads считаются внутренними и привязаны к версии.
