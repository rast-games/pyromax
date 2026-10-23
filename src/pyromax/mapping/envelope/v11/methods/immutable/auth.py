from .base import BaseMethod, Envelope, Opcode, Cmd
from ...payloads.models import (
    TrackLoginMappingModel,
    AuthMappingModel,
    BaseUserAgentMappingModel,
)
from ...payloads.requests import (
    KeepAliveRequest,
    Resolve2FARequest,
    StartPhoneAuthRequest,
    VerifySMSCodeRequest,
    ConfirmRegistrationRequest,
    GetEmailCodeRequest,
    SetHintRequest,
    SetPasswordRequest,
    VerifyEmailRequest,
    GetTrackIdFor2FARequest,
    SetTwoFactorRequest,
    ApproveQrLoginRequest,
    RemoveTwoFactorRequest,
    TelemetryRequest,
)

# from .base import VERSION


class TrackLoginMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the track login protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.TRACK_LOGIN
        request.cmd = Cmd.REQUEST
        request.payload = TrackLoginMappingModel(
            track_id=self.args["track_id"],
        ).model_dump(by_alias=True, exclude_none=True)
        request.ver = self.VERSION

        return request


class GetUserDataMethod(TrackLoginMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get user data protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request = await super().__call__(request)
        request.opcode = Opcode.GET_USER_DATA
        request.ver = self.VERSION
        return request


class Resolve2FAMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the resolve2 f a protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.RESOLVE_2FA
        request.cmd = Cmd.REQUEST
        request.payload = Resolve2FARequest(
            track_id=self.args["track_id"],
            password=self.args["password"],
        ).model_dump(by_alias=True, exclude_none=True)
        request.ver = self.VERSION
        return request


class StartSMSAuthMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the start s m s auth protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.START_SMS_AUTH
        request.cmd = Cmd.REQUEST
        request.payload = StartPhoneAuthRequest(
            type=self.args["type"],
            phone=self.args["phone"],
            mode=self.args.get("mode"),
        ).model_dump(by_alias=True, exclude_none=True)
        request.ver = self.VERSION
        return request


class VerifySMSCodeMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the verify s m s code protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CHECK_SMS_CODE
        request.cmd = Cmd.REQUEST
        request.payload = VerifySMSCodeRequest(
            auth_token_type=self.args["auth_token_type"],
            token=self.args["temp_token"],
            verify_code=self.args["verify_code"],
        ).model_dump(by_alias=True, exclude_none=True)
        request.ver = self.VERSION
        return request


class GetMetadataForLoginMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get metadata for login protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.METADATA_FOR_LOGIN
        request.cmd = Cmd.REQUEST
        request.payload = None
        request.ver = self.VERSION
        return request


class SendUserAgentMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the send user agent protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SEND_USER_AGENT
        request.cmd = Cmd.REQUEST
        user_agent: BaseUserAgentMappingModel = self.args["user_agent"]
        request.payload = user_agent.to_request().model_dump(
            by_alias=True, exclude_none=True
        )
        request.ver = self.VERSION
        return request


class SendAuthTokenMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the send auth token protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.AUTHORIZE
        request.cmd = Cmd.REQUEST
        request.payload = AuthMappingModel(**self.args).model_dump(
            by_alias=True, exclude_none=True
        )
        request.ver = self.VERSION
        return request


class SendKeepAlivePingMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the send keep alive ping protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.PING
        request.cmd = Cmd.REQUEST
        request.payload = KeepAliveRequest(
            interactive=self.args.get("interactive", True),
        ).model_dump(by_alias=True, exclude_none=True)
        request.ver = self.VERSION
        return request


class ConfirmRegistrationMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the confirm registration protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CONFIRM_REGISTRATION
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = ConfirmRegistrationRequest(
            token=self.args["token"],
            first_name=self.args["first_name"],
            last_name=self.args["last_name"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetEmailCodeMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get email code protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SET_EMAIL
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = GetEmailCodeRequest(
            track_id=self.args["track_id"],
            email=self.args["email"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class VerifyEmailMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the verify email protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.VERIFY_EMAIL
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = VerifyEmailRequest(
            track_id=self.args["track_id"],
            verify_code=self.args["verify_code"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class SetHintMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the set hint protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SET_HINT
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = SetHintRequest(
            track_id=self.args["track_id"],
            hint=self.args["hint"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class SetPasswordMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the set password protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SET_PASSWORD
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = SetPasswordRequest(
            track_id=self.args["track_id"],
            password=self.args["password"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetTrackIdFor2FAMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get track id for2 f a protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.GET_TRACKID_FOR2FA
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = GetTrackIdFor2FARequest().model_dump(
            by_alias=True, exclude_none=True
        )
        return request


class SetTwoFactorMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the set two factor protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SET_2_FACTOR
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = SetTwoFactorRequest(
            expected_capabilities=self.args["expected_capabilities"],
            track_id=self.args["track_id"],
            password=self.args["password"],
            hint=self.args.get("hint"),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class CheckPasswordMethod(SetPasswordMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the check password protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request = await super().__call__(request)
        request.opcode = Opcode.AUTH_CHECK_PASSWORD
        return request


class RemoveTwoFactorMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the remove two factor protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SET_2_FACTOR
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = RemoveTwoFactorRequest(
            track_id=self.args["track_id"],
            expected_capabilities=self.args["expected_capabilities"],
            remove2fa=self.args.get("remove2fa") or True,
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class ApproveQrLoginMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the approve qr login protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.AUTH_QR_APPROVE
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = ApproveQrLoginRequest(
            qr_link=self.args["qr_link"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class SendTelemetryMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.LOG
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = TelemetryRequest(
            events=self.args["events"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


__all__ = [
    "TrackLoginMethod",
    "GetUserDataMethod",
    "Resolve2FAMethod",
    "StartSMSAuthMethod",
    "VerifySMSCodeMethod",
    "GetMetadataForLoginMethod",
    "SendUserAgentMethod",
    "SendAuthTokenMethod",
    "SendKeepAlivePingMethod",
    "ConfirmRegistrationMethod",
    "GetEmailCodeMethod",
    "SetHintMethod",
    "SetPasswordMethod",
    "VerifyEmailMethod",
    "GetTrackIdFor2FAMethod",
    "SetTwoFactorMethod",
    "CheckPasswordMethod",
    "RemoveTwoFactorMethod",
    "ApproveQrLoginMethod",
    "SendTelemetryMethod",
]
