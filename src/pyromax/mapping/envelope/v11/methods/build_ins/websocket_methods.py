from __future__ import annotations
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Coroutine


from .base import LoginBuildInMappingMethod
from ......exceptions import MapperApiError
from ..immutable import GetUserDataMethod
from ...payloads.responses import ChoiceLoginVariantResponse


if TYPE_CHECKING:
    from ...Mapper import Mapper
    from ...payloads.responses import MetadataResponse


class WebSocketLoginBuildInMappingMethod(LoginBuildInMappingMethod):
    async def __call__(
            self,
            mapper: Mapper,
            *args: Any,
            metadata: MetadataResponse | None = None,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
            **kwargs: Any
    ) -> ChoiceLoginVariantResponse:
        if metadata is None:
            raise MapperApiError('Metadata not given for login')
        url = metadata.qr_link
        track_id = metadata.track_id
        await self._resolve_qr(
            mapper=mapper,
            url_callback=url_callback,
            metadata=metadata
        )
        response = await mapper.send_raw_with_running_wait(
            method=GetUserDataMethod(
                track_id=track_id
            ),
        )
        payload = response.payload
        user = ChoiceLoginVariantResponse(
            payload=payload,
        )
        return user
