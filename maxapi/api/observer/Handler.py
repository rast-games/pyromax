from typing import List, Any, TYPE_CHECKING

from .ObserverPattern import Observer

if TYPE_CHECKING:
    from .. import MaxApi
    from maxapi.types import Update


class Handler(Observer):
    def __init__(self, function, pattern = lambda update: True, args: List[Any] = [], from_me=False):
        self.args = args
        self.function = function
        self.pattern = pattern
        self.from_me = from_me


    async def update(self, update: 'Update', max_api: 'MaxApi') -> bool:
        if (update.sender == max_api.id) != self.from_me:
            return False
        return self.pattern(update)
