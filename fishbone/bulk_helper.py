# Copyright (c) 2010, Calvin Rien
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys

from google.appengine.api import datastore, datastore_types
from google.appengine.ext import db
import base64
from django.utils import simplejson

def key_to_reverse_str(value):
    '''
    this is a handy way to encode/decode a key so that it is still
    human readable, but contains all info (including parents)
    '''
    if (not value):
        return ''
    elif isinstance(value, datastore.Key):
        value = value.to_path()
        value.reverse()

    for i in range(len(value)):
        if isinstance(value[i], long):
            value[i] = '%s*'%value[i]
                    
    return ':'.join(value)

def reverse_str_to_key(value):
    '''
    this is a handy way to encode/decode a key so that it is still
    human readable, but contains all info (including parents)
    '''
    if (value == '' or value == None):
        return None
    
    decoded_value = value.split(':')
    decoded_value.reverse()
    
    for i in range(len(decoded_value)):
        if decoded_value[i].endswith('*'):
            decoded_value[i] = long(decoded_value[i].rstrip('*'))
        
    return datastore.Key.from_path(*decoded_value)

def key_to_b64(value):
    '''
    encodes/decodes a key to/from urlsafe base64
    '''
    if isinstance(value, datastore.Key):
        value = value.to_path()  
    
    return base64.urlsafe_b64encode(simplejson.dumps(value, separators=(',', ':')))

def b64_to_key(value):
    '''
    encodes/decodes a key to/from urlsafe base64
    '''
    # NOTE: urlsafe_b64decode doesn't like unicode
    decoded_value = simplejson.loads(base64.urlsafe_b64decode(str(value)))
    
    if (not decoded_value):
        return None
    
    return datastore.Key.from_path(*decoded_value)

def list_to_json(transformer):
    '''
    takes a string property, applies 'transformer'
    to all elements and then JSON encodes the result
    handy for the 'class' field of Polymodels
    
    - property: class
      external_name: class
      export_transform: bulk_helper.list_to_json(str)
      import_transform: bulk_helper.json_to_list(str)
        
    @param transformer:
    '''
    def list_to_json_lambda(value):
        if value is None:
            return ''
    
        output = []
        for element in value:
            output.append(transformer(element))

        return simplejson.dumps(output, separators=(',', ':'))
    
    return list_to_json_lambda

def json_to_list(transformer):
    def json_to_list_lambda(value):
        if value is None or value is '':
            return None

        decoded_value = simplejson.loads(value)
        
        output = []
        for element in decoded_value:
            output.append(transformer(element))

        return output
    
    return json_to_list_lambda
    

