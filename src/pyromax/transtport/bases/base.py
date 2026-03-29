from abc import ABC, abstractmethod
from collections.abc import Awaitable

from src.pyromax.mixins import AsyncInitializerMixin


class BaseTransport(AsyncInitializerMixin):
    BASE_EXCEPTION_FOR_TRANSPORT: type[Exception]

    OTHER_EXCEPTIONS_FOR_TRANSPORT: list[type[Exception]]
