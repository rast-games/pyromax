from .StandardMaxEventObserver import StandardMaxEventObserver
from ...filters import EmojiReactionAddFilter, EmojiReactionRemoveFilter
from ...models.EmojiReaction import EmojiReaction


class EmojiReactionAddObserver(StandardMaxEventObserver[EmojiReaction]):
    async def is_my_update(
            self,
            update: EmojiReaction
    ) -> bool:
        emoji_filter = EmojiReactionAddFilter()
        return bool(await super().is_my_update(update) and await emoji_filter(update=update, data={EmojiReaction: update}))


class EmojiReactionRemoveObserver(StandardMaxEventObserver[EmojiReaction]):
    async def is_my_update(
            self,
            update: EmojiReaction
    ) -> bool:
        emoji_filter = EmojiReactionRemoveFilter()
        return bool(await super().is_my_update(update) and await emoji_filter(update=update, data={EmojiReaction: update}))