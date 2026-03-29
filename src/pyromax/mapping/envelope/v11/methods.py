from src.pyromax.protocol.bases.methods import BaseMaxMethod
from src.pyromax.protocol.envelope import Envelope
from .constants import Opcode, Cmd
from .payloads import UserAgentPayload, UserAgentModel, AuthModel, CreateCellForFileModel

import abc


class BaseMethod(abc.ABC):
    def __init__(self, **kwargs):
        self.args = kwargs

    @abc.abstractmethod
    async def __call__(self, request: Envelope) -> Envelope:
        pass



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
    type_of_file_opcode: int
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = self.type_of_file_opcode
        request.cmd = Cmd.REQUEST
        count = 1
        if 'count' in self.args:
            count = int(self.args['count'])
        request.payload = CreateCellForFileModel(
            count=count,
        )
        return request