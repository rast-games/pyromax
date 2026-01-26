# Python imports
from __future__ import annotations
from typing import Any, Callable


async def apply_decorator_to_method(
    obj: Any,
    method_name: str,
    decorator: Callable[[Any, Callable[..., Any]], Any]
) -> None:
    """
    Apply a decorator function to a method of an object and replace the original method.
    
    This function retrieves the original method from the object, applies the decorator
    to it (which may be async), and then replaces the original method with the decorated version.
    
    Args:
        obj: The object whose method should be decorated
        method_name: Name of the method to decorate
        decorator: Async callable that takes (obj, original_method) and returns
                   a decorated version of the method
                   
    Example:
        >>> async def my_decorator(obj, method):
        ...     async def wrapper(*args, **kwargs):
        ...         # Do something before
        ...         result = await method(*args, **kwargs)
        ...         # Do something after
        ...         return result
        ...     return wrapper
        >>> await apply_decorator_to_method(client, 'send_message', my_decorator)
    """
    original_method = getattr(o=obj, name=method_name)
    decorated_method = await decorator(obj, original_method)
    setattr(obj=obj, name=method_name, value=decorated_method)
