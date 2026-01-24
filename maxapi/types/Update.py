from .Message import Message
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..api.MaxApi import MaxApi


class Update(Message):
    def __init__(self, update: dict, max_api: 'MaxApi'):
        if not update:
            return
        super().__init__(update['message'])
        self.max_api = max_api
        self.chat_id = update['chatId']
        self.mark = update['mark']
        self.unread = update['unread']


    async def answer(self, text="", attaches=[]):
        await self.max_api.send_message(chat_id=self.chat_id, text=text, attaches=attaches)


    async def reply(self, text="", attaches=[]):
        await self.max_api.send_message(chat_id=self.chat_id, text=text, attaches=attaches, other_message_elements={
            'link': {
                'type': 'REPLY',
                'messageId': self.id,
            },
        })