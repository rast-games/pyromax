from __future__ import annotations


from pydantic import ConfigDict

from .base import BaseMaxObject
from ..protocol.bases.request_response import Response


class ErrorEvent(BaseMaxObject):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    update: BaseMaxObject | Response
    """Received update"""
    exception: Exception
    """Exception"""