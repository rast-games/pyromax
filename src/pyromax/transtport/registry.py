TRANSPORTS = {}


def register_transport(transport: str):
    global TRANSPORTS
    def wrapper(cls: type):
        TRANSPORTS[transport] = cls
        return cls
    return wrapper
