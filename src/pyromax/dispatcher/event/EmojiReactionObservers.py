from .StandardMaxEventObserver import StandardMaxEventObserver
from ...models.EmojiReaction import EmojiReaction


class EmojiReactionAddObserver(StandardMaxEventObserver[EmojiReaction]):
    async def is_my_update(
            self,
            update: EmojiReaction
    ) -> bool:
        return await super().is_my_update(update) and update.counters


class EmojiReactionRemoveObserver(StandardMaxEventObserver[EmojiReaction]):
    async def is_my_update(
            self,
            update: EmojiReaction
    ) -> bool:
        return await super().is_my_update(update) and not (update.counters or update.your_reaction or update.total_count)