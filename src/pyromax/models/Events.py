from .base import BaseMaxObject
from .Chat import Chat
from .Message import Message
from .Presence import Presence


class MessageReadEvent(BaseMaxObject):
    """A user's read marker changed in a chat."""

    set_as_unread: bool
    chat_id: int
    user_id: int
    mark: int


class TypingEvent(BaseMaxObject):
    """A user is typing in a chat."""

    chat_id: int
    user_id: int


class PresenceEvent(BaseMaxObject):
    """A user's presence changed."""

    presence: Presence
    user_id: int


class MessageDeleteEvent(BaseMaxObject):
    """One or more messages were deleted from a chat."""

    message_ids: list[int | str]
    chat_id: int
    chat: Chat | None = None
    message: Message | None = None
    ttl: bool = False
