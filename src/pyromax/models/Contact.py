from .base import BaseMaxObject


class Contact(BaseMaxObject):
    first_name: str = ''
    last_name: str = ''
    name: str = ''
    id: int
    description: str = ''