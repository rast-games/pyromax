from pydantic import ConfigDict

from src.pyromax.core.MaxApiContextController import ContextController



class BaseMaxObject(ContextController):
    model_config = ConfigDict(
        validate_by_name=True
    )
