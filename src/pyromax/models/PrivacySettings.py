
from .base import BaseMaxObject
from .enum import PrivacyAccess


class PrivacySettings(BaseMaxObject):
    search_by_phone: PrivacyAccess | None = None
    incoming_calls: PrivacyAccess | None = None
    chat_invites: PrivacyAccess | None = None
    phone_number_visibility: PrivacyAccess | None = None
    hide_online_status: bool | None = None
    safe_content_only: bool | None = None
