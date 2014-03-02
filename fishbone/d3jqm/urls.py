from django.conf.urls.defaults import patterns, url,include
from django.views.generic.base import TemplateView

urlpatterns = patterns('d3jqm',
    (r'index', 'views.main_index'),
    (r'sorter', 'views.main_sorter'),
    (r'system', 'views.main_system'),
    (r'movement', 'views.main_movement'),
    (r'', 'views.main_sorter'),
)
