import random


def get_random_string(length: int, chars: str) -> str:
    """
    Generate a random string of specified length using characters from the provided set.
    
    This function creates a random string by selecting characters randomly
    from the provided character set. Each character in the result is chosen
    independently and uniformly from the chars string.
    
    Args:
        length: The desired length of the random string
        chars: String containing the set of characters to choose from
        
    Returns:
        A random string of the specified length containing only characters from chars
    """
    random_string = ""
    for i in range(length):
        random_string += random.choice(chars)
    return random_string
