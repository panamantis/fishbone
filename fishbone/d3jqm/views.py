import logging
import re
import urllib #For encoding
import urllib2
import datetime

from google.appengine.api import mail
from google.appengine.api import files,urlfetch # as given by GAE nov11
from google.appengine.ext import blobstore
from google.appengine.api import images

from django import http # For HttpResponse
from django.utils import simplejson
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.simple import direct_to_template

from beautifulsoup import BeautifulSoup



#http://localhost:8080/handler/debug_parser


class NestedDict(dict):
    def __getitem__(self, key):
        if key in self: return self.get(key)
        return self.setdefault(key, NestedDict())
    
    
        


def load_svg_card1(request,*args,**kwargs):
    ###############################################################
    var_django_view=""
    return direct_to_template(request, 'landingpage/page_svg_card1.html', {
                                                                     'var_django_view': var_django_view
                                                                     })
        
        
def main_index(request,*args,**kwargs):
    ###############################################################
    var_django_view=""
    return direct_to_template(request, 'df.html', {
                                                                     'var_django_view': var_django_view
                                                                     })
    
def main_fashion(request,*args,**kwargs):
    ###############################################################
    var_django_view=""
    return direct_to_template(request, 'fashion.html', {
                                                                     'var_django_view': var_django_view
                                                                     })
    
    
    
    