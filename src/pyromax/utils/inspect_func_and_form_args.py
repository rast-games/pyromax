import inspect
from typing import Any, Callable, TypeVar

from ..exceptions import AnnotationError

T = TypeVar('T')

def inspect_and_form(func: Callable[..., Any], data: dict[type[T], T], raise_if_not_annotated: bool = False) -> dict[str, Any]:
    signature = inspect.signature(func)
    data_str_keys: dict[str, T] = {str(key.__name__): value for key, value in data.items()}
    args_and_annotation = [(param.name, param.annotation) for param in signature.parameters.values()]
    args: dict[str, Any] = {}
    for name, annotation in args_and_annotation:
        if annotation in data:
            args.update(
                {
                    name: data[annotation],
                }
            )
        elif annotation in data_str_keys:
            args.update(
                {
                    name: data_str_keys[annotation],
                }
            )
        else:
            if raise_if_not_annotated and annotation == inspect.Parameter.empty:
                raise AnnotationError(''' Need annotate all params''')
            args.update(
                {
                    name: None
                }
            )

    return args