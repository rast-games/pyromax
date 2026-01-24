from .File import Video, Photo, File

class Message:
    def __init__(self, message: dict):
        self.id = int(message['id'])
        self.text = message['text']
        self.sender = message['sender']
        self.type = message['type']
        self.time = message['time']
        types_of_attaches = {
            'VIDEO': Video.load_attach,
            'PHOTO': Photo.load_attach,
            'FILE': File.load_attach,
        }
        attaches = []
        for attach in message['attaches']:
            if attach['_type'] in types_of_attaches:
                attaches.append(types_of_attaches[attach['_type']](attach))
            else:
                attaches.append(attach)
        self.attaches = attaches



    def __repr__(self):
        details = []
        for key, value in self.__dict__.items():
            details.append(f"{key}={value}")
        return '\n'.join(details)