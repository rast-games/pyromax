from .base import BaseMaxObject


class CommentsInfo(BaseMaxObject):
    """Comment counters for a channel post."""

    total_count: int = 0


class CommentsInfoUpdate(BaseMaxObject):
    """Comment counters associated with a channel post."""

    post_id: int
    comments_info: CommentsInfo | None
