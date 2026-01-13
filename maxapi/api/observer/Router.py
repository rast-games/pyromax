from typing import List

from .Handler import Handler

class Router:
    def __init__(self):
        self._handlers: List[Handler] = []
        self._allowed_args_for_handler = {}


    def register_handler(self, args=[], pattern=lambda update: True):
        def decorator(func):
            self._handlers.append(Handler(func, pattern, args))
        return decorator

