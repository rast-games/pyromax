<p align="center">
  <img src="./docs/pyromax_logo.png" alt="Лого Pyromax" width="400" />
</p>

> **Современный асинхронный Python-фреймворк для создания юзерботов в MAX Messenger.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![PyPI](https://img.shields.io/pypi/v/pyromax)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Beta-blue)

Pyromax — современный фреймворк, вдохновлённый **aiogram 3.x**, который переносит привычную архитектуру Telegram-ботов в экосистему **MAX Messenger**.

Библиотека предоставляет всё необходимое для разработки масштабируемых проектов: **Router**, **Dispatcher**, **Middlewares**, **FSM**, **Magic Filters**, строгую типизацию и полностью асинхронное ядро.

---

# ✨ Основные возможности

### 📦 Router

Разделяйте проект на независимые модули.

### ⚡ Async First

Полностью асинхронное ядро на `asyncio`, `aiohttp` и `websockets`.

### 🛡 Middlewares

Перехватывайте события до и после обработки.

Подходит для:

* логирования;
* антифлуда;
* проверки прав;
* работы с БД;
* Dependency Injection;
* аналитики.

---

### 🎭 FSM (Finite State Machine)

Создавайте сложные сценарии общения:

* анкеты;
* формы;
* мастера настройки;
* регистрации;
* диалоги;
* опросы.

---

### ✨ Magic Filters

Фильтрация сообщений похожа на aiogram.

```python
@router.message(F.text.startswith("!"))
```

---

[//]: # (### 🔍 Строгая типизация)

[//]: # ()
[//]: # (Полностью типизированные объекты:)

[//]: # ()
[//]: # (* Message)

[//]: # (* Update)

[//]: # (* User)

[//]: # (* Chat)

[//]: # (* Attachments)

[//]: # (* Callback)

[//]: # ()
[//]: # (---)

### 🧩 Масштабируемая архитектура

Pyromax подходит как для небольших скриптов, так и для крупных проектов.

Используйте:

* Routers
* Nested Routers
* Middlewares
* FSM
* Custom Filters
* Dependency Injection

без необходимости переписывать архитектуру.

---

# 📦 Установка

```bash
pip install pyromax
```

или

```bash
uv add pyromax
```

---

# 🚀 Быстрый старт


```python

import asyncio


from pyromax import MaxApi, Dispatcher
from pyromax.models import Message

# Инициализация диспетчера
dp = Dispatcher()


# Регистрация хендлера (обрабатываем все сообщения, включая свои)
@dp.message(from_me=True)
async def echo(message: Message):
    await message.reply(message.text)


async def main():
    # Создаем экземпляр API
    max_api = await MaxApi()
    # Запускаем бота с диспетчером
    await dp.start_polling(max_api=max_api)



if __name__ == "__main__":
    asyncio.run(main())

```

---

# 🧩 Router

Разделяйте проект по файлам.

```python
router = Router()


@router.message(Command("ping"))
async def ping(message: Message):
    await message.reply("🏓 Pong")
```

```python
dp.include_router(router)
```

---

# 🛡 Middlewares

Используйте middleware для обработки каждого события.

Здесь ключами в data выступают объекты, которыми вы аннотируете хэндлер(по ним библиотека и понимает что нужно передать 
в соответствующий хэндлер). В самом простом случае ключ это класс, а значение ключа это объект этого класса

```python
from pyromax import Dispatcher
from pyromax.dispatcher.middlewares.base import BaseMiddleware
from pyromax.dispatcher.event import MaxObject


dp = Dispatcher()

class MyDB:
    """Your DB, now its just dummy for demonstrate"""

class MyUpdateOuterMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[MaxObject, dict[Any, Any]], Awaitable[Any]],
            event: MaxObject,
            data: dict[type[Any] | str, Any],
    ) -> Any:
        data[MyDB] = MyDB()
        return await handler(event, data)
    
    
dp.update.outer_middleware(
    MyUpdateOuterMiddleware()
)

@dp.message()
async def need_to_get_db_instance(my_db: MyDB):
    pass
```

Также в data ключами могут быть не только классы, которыми вы аннотируете параметры в хэндлерах, но и также forward ref,
и обращаться в хэндлерах надо через них соответственно

```python

class MyUpdateOuterMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[MaxObject, dict[Any, Any]], Awaitable[Any]],
            event: MaxObject,
            data: dict[type[Any] | str, Any],
    ) -> Any:
        data['DataBase'] = MyDB()
        return await handler(event, data)

@dp.message()
async def need_to_get_db_instance(my_db: 'DataBase'):
    pass
```

---

# 🎭 FSM

```python
from pyromax.fsm.state import State, StatesGroup
from pyromax.fsm.context import FSMContext
from pyromax import Dispatcher, MaxApi
from pyromax.filters.command import Command
from pyromax.models import Message

class SimpleSurvey(StatesGroup):
    name = State()
    weather = State()
    whats_up = State()

dp = Dispatcher()


@dp.message(Command('survey'))
async def start_survey(msg: Message, state: FSMContext):
    await msg.reply(
        text='Привет, как тебя зовут?'
    )
    
    await state.set_state(
        SimpleSurvey.name
    )

@dp.message(SimpleSurvey.name)
async def handle_name(msg: Message, state: FSMContext):
    if not msg.text:
        await msg.reply(
            text='Напиши свое имя текстом!'
        )
        return
    await state.update_data(
        user_name=msg.text
    )
    await state.set_state(
        SimpleSurvey.weather
    )
    await msg.answer(
        text='Какая у тебя погода?'
    )

@dp.message(SimpleSurvey.weather)
async def handle_weather(msg: Message, st: FSMContext):
    if not msg.text:
        await msg.reply(
            text='Напиши свою погоду текстом!'
        )
        return
    await st.update_data(
        weather=msg.text
    )
    await st.set_state(
        SimpleSurvey.whats_up
    )
    
    await msg.reply(
        text="Как дела?"
    )

@dp.message(SimpleSurvey.whats_up)
async def handle_whats_up(msg: Message, state: FSMContext):
    if not msg.text:
        await msg.reply(
            text='Напиши свои дела текстом!'
        )
        return 
    await state.update_data(
        whats_up=msg.text
    )
    data = await state.get_data()

    await state.clear()

    await msg.answer(
        text=f"Тебя зовут {data.get('user_name')}, погода у тебя {data.get('weather')}, а дела у тебя {data.get('whats_up')}"
    )
```





---

# ✨ Magic Filters

```python
@router.message(
    F.text.startswith("/"),
    from_me=True
)
async def handler(message: Message):
    ...
```

---

# 💬 Форматирование сообщений

Поддерживается разметка MAX.

```python
@dp.message(Command('lyric'), from_me=True)
async def lyric(msg: Message):
    await msg.answer(text='<STRONG>They tell me, "keep it simple"</STRONG>'
                             '<QUOTE>I tell them, "take it slow"</QUOTE>'
                             '<STRIKETHROUGH>I feed a water an idea so I let it grow </STRIKETHROUGH> \n'
                             '<UNDERLINE>I tell them, "take it easy"</UNDERLINE> \n'
                             '<EMPHASIZED>They laugh and tell me, "No"</EMPHASIZED> \n'
                             '<LINK url="https://www.youtube.com/watch?v=9Zj0JOHJR-s">its cool...</LINK>'
                     )
```
---

### [Полная документация](https://docs.pyromax.org/)


# 📚 Roadmap

## Уже реализовано

* ✅ Async Core
* ✅ Dispatcher
* ✅ Router
* ✅ Nested Routers
* ✅ Observer Pattern
* ✅ Magic Filters
* ✅ Middlewares
* ✅ FSM
* ✅ telemetry
* ✅ Типизация
* ✅ Formatting API
* ✅ Redis Storage
* ✅ Memory Storage
* ✅ Memory Storage
* ✅ покрытие MAX API
* ✅ Документация

[//]: # (## В разработке)

[//]: # ()
[//]: # (* 🚧 )

[//]: # (* 🚧 )

[//]: # (* 🚧 )

---

# 🤝 Contributing

Pull Requests приветствуются.

Если хотите предложить новую возможность — создайте Issue или откройте Pull Request.

---

## 📞 Контакты
Telegram разработчика: [ТЫК](https://t.me/PyroDeveloper)


## Ссылки
- [Телеграм канал](https://t.me/PyromaxLib)
- [Github](https://github.com/rast-games/pyromax)
- [PyPi](https://pypi.org/project/pyromax/)


# 📄 License

MIT License.
