from .base import BaseMaxObject
from .Message import Message, MessageLink
from .EmojiReaction import EmojiReaction
from .Files import *
from .Contact import Contact
from .UserAgent import BaseUserAgent

__all__ = [
    'BaseMaxObject',
    'Message',
    'MessageLink',
    'EmojiReaction',
    'BaseFileAttachment',
    'PhotoAttachment',
    'VideoAttachment',
    'FileAttachment',
    'ShareAttachment',
    'Contact',
    'BaseUserAgent',
]