from typing import TypeVar

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import BaseMaxObject
    from ...protocol import Response

Update = TypeVar('Update', bound='BaseMaxObject | Response')