"""
WSGI config for Reddit_Shredder project.
It exposes the WSGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os
import sys

sys.path.append('/var/www/redditshredder.joshharkema.com')
sys.path.append('/var/www/redditshredder.joshharkema.com/Reddit_Shredder')

os.environ["DJANGO_SETTINGS_MODULE"] = "Reddit_Shredder.settings"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()