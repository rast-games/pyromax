from pydantic import ConfigDict

from .base import BaseMaxObject
from .Chat import Chat
from .Message import Message
from .Presence import Presence
from ..exceptions import UnsupportedClientVersionMapperError


class DisconnectEvent(BaseMaxObject):
    """The client connection was lost."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    exception: Exception
    reconnect: bool
    delay: float


class UnsupportedClientVersionEvent(BaseMaxObject):
    """MAX rejected the application version reported by the client."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    exception: UnsupportedClientVersionMapperError
    app_version: str | None
    available_versions: tuple[str, ...]


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
