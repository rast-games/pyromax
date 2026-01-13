
class NotFoundFlag:
    def __init__(self):
        pass

    def __eq__(self, other):
        if type(other) == NotFoundFlag or (type(self) == type(other()) if type(other) == type else None):
            return True
        return False

    def __bool__(self):
        return False

if __name__ == '__main__':
    not_found = NotFoundFlag()
