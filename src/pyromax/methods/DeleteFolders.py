from typing import cast

from .Base import BaseMaxApiMethod
from ..models.Folder import FolderUpdate


class DeleteFoldersMethod(BaseMaxApiMethod[FolderUpdate]):
    async def __call__(
        self,
        folder_ids: list[str],
    ) -> FolderUpdate:
        """Execute the delete folders MAX API method.

        :param folder_ids: Identifiers of the folders.
        :type folder_ids: list[str]
        :returns: The resulting FolderUpdate value.
        :rtype: FolderUpdate
        :raises RuntimeError: If deleteFolders method not bound to MaxApi instance.
        """
        if not self._max_api:
            raise RuntimeError("DeleteFolders method not bound to MaxApi instance")

        return cast(
            FolderUpdate,
            await self._max_api.mapper.call_method(
                type(self),
                folder_ids=folder_ids,
            ),
        )
