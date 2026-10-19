from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RawUpdateMode(StrEnum):
    """Control which protocol responses reach update outer middlewares."""

    TRANSLATED_ONLY = "translated_only"
    ALL_RESPONSES = "all_responses"


@dataclass(frozen=True, slots=True)
class UpdateTranslationFailure:
    """Translation failure exposed to raw update middlewares through data."""

    exception: Exception
