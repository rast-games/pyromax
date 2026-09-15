from __future__ import annotations
import logging
import asyncio
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, TYPE_CHECKING, cast

import qrcode

from .....config import ExtraConfig
from .....protocol.envelope import Envelope, EnvelopeProtocol
from .....models import (
    Profile,
    Chat,
    Contact,
    Message,
    TwoFactorAction,
    RegistrationConfig,
    SyncState,
    SessionInfo,
    DeviceType,
)
from .....config import EnvelopeMapperConfigV11
from ..payloads.models import BaseUserAgentMappingModel, ProfileOptionsMappingModel
from ..methods.immutable import (
    SendUserAgentMethod,
    SendAuthTokenMethod,
    GetMetadataForLoginMethod,
    SendKeepAlivePingMethod,
    Resolve2FAMethod,
    StartSMSAuthMethod,
    VerifySMSCodeMethod,
    TrackLoginMethod,
    ConfirmRegistrationMethod,
    GetEmailCodeMethod,
    VerifyEmailMethod,
    SetHintMethod,
    SetPasswordMethod,
    GetTrackIdFor2FAMethod,
    SetTwoFactorMethod,
    GetUserDataMethod,
    CheckPasswordMethod,
    RemoveTwoFactorMethod,
    ApproveQrLoginMethod,
)
from ..payloads.responses import (
    AuthResponse,
    SuccessLoginResponse,
    MetadataResponse,
    ChoiceLoginVariantResponse,
    TwoFactorLoginResponse,
    UserAgentResponse,
    StartSMSAuthResponse,
    TrackLoginResponse,
    ConfirmRegistrationResponse,
    GetTrackIdFor2FAResponse,
)
from ..translate.ToDTO import translate_models
from ..translate.FromDTO import reverse_translate_two_factor_actions
from .....utils import read_token, write_token, Backoff
from .....exceptions import (
    MapperCancelledError,
    RestartMapperError,
    BaseMapperError,
    MapperTransportError,
    MapperApiError,
    NeedReloginMapperError,
)
from ..constants import DEFAULT_BACKOFF_CONFIG
from ..LifecycleManager import LifecycleManager

if TYPE_CHECKING:
    from .....core import MaxApi

from .MixinProtocol import MixinProtocol


class AuthMixin(MixinProtocol):
    _lifecycle_manager: LifecycleManager | None
    user_agent: BaseUserAgentMappingModel | None

    async def _send_user_agent(
        self,
        user_agent: BaseUserAgentMappingModel,
    ) -> None:
        """Send user agent.

        :param user_agent: BaseUserAgentMappingModel instance to process.
        :type user_agent: BaseUserAgentMappingModel
        """
        response = await self.send_raw(
            method=SendUserAgentMethod(
                user_agent=user_agent,
            )
        )
        calls_seed = UserAgentResponse(**response.payload).calls_seed
        self.calls_seed = calls_seed

    async def _send_auth_token(
        self,
        token: str,
    ) -> None:
        """Send auth token.

        :param token: Authentication token.
        :type token: str
        :param chats_count: The chats count value.
        :type chats_count: int
        :param interactive: The interactive value.
        :type interactive: bool
        :param presence_sync: The presence sync value.
        :type presence_sync: int
        :param chats_sync: The chats sync value.
        :type chats_sync: int
        :param contacts_sync: The contacts sync value.
        :type contacts_sync: int
        :param drafts_sync: The drafts sync value.
        :type drafts_sync: int
        :raises RuntimeError: If you try a send auth token, but not bound MaxApi instance to mapper.
        """
        self._logger.debug("sending auth token")

        if self.max_api.session is None:
            raise RuntimeError("You try send auth token, without session.")
        sync = self.extra_config.sync.resolve(self.max_api.session.sync)

        try:
            response = await self.send_raw(
                method=SendAuthTokenMethod(
                    token=token,
                    chats_count=sync.chats_count,
                    interactive=self.keep_alive_interactive,
                    presence_sync=sync.presence_sync,
                    chats_sync=sync.chats_sync,
                    contacts_sync=sync.contacts_sync,
                    drafts_sync=sync.drafts_sync,
                ),
                check_errors=True,
            )
        except MapperApiError as e:
            error = e.error
            match error:
                case "login.token":
                    self._logger.error("Login error. Please log in again.")
                    self.logged = False
                    if self.max_api.session_storage is not None:
                        self._logger.debug("deleting current session")
                        await self.max_api.session_storage.delete_session(
                            self.max_api.session_key
                        )
                    self.token = None
                    # self.user_agent = None
                    self.max_api.token = None
                    raise NeedReloginMapperError(e.message)
                case "login.cred":
                    self._logger.error("Login error. Please log in again.")
                    self.logged = False
                    if self.max_api.session_storage is not None:
                        self._logger.debug("deleting current session")
                        await self.max_api.session_storage.delete_session(
                            self.max_api.session_key
                        )
                    self.token = None
                    # self.user_agent = None
                    self.max_api.token = None
                    raise NeedReloginMapperError(e.message)

            raise e

        self._logger.debug("recv auth token response")

        auth_model = AuthResponse(**response.payload)
        sync = auth_model.update_sync_state(self.max_api.session.sync)

        updated = self.max_api.session.model_copy(
            update={
                "sync": sync,
            },
        )

        self.max_api.session = updated

        await self.max_api.session_storage.update_session(
            self.max_api.session_key, updated
        )

        if self.max_api is None:
            raise RuntimeError(
                "You try a send auth token, but not bound MaxApi instance to mapper"
            )

        if auth_model.profile:

            self.max_api.id = auth_model.profile.contact.id
            self.max_api.me = cast(Profile, translate_models(auth_model.profile))
            self.max_api.phone = str(auth_model.profile.contact.phone)
        self.max_api.chats = [
            self.bind_api_instance(cast(Chat, translate_models(chat)))
            for chat in auth_model.chats
        ]
        self.max_api.contacts = [
            self.bind_api_instance(cast(Contact, translate_models(contact)))
            for contact in auth_model.contacts
            if contact is not None
        ]
        # self.max_api.messages = {
        #     i: [cast(Message, translate_models(msg)) for msg in msg_list]
        #     for i, msg_list in auth_model.messages.items()
        # }
        if self.max_api.me is not None:
            self.max_api.users[self.max_api.me.contact.id] = self.bind_api_instance(
                self.max_api.me.contact
            )

            self.max_api.names = self.max_api.me.contact.names

    async def request_code(
        self,
        phone: str,
        auth_type: str = "START_AUTH",
        use_mobile_fingerprint: bool = True,
    ) -> StartSMSAuthResponse:
        """Request code.

        :param phone: Phone number in the format accepted by MAX.
        :type phone: str
        :param auth_type: The auth type value.
        :type auth_type: str
        :param use_mobile_fingerprint: Whether to use mobile fingerprint.
        :type use_mobile_fingerprint: bool
        :returns: The resulting StartSMSAuthResponse value.
        :rtype: StartSMSAuthResponse
        """
        user_agent = self.user_agent
        if (
            use_mobile_fingerprint
            and user_agent is not None
            and self.calls_seed is not None
            and hasattr(user_agent, "arch")
            and hasattr(user_agent, "app_version")
        ):
            mode = self.fingerprint_generator.generate_fingerprint(
                version=user_agent.app_version,
                device_id=user_agent.device_id,
                calls_seed=self.calls_seed,
                arch=user_agent.arch,
            )
        else:
            mode = None
        self._logger.info("requesting sms code phone_set=%s", bool(phone))
        response = await self.send_raw(
            method=StartSMSAuthMethod(
                phone=phone,
                type=auth_type,
                mode=mode,
            ),
            check_errors=True,
        )
        auth_response = StartSMSAuthResponse(**response.payload)
        return auth_response

    async def send_code(
        self,
        token: str,
        verify_code: str,
        auth_token_type: str = "CHECK_CODE",
    ) -> ChoiceLoginVariantResponse:
        """Send code.

        :param token: Authentication token.
        :type token: str
        :param verify_code: The verify code value.
        :type verify_code: str
        :param auth_token_type: The auth token type value.
        :type auth_token_type: str
        :returns: The resulting ChoiceLoginVariantResponse value.
        :rtype: ChoiceLoginVariantResponse
        """
        check_response = await self.send_raw(
            method=VerifySMSCodeMethod(
                temp_token=token,
                auth_token_type=auth_token_type,
                verify_code=str(verify_code),
            ),
            check_errors=True,
        )
        choice = ChoiceLoginVariantResponse(payload=check_response.payload)
        return choice

    async def request_qr(
        self,
    ) -> MetadataResponse:
        """Request qr.

        :returns: The resulting MetadataResponse value.
        :rtype: MetadataResponse
        """
        response = await self.send_raw(
            method=GetMetadataForLoginMethod(), check_errors=True
        )
        metadata = MetadataResponse(**response.payload)

        return metadata

    async def check_qr(self, track_id: str) -> TrackLoginResponse:
        """Check qr.

        :param track_id: Identifier of the track.
        :type track_id: str
        :returns: The resulting TrackLoginResponse value.
        :rtype: TrackLoginResponse
        :raises RuntimeError: If track login failed.
        """
        response = await self.send_raw_with_running_wait(
            method=TrackLoginMethod(track_id=track_id),
            # return_exception=True
        )

        track_data = TrackLoginResponse(**response.payload)

        if track_data is None:
            raise RuntimeError("Track login failed.")

        return track_data

    async def confirm_qr(self, track_id: str) -> ChoiceLoginVariantResponse:
        """Confirm qr.

        :param track_id: Identifier of the track.
        :type track_id: str
        :returns: The resulting ChoiceLoginVariantResponse value.
        :rtype: ChoiceLoginVariantResponse
        """
        response = await self.send_raw_with_running_wait(
            method=GetUserDataMethod(track_id=track_id),
        )
        payload = response.payload
        user = ChoiceLoginVariantResponse(
            payload=payload,
        )
        return user

    async def confirm_registration(
        self,
        first_name: str,
        last_name: str | None,
        token: str,
    ) -> ConfirmRegistrationResponse:
        """Confirm registration.

        :param first_name: The first name value.
        :type first_name: str
        :param last_name: The last name value.
        :type last_name: str | None
        :param token: Authentication token.
        :type token: str
        :returns: The resulting ConfirmRegistrationResponse value.
        :rtype: ConfirmRegistrationResponse
        """
        response = await self.send(
            method=ConfirmRegistrationMethod(
                first_name=first_name,
                last_name=last_name,
                token=token,
            )
        )

        return ConfirmRegistrationResponse(**response.payload)

    async def _get_track_id(self) -> str | None:
        """Retrieve track id.

        :returns: The resulting str | None value.
        :rtype: str | None
        """
        response = await self.send(method=GetTrackIdFor2FAMethod())

        track_id = GetTrackIdFor2FAResponse(**response.payload).track_id
        return track_id

    async def _set_email(
        self,
        track_id: str,
        email: str,
        email_code_getter: Callable[[str], Coroutine[Any, Any, str]],
    ) -> None:
        """Set email.

        :param track_id: Identifier of the track.
        :type track_id: str
        :param email: The email value.
        :type email: str
        :param email_code_getter: Callable to invoke.
        :type email_code_getter: Callable[[str], Coroutine[Any, Any, str]]
        """
        response = await self.send(
            method=GetEmailCodeMethod(
                track_id=track_id,
                email=email,
            )
        )

        code = await email_code_getter(email)

        response = await self.send(
            method=VerifyEmailMethod(
                track_id=track_id,
                verify_code=code,
            )
        )

    async def _set_hint(
        self,
        track_id: str,
        hint: str,
    ) -> None:
        """Set hint.

        :param track_id: Identifier of the track.
        :type track_id: str
        :param hint: The hint value.
        :type hint: str
        """
        response = await self.send(
            method=SetHintMethod(
                track_id=track_id,
                hint=hint,
            )
        )

    async def _set_password(
        self,
        track_id: str,
        password: str,
    ) -> None:
        """Set password.

        :param track_id: Identifier of the track.
        :type track_id: str
        :param password: Account password.
        :type password: str
        """
        response = await self.send(
            method=SetPasswordMethod(
                track_id=track_id,
                password=password,
            )
        )

    async def set_2fa(
        self,
        password: str,
        email: str | None = None,
        hint: str | None = None,
        email_code_getter: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        two_factor_actions: list[TwoFactorAction] | None = None,
    ) -> None:
        """Set 2fa.

        :param password: Account password.
        :type password: str
        :param email: The email value.
        :type email: str | None
        :param hint: The hint value.
        :type hint: str | None
        :param email_code_getter: Callable to invoke.
        :type email_code_getter: Callable[[str], Coroutine[Any, Any, str]] | None
        :param two_factor_actions: Collection of two factor actions.
        :type two_factor_actions: list[TwoFactorAction] | None
        :raises MapperApiError: If no track id provided.
        """
        if two_factor_actions is None:
            two_factor_actions = []
        track_id = await self._get_track_id()

        if track_id is None:
            raise MapperApiError("No track id provided.")

        await self._set_password(
            track_id=track_id,
            password=password,
        )

        has_hint = False
        has_email = False

        if email is not None:

            async def default_email_code_getter(e: str) -> str:
                """Default email code getter.

                :param e: The e value.
                :type e: str
                :returns: The resulting str value.
                :rtype: str
                """
                return await asyncio.to_thread(input, f"Введите код с почты {e}: ")

            callback = email_code_getter or default_email_code_getter

            await self._set_email(
                track_id=track_id, email=email, email_code_getter=callback
            )

            has_email = True

        if hint is not None:
            await self._set_hint(track_id=track_id, hint=str(hint))
            has_hint = True

        expected_capabilities = [TwoFactorAction.SET_PASSWORD]

        if has_hint:
            if TwoFactorAction.HINT not in expected_capabilities:
                expected_capabilities.append(TwoFactorAction.HINT)
        if has_email:
            if TwoFactorAction.EMAIL not in expected_capabilities:
                expected_capabilities.append(TwoFactorAction.EMAIL)

        response = await self.send(
            method=SetTwoFactorMethod(
                track_id=track_id,
                password=password,
                hint=str(hint) if has_hint else None,
                expected_capabilities=[
                    reverse_translate_two_factor_actions(action)
                    for action in expected_capabilities
                ],
            )
        )

    async def _check_2fa_password(
        self, track_id: str, password: str
    ) -> GetTrackIdFor2FAResponse:
        """Check 2fa password.

        :param track_id: Identifier of the track.
        :type track_id: str
        :param password: Account password.
        :type password: str
        :returns: The resulting GetTrackIdFor2FAResponse value.
        :rtype: GetTrackIdFor2FAResponse
        """
        response = await self.send(
            method=CheckPasswordMethod(
                track_id=track_id,
                password=password,
            )
        )

        return GetTrackIdFor2FAResponse(**response.payload)

    async def remove_2fa(
        self,
        password: str,
        expected_capabilities: list[TwoFactorAction] | None = None,
        remove_2fa: bool = True,
    ) -> None:
        """Remove 2fa.

        :param password: Account password.
        :type password: str
        :param expected_capabilities: Collection of expected capabilities.
        :type expected_capabilities: list[TwoFactorAction] | None
        :param remove_2fa: The remove 2fa value.
        :type remove_2fa: bool
        :raises RuntimeError: If failed to create auth track.
        """
        if expected_capabilities is None:
            expected_capabilities = []
        self._logger.info("removing 2fa password_set=%s", bool(password))

        track_id = await self._get_track_id()

        if track_id is None:
            self._logger.error("missing track_id in auth create track response")
            raise RuntimeError("Failed to create auth track")

        await self._check_2fa_password(track_id, password)

        response = await self.send(
            method=RemoveTwoFactorMethod(
                track_id=track_id,
                expected_capabilities=[
                    reverse_translate_two_factor_actions(action)
                    for action in expected_capabilities
                ],
                remove2fa=remove_2fa,
            )
        )
        return None

    async def approve_qr_login(self, qr_link: str) -> None:
        """Approve qr login.

        :param qr_link: The qr link value.
        :type qr_link: str
        """
        response = await self.send(
            method=ApproveQrLoginMethod(
                qr_link=qr_link,
            )
        )
        return None

    async def check_2fa(self) -> bool:
        """Check 2fa.

        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        :raises RuntimeError: If mapper not bound to MaxApi instance.
        """
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to MaxApi instance.")

        if self.max_api.me is None or self.max_api.me.profile_options is None:
            return False
        return (
            ProfileOptionsMappingModel.SECOND_FACTOR_PASSWORD_ENABLED
            in self.max_api.me.profile_options
        )

    async def change_password(
        self,
        password_old: str,
        password_new: str,
        expected_capabilities: list[TwoFactorAction] | None = None,
        hint: str | None = None,
    ) -> None:
        """Change password.

        :param password_old: The password old value.
        :type password_old: str
        :param password_new: The password new value.
        :type password_new: str
        :param expected_capabilities: Collection of expected capabilities.
        :type expected_capabilities: list[TwoFactorAction] | None
        :param hint: The hint value.
        :type hint: str | None
        :raises RuntimeError: If failed to create auth track.
        """
        if expected_capabilities is None:
            expected_capabilities = []
        if TwoFactorAction.UPDATE_PASSWORD not in expected_capabilities:
            expected_capabilities.append(TwoFactorAction.UPDATE_PASSWORD)

        track_id = await self._get_track_id()

        if not track_id:
            self._logger.error("missing track_id in auth create track response")
            raise RuntimeError("Failed to create auth track")

        await self._check_2fa_password(track_id, password_old)

        await self._set_password(track_id, password_new)

        response = await self.send(
            method=SetTwoFactorMethod(
                track_id=track_id,
                password=password_new,
                hint=hint,
                expected_capabilities=[
                    reverse_translate_two_factor_actions(action)
                    for action in expected_capabilities
                ],
            )
        )

    async def start_auth_flow(
        self,
        *args: Any,
        extra_config: ExtraConfig,
        max_api: MaxApi,
        **kwargs: Any,
    ) -> None:
        mapper_conf = extra_config.mapper

        if not isinstance(mapper_conf, EnvelopeMapperConfigV11):
            raise TypeError(
                "mapper config must be an instance of EnvelopeMappingConfigV11 for this mapper"
            )

        connect_timeout = mapper_conf.connect_timeout
        device_type = mapper_conf.device_type
        user_agent_params = mapper_conf.user_agent_config.model_dump()
        device_id = mapper_conf.user_agent_config.device_id

        if not mapper_conf.user_agent_config.is_custom_device_id:
            del user_agent_params["device_id"]

        user_agent_model = self.DEVICE_TYPE_TO_USERAGENT_MODEL[device_type]
        user_agent = user_agent_model.get_random_user_agent(**user_agent_params)
        self.user_agent = user_agent

        from ..LifecycleManager import LifecycleManager
        from ..Mapper import Mapper

        self._lifecycle_manager = LifecycleManager(
            mapper=cast(Mapper, self),
            connect_timeout=connect_timeout,
            need_login=max_api.token is None,
        )

        self.protocol.set_generation_getter(self._lifecycle_manager.get_generation)
        self.protocol.set_exceptions_callback(
            self._lifecycle_manager.notify_about_exception
        )

        self._lifecycle_manager.start(
            only_send_user_agent=True,
        )
        await self._protocol_connected.wait()

    async def end_auth_flow(self, token: str | None) -> None:
        if token is not None:
            self.token = token
        self.mapper_config.token = token
        lifecycle_manager = self._lifecycle_manager

        if lifecycle_manager is not None:
            await lifecycle_manager.stop()
        self._lifecycle_manager = None
        # self.user_agent = None
        self.protocol.set_generation_getter(None)
        self.protocol.set_exceptions_callback(None)

    async def login(
        self,
        url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
        login_backoff: Backoff | None = None,
        registration_config: RegistrationConfig | None = None,
        use_mobile_fingerprint: bool = True,
    ) -> SuccessLoginResponse | None:
        """Login.

        :param url_callback: Callable to invoke.
        :type url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None
        :param login_backoff: Backoff instance to process.
        :type login_backoff: Backoff | None
        :param registration_config: RegistrationConfig instance to process.
        :type registration_config: RegistrationConfig | None
        :param use_mobile_fingerprint: Whether to use mobile fingerprint.
        :type use_mobile_fingerprint: bool
        :returns: The resulting SuccessLoginResponse | None value.
        :rtype: SuccessLoginResponse | None
        :raises RuntimeError: If user agent is not initialized.
        :raises MapperApiError: If server not return token.
        """
        token = self.token

        if token is None:

            self._logger.info("haven`t token. Start login...")
            if self.user_agent is None:
                raise RuntimeError("user agent is not initialized.")
            user = await self._login(
                user_agent=self.user_agent,
                login_backoff=login_backoff,
                url_callback=url_callback,
                registration_config=registration_config,
                use_mobile_fingerprint=use_mobile_fingerprint,
            )

            self._logger.info("get token from login...")

            token = user.token_attrs.token
            self.token = token

            if token is None:
                raise MapperApiError("Server not return token.")

            if self.max_api.session_id is None:
                self.max_api.session_id = str(uuid.uuid4())
            # session = SessionInfo(
            #     token=token,
            #     device_id=self.mapper_config.user_agent_config.device_id,
            #     phone=self.mapper_config.phone or "",
            #     session_id=self.max_api.session_id,
            #     user_agent_config=self.mapper_config.user_agent_config.to_string(),
            #     **self.mapper_config.user_agent_config.session_info_params,
            # )

            self.max_api.token = token

            # self.max_api.session = session

            # await self.max_api.session_storage.save_session(
            #     session, self.max_api.session_key
            # )

            # await write_token(token=token, name_of_token=self.TOKEN_NAME)
            # self._logger.info("was write token in tokens.json successfully.")
            return user
        else:
            self._logger.info("already has token, login skipped.")
            return None

    async def _login(
        self,
        user_agent: BaseUserAgentMappingModel,
        login_backoff: Backoff | None = None,
        code_getter: Callable[[str], Coroutine[Any, Any, int]] | None = None,
        url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
        registration_config: RegistrationConfig | None = None,
        use_mobile_fingerprint: bool = True,
    ) -> SuccessLoginResponse:
        """Login.

        :param user_agent: BaseUserAgentMappingModel instance to process.
        :type user_agent: BaseUserAgentMappingModel
        :param login_backoff: Backoff instance to process.
        :type login_backoff: Backoff | None
        :param code_getter: Callable to invoke.
        :type code_getter: Callable[[str], Coroutine[Any, Any, int]] | None
        :param url_callback: Callable to invoke.
        :type url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None
        :param registration_config: RegistrationConfig instance to process.
        :type registration_config: RegistrationConfig | None
        :param use_mobile_fingerprint: Whether to use mobile fingerprint.
        :type use_mobile_fingerprint: bool
        :returns: The resulting SuccessLoginResponse value.
        :rtype: SuccessLoginResponse
        :raises RestartMapperError: If failed to login.
        :raises RestartMapperError: If failed to login - timeout.
        :raises MapperApiError: If password is required to login in account with 2FA.
        """
        if login_backoff is None:
            login_backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
        if not url_callback:

            async def url_callback(url: str) -> None:
                """Creating a QR code scanned by max. It is displayed immediately in the console

                Args:
                    url - authorization url

                :param url: Resource URL.
                :type url: str
                """

                qr = qrcode.QRCode()
                qr.add_data(url)

                qr.make(fit=True)
                qr.print_ascii(invert=True)

        try:
            await self._send_user_agent(
                user_agent=user_agent,
            )

            choice: ChoiceLoginVariantResponse = await self._call_build_in_method(
                method_name="LOGIN",
                # metadata=metadata,
                url_callback=url_callback,
                code_getter=code_getter,
                login_backoff=login_backoff,
                user_agent=user_agent,
                sms_auth=self.sms_auth,
                registration_config=registration_config,
                use_mobile_fingerprint=use_mobile_fingerprint,
            )
            user: SuccessLoginResponse

            if isinstance(choice.payload, TwoFactorLoginResponse):
                if self.password is None:
                    raise MapperApiError(
                        "password is required to login in account with 2FA."
                    )
                user = await self.resolve_two_factor(
                    track_id=choice.payload.password_challenge.track_id,
                    password=self.password,
                )
            else:
                user = choice.payload

            return user
        except MapperCancelledError:
            self._logger.error("Login cancelled")
            await login_backoff.asleep()
            raise RestartMapperError("Failed to login")
        except TimeoutError as e:
            self._logger.error("Login timed out")
            raise RestartMapperError("Failed to login - timeout")
        except Exception as e:
            self._logger.error("Failed to login: %s - %s", e.__class__.__name__, e)
            await login_backoff.asleep()
            raise RestartMapperError("Failed to login")

    async def resolve_two_factor(
        self, track_id: str, password: str
    ) -> SuccessLoginResponse:
        # if password is None:
        #     raise RuntimeError("No password given, but need 2FA")
        """Resolve two factor.

        :param track_id: Identifier of the track.
        :type track_id: str
        :param password: Account password.
        :type password: str
        :returns: The resulting SuccessLoginResponse value.
        :rtype: SuccessLoginResponse
        """
        response = await self.send_raw_with_running_wait(
            method=Resolve2FAMethod(
                password=password,
                track_id=track_id,
            )
        )
        user = SuccessLoginResponse(**response.payload)
        return user

    async def _send_only_user_agent(
        self,
        user_agent: BaseUserAgentMappingModel,
    ) -> None:
        try:
            await self._send_user_agent(
                user_agent=user_agent,
            )
        except BaseMapperError as e:
            self._logger.warning("Error while sending user agent: %s", e)
            # self._authorized.clear()
            raise RestartMapperError("Auth failed") from e
        except Exception as e:
            self._logger.warning("Unexpected error while sending user agent: %s", e)
            raise RestartMapperError("Auth failed") from e

    async def _auth(
        self,
        token: str,
        user_agent: BaseUserAgentMappingModel,
        # interactive: bool = True,
        send_user_agent: bool = True,
        **kwargs: Any,
    ) -> None:
        """Auth.

        :param token: Authentication token.
        :type token: str
        :param user_agent: BaseUserAgentMappingModel instance to process.
        :type user_agent: BaseUserAgentMappingModel
        :param chats_count: The chats count value.
        :type chats_count: int
        :param interactive: The interactive value.
        :type interactive: bool
        :param presence_sync: The presence sync value.
        :type presence_sync: int
        :param chats_sync: The chats sync value.
        :type chats_sync: int
        :param contacts_sync: The contacts sync value.
        :type contacts_sync: int
        :param drafts_sync: The drafts sync value.
        :type drafts_sync: int
        :param send_user_agent: The send user agent value.
        :type send_user_agent: bool
        :raises RestartMapperError: If auth failed.
        :raises NeedReloginMapperError: if session experied
        """
        try:
            if send_user_agent:
                await self._send_user_agent(
                    user_agent=user_agent,
                )

            await self._send_auth_token(
                token=token,
            )
            self._authorized.set()
            if self._telemetry is not None:
                await self._telemetry.start()
        except NeedReloginMapperError as e:
            self._logger.warning("Need relogin")
            self._authorized.clear()
            raise NeedReloginMapperError("Auth failed") from e

        except BaseMapperError as e:
            self._logger.warning("Cancelled auth")
            self._authorized.clear()
            raise RestartMapperError("Auth failed") from e
        except Exception as e:
            self._logger.warning("Unexpected error while auth: %s", e)
            self._authorized.clear()
            raise RestartMapperError("Auth failed") from e

    async def _keepalive(self) -> None:
        """Keepalive."""
        try:
            while True:
                await asyncio.sleep(self._keepalive_ping_interval)
                self._logger.debug("send keepalive ping...")
                pong = await self.send(
                    method=SendKeepAlivePingMethod(
                        interactive=self.keep_alive_interactive
                    ),
                    return_exception=True,
                    wait_auth=False,
                )
                self._logger.debug("keepalive pong %s", pong)
        except MapperCancelledError:
            self._logger.warning("keepalive ping canceled")
        except MapperTransportError as e:
            self._logger.warning("keepalive transport error: %s", e, exc_info=True)
