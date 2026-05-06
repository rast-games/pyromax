from .base import BaseMethod, Envelope, Opcode, Cmd
from ...payloads.models import (
    TrackLoginMappingModel, AuthMappingModel, BaseUserAgentMappingModel
)
from ...payloads.requests import (
KeepAliveRequest, Resolve2FARequest,
StartPhoneAuthRequest, VerifySMSCodeRequest
)
from .base import VERSION


class TrackLoginMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.TRACK_LOGIN
        request.cmd = Cmd.REQUEST
        request.payload = TrackLoginMappingModel(
            track_id=self.args['track_id'],
        ).model_dump(by_alias=True)
        request.ver = VERSION

        return request


class GetUserDataMethod(TrackLoginMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request = await super().__call__(request)
        request.opcode = Opcode.GET_USER_DATA
        request.ver = VERSION
        return request


class Resolve2FAMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.RESOLVE_2FA
        request.cmd = Cmd.REQUEST
        request.payload = Resolve2FARequest(
            track_id=self.args['track_id'],
            password=self.args['password'],
        )
        request.ver = VERSION
        return request

class StartSMSAuthMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.START_SMS_AUTH
        request.cmd = Cmd.REQUEST
        request.payload = StartPhoneAuthRequest(
            type=self.args['type'],
            phone=self.args['phone'],
        )
        request.ver = VERSION
        return request


class VerifySMSCodeMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.CHECK_SMS_CODE
        request.cmd = Cmd.REQUEST
        request.payload = VerifySMSCodeRequest(
            auth_token_type=self.args['auth_token_type'],
            token=self.args['temp_token'],
            verify_code=self.args['verify_code'],
        )
        request.ver = VERSION
        return request


class GetMetadataForLoginMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.METADATA_FOR_LOGIN
        request.cmd = Cmd.REQUEST
        request.payload = None
        request.ver = VERSION
        return request


class SendUserAgentMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.SEND_USER_AGENT
        request.cmd = Cmd.REQUEST
        user_agent: BaseUserAgentMappingModel = self.args['user_agent']
        request.payload = user_agent.to_request().model_dump(by_alias=True)
        request.ver = VERSION
        return request


class SendAuthTokenMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.AUTHORIZE
        request.cmd = Cmd.REQUEST
        request.payload = AuthMappingModel(**self.args).model_dump(by_alias=True)
        request.ver = VERSION
        return request


class SendKeepAlivePingMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.PING
        request.cmd = Cmd.REQUEST
        request.payload = KeepAliveRequest(
            interactive=self.args.get('interactive', True),
        )
        request.ver = VERSION
        return request
