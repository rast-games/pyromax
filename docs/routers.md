# Filters

## What are filters?

The filter checks the update before calling the handler.

## Examples

- `FromMeFilter`
- `ReplyToMessageFilter`
- `MessageForwardFromFilter`
- `MessageRemovedFilter`
- `Command`
- `CommandStart`
- `EmojiReactionAddFilter`
- `EmojiReactionRemoveFilter`

## Usage

```python
@router.message(Command("ping"), from_me=True)
async def ping_handler(message):
    await message.reply("Pong!")
```

## Your filters
To create your own filter, inherit from `Filter` and override `__call__`.