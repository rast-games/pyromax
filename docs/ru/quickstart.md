# Быстрый старт

## Требования и установка

Для Pyromax 0.8.5 нужен Python 3.11 или новее.

```bash
python -m pip install pyromax
```

Через `uv`:

```bash
uv add pyromax
```

## Создание приложения

```python
import asyncio

from pyromax import Dispatcher, MaxApi
from pyromax.filters import Command
from pyromax.models import DeviceType, Message

dispatcher = Dispatcher()


@dispatcher.message(Command("ping"), from_me=True)
async def ping(message: Message) -> None:
    await message.reply("Pong!")


async def main() -> None:
    api = await MaxApi(device_type=DeviceType.Web)
    await dispatcher.start_polling(max_api=api)


asyncio.run(main())
```

Конструкция `await MaxApi(...)` используется намеренно: асинхронный конструктор создаёт выбранные транспорт, протокол и маппер, после чего выполняет авторизацию. `start_polling()` читает и обрабатывает события до отмены задачи.

## Использование готового токена

```python
from pyromax.models import DeviceType

api = await MaxApi(token="YOUR_TOKEN", device_type=DeviceType.Web)
```

Не сохраняйте токен в Git. Загружайте его из переменной окружения или хранилища секретов. Токен связан со сценарием авторизации и backend, в котором был получен.

## Разделение обработчиков по роутерам

```python
from pyromax import Dispatcher, Router
from pyromax.models import Message

dispatcher = Dispatcher()
messages = Router(name="messages")


@messages.message()
async def handle_message(message: Message) -> None:
    await message.answer("Получено")


dispatcher.include_router(messages)
```

У одного роутера может быть только один родитель. Ссылки на самого себя и циклические графы запрещены.

## Что дальше

- Выберите [способ авторизации](authentication.md).
- Настройте [профиль устройства и постоянные сессии](guide/configuration.md).
- Разберитесь с [роутингом и DI](guide/routing.md).
- Добавьте [фильтры](guide/filters.md), [middleware](guide/middlewares.md) или [FSM](guide/fsm.md).
