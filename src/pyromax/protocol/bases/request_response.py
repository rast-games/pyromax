from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ...models import BaseMaxObject


class Response(ABC):
    pass

T_response = TypeVar('T_response', bound=Response)

class Request(ABC, Generic[T_response]):


    @abstractmethod
    def is_my_response(self, response: T_response) -> bool: pass


    @abstractmethod
    def __hash__(self) -> int: pass