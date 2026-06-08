from .base import BaseMaxObject


class Contact(BaseMaxObject):
    first_name: str = ''
    last_name: str = ''
    name: str = ''
    id: int
    description: str = ''
    phone: str | None = None
    avatar_url: str | None = None
    raw_avatar_url: str | None = None
    photo_id: str | None = None
    country: str | None = None
    account_status: int | None = None
    email: str | None = None
    registration_time: int | None = None