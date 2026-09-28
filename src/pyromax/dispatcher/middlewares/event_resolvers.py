from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from collections.abc import Callable

from ...models import (
    Chat,
    EmojiReaction,
    Message,
    MessageDeleteEvent,
    MessageReadEvent,
    PresenceEvent,
    TypingEvent,
)

if TYPE_CHECKING:
    from ..event import MaxObject


@dataclass(frozen=True)
class EventContext:
    chat_id: int | None = None
    user_id: int | None = None


def resolve_message(m: Message) -> EventContext:
    """Resolve message.

    :param m: Message instance to process.
    :type m: Message
    :returns: The resulting EventContext value.
    :rtype: EventContext
    """
    return EventContext(chat_id=m.chat_id, user_id=m.sender_id)


def resolve_emoji_reaction(r: EmojiReaction) -> EventContext:
    """Resolve emoji reaction.

    :param r: EmojiReaction instance to process.
    :type r: EmojiReaction
    :returns: The resulting EventContext value.
    :rtype: EventContext
    """
    return EventContext(chat_id=r.chat_id, user_id=None)


def resolve_domain_event(event: Any) -> EventContext:
    return EventContext(
        chat_id=getattr(event, "chat_id", None),
        user_id=getattr(event, "user_id", None),
    )


def resolve_chat_update(chat: Chat) -> EventContext:
    return EventContext(chat_id=chat.id)


EVENT_STRUCTURE_RESOLVERS: dict[type[MaxObject], Callable[[Any], EventContext]] = {
    Message: resolve_message,
    EmojiReaction: resolve_emoji_reaction,
    MessageReadEvent: resolve_domain_event,
    TypingEvent: resolve_domain_event,
    PresenceEvent: resolve_domain_event,
    MessageDeleteEvent: resolve_domain_event,
    Chat: resolve_chat_update,
}
