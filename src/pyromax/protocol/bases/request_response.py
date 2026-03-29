from typing import Any

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Response(ABC):
    pass

class Request(ABC):
    # def __init__(self, data: dict[str, Any]):
    #     self.data = data


    @abstractmethod
    def is_my_response(self, response: Response) -> bool: pass


    @abstractmethod
    def __hash__(self) -> int: pass
