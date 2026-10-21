# Channel comments

In 0.9, comments under a channel post are represented by the regular bound `Message` model. Every comment operation needs the channel `chat_id` and parent `post_id`; individual comments additionally use `message_id`.

## Publish and reply

```python
comment = await api.send_comment(
    chat_id=123456,
    post_id=789,
    text="First comment",
)

reply = await api.send_comment(
    chat_id=123456,
    post_id=789,
    text="Reply",
    reply_to=comment.id if comment else None,
)
```

`attachments` accepts the usual file attachment models and `notify` controls MAX notifications.

## Read comments

Use `get_comment()` or `get_comments()` when IDs are known. `fetch_comments()` loads a window around `from_`:

```python
comments, chat = await api.fetch_comments(
    chat_id=123456,
    post_id=789,
    backward=30,
    forward=0,
    get_messages=True,
    get_chat=True,
)
```

With `get_messages=False`, the method returns comment IDs instead of models. With `get_chat=True`, the result is paired with a bound `Chat | None`.

## Edit, delete, and react

```python
edited = await api.edit_comment(
    chat_id=123456,
    post_id=789,
    message_id=1011,
    text="Updated",
)

await api.add_comment_reaction(123456, 789, 1011, "👍")
await api.remove_comment_reaction(123456, 789, 1011)
await api.delete_comment(123456, 789, [1011], for_me=False)
```

## Subscriptions and counters

`subscribe_comments(chat_id, post_id, subscribe=True)` subscribes the current account to comment activity. `get_comments_info(chat_id, post_ids)` returns `CommentsInfoUpdate` entries containing a post ID and its counters.

## Channel moderation

```python
# Bound helper; equivalent to api.set_channel_comments(chat.id, True).
await channel.set_comments(True)

await api.block_comment_author(
    chat_id=123456,
    post_id=789,
    user_ids=[42],
    message_id=1011,
    clean_msg_period=0,
)

await api.delete_user_comments(
    chat_id=123456,
    post_id=789,
    user_id=42,
    message_id=1011,
)
```

Moderation operations require the corresponding channel permissions. Server-side permission and validation failures are exposed through the normal mapper/API error path.

## Method classes

All operations also have `BaseMaxApiMethod` classes such as `SendCommentMethod`, `FetchCommentsMethod`, and `SetChannelCommentsMethod`, so generic code can invoke them with `await api(MethodClass, ...)`.
