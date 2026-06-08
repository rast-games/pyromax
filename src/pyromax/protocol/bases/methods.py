from typing import Protocol, TypeVar, Any, Generic

from .request_response import Request

T = TypeVar('T', bound=Request[Any])

class BaseMaxProtocolMethod(Protocol[T]):
    async def __call__(self, request: T) -> T:
        pass