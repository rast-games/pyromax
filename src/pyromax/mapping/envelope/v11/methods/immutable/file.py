from .base import BaseMethod, Envelope, Cmd, VERSION
from ...payloads.requests import CreateCellForFileRequest


class GetUrlToUploadFileMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = self.args['type_of_file_opcode']
        request.cmd = Cmd.REQUEST
        count = 1
        if 'count' in self.args:
            count = int(self.args['count'])
        request.payload = CreateCellForFileRequest(
            count=count,
        )
        request.ver = VERSION
        return request


class GetFileLinkMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = self.args['opcode']
        request.cmd = Cmd.REQUEST
        request.payload = self.args['file'].get_payload_to_get_link
        request.ver = VERSION
        return request

__all__ = ['GetUrlToUploadFileMethod', 'GetFileLinkMethod']