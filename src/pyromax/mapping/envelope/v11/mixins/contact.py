from collections.abc import Sequence
from typing import cast

from .MixinProtocol import MixinProtocol, T_USER
from .....models import Contact, Session, ContactInfo
from ..methods.immutable import (
    GetGeneralInfoAboutMemberMethod,
    SearchByPhoneMethod,
    GetSessionsMethod,
    ContactActionMethod,
    ImportContactsMethod,
)
from ..payloads.responses import (
    GetContactResponse,
    ContactContainsResponse,
    SessionsContainsResponse,
    ContactsContainsResponse,
)
from ..translate.ToDTO import translate_models


class ContactMixin(MixinProtocol):
    def _cache_user(self, user: T_USER) -> T_USER:
        """Cache user.

        :param user: Contact instance to process.
        :type user: Contact
        :returns: The resulting Contact value.
        :rtype: Contact
        :raises RuntimeError: If mapper not bound to max_api instance.
        """
        user = self.bind_api_instance(user)
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to max_api instance")
        self.max_api.users[user.id] = user
        return user

    def get_cached_user(self, user_id: int) -> Contact | None:
        """Retrieve cached user.

        :param user_id: Identifier of the user.
        :type user_id: int
        :returns: The resulting Contact | None value.
        :rtype: Contact | None
        :raises RuntimeError: If mapper not bound to max_api instance.
        """
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to max_api instance")
        user = self.max_api.users.get(user_id)
        self._logger.debug("get_cached_user id=%s hit=%s", user_id, bool(user))
        return self.bind_api_instance(user) if user is not None else None

    async def get_members_by_ids(
        self, member_ids: int | list[int]
    ) -> Sequence[Contact]:
        """Retrieve members by ids.

        :param member_ids: Identifiers of the members.
        :type member_ids: int | list[int]
        :returns: The resulting collection.
        :rtype: Sequence[Contact]
        :raises TypeError: If member_id must be int or list[int].
        """
        contact_ids: list[int]
        if isinstance(member_ids, int):
            contact_ids = [member_ids]
        elif isinstance(member_ids, list):
            contact_ids = member_ids
        else:
            raise TypeError("member_id must be int or list[int]")

        response_envelope = await self.send(
            method=GetGeneralInfoAboutMemberMethod(
                contact_ids=contact_ids,
            )
        )

        response = GetContactResponse(**response_envelope.payload)

        contacts = [
            self._cache_user(cast(Contact, translate_models(mapping_contact)))
            for mapping_contact in response.contacts
        ]

        return [contact for contact in contacts if isinstance(contact, Contact)]

        # return cast(list[BaseMaxObject], contacts)

    async def get_users(self, user_ids: list[int]) -> list[Contact]:
        """Retrieve users.

        :param user_ids: Identifiers of the users.
        :type user_ids: list[int]
        :returns: The resulting collection.
        :rtype: list[Contact]
        """
        cached = {
            user_id: user
            for user_id in user_ids
            if (user := self.get_cached_user(user_id)) is not None
        }
        missing_ids = [user_id for user_id in user_ids if user_id not in cached]

        if missing_ids:
            for user in await self.get_members_by_ids(missing_ids):
                cached[user.id] = user

        return [cached[user_id] for user_id in user_ids if user_id in cached]

    async def search_by_phone(self, phone: str) -> Contact:
        """Search for by phone.

        :param phone: Phone number in the format accepted by MAX.
        :type phone: str
        :returns: The resulting Contact value.
        :rtype: Contact
        """
        response = await self.send(
            method=SearchByPhoneMethod(
                phone=phone,
            )
        )

        mapped_contact = ContactContainsResponse(**response.payload).contact

        contact = cast(Contact, translate_models(mapped_contact))
        return self._cache_user(contact)

    async def get_sessions(self) -> list[Session]:
        """Retrieve sessions.

        :returns: The resulting collection.
        :rtype: list[Session]
        """
        response = await self.send(method=GetSessionsMethod())
        mapped_sessions = SessionsContainsResponse(**response.payload).sessions
        sessions = [
            self.bind_api_instance(cast(Session, translate_models(session)))
            for session in mapped_sessions
        ]
        return sessions

    async def add_contact(self, contact_id: int) -> Contact:
        """Add contact.

        :param contact_id: Identifier of the contact.
        :type contact_id: int
        :returns: The resulting Contact value.
        :rtype: Contact
        """
        response = await self.send(
            method=ContactActionMethod(
                contact_id=contact_id,
                action="ADD",
            )
        )
        mapped_contact = ContactContainsResponse(**response.payload).contact

        contact = cast(Contact, translate_models(mapped_contact))
        return self._cache_user(contact)

    async def remove_contact(self, contact_id: int) -> None:
        """Remove contact.

        :param contact_id: Identifier of the contact.
        :type contact_id: int
        :raises RuntimeError: If mapper not bound to max_api instance.
        """
        await self.send(
            method=ContactActionMethod(
                contact_id=contact_id,
                action="REMOVE",
            )
        )
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to max_api instance")
        self.max_api.users.pop(contact_id, None)
        return None

    async def import_contacts(self, contacts: list[ContactInfo]) -> list[Contact]:
        """Import contacts.

        :param contacts: Collection of contacts.
        :type contacts: list[ContactInfo]
        :returns: The resulting collection.
        :rtype: list[Contact]
        """
        response = await self.send(method=ImportContactsMethod(contact_list=contacts))

        mapped_contacts = ContactsContainsResponse(**response.payload).contacts

        users = [
            cast(Contact, translate_models(contact)) for contact in mapped_contacts
        ]
        return [self._cache_user(user) for user in users]

    async def get_chat_id(self, first_user_id: int, second_user_id: int) -> int:
        """Retrieve chat id.

        :param first_user_id: Identifier of the first user.
        :type first_user_id: int
        :param second_user_id: Identifier of the second user.
        :type second_user_id: int
        :returns: The resulting int value.
        :rtype: int
        """
        return first_user_id ^ second_user_id
