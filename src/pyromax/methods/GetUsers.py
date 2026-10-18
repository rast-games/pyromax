from typing import cast

from .Base import BaseMaxApiMethod
from ..models.Contact import Contact


class GetUsersMethod(BaseMaxApiMethod[list[Contact]]):
    async def __call__(self, user_ids: int) -> list[Contact]:
        """Execute the get users MAX API method.

        :param user_ids: Identifiers of the users.
        :type user_ids: int
        :returns: The resulting collection.
        :rtype: list[Contact]
        :raises RuntimeError: If getUser method not bound to MaxApi instance.
        """
        if not self._max_api:
            raise RuntimeError("GetUser method not bound to MaxApi instance")
        return cast(
            list[Contact],
            await self._max_api.mapper.call_method(
                type(self),
                user_ids=user_ids,
            ),
        )
