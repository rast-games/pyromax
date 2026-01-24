from .Message import Message


class Update(Message):
    def __init__(self, update: dict):
        if not update:
            return
        super().__init__(update['message'])
        self.chat_id = update['chatId']
        self.mark = update['mark']
        self.unread = update['unread']
