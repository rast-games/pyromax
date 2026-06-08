from pydantic import ConfigDict

from ..core.MaxApiContextController import ContextController



class BaseMaxObject(ContextController):
    model_config = ConfigDict(
        validate_by_name=True
    )
