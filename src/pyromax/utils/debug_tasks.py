import asyncio


def debug_tasks():
    """Выводит ВСЕ активные задачи."""
    tasks = asyncio.all_tasks()
    print(f"🔥 Всего задач: {len(tasks)}")

    for i, task in enumerate(tasks):
        print(f"  {i}: {task.get_name()} state={task._state} coro={task.get_coro().__qualname__}")
        if task._exception:
            print(f"    ❌ Exception: {task._exception}")