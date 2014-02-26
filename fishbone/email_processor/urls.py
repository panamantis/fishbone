from django.conf.urls.defaults import patterns, url,include
from django.views.generic.base import TemplateView

urlpatterns = patterns('email_processor',
    (r'^/(?P<email_destination>hal@truthhost.appspotmail.com)', 'views.email_handler'),
    (r'^/(?P<email_destination>david@truthhost.appspotmail.com)', 'views.email_handler'),
    (r'^/(?P<email_destination>.*)', 'views.email_handler'),
    (r'debug_parser', 'views.debug_parser'),
    (r'debug_post', 'views.debug_post'),
)
