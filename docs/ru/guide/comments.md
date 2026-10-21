# Комментарии каналов

В 0.9 комментарии под постом канала представлены обычной bound-моделью `Message`. Для каждой операции нужны `chat_id` канала и `post_id` родительского поста; для конкретного комментария дополнительно используется `message_id`.

## Отправка и ответ

```python
comment = await api.send_comment(
    chat_id=123456,
    post_id=789,
    text="Первый комментарий",
)

reply = await api.send_comment(
    chat_id=123456,
    post_id=789,
    text="Ответ",
    reply_to=comment.id if comment else None,
)
```

`attachments` принимает обычные модели вложений, а `notify` управляет уведомлениями MAX.

## Чтение комментариев

Если ID известны, используйте `get_comment()` или `get_comments()`. `fetch_comments()` загружает окно относительно `from_`:

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

При `get_messages=False` возвращаются ID вместо моделей. При `get_chat=True` результат содержит также bound-объект `Chat | None`.

## Изменение, удаление и реакции

```python
edited = await api.edit_comment(
    chat_id=123456,
    post_id=789,
    message_id=1011,
    text="Исправлено",
)

await api.add_comment_reaction(123456, 789, 1011, "👍")
await api.remove_comment_reaction(123456, 789, 1011)
await api.delete_comment(123456, 789, [1011], for_me=False)
```

## Подписки и счётчики

`subscribe_comments(chat_id, post_id, subscribe=True)` подписывает текущий аккаунт на активность комментариев. `get_comments_info(chat_id, post_ids)` возвращает `CommentsInfoUpdate` с ID поста и его счётчиками.

## Модерация канала

```python
# Bound helper; эквивалент api.set_channel_comments(channel.id, True).
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

Для moderation operations нужны соответствующие права канала. Ошибки permissions и валидации сервера проходят через стандартный mapper/API error path.

## Классы методов

У операций есть классы `BaseMaxApiMethod`, например `SendCommentMethod`, `FetchCommentsMethod`, `SetChannelCommentsMethod`; generic-код может вызвать их через `await api(MethodClass, ...)`.
