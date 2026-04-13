from typing import cast, Literal

from ...payloads.models import MessageLinkMappingModel, MessageMappingModel
from ......models import Message


def reverse_translate_message(message: Message) -> MessageMappingModel | None:
    if not message:
        return None
    message_link = message.link
    if message.status not in ('USER', 'EDITED', 'REPLY'):
        status = 'USER'
    else:
        status = message.status
    if message_link:
        inner_message = message_link.message

        if inner_message is None:
            raise RuntimeError('In message link exists, but not bound to another message')

        return MessageMappingModel(
            id=str(message.message_id),
            status=cast(Literal['USER', 'EDITED', 'REPLY'], status),
            time=message.time,
            type=message.type,
            text=message.text,
            elements=message.elements,
            chat_id=message.chat_id,
            link=MessageLinkMappingModel(
                type=message_link.type,
                message=reverse_translate_message(inner_message),
            )
        )
    return MessageMappingModel(
        id=str(message.message_id),
        status=cast(Literal['USER', 'EDITED', 'REPLY'], status),
        time=message.time,
        type=message.type,
        text=message.text,
        elements=message.elements,
        chat_id=message.chat_id,
    )