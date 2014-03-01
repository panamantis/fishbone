from django.conf.urls.defaults import *

# JC:  Add urls.py branch to deal with JSON / DATA / API requests.  Clean things up.
# Notes:
#  Allow for endings in / or "" where possible
#
urlpatterns = patterns('v1',
    (r'api/(?P<toptype>topic)/(?P<topic_id>\d+)/(?P<type>stories)/', include('json.gettopic.urls')),
    (r'api/(?P<toptype>topic)/(?P<topic_id>\d+)/(?P<type>subtopics)/', include('json.gettopic.urls')),
    (r'api/(?P<toptype>topic)/(?P<topic_id>\d+)', include('json.gettopic.urls')),
    (r'api/(?P<toptype>story)/', include('json.getuser.urls')),
    (r'api/(?P<toptype>topic)/', include('topic.urls')),
    (r'location$', include('json.location.urls')),
    (r'location/$', include('json.location.urls'))
)
