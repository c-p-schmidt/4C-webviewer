def list_is_iterable(obj):
    try:
        iter(obj)
    except Exception:
        return False
    else:
        return True
