from typing import Protocol, TypeVar

from .request_response import Request


T = TypeVar('T', bound=Request)

class BaseMaxProtocolMethod(Protocol):
    async def __call__(self, request: T) -> T:
        pass