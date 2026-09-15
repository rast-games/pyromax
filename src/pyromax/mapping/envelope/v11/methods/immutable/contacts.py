from typing import cast

from .base import BaseMethod, Envelope, Cmd, Opcode, VERSION

from ...payloads.requests import (
    GetContactRequest,
    SearchByPhoneRequest,
    ContactActionRequest,
    ImportContactsRequest,
    ContactRequest,
)
from ......models import ContactInfo


class GetGeneralInfoAboutMemberMethod(BaseMethod):

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get general info about member protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.GET_CONTACT
        request.cmd = Cmd.REQUEST
        request.payload = GetContactRequest(
            contact_ids=self.args["contact_ids"],
        ).model_dump(by_alias=True, exclude_none=True)
        request.ver = VERSION

        return request


class SearchByPhoneMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the search by phone protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CONTACT_INFO_BY_PHONE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = SearchByPhoneRequest(
            phone=self.args["phone"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetSessionsMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get sessions protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SESSIONS_INFO
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = {}
        return request


class ContactActionMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the contact action protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CONTACT_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = ContactActionRequest(
            contact_id=self.args["contact_id"],
            action=self.args["action"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class ImportContactsMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the import contacts protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SYNC
        request.cmd = Cmd.REQUEST
        request.ver = VERSION

        contacts_list: list[ContactInfo] = []
        for c in self.args["contact_list"]:
            contact = cast(ContactInfo, c)
            contacts_list.append(contact)

        request.payload = ImportContactsRequest(
            contact_list={
                contact_info.phone: ContactRequest(
                    first_name=contact_info.first_name,
                    last_name=contact_info.last_name,
                )
                for contact_info in contacts_list
            },
        ).model_dump(by_alias=True, exclude_none=True)
        return request


__all__ = [
    "GetGeneralInfoAboutMemberMethod",
    "SearchByPhoneMethod",
    "GetSessionsMethod",
    "ContactActionMethod",
    "ImportContactsMethod",
]
