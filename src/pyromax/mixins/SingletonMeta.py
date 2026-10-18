from typing import Any, ClassVar


class SingletonMeta(type):
    _instances: ClassVar[dict[type[Any], Any]] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Invoke the singleton meta.

        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)

        return SingletonMeta._instances[cls]
