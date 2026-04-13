from abc import ABC, abstractmethod
from typing import Generic, TypeVar


class Response(ABC):
    pass

T_response = TypeVar('T_response', bound=Response)

class Request(ABC, Generic[T_response]):
    # def __init__(self, data: dict[str, Any]):
    #     self.data = data


    @abstractmethod
    def is_my_response(self, response: T_response) -> bool: pass


    @abstractmethod
    def __hash__(self) -> int: pass