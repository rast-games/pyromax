from typing import List
import inspect

from .Handler import Handler
from pyromax.exceptions import AnnotationHandlerError

class Router:
    def __init__(self):
        self._handlers: List[Handler] = []
        self._allowed_args_for_handler = {}


    def register_handler(self, pattern=lambda update: True, from_me: bool = False):
        def decorator(func):
            signature = inspect.signature(func)
            args = [param.annotation for param in signature.parameters.values()]
            if inspect._empty in args:
                raise AnnotationHandlerError('need annotation all params in handler')
            self._handlers.append(Handler(func, pattern, args, from_me=from_me))
        return decorator

