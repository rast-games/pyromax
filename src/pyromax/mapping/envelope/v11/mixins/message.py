from __future__ import annotations
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Coroutine
import time
import asyncio

from ..payloads.models import BaseFileMappingModel, MessageMappingModel
from .....protocol.envelope import Envelope
from ..constants import DEFAULT_BACKOFF_CONFIG
from .....utils import clean_and_map, Backoff
from ..methods.immutable import SendMessageMethod
from .....exceptions import SendMessageFileError, SendMessageNotFoundError, SendMessageError, BackoffError
from ..payloads.responses import SendMessageResponse


if TYPE_CHECKING:
    from .....models import MessageLink

class MessageMixin:
    send: Callable[..., Coroutine[Any, Any, Envelope]]
    _logger: logging.Logger


    async def send_message( # type: ignore[override]
            self,
            chat_id: int,
            text: str | None = None,
            attaches: Sequence[BaseFileMappingModel] | None = None,
            link: MessageLink | None = None,
    ) -> MessageMappingModel | None:
        original_attaches = attaches
        if not attaches:
            attaches = []
        attachments = []
        for attach in attaches:
            if hasattr(attach, 'is_attach') and attach.is_attach:
                attachments.extend(attach.to_payload)
        backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
        text, elements = clean_and_map(
            text if text else '',
            [
                'STRONG', 'EMPHASIZED', 'UNDERLINE', 'STRIKETHROUGH', 'QUOTE', 'LINK'
            ]
        )
        try:
            response = await self.send(
                method=SendMessageMethod(
                    chat_id=chat_id,
                    text=text,
                    cid=-round(time.time() * 1000),
                    attaches=attachments,
                    elements=elements,
                    link=link,
                ),
            )

            try:
                while error_if_exist := response.model_dump().get('payload', {}).get('error'):
                    error_message = response.model_dump().get('payload', {}).get('message')
                    title = response.model_dump().get('payload', {}).get('title')
                    match error_if_exist:
                        case 'attachment.not.ready':
                            response = await self.send(
                                method=SendMessageMethod(
                                    chat_id=chat_id,
                                    text=text,
                                    cid=-round(time.time() * 1000),
                                    attaches=attachments,
                                    elements=elements,
                                    link=link,
                                ),
                            )
                            await backoff.asleep()
                            continue
                        case 'proto.payload':
                            raise SendMessageFileError(
                                f'''
                                title: {title},
                                error: {error_if_exist},
                                message: {error_message}
                                '''
                            )
                        case 'not.found':
                            raise SendMessageNotFoundError(
                                f'''
                                title: {title},
                                error: {error_if_exist},
                                message: {error_message}
                                '''
                            )
                        case _:
                            raise SendMessageError(
                                f'''
                                title: {title},
                                error: {error_if_exist},
                                message: {error_message}
                                '''
                            )
            except BackoffError:
                raise SendMessageError('Max attempts to send message exceeded')
            response_parsed = SendMessageResponse(
                **response.payload
            )
            for attach in response_parsed.message.attaches:
                attach.message_id = response_parsed.message.id
                attach.chat_id = response_parsed.chat_id
                attach.uploaded = True
            for i, attach in enumerate(original_attaches or []):
                if hasattr(attach, 'is_attach') and attach.is_attach and hasattr(attach, 'is_downloadable') and attach.is_downloadable:
                    recv_attach = response_parsed.message.attaches[i]
                    for attr, value in recv_attach.__dict__.items():
                        setattr(attach, attr, value)
            return response_parsed.message

        except (asyncio.CancelledError, self.protocol.transport.BASE_EXCEPTION_FOR_TRANSPORT) as e:
            self._logger.error('Error sending message: %s', e)
            return None

