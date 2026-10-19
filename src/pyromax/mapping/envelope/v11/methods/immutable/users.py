from uuid import uuid4

from .base import BaseMethod, Envelope, Cmd, Opcode, VERSION
from ...payloads.requests import (
    ChangeProfileRequest,
    CreateFolderRequest,
    GetFoldersRequest,
    UpdateFolderRequest,
    DeleteFoldersRequest,
    ChangeProfileSettingsRequest,
)
from ...payloads.models import ChangeProfileSettingsMappingModel


class ChangeProfileMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the change profile protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.PROFILE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = ChangeProfileRequest(
            first_name=self.args["first_name"],
            last_name=self.args.get("last_name"),
            description=self.args.get("description"),
            photo_token=self.args.get("photo_token"),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class CreateFolderMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the create folder protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.FOLDERS_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = CreateFolderRequest(
            id=self.args.get("id") or str(uuid4()),
            title=self.args["title"],
            include=self.args["include"],
            filters=self.args.get("filters") or [],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetFoldersMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get folders protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.FOLDERS_GET
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = GetFoldersRequest(
            folder_sync=self.args["folder_sync"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class UpdateFolderMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the update folder protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.FOLDERS_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = UpdateFolderRequest(
            id=self.args["id"],
            title=self.args["title"],
            include=self.args.get("include") or [],
            filters=self.args.get("filters") or [],
            options=self.args.get("options") or [],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class DeleteFoldersMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the delete folders protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.FOLDERS_DELETE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = DeleteFoldersRequest(
            folder_ids=self.args["folder_ids"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class CloseAllSessionsMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the close all sessions protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SESSIONS_CLOSE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = {}
        return request


class LogoutMethod(CloseAllSessionsMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the logout protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request = await super().__call__(request)
        request.opcode = Opcode.LOGOUT
        return request


class ChangeProfileSettingsMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the change profile settings protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CONFIG
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = ChangeProfileSettingsRequest(
            settings=ChangeProfileSettingsMappingModel(
                user=self.args["user"],
            )
        ).model_dump(by_alias=True, exclude_none=True)
        return request


__all__ = [
    "ChangeProfileMethod",
    "CreateFolderMethod",
    "GetFoldersMethod",
    "UpdateFolderMethod",
    "DeleteFoldersMethod",
    "CloseAllSessionsMethod",
    "LogoutMethod",
    "ChangeProfileSettingsMethod",
]
