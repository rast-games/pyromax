# Quick Start

## Установка

```bash
pip install pyromax
```

## Минимальный пример

```python
import asyncio
import logging

from pyromax.api import MaxApi
from pyromax.api.observer import Dispatcher as MaxDispatcher
from pyromax.types import Message

dp = MaxDispatcher()

@dp.message(pattern=lambda update: True, from_me=True)
async def echo_handler(update: Message, max_api: MaxApi):
    await update.reply(text=update.text, attaches=update.attaches)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = await MaxApi()
    await bot.reload_if_connection_broke(dp)

if __name__ == "__main__":
    asyncio.run(main())
```

## Что дальше
После этого открой страницу Routers.