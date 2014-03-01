import logging, email
from google.appengine.api import users
from google.appengine.ext import webapp 
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.ext.webapp.util import run_wsgi_app

from models import *
from util import *

def process_weight(received_text):
    entry = WeightEntry()
    entry.weight = float(received_text)
    return entry
    
def process_annotation(received_text):
    entry = FoodEntry()
    entry.content = received_text
    return entry

def get_recent_weight():
    result = db.GqlQuery("SELECT * FROM WeightEntry order by weight desc LIMIT 1").fetch(1)
    if (len(result) == 0):
        return None #ain't no weights yet!
    return result[0].weight

class LogSenderHandler(InboundMailHandler):
    def receive(self, email):
        attachments = get_attachments(email)
        if len(attachments) >= 1:
            #for filename, content in attachments:
            if len(attachments) > 1:
                logging.warn("recvd multiple email attachments, discarding all but first")
            
            filename, content = attachments[0]
            picentry = PicEntry()
            picentry.picture = content.decode() #EncodedPayload.decode()
            picentry.weight = get_recent_weight()
            picentry.author = None #get user from mail_message.sender
            picentry.put()

            #ignoring text portion, for example verizon adds junk to data-only mms
            #"This message was sent using the Picture and Video ..."
            return
            
        email_text = get_clean_body(email)
        logging.info('recvd email, text "%s"' % email_text)
        if len(email_text) > 0:
            if is_float_string(email_text):
                entry = process_weight(email_text)
            else:
                entry = process_annotation(email_text)
            
            #check for duplicate date entries?
            entry.author = None #get user from mail_message.sender
            entry.put()


def get_clean_body(email):
    bodies = email.bodies(content_type='text/plain') #generator
    
    allBodies = ""; numBodies=0
    for body in bodies:
        allBodies = allBodies + body[1].decode()
        numBodies += 1
        if isinstance(allBodies, unicode):
            allBodies = allBodies.encode('utf-8')
    
    
    if numBodies > 1: logging.warn("recvd mail with %s bodies: %s" % (numBodies, email))
    return allBodies

def get_attachments(email):
    attachments = []
    #if email.attachments: #AttributeError: 'InboundEmailMessage' object has no attribute 'attachments'
    if hasattr(email, 'attachments'):
        if isinstance(email.attachments[0], basestring):
            attachments = [email.attachments]
        else:
            attachments = email.attachments
    return attachments



application = webapp.WSGIApplication([LogSenderHandler.mapping()], debug=True)

def main():
   run_wsgi_app(application)
 
if __name__ == '__main__':
    main()

