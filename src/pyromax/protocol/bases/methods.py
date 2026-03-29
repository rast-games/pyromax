from typing import Protocol, TypeVar

from src.pyromax.protocol.bases.request_response import Request


T = TypeVar('T', bound=Request)

class BaseMaxMethod(Protocol):
    async def __call__(self, request: T) -> T:
        pass