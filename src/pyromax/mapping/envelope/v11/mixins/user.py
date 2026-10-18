import uuid
from typing import cast, Any

from .....models import (
    PhotoAttachment,
    Profile,
    FolderUpdate,
    FolderList,
    PrivacySettings,
)
from ..payloads.responses import (
    ResponseWithUrl,
    ProfileContainsResponse,
    CloseAllSessionsResponse,
    ConfigHashContainsResponse,
)
from ..methods.immutable import (
    CreateCellForProfilePhotoMethod,
    ChangeProfileMethod,
    CreateFolderMethod,
    GetFoldersMethod,
    UpdateFolderMethod,
    DeleteFoldersMethod,
    CloseAllSessionsMethod,
    LogoutMethod,
    ChangeProfileSettingsMethod,
)
from ..payloads.models import (
    PhotoMappingModel,
    FolderUpdateMappingModel,
    FolderListMappingModel,
)
from ..translate.ToDTO import (
    translate_models,
    upload_file,
)
from ..constants import Opcode
from ..translate.FromDTO import reverse_translate_privacy_settings

from .MixinProtocol import MixinProtocol


class UserMixin(MixinProtocol):
    async def _create_cell_for_profile_photo(
        self,
        count: int = 1,
        profile: bool = True,
    ) -> dict[str, Any]:
        """Create cell for profile photo.

        :param count: Maximum number of items to retrieve.
        :type count: int
        :param profile: The profile value.
        :type profile: bool
        :returns: The resulting dict[str, Any] value.
        :rtype: dict[str, Any]
        """
        response = await self.send(
            method=CreateCellForProfilePhotoMethod(
                type_of_file_opcode=Opcode.CREATE_PHOTO,
                count=count,
                profile=profile,
            )
        )

        payload = ResponseWithUrl(**response.payload).model_dump(exclude_none=True)

        return payload

    async def upload_profile_photo(
        self,
        data: bytes | None,
        count: int = 1,
        file_name: str | None = None,
        uploaded: bool = False,
        **kwargs: Any,
    ) -> list[PhotoMappingModel]:
        """Upload profile photo.

        :param data: Contextual data passed through the processing pipeline.
        :type data: bytes | None
        :param count: Maximum number of items to retrieve.
        :type count: int
        :param file_name: The file name value.
        :type file_name: str | None
        :param uploaded: The uploaded value.
        :type uploaded: bool
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting collection.
        :rtype: list[PhotoMappingModel]
        """
        payload = {}
        if not uploaded:
            payload = await self._create_cell_for_profile_photo(
                count=count,
                profile=True,
            )

        uploaded_file = await upload_file(
            data=data,
            typeof=PhotoAttachment,
            file_name=file_name,
            uploaded=uploaded,
            **payload,
            **kwargs,
        )

        return cast(list[PhotoMappingModel], uploaded_file)

    async def change_profile(
        self,
        first_name: str,
        last_name: str | None = None,
        description: str | None = None,
        photo: bytes | None = None,
        file_name: str | None = None,
        photo_token: str | None = None,
    ) -> Profile:
        """Change profile.

        :param first_name: The first name value.
        :type first_name: str
        :param last_name: The last name value.
        :type last_name: str | None
        :param description: The description value.
        :type description: str | None
        :param photo: The photo value.
        :type photo: bytes | None
        :param file_name: The file name value.
        :type file_name: str | None
        :param photo_token: The photo token value.
        :type photo_token: str | None
        :returns: The resulting Profile value.
        :rtype: Profile
        :raises RuntimeError: If max_api not bounded to mapper.
        """
        if self.max_api is None:
            raise RuntimeError("max_api not bounded to mapper")

        if photo is not None:
            if photo_token:
                self._logger.warning(
                    "photo_token argument was provided but will be overridden by "
                    "the uploaded photo token"
                )
            attach = await self.upload_profile_photo(
                data=photo,
                file_name=file_name,
            )
            photo_token = attach[0].photo_token
        response = await self.send(
            method=ChangeProfileMethod(
                first_name=first_name,
                last_name=last_name,
                description=description,
                photo_token=photo_token,
            )
        )

        mapped_profile = ProfileContainsResponse(**response.payload)

        profile = self.bind_api_instance(
            cast(Profile, translate_models(mapped_profile))
        )
        self.max_api.me = profile
        self.max_api.users[profile.contact.id] = profile.contact
        return profile

    async def create_folder(
        self,
        title: str,
        chat_include: list[int],
        filters: list[Any] | None = None,
        folder_id: str | None = None,
    ) -> FolderUpdate:
        """Create folder.

        :param title: The title value.
        :type title: str
        :param chat_include: Collection of chat include.
        :type chat_include: list[int]
        :param filters: Collection of filters.
        :type filters: list[Any] | None
        :param folder_id: Identifier of the folder.
        :type folder_id: str | None
        :returns: The resulting FolderUpdate value.
        :rtype: FolderUpdate
        """
        self._logger.info("creating folder")

        response = await self.send(
            method=CreateFolderMethod(
                id=folder_id or str(uuid.uuid4()),
                title=title,
                include=chat_include,
                filters=filters or [],
            )
        )

        folder_update_mapped = FolderUpdateMappingModel(**response.payload)
        folder_update = cast(FolderUpdate, translate_models(folder_update_mapped))
        return self.bind_api_instance(folder_update)

    async def get_folders(self, folder_sync: int = 0) -> FolderList:
        """Retrieve folders.

        :param folder_sync: The folder sync value.
        :type folder_sync: int
        :returns: The resulting FolderList value.
        :rtype: FolderList
        """
        self._logger.info("fetching folders")
        response = await self.send(
            method=GetFoldersMethod(
                folder_sync=folder_sync,
            )
        )
        mapped_folder_list = FolderListMappingModel(**response.payload)
        folder_list = cast(FolderList, translate_models(mapped_folder_list))
        return self.bind_api_instance(folder_list)

    async def update_folder(
        self,
        folder_id: str,
        title: str,
        chat_include: list[int] | None = None,
        filters: list[Any] | None = None,
        options: list[Any] | None = None,
    ) -> FolderUpdate:
        """Update folder.

        :param folder_id: Identifier of the folder.
        :type folder_id: str
        :param title: The title value.
        :type title: str
        :param chat_include: Collection of chat include.
        :type chat_include: list[int] | None
        :param filters: Collection of filters.
        :type filters: list[Any] | None
        :param options: Collection of options.
        :type options: list[Any] | None
        :returns: The resulting FolderUpdate value.
        :rtype: FolderUpdate
        """
        self._logger.info("updating folder")
        response = await self.send(
            method=UpdateFolderMethod(
                id=folder_id,
                title=title,
                include=chat_include or [],
                filters=filters or [],
                options=options or [],
            )
        )
        folder_update_mapped = FolderUpdateMappingModel(**response.payload)
        folder_update = cast(FolderUpdate, translate_models(folder_update_mapped))
        return self.bind_api_instance(folder_update)

    async def delete_folders(self, folder_ids: list[str]) -> FolderUpdate:
        """Delete folders.

        :param folder_ids: Identifiers of the folders.
        :type folder_ids: list[str]
        :returns: The resulting FolderUpdate value.
        :rtype: FolderUpdate
        """
        response = await self.send(
            method=DeleteFoldersMethod(
                folder_ids=folder_ids,
            )
        )
        folder_update_mapped = FolderUpdateMappingModel(**response.payload)
        folder_update = cast(FolderUpdate, translate_models(folder_update_mapped))
        return self.bind_api_instance(folder_update)

    async def close_all_sessions(self) -> bool:
        """Close all sessions.

        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        :raises RuntimeError: If mapper not bound to max_api instance.
        """
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to max_api instance")

        self._logger.info("closing all other sessions")

        response = await self.send(method=CloseAllSessionsMethod())

        token = CloseAllSessionsResponse(**response.payload).token

        if token is None:
            self._logger.warning(
                "no token received after closing sessions, skipping token update"
            )
            return False

        self.token = token
        self.max_api.token = token
        return True

    async def logout(self) -> None:
        """Logout.
        """
        self._logger.info("logout")
        await self.send(method=LogoutMethod())
        return None

    async def set_presence(self, online: bool) -> None:
        """Set presence.

        :param online: The online value.
        :type online: bool
        """
        self._logger.info("setting presence to %s", "online" if online else "offline")
        self.keep_alive_interactive = online

    async def change_profile_settings(self, privacy_settings: PrivacySettings) -> None:

        """Change profile settings.

        :param privacy_settings: PrivacySettings instance to process.
        :type privacy_settings: PrivacySettings
        :raises ValueError: If server not send a config hash.
        """
        mapped_privacy_settings = reverse_translate_privacy_settings(privacy_settings)

        response = await self.send(
            method=ChangeProfileSettingsMethod(
                user=mapped_privacy_settings,
            )
        )
        config_hash = ConfigHashContainsResponse(**response.payload).config_hash
        if config_hash is None:
            raise ValueError("Server not send a config hash")
        return None
