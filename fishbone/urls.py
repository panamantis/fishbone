from django.conf.urls.defaults import patterns, url,include
from django.views.generic.base import TemplateView

urlpatterns = patterns('',
    url(r'^$', include('d3jqm.urls')),
    (r'handler/',include('email_processor.urls')),
    (r'd3jqm/',include('d3jqm.urls')),
    (r'^_ah/mail',include('email_processor.urls')),
)

#    url(r'^$', TemplateView.as_view(template_name='base.html'), name='homepage'),