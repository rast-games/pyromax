import unittest

from pyromax.auth import (
    AuthCallbacks,
    AuthInteractor,
    PasswordRequest,
    TerminalAuthInteractor,
)
from pyromax.config import ExtraConfig
from pyromax.exceptions import AuthInputRequired


class NonInteractiveAuthInteractor(TerminalAuthInteractor):
    @property
    def can_prompt(self) -> bool:
        return False


class AuthInteractorTest(unittest.IsolatedAsyncioTestCase):
    async def test_custom_interactor_is_preserved_by_config(self) -> None:
        class CustomInteractor(TerminalAuthInteractor):
            async def request_password(self, request: PasswordRequest) -> str:
                return request.track_id

        interactor = CustomInteractor()
        config = ExtraConfig(auth_interactor=interactor)

        self.assertIs(config.auth_interactor, interactor)
        self.assertIsInstance(config.auth_interactor, AuthInteractor)

    async def test_password_callback_receives_request_context(self) -> None:
        async def get_password(request: PasswordRequest) -> str:
            self.assertEqual(request.track_id, "track-id")
            self.assertEqual(request.phone, "79990000000")
            return "secret"

        interactor = TerminalAuthInteractor(
            AuthCallbacks(password=get_password),
        )

        password = await interactor.request_password(
            PasswordRequest(track_id="track-id", phone="79990000000")
        )

        self.assertEqual(password, "secret")

    async def test_non_interactive_password_request_has_actionable_error(self) -> None:
        interactor = NonInteractiveAuthInteractor()

        with self.assertRaisesRegex(AuthInputRequired, "provide an AuthInteractor"):
            await interactor.request_password(PasswordRequest(track_id="track-id"))

    async def test_sms_callback_result_is_normalized_to_string(self) -> None:
        async def get_code(phone: str) -> int:
            self.assertEqual(phone, "79990000000")
            return 12345

        interactor = TerminalAuthInteractor(
            AuthCallbacks(sms_code=get_code),
        )

        self.assertEqual(await interactor.request_sms_code("79990000000"), "12345")


if __name__ == "__main__":
    unittest.main()
