from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyromax.api import MaxApi


class ReplyMixin:
    chat_id: int

    async def answer(self, text="", attaches=[]):
        await self.max_api.send_message(chat_id=self.chat_id, text=text, attaches=attaches)


    async def reply(self, text="", attaches=[]):
        await self.max_api.send_message(chat_id=self.chat_id, text=text, attaches=attaches, other_message_elements={
            'link': {
                'type': 'REPLY',
                'messageId': self.id,
            },
        })