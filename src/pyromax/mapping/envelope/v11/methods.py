from typing import cast

from typing_extensions import Literal

from ....models import Message
from ....protocol import Envelope
from .constants import Opcode, Cmd
from .payloads import UserAgentPayload, AuthModel, CreateCellForFileModel, SendMessageModel, \
    MessageModel, MessageLinkModel, TrackLoginPayloadModel

import abc


class BaseMethod(abc.ABC):
    def __init__(self, **kwargs):
        self.args = kwargs


    @abc.abstractmethod
    async def __call__(self, request: Envelope) -> Envelope:
        pass




class TrackLogin(BaseMethod):
    async def __call__(self, request: Envelope):
        request.opcode = Opcode.TRACK_LOGIN
        request.payload = TrackLoginPayloadModel(
            track_id=self.args['track_id'],
        ).model_dump(by_alias=True)

        return request


class GetUserData(TrackLogin):
    async def __call__(self, request: Envelope) -> Envelope:
        request = await super().__call__(request)
        request.opcode = Opcode.GET_USER_DATA
        return request


class GetMetadataForLogin(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.METADATA_FOR_LOGIN
        request.payload = None
        return request


class SendUserAgentMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.SEND_USER_AGENT
        request.cmd = Cmd.REQUEST
        request.payload = UserAgentPayload(**self.args).model_dump(by_alias=True)
        return request


class SendAuthTokenMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.AUTHORIZE
        request.cmd = Cmd.REQUEST
        request.payload = AuthModel(**self.args).model_dump(by_alias=True)
        return request


class SendKeepAlivePingMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.PING
        request.cmd = Cmd.REQUEST
        request.payload = None
        return request


class GetUrlToUploadFileMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = self.args['type_of_file_opcode']
        request.cmd = Cmd.REQUEST
        count = 1
        if 'count' in self.args:
            count = int(self.args['count'])
        request.payload = CreateCellForFileModel(
            count=count,
        )
        return request


class SendMessageMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.SEND_MESSAGE
        request.cmd = Cmd.REQUEST


        def reverse_translate_message(message: Message) -> MessageModel | None:
            if not message:
                return None
            message_link = message.message_link
            if message.status not in ('USER', 'EDITED', 'REPLY'):
                status = 'USER'
            else:
                status = message.status
            if message_link:
                return MessageModel(
                    id=str(message.message_id),
                    status=cast(Literal['USER', 'EDITED', 'REPLY'], status),
                    time = message.time,
                    type = message.type,
                    text = message.text,
                    elements = message.elements,
                    chat_id=message.chat_id,
                    link=MessageLinkModel(
                        type=message_link.type,
                        message=reverse_translate_message(message_link.message),
                    )
                )
            return MessageModel(
                id=str(message.message_id),
                status=cast(Literal['USER', 'EDITED', 'REPLY'], status),
                time=message.time,
                type=message.type,
                text=message.text,
                elements=message.elements,
                chat_id=message.chat_id,
            )


        main_link = self.args.get('link')
        request.payload = SendMessageModel(
            chat_id=self.args['chat_id'],
            message=MessageModel(
                text=self.args['text'],
                cid=self.args['cid'],
                attaches=self.args['attaches'],
                elements=self.args['elements'],
                link=MessageLinkModel(
                    type=main_link.type,
                    message_id=str(main_link.message_id),
                    message=reverse_translate_message(main_link.message),
                ) if main_link else None,
            ),
        ).model_dump(by_alias=True, exclude_none=True)
        return request

