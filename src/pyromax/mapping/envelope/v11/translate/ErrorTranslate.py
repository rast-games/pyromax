from __future__ import annotations

from .....exceptions import MapperApiError, UnsupportedClientVersionMapperError
from ..constants import ErrorCode
from ..payloads.responses import ErrorMessageResponse


def translate_error_response(
    error: ErrorMessageResponse,
    *,
    app_version: str | None = None,
) -> MapperApiError:
    """Translate an Envelope V11 error payload into a public mapper error."""
    error_message = f"""
    error: {error.error},
    title: {error.title},
    localized_message: {error.localized_message},
    message: {error.error_message}

    """

    if error.error == ErrorCode.UNSUPPORTED_CLIENT_VERSION:
        translated_error: MapperApiError = UnsupportedClientVersionMapperError(
            error_message,
            app_version=app_version,
        )
    else:
        translated_error = MapperApiError(error_message)

    translated_error.title = error.title
    translated_error.localized_message = error.localized_message
    translated_error.message = error.error_message
    translated_error.error = error.error
    return translated_error
