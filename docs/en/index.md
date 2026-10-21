# Pyromax 0.9

Pyromax is an asynchronous Python 3.11+ framework for building userbots for MAX Messenger. Version 0.9 adds channel comments, scheduled messages, managed client-version fingerprints, lifecycle events, raw-response middleware, and resilient mapper circuits.

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
- Channel comment reading, publishing, reactions, subscriptions, and moderation.
- Runtime app-version switching, disconnect/version events, and configurable circuit breakers.

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
    api = await MaxApi(dispatcher=dp)
    await dp.start_polling(api)


if __name__ == "__main__":
    asyncio.run(main())
```

[Start with the installation and first handler](quickstart.md){ .md-button .md-button--primary }
[Understand the architecture](guide/architecture.md){ .md-button }

For migration details, see the [0.9 changelog](changelog.md).

## Documentation baseline

These pages describe **Pyromax 0.9**. The version selector is backed by `mike`; published 0.8 and 0.8.5 snapshots remain separate.
