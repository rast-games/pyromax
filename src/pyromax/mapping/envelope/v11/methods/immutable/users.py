from .base import BaseMethod, Envelope, Cmd, Opcode, VERSION
from ...payloads.requests import GetContactRequest



class GetGeneralInfoAboutMemberMethod(BaseMethod):

    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.GET_CONTACT
        request.cmd = Cmd.REQUEST
        request.payload = GetContactRequest(
            contact_ids=self.args['contact_ids'],
        ).model_dump(by_alias=True)
        request.ver = VERSION

        return request