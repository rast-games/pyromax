
async def use_decorator_on_obj_method(self, method: str, decorator):
    setattr(self, method, await decorator(self, getattr(self, method)))