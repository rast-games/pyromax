import random

def get_random_string(length, chars):
    random_string = ''
    for i in range(length):
        random_string += random.choice(chars)
    return random_string
