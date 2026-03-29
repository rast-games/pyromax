import abc
from typing import TypeVar, Generic, Any

from pydantic import BaseModel

from src.pyromax.core.MaxApiContextController import ContextController



T = TypeVar('T', bound=Any)

class BaseMaxApiMethod(ContextController, BaseModel, Generic[T], abc.ABC):

    @abc.abstractmethod
    async def __call__(self, *args, **kwargs) -> T: pass