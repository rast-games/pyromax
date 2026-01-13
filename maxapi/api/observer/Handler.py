from .ObserverPattern import Observer

class Handler(Observer):
    def __init__(self, function,  pattern=lambda update: True, args=['MaxApi']):
        self.args = args
        self.function = function
        self.pattern = pattern


    async def update(self, update):
        return self.pattern(update)
