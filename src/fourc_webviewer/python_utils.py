""" Module for python utils."""


def list_is_iterable(obj):
    """Check if object is iterable.

    Args:
        obj (obj): Object to be checked

    Returns:
        bool: True if object is iterable
    """
    try:
        iter(obj)
    except TypeError:
        return False
    return True
