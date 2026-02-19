from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

# COPY-PASTED FROM AIOGRAM

class Filter(ABC):
    """
    If you want to register own filters like builtin filters you will need to write subclass
    of this class with overriding the :code:`__call__`
    method and adding filter attributes.
    """

    if TYPE_CHECKING:
        # This checking type-hint is needed because mypy checks validity of overrides and raises:
        # error: Signature of "__call__" incompatible with supertype "BaseFilter"  [override]
        # https://mypy.readthedocs.io/en/latest/error_code_list.html#check-validity-of-overrides-override
        __call__: Callable[..., Awaitable[bool | dict[str, Any]]]
    else:  # pragma: no cover

        @abstractmethod
        async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
            """
            This method should be overridden.

            Accepts incoming event and should return boolean or dict.

            :return: :class:`bool` or :class:`dict[str, Any]`
            """

