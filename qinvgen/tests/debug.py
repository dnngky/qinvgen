from typing import Callable, Optional


def debug(db_func: Optional[Callable]):
    """
    A decorator which replaces the decorated function with a debug function.

    :param Callable | None db_func: Debug function to replace the original
        function with. If None is given, the original function is kept.
    """
    def wrapper(func):
        if db_func is None:
            return lambda *args, **kwargs: func(*args, **kwargs)
        return lambda *args, **kwargs: db_func(*args, **kwargs)
    return wrapper
