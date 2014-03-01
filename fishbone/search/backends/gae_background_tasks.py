import logging #JC
from django.conf import settings
from django.db import models
from google.appengine.ext import deferred
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

default_search_queue = getattr(settings, 'DEFAULT_SEARCH_QUEUE', 'default')

def update_relation_index(search_manager, parent_pk, delete):
    # JC NOTES:  This called when db updated (seen as deferred running task)
    # pass only the field / model names to the background task to transfer less
    # data
    
#    logging.info("jc9> update_relation_index!")
    app_label = search_manager.model._meta.app_label
    object_name = search_manager.model._meta.object_name
    deferred.defer(update, app_label, object_name, search_manager.name, parent_pk, delete, _queue=default_search_queue)

def update(app_label, object_name, manager_name, parent_pk, delete):
    model = models.get_model(app_label, object_name)
    try:
        manager = getattr(model, manager_name)
    except AttributeError:
        # AttributeError: type object 'conceptdb' has no attribute 'concepts1'
        # JC July 5, 2012
        # Deferred tasks not recognizing django search indexes so run autodiscover (which is in settings.py but not always there)
        from dbindexer import autodiscover
        autodiscover()
#        logging.warning("Likely couldn't find search index so ran autodiscover")
#        logging.info(str(model)) # <class 'concept.models.conceptdb'>
        logging.warning("Manually importing search index algorithms (concepts1 index thing)") 
#        app="dbindexes"
#        module_name="dbindexes"
#        import_module('%s.%s' % (app, module_name))
        app="concept"
        import_module("concept.search_indexes")
        app="tool"                          
        import_module("tool.search_indexes") # Was failing on jc-alg2 import on newly restarted tasks.
        
        manager = getattr(model, manager_name) # re-run
    manager.update_relation_index(parent_pk, delete)