from typing import cast

from .Base import BaseMaxApiMethod
from ..models import TwoFactorAction

NoneType = type(None)


class Remove2FaMethod(BaseMaxApiMethod[NoneType]):
    async def __call__(
        self,
        password: str,
        two_factor_actions: list[TwoFactorAction] | None = None,
        remove_2fa: bool = True,
    ) -> None:
        """Execute the remove2 fa MAX API method.

        :param password: Account password.
        :type password: str
        :param two_factor_actions: Collection of two factor actions.
        :type two_factor_actions: list[TwoFactorAction] | None
        :param remove_2fa: The remove 2fa value.
        :type remove_2fa: bool
        :raises RuntimeError: If remove2Fa method not bound to MaxApi instance.
        """
        if not self._max_api:
            raise RuntimeError("Remove2Fa method not bound to MaxApi instance")
        return cast(
            None,
            await self._max_api.mapper.call_method(
                type(self),
                password=password,
                expected_capabilities=two_factor_actions,
                remove_2fa=remove_2fa,
            ),
        )
