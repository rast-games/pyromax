PROTOCOLS = {}


def register_protocol(protocol: str):
    global PROTOCOLS
    def wrapper(cls: type):
        PROTOCOLS[protocol] = cls
        return cls
    return wrapper
