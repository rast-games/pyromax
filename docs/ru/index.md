# Pyromax 0.8.5

Pyromax — асинхронный фреймворк для Python 3.11+, предназначенный для создания юзерботов MAX Messenger. Версия 0.8.5 объединяет высокоуровневый клиент, роутинг в стиле aiogram, фильтры, middleware, внедрение зависимостей и машину состояний.

## Возможности

- `MaxApi`: авторизация, настройка транспорта и протокола, сообщения, чаты, контакты, файлы, опросы, профиль, сессии и 2FA.
- `Dispatcher` и вложенные `Router` для модульной обработки событий.
- Внедрение типизированных параметров из события, фильтров, middleware, FSM и `workflow_data`.
- Встроенные и пользовательские фильтры, включая команды и magic filters.
- FSM с хранилищами в памяти, Redis и MongoDB.
- Привязанные к клиенту модели `Message`, `Chat` и `Contact` с удобными методами.
- Заменяемые слои транспорта, протокола и маппера.
- Профили Web, Desktop и Android с совместимыми транспортом и кодированием.
- Постоянные SQLite-сессии, адаптеры интерактивной авторизации, доменные события и корректное завершение работы.

!!! warning "Неофициальный клиент"
    Pyromax управляет пользовательским аккаунтом, а не аккаунтом Bot API. Храните токены как пароли, учитывайте ограничения MAX и тестируйте автоматизацию на некритичном аккаунте.

## Минимальный пример

```python
import asyncio

from pyromax import Dispatcher, MaxApi
from pyromax.models import Message

dp = Dispatcher()


@dp.message(from_me=True)
async def echo(message: Message) -> None:
    await message.reply(message.text or "")


async def main() -> None:
    api = await MaxApi()
    await dp.start_polling(api)


if __name__ == "__main__":
    asyncio.run(main())
```

[Установка и первый обработчик](quickstart.md){ .md-button .md-button--primary }
[Архитектура проекта](guide/architecture.md){ .md-button }

Изменения при обновлении перечислены в [changelog 0.8.5](changelog.md).

## Версия документации

Эти страницы описывают **Pyromax 0.8.5**. Переключатель версий работает через `mike`; опубликованная документация 0.8 сохраняется отдельным снимком.
