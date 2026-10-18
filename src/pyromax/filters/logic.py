from __future__ import annotations
from abc import ABC
from typing import Any


from typing_extensions import TYPE_CHECKING

from ..models import BaseMaxObject, DataDict
from .base import Filter

if TYPE_CHECKING:
    from ..dispatcher.event.Handler import FilterObject
    from .magic import MagicFilter
    from ..dispatcher.event import ResolvedUpdate


class _LogicFilter(Filter, ABC):
    pass


class _InvertFilter(_LogicFilter):
    def __init__(self, target: FilterObject[Filter]) -> None:
        """Initialize the invert filter.

        :param target: FilterObject[Filter] instance to process.
        :type target: FilterObject[Filter]
        """
        super().__init__()
        self._SKIP_CHECK_PREPARATIONS = target.filter._SKIP_CHECK_PREPARATIONS
        self.target = target

    @property
    def work_with(self) -> tuple[type[BaseMaxObject], ...]:
        """Work with.

        :returns: The resulting tuple[type[BaseMaxObject], ...] value.
        :rtype: tuple[type[BaseMaxObject], ...]
        """
        return self.target.filter.work_with

    async def _check(self, update: ResolvedUpdate, data: DataDict) -> bool:
        """Check.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: DataDict
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        return not await self.target(update, data)

    def __repr__(self) -> str:
        """Return the developer representation of the invert filter.

        :returns: The resulting str value.
        :rtype: str
        """
        return f"{self.__class__.__name__}({self.target})"


class _AndFilter(_LogicFilter):
    _SKIP_CHECK_PREPARATIONS = True

    def __init__(self, *targets: FilterObject[Filter]) -> None:
        """Initialize the and filter.

        :param targets: FilterObject[Filter] instance to process.
        :type targets: FilterObject[Filter]
        """
        super().__init__()
        self.targets = targets

    @property
    def work_with(self) -> tuple[type[BaseMaxObject], ...]:
        """Work with.

        :returns: The resulting tuple[type[BaseMaxObject], ...] value.
        :rtype: tuple[type[BaseMaxObject], ...]
        """
        t = []
        for target in self.targets:
            work_types = target.filter.work_with
            for work_type in work_types:
                if work_type not in t:
                    t.append(work_type)
        return tuple(t)

    async def _check(
        self, update: ResolvedUpdate, data: DataDict
    ) -> bool | dict[Any, Any]:
        """Check.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: DataDict
        :returns: The resulting bool | dict[Any, Any] value.
        :rtype: bool | dict[Any, Any]
        """
        final_result = {}
        for target in self.targets:
            result = await target(update, data)
            if not result:
                return False
            if isinstance(result, dict):
                final_result.update(result)

        if final_result:
            return final_result
        return True


class _OrFilter(_LogicFilter):
    _SKIP_CHECK_PREPARATIONS = True

    def __init__(self, *targets: FilterObject[Filter]) -> None:
        """Initialize the or filter.

        :param targets: FilterObject[Filter] instance to process.
        :type targets: FilterObject[Filter]
        """
        super().__init__()
        self.targets = targets

    @property
    def work_with(self) -> tuple[type[BaseMaxObject], ...]:
        """Work with.

        :returns: The resulting tuple[type[BaseMaxObject], ...] value.
        :rtype: tuple[type[BaseMaxObject], ...]
        """
        t = []
        for target in self.targets:
            work_types = target.filter.work_with
            for work_type in work_types:
                if work_type not in t:
                    t.append(work_type)
        return tuple(t)

    async def _check(
        self, update: ResolvedUpdate, data: DataDict
    ) -> bool | dict[str, Any]:
        """Check.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: DataDict
        :returns: The resulting bool | dict[str, Any] value.
        :rtype: bool | dict[str, Any]
        """
        for target in self.targets:
            result = await target(update, data)
            if not result:
                continue
            if isinstance(result, dict):
                return result
            return bool(result)
        return False


def and_f(*targets: Filter | MagicFilter) -> _AndFilter:
    """And f.

    :param targets: Filter | MagicFilter instance to process.
    :type targets: Filter | MagicFilter
    :returns: The resulting _AndFilter value.
    :rtype: _AndFilter
    """
    from ..dispatcher.event.Handler import FilterObject

    return _AndFilter(*(FilterObject(target) for target in targets))


def or_f(*targets: Filter | MagicFilter) -> _OrFilter:
    """Or f.

    :param targets: Filter | MagicFilter instance to process.
    :type targets: Filter | MagicFilter
    :returns: The resulting _OrFilter value.
    :rtype: _OrFilter
    """
    from ..dispatcher.event.Handler import FilterObject

    return _OrFilter(*(FilterObject(target) for target in targets))


def invert_f(target: Filter | MagicFilter) -> _InvertFilter:
    """Invert f.

    :param target: Filter | MagicFilter instance to process.
    :type target: Filter | MagicFilter
    :returns: The resulting _InvertFilter value.
    :rtype: _InvertFilter
    """
    from ..dispatcher.event.Handler import FilterObject

    return _InvertFilter(FilterObject(target))
