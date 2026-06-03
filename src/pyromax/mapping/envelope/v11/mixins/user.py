from collections.abc import Sequence, Coroutine, Callable
from typing import cast, Any

from .....models import BaseMaxObject
from .....protocol.envelope import Envelope
from ..payloads.shared import CamelCaseModel
from ..payloads.responses import GetContactResponse
from ..methods.immutable import GetGeneralInfoAboutMemberMethod
from ..translate.ToDTO import translate_models

from .MixinProtocol import MixinProtocol

class UserMixin(MixinProtocol):
    async def get_member_by_id(self, member_id: int | list[int]) -> Sequence[BaseMaxObject | CamelCaseModel]:
        contact_ids: list[int]
        if isinstance(member_id, int):
            contact_ids = [member_id]
        elif isinstance(member_id, list):
            contact_ids = member_id
        else:
            raise TypeError('member_id must be int or list[int]')

        response_envelope = await self.send(
            method=GetGeneralInfoAboutMemberMethod(
                contact_ids=contact_ids,
            )
        )

        response = GetContactResponse(
            **response_envelope.payload
        )


        contacts = [translate_models(mapping_contact) for mapping_contact in response.contacts]

        return cast(list[BaseMaxObject], contacts)
