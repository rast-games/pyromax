from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Coroutine


import qrcode


from ..immutable import TrackLoginMethod
from ...payloads.responses import TrackLoginResponse


if TYPE_CHECKING:
    from ...Mapper import Mapper
    from ......utils import Backoff
    from ...payloads.responses import ChoiceLoginVariantResponse, MetadataResponse


class BaseBuildInMappingMethod(ABC):
    @abstractmethod
    async def __call__(self, mapper: Mapper, *args, **kwargs) -> Any: pass


class LoginBuildInMappingMethod(BaseBuildInMappingMethod):
    async def __call__(
            self,
            mapper: Mapper,
            *args,
            login_backoff: Backoff | None = None,
            **kwargs
    ) -> ChoiceLoginVariantResponse: pass

    @staticmethod
    async def _track_login(
            mapper: Mapper,
            track_id: str,
            polling_interval: int | float,
    ) -> None:

        not_logged = True
        while not_logged:
            await asyncio.sleep(polling_interval)

            response = await mapper.send_raw_with_running_wait(
                method=TrackLoginMethod(
                    track_id=track_id
                ),
                # return_exception=True
            )

            track_data = TrackLoginResponse(
                **response.payload
            )

            if track_data is None:
                raise RuntimeError('Track login failed.')

            if track_data.status is None:
                raise RuntimeError("Track status is missing in response")


            if track_data.status and track_data.status.expires_at < time.time() or track_data.error or track_data.error_message or track_data.localized_message:
                msg = '''
                Time for login expired
                    '''
                raise TimeoutError(msg)


            if track_data.status.login_available:
                not_logged = False

    async def _resolve_qr(
            self,
            mapper: Mapper,
            metadata: MetadataResponse,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,

    ):

        if not url_callback:
            async def url_callback(url: str) -> None:
                """
                Creating a QR code scanned by max. It is displayed immediately in the console

                Args:
                    url - authorization url

                """

                qr = qrcode.QRCode()
                qr.add_data(url)

                qr.make(fit=True)
                qr.print_ascii(invert=True)

        url = metadata.qr_link
        track_id = metadata.track_id
        await url_callback(url)

        await self._track_login(
            mapper=mapper,
            polling_interval=metadata.polling_interval,
            track_id=track_id,
        )


