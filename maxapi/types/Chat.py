from maxapi.utils import try_to_find_in_dict_and_return, NotFoundFlag
from maxapi.types import Message
from maxapi.api import MaxClient


class Chat:
    def __init__(self, json_chat: dict, max_client: MaxClient, id: int = None):
        self.max_client: MaxClient = max_client
        self.id: int = id if id else json_chat['id']
        self.owner: str = json_chat['owner']
        self.participants: dict = json_chat['participants']
        self.status: str = json_chat['status']
        self.type: str = json_chat['type']
        self.restrictions: str = try_to_find_in_dict_and_return('restrictions', json_chat)
        self.has_bots: str = try_to_find_in_dict_and_return('hasBots', json_chat)
        self.options: str = try_to_find_in_dict_and_return('options', json_chat)
        self.last_message: Message = Message(json_chat['lastMessage'])
        if self.type == 'CHAT':
            self.access: str = json_chat['access']
            self.admins: list[str] = json_chat['admins']
            self.title: str = json_chat['title']
        elif self.type == 'DIALOG':
            pass

        for item in list(self.__dict__):
            if getattr(self, item) == NotFoundFlag:
                delattr(self, item)



    def __repr__(self):
        details = []
        for key, value in self.__dict__.items():
            details.append(f"{key}={value}")
        return '\n'.join(details)


    async def get_messages_per_chunk(self, time: int) -> list[Message]:
        response = await self.max_client.send_and_receive(opcode=49, payload={
            'chatId': self.id,
            'from': time,
            'forward': 0,
            'backward': 30,
            'getMessages': True,

        })

        messages = []

        for message in response['payload']['messages']:
            messages.append(Message(message))

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