from datetime import datetime

from .base import BaseMaxObject


class Message(BaseMaxObject):

    message_id: str
    chat_id: int
    time: int
    type: str | None
    status: str | None
    text: str | None
    cid: int | None
    attaches: list | None = None