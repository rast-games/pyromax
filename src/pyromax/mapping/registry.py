MAPPERS = {}


def register_mapper(mapper: str):
    global MAPPERS
    def wrapper(cls: type):
        MAPPERS[mapper] = cls
        return cls
    return wrapper
