import asyncio
from typing import Any
import sys


def debug_tasks() -> str:
    """Выводит ВСЕ активные задачи.

    :returns: The resulting str value.
    :rtype: str
    """
    tasks = asyncio.all_tasks()
    msg = f"🔥 All tasks: {len(tasks)}\n"

    for i, task in enumerate(tasks):
        coro: Any = task.get_coro()
        coro_name = getattr(coro, "__qualname__", str(coro))
        state = "DONE" if task.done() else "PENDING"
        msg += f"  {i}: {task.get_name()} state={state} coro={coro_name}\n"
        if task.done() and not task.cancelled():
            try:
                exc = task.exception()
                if exc:
                    msg += f"    ❌ Exception: {exc}\n"
            except (asyncio.CancelledError, asyncio.InvalidStateError):
                pass
    return msg


def get_caller_info(depth: int = 1) -> str:
    """Точное место вызова: file:line:function

    :param depth: The depth value.
    :type depth: int
    :returns: The resulting str value.
    :rtype: str
    """
    frame = sys._getframe(depth)
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    funcname = frame.f_code.co_name
    return f"{filename}:{lineno} in {funcname}"


class EventFake:
    def __init__(self, event: asyncio.Event) -> None:
        """Initialize the event fake.

        :param event: Incoming event to process.
        :type event: asyncio.Event
        """
        self.event = event

    def _get_caller_info(self, depth: int = 1) -> str:
        """Точное место вызова: file:line:function

        :param depth: The depth value.
        :type depth: int
        :returns: The resulting str value.
        :rtype: str
        """
        frame = sys._getframe(depth)
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        funcname = frame.f_code.co_name
        return f"{filename}:{lineno} in {funcname}"

    def is_set(self) -> bool:
        """Return whether set.

        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        return self.event.is_set()

    def set(self) -> None:
        """Set."""
        self.event.set()

    def clear(self) -> None:
        """Clear."""
        caller = get_caller_info(2)
        print(f"🟢 FAILED.CLEAR() from {caller}")
        self.event.clear()

    async def wait(self) -> Any:
        """Wait.

        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        return await self.event.wait()
