from pydantic import ConfigDict, BaseModel


def to_camel_case(snake_str: str) -> str:
    words = snake_str.split('_')
    camel_case = [words[0].lower()] + [word.capitalize() for word in words[1:]]
    return ''.join(camel_case)


CAMEL_CASE_CONFIG = ConfigDict(
        alias_generator=to_camel_case,
        validate_by_name=True,
    )


class CamelCaseModel(BaseModel):
    model_config = CAMEL_CASE_CONFIG

