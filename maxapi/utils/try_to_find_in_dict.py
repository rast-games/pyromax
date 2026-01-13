from .NotFoundFlag import NotFoundFlag

def try_to_find_in_dict_and_return(path: str, data: dict):
    layers = path.split()
    for layer in layers:
        if layer not in data:
            break
        data = data[layer]
    else:
        return data
    return NotFoundFlag()

def try_to_find_in_dict(path: str, data: dict):
    return not (try_to_find_in_dict_and_return(path, data) == NotFoundFlag)


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
    result = try_to_find_in_dict_and_return('payload other_directory last_dr', test_data)
    print(result)
    if result:
        print('work')