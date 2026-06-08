import asyncio
from typing import Any
import sys


def debug_tasks() -> str:
    """Выводит ВСЕ активные задачи."""
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
                    msg +=f"    ❌ Exception: {exc}\n"
            except (asyncio.CancelledError, asyncio.InvalidStateError):
                pass
    print(msg)
    return msg


def get_caller_info(depth:int=1) -> str:
    """Точное место вызова: file:line:function"""
    frame = sys._getframe(depth)
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    funcname = frame.f_code.co_name
    return f"{filename}:{lineno} in {funcname}"


class EventFake:
    def __init__(self, event: asyncio.Event) -> None:
        self.event = event

    def _get_caller_info(self, depth:int=1) -> str:
        """Точное место вызова: file:line:function"""
        frame = sys._getframe(depth)
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        funcname = frame.f_code.co_name
        return f"{filename}:{lineno} in {funcname}"

    def is_set(self) -> bool:
        return self.event.is_set()

    def set(self) -> None:
        caller = get_caller_info(2)  # 2 уровня вверх
        print(f"🔴 FAILED.SET() from {caller}")
        self.event.set()

    def clear(self) -> None:
        caller = get_caller_info(2)
        print(f"🟢 FAILED.CLEAR() from {caller}")
        self.event.clear()

    async def wait(self) -> Any:
        return await self.event.wait()