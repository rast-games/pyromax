from .base import BaseMaxObject

from typing_extensions import TypedDict, Literal


class Counters(TypedDict):
    count: int
    reaction: str


class EmojiReaction(BaseMaxObject):
    chat_id: int
    message_id: str
    counters: list[Counters] | None
    total_count: int | None
    your_reaction: str | None
    status: Literal['ADD', 'REMOVE'] = 'ADD'
