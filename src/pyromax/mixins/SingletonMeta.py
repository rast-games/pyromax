from typing import Any, ClassVar, Self

class SingletonMeta(type):
    _instances: ClassVar[dict[type[Any], Any]] = {}
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)

        return SingletonMeta._instances[cls]