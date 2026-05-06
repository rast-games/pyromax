# Routers

## Зачем нужны роутеры

Роутеры помогают разбить бота на отдельные файлы и модули. Это удобно, когда проект начинает расти.

## Пример

```python
from pyromax.api.observer import Router

router = Router()

@router.message(from_me=True)
async def ping_handler(message):
    await message.reply("Pong!")
```

## Подключение

```python
dp.include_router(router)
```