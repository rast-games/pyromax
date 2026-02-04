from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from pyromax.utils import get_dict_value_by_path, NotFoundFlag
from pyromax.types import Message
from pyromax.types.OpcodeEnum import Opcode


# if TYPE_CHECKING:
#     from pyromax.api import MaxApi


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

    # def __init__(self, json: dict, max_api: 'MaxApi', id: int = None):
    #     json_chat = get_dict_value_by_path('payload chats', json)
    #     self.max_client: 'MaxApi' = max_api
    #     self.id: int = id if id else json_chat['id']
    #     json['payload']['attaches'] = json_chat['lastMessage']['attaches']
    #     self.owner: str = json_chat['owner']
    #     self.participants: dict = json_chat['participants']
    #     self.status: str = json_chat['status']
    #     self.type: str = json_chat['type']
    #     self.restrictions: str = get_dict_value_by_path('restrictions', json_chat)
    #     self.has_bots: str = get_dict_value_by_path('hasBots', json_chat)
    #     self.options: str = get_dict_value_by_path('options', json_chat)
    #     self.last_message: Message = Message(**json_chat['lastMessage'], **json, max_client=max_api, chat_id=self.id)
    #     if self.type == 'CHAT':
    #         self.access: str = json_chat['access']
    #         self.admins: list[str] = json_chat['admins']
    #         self.title: str = json_chat['title']
    #     elif self.type == 'DIALOG':
    #         pass
    #
    #     for item in list(self.__dict__):
    #         if getattr(self, item) == NotFoundFlag:
    #             delattr(self, item)

    @classmethod
    def from_json(cls, json, max_api: 'MaxApi') -> list['Chat']:

        if not isinstance(json, list):
            json = [json]
        chats = []
        for json_chat in json:
            instance = cls(**json_chat, max_api=max_api)
            if 'lastMessage' in json_chat:
                instance.last_message = Message(**json_chat['lastMessage'], max_api=max_api, chat_id=instance.id, opcode=Opcode.SEND_MESSAGE.value)

            chats.append(instance)
        return chats


    def __repr__(self):
        details = []
        for key, value in self.__dict__.items():
            details.append(f"{key}={value}")
        return '\n'.join(details)


    async def get_messages_per_chunk(self, time: int) -> list[Message]:
        response = await self.max_api.max_client.send_and_receive(opcode=49, payload={
            'chatId': self.id,
            'from': time,
            'forward': 0,
            'backward': 30,
            'getMessages': True,

        })

        messages = []

        for message in response['payload']['messages']:
            messages.append(Message(**message))

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