from .base import BaseMethod, Envelope, Cmd, VERSION
from ...payloads.requests import (
    CreateCellForFileRequest,
    CreateCellForProfilePhotoRequest,
)


class GetUrlToUploadFileMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get url to upload file protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = self.args["type_of_file_opcode"]
        request.cmd = Cmd.REQUEST
        count = 1
        if "count" in self.args:
            count = int(self.args["count"])
        request.payload = CreateCellForFileRequest(
            count=count,
            uploader_type=self.args.get("uploader_type") or 0,
            type=self.args.get("upload_type") or 0,
        )
        request.ver = self.VERSION
        return request


class CreateCellForProfilePhotoMethod(GetUrlToUploadFileMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the create cell for profile photo protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request = await super().__call__(request)
        count = request.payload.count
        request.payload = CreateCellForProfilePhotoRequest(
            count=count,
            profile=self.args.get("profile") or True,
        ).model_dump(
            by_alias=True,
            exclude_none=True,
        )
        return request


class GetFileLinkMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get file link protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = self.args["opcode"]
        request.cmd = Cmd.REQUEST
        request.payload = self.args["file"].get_payload_to_get_link
        request.ver = self.VERSION
        return request


__all__ = [
    "GetUrlToUploadFileMethod",
    "GetFileLinkMethod",
    "CreateCellForProfilePhotoMethod",
]
