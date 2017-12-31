"""
Basic logger, used by the logging decorator.
"""
import logging


def create_logger():
    """
    Creates a logging object and returns it
    """
    logger = logging.getLogger("shredder_logger")
    logger.setLevel(logging.INFO)

    # create the logging file handler
    fh = logging.FileHandler(
        "/var/www/redditshredder.joshharkema.com/reddit_connection.log")

    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    fh.setFormatter(formatter)

    # add handler to logger object
    logger.addHandler(fh)
    return logger


logger = create_logger()
