class Message:
    def __init__(self, message: dict):
        self.text = message['text']
        self.sender = message['sender']
        self.type = message['type']
        self.time = message['time']
        self.attaches = message['attaches']


    def __repr__(self):
        details = []
        for key, value in self.__dict__.items():
            details.append(f"{key}={value}")
        return '\n'.join(details)