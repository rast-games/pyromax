# Pyromax 0.8.5

Pyromax is an asynchronous Python 3.11+ framework for building userbots for MAX Messenger. Version 0.8.5 combines a high-level client API with aiogram-inspired routing, filters, middleware, dependency injection, and a finite-state machine.

## What is included

- `MaxApi`: authentication, transport/protocol setup, messaging, chats, contacts, files, polls, profile, sessions, and 2FA.
- `Dispatcher` and nested `Router` objects for modular event handling.
- Typed handler injection from update data, filters, middleware, and `workflow_data`.
- Built-in and custom filters, including command and magic filters.
- FSM with memory, Redis, and MongoDB storage backends.
- Bound `Message`, `Chat`, and `Contact` models with convenience methods.
- Swappable transport, protocol, and mapper layers.
- Web, desktop, and Android device profiles with matching transport and encoding presets.
- Persistent SQLite sessions, interactive authentication adapters, domain events, and graceful shutdown.

!!! warning "Unofficial client"
    Pyromax operates a user account rather than a Bot API account. Treat tokens as passwords, account for MAX rate limits, and test automation on a non-critical account.

## Minimal example

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

[Start with the installation and first handler](quickstart.md){ .md-button .md-button--primary }
[Understand the architecture](guide/architecture.md){ .md-button }

For migration details, see the [0.8.5 changelog](changelog.md).

## Documentation baseline

These pages describe **Pyromax 0.8.5**. The version selector is backed by `mike`; the published 0.8 documentation remains available as a separate snapshot.
