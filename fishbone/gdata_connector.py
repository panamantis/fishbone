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

from gdata.auth import AuthSubToken
from gdata.service import lookup_scopes
from google.appengine.api import users, validation
from google.appengine.ext import webapp
from google.appengine.ext.bulkload import connector_interface, bulkloader_parser
from google.appengine.ext.webapp.util import run_wsgi_app
import atom.url
import gdata.alt.appengine
import gdata.spreadsheet.service
import logging
from django.utils import simplejson

port = os.environ.get('SERVER_PORT')
if port and port != '80':
    HOST_NAME = '%s:%s' % (os.environ.get('SERVER_NAME'), port)
else:
    HOST_NAME = os.environ.get('SERVER_NAME')

FEEDS = ['http://spreadsheets.google.com/feeds/', 
         'https://spreadsheets.google.com/feeds/',]

SPREADSHEET = 'GDataTest'
AUTHSUB_TOKEN = '1/JZabtFN1sZ85YK_bZJtr36oKgCHu_BL8GmD3RnBU7v8'

bulkloader_parser.ConnectorOptions.ATTRIBUTES.update({
    'token': validation.Optional(validation.TYPE_STR),
    'spreadsheet': validation.Optional(validation.TYPE_STR),
    'worksheet': validation.Optional(validation.TYPE_STR),
    'key_label': validation.Optional(validation.TYPE_STR),
})

class GDataAuthHandler(webapp.RequestHandler):
    
    def get(self):
        # make sure user is logged in and an admin user
        
        # look up the token for this user
        client = gdata.spreadsheet.service.SpreadsheetsService()
        gdata.alt.appengine.run_on_appengine(client)
        
        tokens = gdata.alt.appengine.load_auth_tokens()
        
        gdata_token = tokens.get(FEEDS[-1])
        
        next_url = atom.url.Url('http', HOST_NAME, path=self.request.path)

        if (not gdata_token):
            auth_token = gdata.auth.extract_auth_sub_token_from_url(self.request.url)
            if (auth_token and users.get_current_user()):
                gdata_token = client.upgrade_to_session_token(auth_token)
                
            if (gdata_token):
                client.token_store.add_token(gdata_token)

        # test that the token works.
        if (gdata_token):
            try:
                client.SetAuthSubToken(gdata_token)
                feed = client.GetSpreadsheetsFeed()
            except:
                # token is either invalid for spreadsheets, or been revoked.
                logging.exception('GetSpreadsheetsFeed failed')
                client.token_store.remove_all_tokens()
            else:
                # success - here's the token you should use.
                return self.response.out.write("""<html><body>
                token: %s
                </body></html>""" %gdata_token.get_token_string() )
            
        # Generate the AuthSub URL and write a page that includes the link
        return self.response.out.write("""<html><body>
            <a href="%s">Request token for the GData Spreadsheet Access</a>
            </body></html>""" % client.GenerateAuthSubURL(next_url,
                FEEDS, secure=False, session=True))

class WorksheetMissing(Exception):
    pass

class GDataConnector(connector_interface.ConnectorInterface):
    @staticmethod
    def get_spreadsheet_id(feed, name):
        for spreadsheet in feed.entry:
            if (spreadsheet.title.text == name):
                return spreadsheet.id.text.split('/')[-1]
                    
        return None

    @staticmethod
    def get_worksheet_dictionary(feed):
        output = {}
        
        for worksheet in feed.entry:
            output[worksheet.title.text] = worksheet.id.text.split('/')[-1]
        
        return output
    
    @staticmethod
    def get_key_dictionary(feed, key_label='key'):
        output = {}
        
        for row in feed.entry:
            key = row.custom.get(key_label)
            if (not key): continue
            output[key.text] = row
        
        return output

    @staticmethod
    def get_neutral_rows(feed):
        output = []
        
        for row in feed.entry:
            dictionary = {}
            for k,v in row.custom.items():
                dictionary[k] = v.text
            
            output.append(dictionary)
        
        return output
            
    def __init__(self, options, name='unknown'):
        self.kind_name = name
        self.token_string = options.get('token', AUTHSUB_TOKEN)
        self.spreadsheet_name = options.get('spreadsheet', SPREADSHEET)
        self.worksheet_name = options.get('worksheet', name)
        self.key_label = options.get('key_label','key')
       
    def setup_client(self, spreadsheet):
        try:
            from google.appengine.api import apiproxy_stub_map
            from google.appengine.api import urlfetch_stub
            apiproxy_stub_map.apiproxy.RegisterStub('urlfetch', urlfetch_stub.URLFetchServiceStub())
        except:
            pass
                
        self.spreadsheet = spreadsheet
        
        self.client = gdata.spreadsheet.service.SpreadsheetsService()
        gdata.alt.appengine.run_on_appengine(self.client, store_tokens=False)
        
        self.token = AuthSubToken()
        self.token.set_token_string(self.token_string)
        self.token.scopes = lookup_scopes(self.client.service)
        self.client.current_token = self.token
        self.feed = self.client.GetSpreadsheetsFeed()
        self.id = GDataConnector.get_spreadsheet_id(self.feed, spreadsheet)
        self.worksheets = GDataConnector.get_worksheet_dictionary(self.client.GetWorksheetsFeed(self.id))
                
    def generate_import_record(self, filename, bulkload_state):        
        if (not hasattr(self, 'client')):
            self.setup_client(self.spreadsheet_name)
                
        worksheet = self.worksheets.get(self.worksheet_name)
        if (worksheet is None):
            raise WorksheetMissing('There is no worksheet to import for %s' % self.kind_name) #if the sheet doesn't exist raise an exception
        
        # get every row
        feed = self.client.GetListFeed(self.id, worksheet)
        rows = self.get_neutral_rows(feed)
        
        # yield each row as a dictionary
        for row in rows:
            yield row
            
    def initialize_export(self, filename, bulkload_state):
        if (self.spreadsheet_name):
            SPREADSHEET = self.spreadsheet_name
        
        if (hasattr(self, 'client')):
            return
        
        self.setup_client(SPREADSHEET)
        
        worksheet = self.worksheets.get(self.worksheet_name)
        
        if (worksheet != None):
            feed = self.client.GetListFeed(self.id, worksheet)
            self.key_dictionary = self.get_key_dictionary(feed, self.key_label)
        else:
            self.key_dictionary = {}     
              
    def write_dict(self, dictionary):
        # find out which model we are writing
        # open/create that worksheet
        # make sure the worksheet has the header row
                
        worksheet = self.worksheets.get(self.worksheet_name)
        if (worksheet is None):
            entry = self.client.AddWorksheet(self.worksheet_name, 2, len(dictionary), self.id)
            
            self.worksheets[self.worksheet_name] = worksheet = entry.id.text.split('/')[-1]
            
            i = 1
            # FIXME: painfully slow. Could be improved with a batch submit
            for key in dictionary.keys():                
                entry = self.client.UpdateCell(row=1, col=i, inputValue=key, key=self.id, wksht_id=worksheet)                
                i += 1
                                                        
        row = self.key_dictionary.get(dictionary.get(self.key_label,''))
        
        # we know we've found the exact row
        if (row):
            # FIXME: could skip the update if the feed.entry is the same as the dictionary for all key/values
            entry = self.client.UpdateRow(row, dictionary)
        else:
            entry = self.client.InsertRow(dictionary, self.id, worksheet)
                
    def finalize_export(self):
        # don't think I need to do anything?
        pass

application = webapp.WSGIApplication([('/.*', GDataAuthHandler)], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

