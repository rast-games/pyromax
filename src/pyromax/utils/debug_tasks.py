import asyncio
from typing import Any


def debug_tasks() -> None:
    """Выводит ВСЕ активные задачи."""
    tasks = asyncio.all_tasks()
    print(f"🔥 Всего задач: {len(tasks)}")

    for i, task in enumerate(tasks):
        coro: Any = task.get_coro()
        coro_name = getattr(coro, "__qualname__", str(coro))
        state = "DONE" if task.done() else "PENDING"
        print(f"  {i}: {task.get_name()} state={state} coro={coro_name}")
        if task.done() and not task.cancelled():
            try:
                exc = task.exception()
                if exc:
                    print(f"    ❌ Exception: {exc}")
            except (asyncio.CancelledError, asyncio.InvalidStateError):
                pass