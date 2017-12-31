"""
Basic exception handler.
"""


def exception(logger):
    """
    A decorator that wraps the passed in function and logs
    exceptions should one occur

    :param logger: The logging object.
    """

    def decorator(func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            # log the exception, a catchall is okay in this instance.
            except:
                err = "There was an exception in  "
                err += func.__name__
                logger.exception(err)

            # re-raise the exception
            raise Exception

        return wrapper

    return decorator
