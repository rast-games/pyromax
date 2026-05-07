from typing import Any

from .base import Filter
from ..models import EmojiReaction


class EmojiReactionAddFilter(Filter):
    """Match emoji reaction add events."""

    @property
    def work_with(self) -> tuple[type[EmojiReaction]]:
        return (EmojiReaction,)

    async def _check(self, emoji_reaction: EmojiReaction) -> bool | dict[str, Any]:
        return emoji_reaction.status == 'ADD'


class EmojiReactionRemoveFilter(Filter):
    """Match emoji reaction remove events."""

    @property
    def work_with(self) -> tuple[type[EmojiReaction]]:
        return (EmojiReaction,)

    async def _check(self, emoji_reaction: EmojiReaction) -> bool | dict[str, Any]:
        return emoji_reaction.status == 'REMOVE'