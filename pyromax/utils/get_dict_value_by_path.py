# Python imports
from __future__ import annotations
from typing import Any

# Local imports
from .not_found_flag import NotFoundFlag


def get_dict_value_by_path(path: str, data: dict[str, Any]) -> dict[str, Any] | NotFoundFlag | None:
    """
    Navigate through a nested dictionary using a space-separated path and return the value.

    This function traverses a dictionary structure by following a path of keys
    separated by spaces. If all keys in the path exist, the final value is returned.
    If any key in the path is missing, NotFoundFlag is returned.

    Args:
        path: Space-separated string of keys representing the path to navigate
              (e.g., "payload other_directory last_dir")
        data: Dictionary to search in

    Returns:
        The value found at the end of the path, or NotFoundFlag() if the path doesn't exist
        :rtype: dict[str, Any] | NotFoundFlag | None
    """
    layers = path.split()
    current = data
    for layer in layers:
        if not isinstance(current, dict) or layer not in current:
            return NotFoundFlag()
        current = current[layer]
    return current


def has_dict_path(path: str, data: dict[str, Any]) -> bool:
    """
    Check if a path exists in a nested dictionary.

    This function checks whether all keys in a space-separated path exist
    in the provided dictionary structure.

    Args:
        path: Space-separated string of keys representing the path to check
        data: Dictionary to search in

    Returns:
        True if the path exists in the dictionary, False otherwise
    """
    result = get_dict_value_by_path(path, data)
    return not (result == NotFoundFlag)


if __name__ == '__main__':
    test_data = {
        'payload': {
            'other_directory': {
                'last_dir': True
            },
            'another_directory': {
            }
        },
        'idk': 'state'
    }
    result = get_dict_value_by_path('payload other_directory last_dr', test_data)
    print(result)
    if result:
        print('work')