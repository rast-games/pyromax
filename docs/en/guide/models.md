# Models and convenience methods

Mapper output is represented by Pydantic models. Most domain objects inherit `BaseMaxObject`; selected models are bound to the `MaxApi` that created them.
If you attempt to call a method on a model that is not bound to MaxApi, a RuntimeError exception will be raised.

## Message

`Message` exposes helpers that already know its chat and message IDs:

```python
@dispatcher.message()
async def handle(message: Message) -> None:
    await message.reply("Reply")
    await message.react("👍")
    await message.read()
```

Other helpers include `answer`, `forward`, `pin`, `edit`, `delete`, `unreact`, and `get_reactions`.

`answer()` and `reply()` accept `send_at` for scheduled delivery: a `datetime`, relative `timedelta`, or Unix timestamp in seconds.

## Chat

`Chat` can `answer`, fetch `history`, retrieve messages, invite/remove users, update settings, enable channel comments, revoke its invite link, leave, or delete itself. `is_dialog()`, `is_group()`, and `is_channel()` help branch on chat type.

## Contact

`Contact` can add/remove itself from contacts and resolve a direct chat ID.

[//]: # (Models that require API access raise `RuntimeError` when used without a bound client.)

## Attachments and other models

The public model package exports file/photo/video/voice attachments, reactions, read state, profile and privacy objects, members, folders, sessions, polls, registration data, and relevant enums.

Use model helper methods when you already have a bound object; use `MaxApi` when operating by raw IDs or implementing a service layer.
