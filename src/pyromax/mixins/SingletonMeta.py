from typing import Any

class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args: Any, **kwargs: Any) -> object:
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)

        return SingletonMeta._instances[cls]