from pydantic import BaseModel, ConfigDict


class BaseMaxObject(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True
    )
