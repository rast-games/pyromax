from .base import BaseMaxObject
from .Message import Message, MessageLink
from .EmojiReaction import EmojiReaction
from .Files import *


__all__ = [
    'BaseMaxObject',
    'Message',
    'MessageLink',
    'EmojiReaction',
    'BaseFileAttachment',
    'PhotoAttachment',
    'VideoAttachment',
    'FileAttachment',
]