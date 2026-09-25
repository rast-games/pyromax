from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# from ...models import BaseMaxObject


class Response(ABC):
    pass


class ErrorResponse(Response):
    def __init__(self, error: Exception) -> None:
        self.error = error

    def __repr__(self) -> str:
        return f"{type(self).__name__}(error={self.error!r})"


T_response = TypeVar("T_response", bound=Response)


class Request(ABC, Generic[T_response]):

    @abstractmethod
    def is_my_response(self, response: T_response) -> bool:
        """Return whether my response.

        :param response: Protocol response to process.
        :type response: T_response
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """Hash.

        :returns: The resulting int value.
        :rtype: int
        """
        pass
