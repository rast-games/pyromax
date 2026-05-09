# Quick Start

## Installation

```bash
pip install pyromax
```

## Minimal example

```python
import asyncio
import logging

from pyromax import MaxApi
from pyromax.dispatcher import Dispatcher as MaxDispatcher
from pyromax.models import Message



@dp.message(from_me=True)
async def echo_handler(update: Message, max_api: MaxApi):
    await update.reply(text=update.text, attaches=update.attaches)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = await MaxApi(
        device_type='WEB',
        transport='websocket'
    )
    dp = MaxDispatcher()
    await dp.start_polling(
        max_api=bot
    )

if __name__ == "__main__":
    asyncio.run(main())
```

[Install and run](/rast-games/Pyromax/quickstart) 

[More about routers](/rast-games/Pyromax/routers)