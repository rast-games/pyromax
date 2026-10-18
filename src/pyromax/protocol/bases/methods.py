from typing import Protocol, TypeVar, Any

from .request_response import Request

T = TypeVar("T", bound=Request[Any])


class BaseMaxProtocolMethod(Protocol[T]):
    async def __call__(self, request: T) -> T:
        """Execute the base max protocol MAX API method.

        :param request: Protocol request envelope to populate or send.
        :type request: T
        :returns: The resulting T value.
        :rtype: T
        """
        pass
