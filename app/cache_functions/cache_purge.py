"""
Function to purge the cache via cron.
"""

from django.core.cache import cache

from app.logger.exception_decor import exception
from app.logger.exception_logger import logger


@exception(logger)
def purge():
    cache.clear()
