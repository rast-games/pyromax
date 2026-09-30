# Quick start

## Requirements and installation

Pyromax 0.8.5 requires Python 3.11 or newer.

```bash
python -m pip install pyromax
```

With `uv`:

```bash
uv add pyromax
```

## Create an application

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

`await MaxApi(...)` is intentional: the client uses an asynchronous constructor to create the selected transport, protocol, and mapper and then runs authentication. `start_polling()` consumes mapped updates until it is cancelled.

## Use an existing token

```python
from pyromax.models import DeviceType

api = await MaxApi(token="YOUR_TOKEN", device_type=DeviceType.Web)
```

Do not commit tokens. Load them from an environment variable or a secret store. A token is tied to the authentication/backend scenario in which it was issued.

## Split handlers into routers

```python
from pyromax import Dispatcher, Router
from pyromax.models import Message

dispatcher = Dispatcher()
messages = Router(name="messages")


@messages.message()
async def handle_message(message: Message) -> None:
    await message.answer("Received")


dispatcher.include_router(messages)
```

One router can only have one parent. Self-references and circular router graphs are rejected.

## Next steps

- Choose an [authentication flow](authentication.md).
- Configure [device profiles and persistent sessions](guide/configuration.md).
- Learn how [routing and typed injection](guide/routing.md) work.
- Add [filters](guide/filters.md), [middleware](guide/middlewares.md), or [FSM](guide/fsm.md).
