from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from pyromax.types import Message
from pyromax.types.OpcodeEnum import Opcode


class Chat(BaseModel):
    max_api: Any
    id: int = None
    owner: int
    participants: dict
    status: str
    type: str
    options: dict | None = None
    restrictions: int | None = None
    has_bots: str | None = None
    access: str | None = None
    last_message: Message | Message = None

    @classmethod
    def from_json(cls, json, max_api: 'MaxApi') -> list['Chat']:

        if not isinstance(json, list):
            json = [json]
        chats = []
        for json_chat in json:
            instance = cls(**json_chat, max_api=max_api)
            if 'lastMessage' in json_chat:
                instance.last_message = Message(**json_chat['lastMessage'], max_api=max_api, chatId=instance.id, opcode=Opcode.SEND_MESSAGE.value)

            chats.append(instance)
        return chats


    def __repr__(self):
        details = []
        for key, value in self.__dict__.items():
            details.append(f"{key}={value}")
        return '\n'.join(details)


    async def get_messages_per_chunk(self, time: int) -> list[Message]:
        response = await self.max_api.max_client.send_and_receive(opcode=Opcode.GET_CHAT_MESSAGES_PER_CHUNK, payload={
            'chatId': self.id,
            'from': time,
            'forward': 0,
            'backward': 30,
            'getMessages': True,

        })

        response = response[0]
        messages = []

        for message in response['payload']['messages']:
            messages.append(Message(**message, max_api=self.max_api, chatId=self.id))

        return messages

    async def get_all_messages(self, time: int) -> list[Message]:


        # pprint(response)
        # while response['opcode'] == 128:
        #     response = await self.max_client.wait_recv()
        #     response = response[0]
        #     print('============')
        #     pprint(response)

        messages = await self.get_messages_per_chunk(time)
        chunk = await self.get_messages_per_chunk(time)
        messages = chunk + messages

        while len(chunk) >= 30:
            chunk = await self.get_messages_per_chunk(chunk[0].time)
            messages = chunk + messages

        return messages