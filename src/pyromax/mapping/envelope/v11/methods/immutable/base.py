import abc
from typing import Any


from ......protocol import Envelope, BaseMaxProtocolMethod
from ....constants import Opcode, Cmd
from ...constants import VERSION


class BaseMethod(abc.ABC, BaseMaxProtocolMethod[Envelope]):
    def __init__(self, **kwargs: Any) -> None:
        self.args = kwargs


    @abc.abstractmethod
    async def __call__(self, request: Envelope) -> Envelope:
        pass


__all__ = [
    'BaseMethod',
    'Opcode',
    'Cmd',
    'VERSION',
    'Envelope'
]