#import search
import os
import logging
import re
from functions.categories import Formatter

DEVELOPMENT_PORT=os.environ.get('SERVER_PORT')
SERVER_PORT=os.environ.get('SERVER_PORT')
SERVER_NAME=os.environ.get('SERVER_NAME')
    
if (SERVER_PORT) and (not str(SERVER_PORT)=="80"): 
    SITE_NAME="http://"+str(SERVER_NAME)+":"+str(SERVER_PORT)
else: 
    SITE_NAME="http://"+str(SERVER_NAME)
    
logging.info("[SITE_NAME]: "+str(SITE_NAME))

if re.search('http://192',SITE_NAME):
    THE_SERVER="autoscale"
elif re.search('http://127',SITE_NAME):
    THE_SERVER="local"
else:
    THE_SERVER="gae"

try:
    from djangoappengine.settings_base import *
    has_djangoappengine = True
except ImportError:
    has_djangoappengine = False
    DEBUG = True
    TEMPLATE_DEBUG = DEBUG

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings' # JC APRIL

MEDIA_DEV_MODE=False
MEDIA_BUNDLES = (
    ( 'main.css',
        'search/search.css',
    ),
    ('main.js',
    ),
    ('mobile.js',
    ),
)

# cache.manifest
OFFLINE_MANIFEST = {
    '/js/cache.manifest2': {
        'cache': (
            r'mobile\.js',
        ),
    },
}
SECRET_KEY = '=r-$b*8hglm+858&9t043hlm6-&6-3d3vfc4((7yd0dbrakhvi'
TIME_ZONE = 'America/New_York'

INSTALLED_APPS = (
    'simplejson',
    'autoload',
    'beautifulsoup',
    'mediagenerator',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'djangotoolbox',
    'search',
    'd3jqm',
    'dashy-db',
)

if has_djangoappengine:
    INSTALLED_APPS = ('djangoappengine',) + INSTALLED_APPS

TEST_RUNNER = 'djangotoolbox.test.CapturingTestSuiteRunner'
ADMIN_MEDIA_PREFIX = '/media/admin'
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'static') #absolute path to media
MEDIA_URL='/static/' #JC Same ad admin media 
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),
                 os.path.join(os.path.dirname(__file__), 'landingpage/templates'),
                 os.path.join(os.path.dirname(__file__), 'lander/templates'),
                 os.path.join(os.path.dirname(__file__), 'search1/templates'),
                 os.path.join(os.path.dirname(__file__), 'xmarks/templates'),
                 os.path.join(os.path.dirname(__file__), 'subscription/templates'),
                 os.path.join(os.path.dirname(__file__), 'os1/templates'),
                 os.path.join(os.path.dirname(__file__), 'jadmin/templates'),
                 os.path.join(os.path.dirname(__file__), 'tadmin/templates'),
                 '/static/css',)

ROOT_URLCONF = 'urls'
SEARCH_BACKEND = 'search.backends.gae_background_tasks' #hopefully indexes my database.

class IgnoreCsrfMiddleware(object):
    def process_request(self, request):
        request.csrf_processing_done = True

if THE_SERVER=="autoscale":
    MIDDLEWARE_CLASSES = (
        'autoload.middleware.AutoloadMiddleware',
    #?appscale error?    'mediagenerator.middleware.MediaMiddleware',
        'dbindexer.middleware.DBIndexerMiddleware',
    #?appscale error?    'settings.IgnoreCsrfMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'google.appengine.ext.appstats.recording.AppStatsDjangoMiddleware'
        )
else:
    MIDDLEWARE_CLASSES = (
        'mediagenerator.middleware.MediaMiddleware', #It's important that the middleware is the very first middleware in the list. Otherwise media files won't be cached correctly on the development server.
        'autoload.middleware.AutoloadMiddleware',
        'dbindexer.middleware.DBIndexerMiddleware',
        'settings.IgnoreCsrfMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'google.appengine.ext.appstats.recording.AppStatsDjangoMiddleware'
        )
    
# put the yuicompressor into the parent folder of the project
YUICOMPRESSOR_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'yuicompressor.jar')

# Compresses your JavaScript and CSS files via YUICompressor
ROOT_MEDIA_FILTERS = {
#Feb 9, 2014    'js': 'mediagenerator.filters.yuicompressor.YUICompressor',
    'css': 'mediagenerator.filters.yuicompressor.YUICompressor',
}

# A boolean which defines whether we're on the development or production server.
# If True media files aren't combined and compressed in order to simplify debugging.
MEDIA_DEV_MODE = True#True # false for production

DEV_MEDIA_URL = '/devmedia/'
PRODUCTION_MEDIA_URL = '/media/'

GLOBAL_MEDIA_DIRS = (
    os.path.join(os.path.dirname(__file__), 'static'),
)

# Function directory
GLOBAL_FUNCTION_DIRS = (
    os.path.join(os.path.dirname(__file__), 'functions'),
)

ADMIN_MEDIA_PREFIX = '/media/admin/'
SITE_ID = 1

DBINDEXER_SITECONF = 'dbindexes' #dbindex obviously.
# Activate django-dbindexer if available
try:
    import dbindexer
    DATABASES = {
    'default': {
        'ENGINE': 'dbindexer',
        'TARGET': 'gae',
        'HIGH_REPLICATION': True, 
        'DEV_APPSERVER_OPTIONS': { 
                        'high_replication' : True, 
                        'use_sqlite': True, 
                        } 
    },
    'gae': {
        'ENGINE': 'djangoappengine.db',
        'HIGH_REPLICATION': True,
        'DEV_APPSERVER_OPTIONS': { 
                        'high_replication' : True, 
                        'use_sqlite': True, 
                        } 
    },
    }

    INSTALLED_APPS += ('dbindexer',)
except ImportError:
    pass

DATABASES['native'] = { 
                'ENGINE': 'djangoappengine.db', 
                'HIGH_REPLICATION': False, 
                'DEV_APPSERVER_OPTIONS': { 
                        'high_replication' : False, 
                        'use_sqlite': False, 
                        } 
                } 

CACHE_MIDDLEWARE_SECONDS=60*60 # 60x60=1hr
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'TIMEOUT': CACHE_MIDDLEWARE_SECONDS,
    }
}

ROOT_URLCONF = 'urls'
AUTOLOAD_SITECONF = 'indexes'  # Autoload INSTALLED_APPS
from dbindexer import autodiscover
autodiscover()
SEARCH_BACKEND = 'search.backends.gae_background_tasks' #hopefully indexes my database.


FILE_UPLOAD_MAX_MEMORY_SIZE = 33554432 #JC Nov 29, 2011 # djangoappengine: 1024 * 1024 #Django: 2621440

EMAIL_USE_TLS = True ## Controls whether a secure connection is used. 
EMAIL_HOST = "smtp.gmail.com"  #auth -- works with jon.clement email (And hal)
temp_email='see_global_settings'

DEFAULT_FROM_EMAIL = temp_email
SERVER_EMAIL = temp_email
EMAIL_HOST_USER = temp_email
EMAIL_HOST_PASSWORD = ""

EMAIL_PORT = "587"
formatter = logging.Formatter("[%(levelname)s] %(filename)s.%(lineno)d]\t %(message)s")
logging.getLogger().handlers[0].setFormatter(formatter)
STATIC_URL = '/static/'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
)