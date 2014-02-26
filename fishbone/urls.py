from django.conf.urls.defaults import patterns, url,include
from django.views.generic.base import TemplateView

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='base.html'), name='homepage'),
    (r'handler/',include('email_processor.urls')),
    (r'^_ah/mail',include('email_processor.urls')),
)
