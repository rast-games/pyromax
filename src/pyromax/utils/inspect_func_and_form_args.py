import inspect
from typing import Any, Callable, TypeVar

from ..exceptions import AnnotationError

T = TypeVar("T")


def inspect_and_form(
    func: Callable[..., Any],
    data: dict[type[T], T],
    strict: bool = True,
) -> dict[str, Any]:
    """Inspect and form.

    :param func: Callable to invoke.
    :type func: Callable[..., Any]
    :param data: Contextual data passed through the processing pipeline.
    :type data: dict[type[T], T]
    :param raise_if_not_annotated: The raise if not annotated value.
    :type raise_if_not_annotated: bool
    :returns: The resulting dict[str, Any] value.
    :rtype: dict[str, Any]
    :raises AnnotationError: If  Need annotate all params.
    """
    signature = inspect.signature(func)
    data_str_keys: dict[str, T] = {
        str(key.__name__) if not isinstance(key, str) else key: value
        for key, value in data.items()
    }
    args_and_annotation = [
        (param.name, param.annotation) for param in signature.parameters.values()
    ]
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
            if strict and annotation == inspect.Parameter.empty:
                raise AnnotationError(""" Need annotate all params""")
            if strict:
                raise AnnotationError("""Annotation object not exits in workflow""")
            args.update({name: None})

    return args
