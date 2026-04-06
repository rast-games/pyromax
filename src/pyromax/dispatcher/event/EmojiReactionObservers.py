from .StandardMaxEventObserver import StandardMaxEventObserver
from ...models.EmojiReaction import EmojiReaction


class EmojiReactionAddObserver(StandardMaxEventObserver):
    def is_my_update(
            self,
            update: EmojiReaction
    ) -> bool:
        return super().is_my_update(update) and update.counters


class EmojiReactionRemoveObserver(StandardMaxEventObserver):
    def is_my_update(
            self,
            update: EmojiReaction
    ) -> bool:
        return super().is_my_update(update) and not (update.counters or update.your_reaction or update.total_count)