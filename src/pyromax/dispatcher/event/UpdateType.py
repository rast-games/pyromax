from typing import TypeVar, TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from ...models import BaseMaxObject
    from ...protocol import Response


from ...mixins import SingletonMeta


class UnhandledObject(metaclass=SingletonMeta):
    """Just unhandled marker"""


UNHANDLED = UnhandledObject()


class UnknownUpdateType(metaclass=SingletonMeta):
    """Just unknown update marker"""


UNKNOWN_UPDATE = UnknownUpdateType()


MaxObject: TypeAlias = "BaseMaxObject | Response"


Update = TypeVar("Update", bound="Response")

ResolvedUpdate = TypeVar("ResolvedUpdate", bound=MaxObject)
