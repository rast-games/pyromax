from .StandardMaxEventObserver import StandardMaxEventObserver, Update


class UpdateMaxEventObserver(StandardMaxEventObserver):
    async def is_my_update(
            self,
            update: Update
    ) -> bool:
        return isinstance(update, self.type_of_update)