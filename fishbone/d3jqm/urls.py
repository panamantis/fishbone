from django.conf.urls.defaults import patterns, url,include
from django.views.generic.base import TemplateView

urlpatterns = patterns('d3jqm',
    (r'index', 'views.main_index'),
    (r'fashion', 'views.main_fashion'),
)
