"""
Definition of urls for RedditShredderOauth.
"""

from datetime import datetime

import django.contrib.auth.views
from django.conf.urls import url

import app.views
from app.reddit_connection import reddit_schedule, reddit_connection

# Uncomment the next lines to enable the admin:
# from django.conf.urls import include
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    url(r'^$', app.views.home, name='home'),
    url(r'^signup/$', app.views.signup, name='signup'),
    url(r'^authorize_callback/$', app.views.authorize_callback,
        name='authorize_callback'),
    url(r'^reddit_api_json/$', reddit_connection.get_json_reddit,
        name='reddit_api_json'),
    url(r'^shredder/$', app.views.shredder, name='shredder'),
    url(r'^shredder/shred/$', app.views.shredder_output,
        name='shredder_output'),
    url(r'^shredder/run/$', reddit_connection.run_shredder, name='run_shredder'),
    url(r'^profile/$', app.views.profile, name='profile'),
    url(r'^profile/scheduler/$', reddit_schedule.change_schedule,
        name='scheduler'),
    url(r'^profile/privacy/$', app.views.privacy, name='privacy'),
    url(r'^profile/karma_limit/$', app.views.karma_exclude,
        name='karma_limit'),
    url(r'^profile/delete/$', app.views.delete, name='delete'),
    url(r'^profile/logs/$', app.views.logs, name='logs'),
    url(r'^profile/exclude/$', app.views.manual_exclude, name='exclude'),
    url(r'^profile/delete_account/$', app.views.delete_account,
        name='delete_account'),
    url(r'^changelog/$', app.views.changelog, name='changelog'),
    url(r'accounts/login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'login.html',
            'authentication_form': app.forms.BootstrapAuthenticationForm,
            'extra_context':
                {
                    'title': 'Log in',
                    'year': datetime.now().year,
                    'message': 'Please Login to Continue'
                }
        }),

    url(r'^login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'login.html',
            'authentication_form': app.forms.BootstrapAuthenticationForm,
            'extra_context':
                {
                    'title': 'Log in',
                    'year': datetime.now().year,
                }
        },
        name='login'),
    url(r'^login/signup/$', app.views.signup),
    url(r'^logout$',
        django.contrib.auth.views.logout,
        {
            'next_page': '/',
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
]
