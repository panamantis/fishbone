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

from beautifulsoup import BeautifulSoup


class NestedDict(dict):
    def __getitem__(self, key):
        if key in self: return self.get(key)
        return self.setdefault(key, NestedDict())
    

@csrf_exempt    
def email_handler(request,*args,**kwargs):
    logging.info("Hello test")
    the_message=False

    if request.POST:
        # STEP 1:  PROCESS EMAIL FIELDS
        #############################
        the_email_destination = kwargs.pop('email_destination', None) # Posted email address to URL
        try:
            the_message = mail.InboundEmailMessage(request.raw_post_data)        
        except:
            logging.warning("Could not decode raw_post_data")
            try:
                the_message = mail.InboundEmailMessage(request.raw_post_data.encode('ascii','ignore')) #Patch Oct 17, 2012
            except:
                logging.warning("Catch email decode message")
                the_message = unicode(request.raw_post_data, errors='ignore') #0v3
        
        try:
            the_message.sender=the_message.sender.encode('ascii','ignore') # utf-8 bug# str(message.sender)
        except:
            logging.warning("Email message arrived without sender!! Set to 'unknown'")

    if the_message:
        logging.info("Received a message from: " + str(the_message.sender))
        logging.info("Subject: " + str(the_message.subject))
        logging.info("To: (none-listed) " + str(the_message.to)) # to is a comma-seperated list of the message's primary recipients
        logging.info("Email handler destination: " + str(the_email_destination))

	#Normalize message content (for txt and html)
	#############################
	decoded_html=False
	txtmsg=''

        plaintext = the_message.bodies(content_type='text/plain')
        for text in plaintext:
            txtmsg = ""
            
            txtmsg = text[1].decode()
	    txtmsg=txtmsg.encode('ascii','ignore')
            logging.info("Body is %s" % txtmsg)

        html_bodies = the_message.bodies('text/html')
        for content_type, body in html_bodies:
            decoded_html = body.decode()
	    decoded_html=decoded_html.encode('ascii','ignore')


	if decoded_html:
	    the_number=get_phone_number(decoded_html)
	else:
	    the_number=get_phone_number(txtmsg)
	
	#Extract entire records (update2)
	the_dat=extract_record(txtmsg,decoded_html)

	logging.info("Decoded number: "+str(the_number))

	# Post email contents
	post_email_items(the_message.sender,the_number,the_message.subject,the_dat)

    return http.HttpResponse('ok')


def post_email_items(the_email,the_phone,the_subject,the_dat):
    logging.info("Posting to spreadsheet")

    the_record={}

    the_record['email']=the_email
    the_record['phone']=the_phone
    the_record['subject']=the_subject
    for key in the_dat:
        the_record[key]=the_dat[key]

    out_json=simplejson.dumps(the_record)
    postjson(out_json)
    return



def postjson(the_json):
    base_url = "https://script.google.com/macros/s/AKfycbzKZHCYJD4YMaWn2QK5aWBW0vNm5pFvtojIYYS_gQA69DZX7cU/exec"
    #data = simplejson.dumps([1, 2, 3])
    #    req = urllib2.Request(base_url, {'Content-Type': 'application/json'})
    data=the_json

    logging.info("POSTING TO: "+str(base_url))
    logging.info("DATA: "+str(data))
#    req = urllib2.Request(base_url, data)
    req = urllib2.Request(base_url, data,{'Content-Type': 'application/json'})
    response=""

    try:
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()
	logging.info("Data posted correctly")
    except:
	logging.info("[warning] Silenced on url POST")


    logging.info("GOT POST RESPONSE: "+str(response))

    return


def debug_post(request,*args,**kwargs):
    # JC Jan 22, 2014 - initial setup
    #/handler/debug/post
    #Write line to google spreadsheet

    # Do standard json data post
    out_json={}
    out_dict=NestedDict()
    nodes=[]
    node_dict=NestedDict()
    cnode=0
    node_dict[cnode]['Name1 field']="Name1 value"
#unused    cnode+=1
#unused    node_dict[cnode]['Name2 field']="Name2 value"

    #Wrap
    #out_dict['results']=nodes
    #out_json=simplejson.dumps(out_dict)

    out_json=simplejson.dumps(node_dict[0]) #Dump first record only

    postjson(out_json)

    return http.HttpResponse('ok')



def get_phone_number(the_content):

    phone_re = re.compile(r'''
                # don't match beginning of string, number can start anywhere
    (\d{3})     # area code is 3 digits (e.g. '800')
    \D*         # optional separator is any number of non-digits
    (\d{3})     # trunk is 3 digits (e.g. '555')
    \D*         # optional separator
    (\d{4})     # rest of number is 4 digits (e.g. '1212')
    \D*         # optional separator
    (\d*)       # extension is optional and can be any number of digits
    $		# EXPECT END!
    ''', re.VERBOSE)

    #For more broad search, allow endings
    phone_re2 = re.compile(r'''
                # don't match beginning of string, number can start anywhere
    (\d{3})     # area code is 3 digits (e.g. '800')
    \D*         # optional separator is any number of non-digits
    (\d{3})     # trunk is 3 digits (e.g. '555')
    \D*         # optional separator
    (\d{4})     # rest of number is 4 digits (e.g. '1212')
    \D*         # optional separator
    (\d*)       # extension is optional and can be any number of digits
    ''', re.VERBOSE)

    soup=BeautifulSoup.BeautifulSoup(the_content)
    the_number=""
    for row in soup.findAll('tr'): #For each row
        #Logic 1:  If row has text 'phone' AND phone number format then grab number
        if re.search('phone',str(row),re.IGNORECASE):
    	    m=phone_re.search(str(row))
	    if m:
	        try: the_number=m.group(1)+"-"+m.group(2)+"-"+m.group(3)
	        except: logging.warning("Could not pull out phone number from: "+str(row))

    if not the_number: #If not found, grab from raw text
        m=phone_re2.search(str(the_content))
        logging.info("NOPE: "+str(the_content))
        if m:
            try: the_number=m.group(1)+"-"+m.group(2)+"-"+m.group(3)
            except: logging.warning("Could not pull out phone number from: "+str(row))
    logging.debug("Found phone number: "+str(the_number)+"]")

    return the_number


def debug_parser(request,*args,**kwargs):
    output_array=[]
    output_array.append("Debug Email Parser<br>")

    sample_templates=load_sample_templates()

    short_sample="""
        <tr>
            <td><strong>Daytime Phone:</strong></td>
            <td><a href=3D"tel:919-261-7549" value=3D"+19192617549" target= =3D"_blank">919-261-7549</a></td>
        </tr>
    """
    #D# sample_templates.append(short_sample)
    
    phone_re = re.compile(r'''
                # don't match beginning of string, number can start anywhere
    (\d{3})     # area code is 3 digits (e.g. '800')
    \D*         # optional separator is any number of non-digits
    (\d{3})     # trunk is 3 digits (e.g. '555')
    \D*         # optional separator
    (\d{4})     # rest of number is 4 digits (e.g. '1212')
    \D*         # optional separator
    (\d*)       # extension is optional and can be any number of digits
    ''', re.VERBOSE)

    c=0
    for template in sample_templates:
        the_number=""
	the_number=get_phone_number(template)
        output_array.append(str(c)+") Phone number: ["+str(the_number)+"]")
	logging.debug("Found phone number: "+str(the_number)+"]")
        output_array.append("                              <br>")
	extract_record(template,template)
	c+=1

    return http.HttpResponse(output_array)


# Update:  Request to pull out complete record detail
# - do on a per-template basis
#Time Received
#Source
#Name
#Phone 1
#Phone 2
#Email
#Address
#Addtl info
#Comments

def extract_record(text,html):
    # Extract record information based on type of template


    dat={}
    dat['Time Received']=""
    dat['Source']=""
    dat['Name']=""
    dat['Phone 1']=""
    dat['Phone 2']=""
    dat['Email']=""
    dat['Address']=""
    dat['Addtl info']=""
    dat['Comments']=""

    template_type=""

    #1.  Discover type of message
    c=0

    if (re.search('Contact this prospect now',text,re.IGNORECASE)):
        template_type='sample4'
    elif (re.search('careinhomes',text,re.IGNORECASE)):
        template_type='sample3'
    elif (re.search('homeadvisor',text,re.IGNORECASE)):
        template_type='sample2'
    elif (re.search('caring.com',text,re.IGNORECASE)):
        template_type='sample1'

    #2.  Pull out records
    the_search_zip=""
    the_search_city=""
    if template_type=='sample2':
	dat['Source']="HomeAdvisor"
	text2=text
	the_split=text.split('*')
	for node in the_split:
	    if node=='Customer Name:': dat['Name']=the_split[c+1]
	    if node=='Daytime Phone:': dat['Phone 1']=the_split[c+1]
	    if node=='Email:': dat['Email']=the_split[c+1]
	    if node=='Address:': dat['Address']=the_split[c+1]
            c+=1
	#Grab Addtl info
	#m=re.search('.*Service Description(.*)http.*',text)
	text2=re.sub(r'>','',text2)
	text2=re.sub(r'\n','',text2)
	m=re.search('.*Service Description (.*)<.*',text2)
	if (m):
	    temp=m.group(1)
	    temp=re.sub('<.*','',temp)
	    temp=re.sub('  ',' ',temp)
	    dat['Addtl info']=temp

    elif template_type=='sample3':
	dat['Source']="CareInHomes"
	the_split=text.splitlines()
	for line in the_split:
	    logging.info(">>>>>>>>>>" +str(line))
	    if (re.search('Full name',line):
	        line=re.sub(r'*','',line)
	        line=re.sub(r'*','',line)
	        m=re.search('Full name: (.*)',line)
        	if m:
		    dat['Name']=m.group(1)

	    m=re.search('Phone: (.*)',line)
	    if m:  dat['Phone 1']=m.group(1)

#old	    m=re.search('Address: (.*)',line)
#old	    if m:  dat['Address']=m.group(1)

	    m=re.search('Email: (.*)',line)
	    if m:  dat['Email']=m.group(1)

	    m=re.search('Search Zip: (.*)',line)
	    if m:  the_search_zip=m.group(1)

	    m=re.search('Search City: (.*)',line)
	    if m:  the_search_city=m.group(1)

            the_search_state=False
	    m=re.search('Search State: (.*)',line)
	    if m:  the_search_state=m.group(1)

	    if the_search_state:
	        dat['Address']=the_search_city+", "+the_search_state+", "+the_search_zip

	    #Addtl info
	    #includes "Relationship to care recipient: Parent" "Care Recipient Age", and a few more fields. 
	    m=re.search('.*(Relationship to care recipient):. (.*)',line)
	    if m: dat['Addtl info']=dat['Addtl info']+m.group(1)+": "+m.group(2)+", "
	    m=re.search('.*(Care Recipient .*):. (.*)',line)
	    if m: dat['Addtl info']=dat['Addtl info']+m.group(1)+": "+m.group(2)+", "
	    m=re.search('.*(Estimated Level .*):. (.*)',line)
	    if m: dat['Addtl info']=dat['Addtl info']+m.group(1)+": "+m.group(2)+", "
	    m=re.search('.*(CareInHomes ID): (.*)',line)
	    if m: dat['Addtl info']=dat['Addtl info']+m.group(1)+": "+m.group(2)+", "

            c+=1

    elif template_type=='sample1':
        soup=BeautifulSoup.BeautifulSoup(html)
	dat['Source']="Caring.com"
        for row in soup.findAll('tr'): #For each row
            #Logic 1:  If row has text 'phone' AND phone number format then grab number
	    c=0
	    found=''
            for field in row.findAll('td'): #For each row
		if found and c==1:
		    dat[found]=field.text #Grab one after
		    found=''
		if (field.text=='Phone Number:'): found="Phone 1"
		if (field.text=='Name:'): found="Name"
		if (field.text=='E-mail Address:'): found="Email"
		if (field.text=='Looking for Care in:'): found="Address"
		c+=1
    elif template_type=='sample4':
        soup=BeautifulSoup.BeautifulSoup(html)
	dat['Source']="Caring.com_new"
        for row in soup.findAll('tr'): #For each row
	    row=str(row)
	    row=re.sub(r'\n','',row)
	    row=re.sub(r'br /','br',row)
            #Logic 1:  If row has text 'phone' AND phone number format then grab number
	    c=0
	    found=''
#D	    logging.info("----------------------------GOT NAME: >1 "+row)
            the_split=row.split('<br>')
	    if (re.search('strong.*Name:.*strong',row)):
       	        for field in the_split:

	            m=re.search('Relationship.*Searching For:.*>(.*)',str(field))
		    if (m):
		    	dat['Addtl info']=m.group(1)
			logging.info("GOT extra info: >"+str(m.group(1)))

	            m=re.search('Name:.*>(.*)',str(field))
		    if (m):
		    	dat['Name']=m.group(1)
			logging.info("GOT NAME: >"+str(m.group(1)))
	            m=re.search('Phone Number.*:.*>(.*)</a.*',str(field))
		    if (m): 
			dat['Phone 1']=m.group(1)
			logging.info("PHONE GOT: >"+str(m.group(1)))
	            m=re.search('E-mail Address.*>(.*)</a.*',str(field))
		    "mailto:jennifermakeda@yahoo.com"
		    if (m): 
	                dat['Email']= m.group(1)
			dat['Email']=re.sub(r'=','',dat['Email'])

	    elif (re.search('strong.*Looking for Care.*strong',row)):
       	        for field in the_split:
		    #m=re.search('.*ooking.*(.*).*',str(field))
		    m=re.search('.*strong>(.*)<.*<.*',str(field)) #<strong>Looking for Care in:</strong>10567</td></tr>
		    if (m):
		    	dat['Address']=m.group(1)
			logging.info("Address: >"+str(m.group(1)))
	       
#            for field in row.findAll('td'): #For each row
#		logging.info("-----:::: "+str(field))
#		if found and c==1:
#		    dat[found]=field.text #Grab one after
#		    found=''
#		if (field.text=='Phone Number:'): found="Phone 1"
#		if (field.text=='Name:'): found="Name"
#		if (field.text=='E-mail Address:'): found="Email"
#		if (field.text=='Looking for Care in:'): found="Address"
#		c+=1
    else:
	logging.error("ERROR:  Unknown type give text blob: "+str(text))

    for key in dat:
        if not dat[key]=='':
	    #Generic clean up
	    dat[key]=re.sub(r'> ','',dat[key])
	    dat[key]=re.sub(r'\n','',dat[key])
	    dat[key]=re.sub(r'^\\r','',dat[key]) #random bad character
	    dat[key] = dat[key].strip()   #remove whitespace
            logging.info("KEY: "+key+" gives: "+dat[key])

    the_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    dat['Time Received']=the_date


#        for line in text.splitlines(True):   # ('\n'):
#	    logging.info(">>>>>>> "+line)

    return dat



def store_attachments(request,message):
    # Handle attachments
    #######################################
    blob_keys=[]
    my_attachment_ids=[]
    if hasattr(message, 'attachments'):
        for file_name, filecontents in message.attachments:
            # STEP 1: DECODE ATTACHMENT CONTENT
            if filecontents.encoding and filecontents.encoding.lower() != '7bit':
                try:
                    payload = filecontents.payload.decode(filecontents.encoding)
                except LookupError:
                    logging.error('Unknown decoding %s.' % filecontents.encoding)
                except (Exception), e:
                    logging.error('Could not decode payload: %s' % e)
            else:
                payload = filecontents.payload
            logging.info("Working with attachment named: "+str(file_name))
            
            # Deal with mimetype
            blob_content_type, encoding = mimetypes.guess_type(file_name)
            if not blob_content_type: 
                logging.warning("No type found for attachment: "+str(file_name))
                blob_content_type='application/octet-stream'
            logging.info("contenttype: "+str(blob_content_type))
            
            # STEP 2: Store contents into new blobstore
            file_blob = files.blobstore.create(mime_type=blob_content_type, _blobinfo_uploaded_filename=file_name)
            with files.open(file_blob, 'a') as f: # Open files for writing
                f.write(payload)
            files.finalize(file_blob) # Finalize the file. Do this before attempting to read it.
            blob_key = files.blobstore.get_blob_key(file_blob) # Get the file's blob key
            blob_keys.append(blob_key)

    return blob_keys


             

def load_sample_templates():
    sample_templates=[]


    sample4="""

<td>
<table cellspacing=3D"0" style=3D"margin-left:auto;margin-right:auto;border=
:1px solid #a4b847" width=3D"600">
<tbody><tr>
<td style=3D"padding:5px;font-family:helvetica;background-color:#8ba319;col=
or:white">
<img src=3D"http://dir.caring.com/images/lead_notifiers/icon-newlead.png" s=
tyle=3D"float:left;margin-right:15px"><div style=3D"margin-top:15px">
<h1 style=3D"font-weight:500;font-size:30px">
Contact this prospect now!
</h1>
</div>
</td>
</tr>
<tr>
<td style=3D"padding:15px;padding-top:25px;font-family:helvetica;background=
-color:#fcffec">
<h2 style=3D"font-size:20px;font-weight:normal">
Remember to add Jennifer Williams to your tracking system and credit Caring=
.com as the source.
</h2>
</td>
</tr>
<tr>
<td style=3D"padding:15px;font-family:helvetica;font-size:15px;font-weight:=
100;background-color:#fcffec">
Let&#39;s work together to find the perfect senior living solution for Jenn=
ifer Williams!
</td>
</tr>
<tr>

<td style=3D"padding-top:10px">
<table style=3D"font-size:12px;font-family:helvetica;margin-left:auto;margi=
n-right:auto" width=3D"600"><tbody><tr>
<td>
<table cellspacing=3D"0" style=3D"border:1px solid #a1a1a1;margin-right:5px=
" width=3D"295">
<tbody><tr>
<td style=3D"color:white;background-color:#8aa318;padding:10px">
Contact Information
</td>
</tr>
<tr>
<td height=3D"250" style=3D"padding:10px;font-size:12px;line-height:20px;ve=
rtical-align:top">
<strong>
Name:
</strong>
Jennifer Williams
<br><strong>
Relationship / Searching For:
</strong>

Friend(s)
<br><strong>
Phone Number:
</strong>

<a href=3D"tel:%28917%29%20482-4874" value=3D"+19174824874" target=3D"_blan=
k">(917) 482-4874</a>
<br><strong>
E-mail Address:
</strong>

<a href=3D"mailto:jennifermakeda@yahoo.com" target=3D"_blank">jennifermaked=
a@yahoo.com</a>
<br><strong>
Caring.com Reference #:
</strong>

905073
</td>
</tr>
</tbody></table>
</td>
<td>
<table cellspacing=3D"0" style=3D"border:1px solid #a1a1a1;margin-right:5px=
" width=3D"295">
<tbody><tr>
<td style=3D"color:white;background-color:#8aa318;padding:10px">
Care Recipient Information
</td>
</tr>
<tr>
<td height=3D"250" style=3D"padding:10px;font-size:12px;line-height:20px;ve=
rtical-align:top">
<strong>
Community:
</strong>
Care Guardian
<br><strong>
Seeking:
</strong>

In-Home Care
<br><strong>
Looking for Care in:
</strong>

10567
</td>
</tr>
</tbody></table>
</td>
</tr></tbody></table>
</td>
</tr>
<tr>
<td style=3D"padding-top:10px">
<table style=3D"font-size:12px;font-family:helvetica;margin-left:auto;margi=
n-right:auto" width=3D"600"><tbody><tr>
<td>
</td>
<td>
</td>
</tr></tbody></table>
</td>
</tr>
<tr>
<td style=3D"padding-top:10px">
<table style=3D"margin-left:auto;margin-right:auto" width=3D"600"><tbody><t=
r style=3D"background-color:#fcffec">
<td>
<p style=3D"border:1px solid ffc109;background-color:#fed96b;padding:15px;f=
ont-size:12px;font-family:helvetica;line-height:20px">
<strong>
Note:
</strong>
Remember to add jennifer williams to your tracking system and credit Caring=
.com as the source.
</p>
</td>
</tr></tbody></table>
</td>

"""

    sample3="""

 Referral from CareInHomes

For Care Guardian

To request a credit for an invalid referral, please login to your account
at portal.careinhomes.com<http://email.careinhomes.com/wf/click?upn=3DtEO-2=
FGAZlOA2FbdncTozANcjo-2FPJwoYFFq9PAzUYf7qxDM4GeS365v1VhJ8Kpl024OeNCRwCtwWFW=
X9dMYOg8AfVE6t9fiZ0YyjWabYCLbSF2PQ1f43Pit3EDc-2FfiXOlXBRyFXGge7ruQmRe2LBHBG=
Q-3D-3D_aQIKMZdMso013X8MWWxT0LJrAMuICoszpLS4PqsVNEWSmkWGGY0-2FqIz-2BJ-2F-2B=
ZxoxTJlKcBZQAdcIcF9KBKN6AkjGqmiTWWaW3EDmN1rEbXDdEgZRJY061v-2Bie8DaWNHN8PB3-=
2Fse2NXrUn-2BM54F2hZKWUCcauEeFfSIwBptbe4i999-2B2zZzA-2BDCUG9Eh6jszNzaEJHk5b=
VFMwV1ix9wv3pTmxezl4mLh7DT9q22-2BIXVHnZxsYsxOxml5tUs8NjdWHG>,
and click on the "referrals" tab.

*Full name:* Harry Diament
Phone: 914-965-5167
Email: hdiament3@aol.com

*Location Where Care is Needed:*
Search Zip: 10458
Search City: Bronx
Search State: NY

*Contact Info:*
Address: 63 Rumsey Rd
City: Yonkers
State: NY
Zip: 10705

*Relationship to care recipient:* Parent
*Care Recipient Age:* 78
*Care Recipient Gender:* F
*Estimated Level of Care Required:* Less than 10 hours/week

CareInHomes ID: 43371

"""

    sample2="""
> Don't miss an important email. Add NewLead@pro-lead.HomeAdvisor.com to
> your address book.
>    [image: My Seniore Care Guide]
> <http://pro.homeadvisor.com/servlet/RedirectServlet?D=3DHOMEm=3Dsmcommtem=
ps&template_id=3D112&todo_id=3D1220898960&entityID=3D26320675&entityHash=3D=
26320675_14219208ba2c2f5fa9e1fb9abdd5932a&entry_point_id=3D15727939>
>
>
> Dear David Muson,
>
> You've been matched to a *Senior Companion Care* Lead!
>
>  Customer Information  *Customer Name:* Eileen Joyce  *Contact Time:* Any
> Phone - Anytime  *Daytime Phone:* 516-567-7616  *Email:*
> lesabre60@excite.com  *Address:* None, fLORAL pARK, NY 11001   * Click
> here to set an appointment
> <http://pro.homeadvisor.com/servlet/RedirectServlet?D=3DSTATIC&targetPage=
=3D/servlet/LeadManagementServlet&requestedPage=3DemailAppt&context=3Dactiv=
ity&subContext=3Dsend_email&srOID=3D53675506&entityID=3D26320675&entityHash=
=3D26320675_14219208ba2c2f5fa9e1fb9abdd5932a&consEntityID=3D39932078&entry_=
point_id=3D345802&templateID=3D112&todo_id=3D1220898960&template_id=3D112>
> *
>  Job Information  *Description:* Senior Companion Care  *Job Number:*
> 53675506
>  Service Description       What is the first name of the care recipient?:
> ..
>   Who needs care?:  Parent
>   Gender::  Male
>   Age Range::  71 - 90 years old
>   Living situation::  Home (lives alone)
>   Are you looking for any of the basic care listed below?:  Yes - care
> recipient needs the basic care services selected below.
> Meal prep
> Medication reminders
>   Personal services:  Yes
> Bathing
> Dressing/grooming
>   Transportation needed:  No
>   Care type::  Visiting care
>   Are you looking for any of the additional services listed below?:  No -
> additional care services are not required.
>   Receptiveness::  Very receptive
>   Ambulation::  Independent
>   Expected funding:  Private
> Long-term care insurance
>   *Comments:*  Fther is just out of hospital 82yo Paying caSH THEN TO BE
> REINMURSED
>
>
> <http://pro.homeadvisor.com/rfs/smpros/mobileAppDownload.jsp?todo_id=3D12=
20898960&template_id=3D112&entityID=3D26320675&spEntityID=3D26320675&entity=
Hash=3D26320675_14219208ba2c2f5fa9e1fb9abdd5932a&entry_point_id=3D15480243>
>
>  Are you creating a positive initial impression with your HomeAdvisor
> profile? *Click here to review profile*<http://pro.homeadvisor.com/profil=
e/?m=3Dservicemagic&entityID=3D26320675&entityHash=3D26320675_14219208ba2c2=
f5fa9e1fb9abdd5932a&todo_id=3D1220898960&template_id=3D112&entry_point_id=
=3D12531>
>
> Remember, for your benefit, HomeAdvisor will encourage this customer to
> review your performance. Your Rating & Review scores create 'online
> word-of-mouth' to set you apart from your competition!
>
> Thank you for being a part of the HomeAdvisor network. We appreciate your
> business.
>
> HomeAdvisor
> (877) 947-3639
> ProCustomerCare@homeadvisor.com <+ProCustomerCare@homeadvisor.com>
>
> Have you added the HomeAdvisor Seal of Approval to your website? It build=
s
> trust with homeowners that you?re a screened and approved member of our
> network. It?s also quick and easy to add ? and FREE to HomeAdvisor member=
s! Add
> the Seal of Approval today!<https://pro.homeadvisor.com/articles/seal-of-=
approval/seal-download/?entry_point_id=3D27352682&template_id=3D112&todo_id=
=3D1220898960&entityID=3D26320675&entityHash=3D26320675_14219208ba2c2f5fa9e=
1fb9abdd5932a>
>
>       Helping You Grow Your Business, One Homeowner at a Time. TM
>
> Leads<http://pro.homeadvisor.com/leads/?entry_point_id=3D15727941&templat=
e_id=3D112&todo_id=3D1220898960&entityID=3D26320675&entityHash=3D26320675_1=
4219208ba2c2f5fa9e1fb9abdd5932a>|
> Ratings<http://pro.homeadvisor.com/ratings/?entry_point_id=3D15727942&tem=
plate_id=3D112&todo_id=3D1220898960&entityID=3D26320675&entityHash=3D263206=
75_14219208ba2c2f5fa9e1fb9abdd5932a>|
> Account<http://pro.homeadvisor.com/account/statement/?entry_point_id=3D15=
727943&template_id=3D112&todo_id=3D1220898960&entityID=3D26320675&entityHas=
h=3D26320675_14219208ba2c2f5fa9e1fb9abdd5932a>| Privacy
> Statement<http://pro.homeadvisor.com/home/Privacy-Policy/?entry_point_id=
=3D15727944&template_id=3D112&todo_id=3D1220898960&entityID=3D26320675&enti=
tyHash=3D26320675_14219208ba2c2f5fa9e1fb9abdd5932a>| Terms
> & Conditions<http://pro.homeadvisor.com/home/Terms-Conditions/?entry_poin=
t_id=3D15727945&template_id=3D112&todo_id=3D1220898960&entityID=3D26320675&=
entityHash=3D26320675_14219208ba2c2f5fa9e1fb9abdd5932a>
>
> Go Mobile
>  [image: iTunes]<http://www.homeadvisor.com/servlet/RedirectServlet?D=3DR=
EDIR&urlForward=3Dhttp://itunes.apple.com/us/app/servicemagic-pros/id437003=
175?mt=3D8&entry_point_id=3D15727946&template_id=3D112&todo_id=3D1220898960=
>  [image:
> Android]<http://www.homeadvisor.com/servlet/RedirectServlet?D=3DREDIR&url=
Forward=3Dhttps://play.google.com/store/apps/details?id=3Dcom.servicemagic.=
pros&entry_point_id=3D15727947&template_id=3D112&todo_id=3D1220898960>
>
> 14023 Denver West Parkway, Building 64
> Golden, CO 80401
>



--=20

Josh Bruno
501.206.6403
@joshbruno <https://twitter.com/joshbruno> |
LinkedIn<http://www.linkedin.com/in/joshbruno/>

--001a11c1ba201b33e804f034b925
Content-Type: text/html; charset=ISO-8859-1
Content-Transfer-Encoding: quoted-printable

<div dir=3D"ltr">Example lead #2 (this one with many fields)<font face=3D"y=
w-51457e76f04c71c6c5e0c43cc4d449507ef31ece-1655db84b665c469f1ccbdcc652fc6d1=
--o" style></font></div><div class=3D"gmail_extra"><br><br><div class=3D"gm=
ail_quote">

On Wed, Dec 18, 2013 at 3:12 PM, HomeAdvisor Lead <span dir=3D"ltr">&lt;<a =
href=3D"mailto:newlead@pro-lead.homeadvisor.com" target=3D"_blank">newlead@=
pro-lead.homeadvisor.com</a>&gt;</span> wrote:<br><blockquote class=3D"gmai=
l_quote" style=3D"margin:0 0 0 .8ex;border-left:1px #ccc solid;padding-left=
:1ex">




  =20
  =20

<div>
<table width=3D"650" cellpadding=3D"0" cellspacing=3D"0" border=3D"0" style=
=3D"font:11px Arial;color:#666">
   <tbody><tr>
      <td colspan=3D"2">
         =20








<table width=3D"100%" border=3D"0" cellpadding=3D"0" cellspacing=3D"0" styl=
e=3D"font:normal 11px arial,verdana,sans-serif;color:#566166">
  =20
      <tbody><tr>
         <td style=3D"padding:15px 0" colspan=3D"2">
            <p>View a <a href=3D"http://m.homeadvisor.com/ld/1919f23_48c570=
90?entry_point_id=3D15727938&amp;template_id=3D112&amp;todo_id=3D1220898960=
" target=3D"_blank">Mobile Version</a></p>
         </td>
      </tr>
  =20
  =20
  =20
  =20
  =20
      <tr>
         <td>
            <p>Don&#39;t miss an important email. Add <a href=3D"mailto:New=
Lead@pro-lead.HomeAdvisor.com" target=3D"_blank">NewLead@pro-lead.HomeAdvis=
or.com</a> to your address book.
              =20
            </p>
         </td>
      </tr>
  =20
   <tr>
     =20
     =20
      <td align=3D"left" style=3D"padding:15px;border-top:2px solid #e4e6e7=
;border-bottom:2px solid #e4e6e7;background:#f4f4f4 url(&#39;http://pro.hom=
eadvisor.com/templates/communications/112/images/header.jpg&#39;)">
        =20
        =20
        =20
         <a href=3D"http://pro.homeadvisor.com/servlet/RedirectServlet?D=3D=
HOMEm=3Dsmcommtemps&amp;template_id=3D112&amp;todo_id=3D1220898960&amp;enti=
tyID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f5fa9e1fb9abdd5932a&=
amp;entry_point_id=3D15727939" target=3D"_blank">
           =20
              =20
                  <img src=3D"http://pro.homeadvisor.com/templates/communic=
ations/images/logos/SeniorCareByPros.png" width=3D"259" height=3D"44" alt=
=3D"My Seniore Care Guide" title=3D"My Seniore Care Guide">
              =20
              =20
           =20
         </a>
      </td>
      <td align=3D"right" valign=3D"bottom" style=3D"background-color:#f4f4=
f4;padding:15px;border-top:2px solid #e4e6e7;border-bottom:2px solid #e4e6e=
7">=A0
        =20
        =20
      </td>
   </tr>
</tbody></table>

      </td>
   </tr>
   <tr>
      <td valign=3D"top" style=3D"padding:8px 10px 10px 10px">
         <p>Dear David Muson,</p>

         <p>You&#39;ve been matched to a <strong>Senior Companion Care</str=
ong> Lead!<br><br>
        =20
         </p>

        =20




<div style=3D"padding-bottom:10px">
    <h2 style=3D"background:url(&#39;http://pro.homeadvisor.com/templates/c=
ommunications/images/customer_icon.jpg&#39;) left no-repeat;padding:5px 0 5=
px 35px;font-size:14px">Customer Information</h2>

    <table cellpadding=3D"2" cellspacing=3D"0" border=3D"0" width=3D"100%" =
style=3D"font:11px Arial;color:#666;margin-left:34px">
       =20
        <tbody><tr>
            <td width=3D"230"><strong>Customer Name:</strong></td>
            <td>Eileen Joyce</td>
        </tr>
       =20
        <tr>
            <td><strong>Contact Time:</strong></td>
            <td>Any Phone - Anytime</td>
        </tr>
       =20
        <tr>
            <td><strong>Daytime Phone:</strong></td>
            <td><a href=3D"tel:516-567-7616" value=3D"+15165677616" target=
=3D"_blank">516-567-7616</a></td>
        </tr>
       =20
        <tr>
            <td><strong>Email:</strong></td>
            <td><a href=3D"mailto:lesabre60@excite.com" target=3D"_blank">l=
esabre60@excite.com</a></td>
        </tr>
       =20
        <tr>
            <td><strong>Address:</strong></td>
            <td>
               =20
                None,
               =20
                fLORAL pARK, NY 11001
            </td>
        </tr>
       =20
        <tr>
            <td colspan=3D"2">
                <strong style=3D"background:url(&#39;http://pro.homeadvisor=
.com/images/red_arrow.gif&#39;) left no-repeat;padding-left:8px">
                    <a href=3D"http://pro.homeadvisor.com/servlet/RedirectS=
ervlet?D=3DSTATIC&amp;targetPage=3D/servlet/LeadManagementServlet&amp;reque=
stedPage=3DemailAppt&amp;context=3Dactivity&amp;subContext=3Dsend_email&amp=
;srOID=3D53675506&amp;entityID=3D26320675&amp;entityHash=3D26320675_1421920=
8ba2c2f5fa9e1fb9abdd5932a&amp;consEntityID=3D39932078&amp;entry_point_id=3D=
345802&amp;templateID=3D112&amp;todo_id=3D1220898960&amp;template_id=3D112"=
 target=3D"_blank">Click here to set an appointment</a>
                </strong>
            </td>
        </tr>
       =20
    </tbody></table>
</div>

        =20



        =20


<div style=3D"padding-bottom:10px">
   <h2 style=3D"background:url(&#39;http://pro.homeadvisor.com/templates/co=
mmunications/images/job_info_icon.jpg&#39;) left no-repeat;padding:5px 0 5p=
x 35px;font-size:14px">Job Information</h2>
  =20
   <table cellpadding=3D"2" cellspacing=3D"0" border=3D"0" width=3D"100%" s=
tyle=3D"font:11px Arial;color:#666;margin-left:34px">
     =20
      <tbody><tr>
         <td width=3D"230"><strong>Description:</strong></td>
         <td>Senior Companion Care</td>
      </tr>
     =20
     =20
      <tr>
         <td><strong>Job Number:</strong></td>
         <td>53675506</td>
      </tr>
   </tbody></table>
</div>

<div style=3D"padding-bottom:20px">
   <h2 style=3D"background:url(&#39;http://pro.homeadvisor.com/templates/co=
mmunications/images/service_descrip_icon.jpg&#39;) left no-repeat;padding:5=
px 0 5px 35px;font-size:14px">Service Description</h2>
  =20
  =20
   <table cellpadding=3D"2" cellspacing=3D"0" border=3D"0" style=3D"font:11=
px Arial;color:#666;margin-left:34px">
<tbody><tr style=3D"font-size:1px;height:1px;line-height:1px">
<td width=3D"47%" height=3D"1" style=3D"font-size:1px;height:1px;line-heigh=
t:1px">=A0</td>
<td width=3D"53%" height=3D"1" style=3D"font-size:1px;height:1px;line-heigh=
t:1px">=A0</td>
</tr><tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">What is the first name of the care recipie=
nt?:</span>
</td>
<td valign=3D"top">
<span>..<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Who needs care?:</span>
</td>
<td valign=3D"top">
<span>Parent<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Gender::</span>
</td>
<td valign=3D"top">
<span>Male<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Age Range::</span>
</td>
<td valign=3D"top">
<span>71 - 90 years old<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Living situation::</span>
</td>
<td valign=3D"top">
<span>Home (lives alone)<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Are you looking for any of the basic care =
listed below?:</span>
</td>
<td valign=3D"top">
<span>Yes - care recipient needs the basic care services selected below.<br=
>Meal prep<br>Medication reminders<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Personal services:</span>
</td>
<td valign=3D"top">
<span>Yes<br>Bathing<br>Dressing/grooming<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Transportation needed:</span>
</td>
<td valign=3D"top">
<span>No<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Care type::</span>
</td>
<td valign=3D"top">
<span>Visiting care<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Are you looking for any of the additional =
services listed below?:</span>
</td>
<td valign=3D"top">
<span>No - additional care services are not required.<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Receptiveness::</span>
</td>
<td valign=3D"top">
<span>Very receptive<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Ambulation::</span>
</td>
<td valign=3D"top">
<span>Independent<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Expected funding:</span>
</td>
<td valign=3D"top">
<span>Private<br>Long-term care insurance<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold"><b>Comments:</b></span>
</td>
<td>
<span>Fther is just out of hospital 82yo Paying caSH THEN TO BE REINMURSED =
</span></td>
</tr>
</tbody></table>

</div>

<p><a href=3D"http://pro.homeadvisor.com/rfs/smpros/mobileAppDownload.jsp?t=
odo_id=3D1220898960&amp;template_id=3D112&amp;entityID=3D26320675&amp;spEnt=
ityID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f5fa9e1fb9abdd5932a=
&amp;entry_point_id=3D15480243" target=3D"_blank"><img src=3D"http://pro.ho=
meadvisor.com/images/smpros/comm-moble-app-banner.png" border=3D"0"></a></p=
>

<p>

         </p><p>
            Are you creating a positive initial impression with your HomeAd=
visor profile?
            <a href=3D"http://pro.homeadvisor.com/profile/?m=3Dservicemagic=
&amp;entityID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f5fa9e1fb9a=
bdd5932a&amp;todo_id=3D1220898960&amp;template_id=3D112&amp;entry_point_id=
=3D12531" target=3D"_blank"><strong>Click here to review profile</strong></=
a>
         </p>

         <p>
            Remember, for your benefit, HomeAdvisor will encourage this cus=
tomer to review your performance. Your Rating &amp; Review scores create
            &#39;online word-of-mouth&#39; to set you apart from your compe=
tition!
         </p>

        =20



<p>Thank you for being a part of the HomeAdvisor network. We appreciate you=
r business.</p>
<p>HomeAdvisor<br>
<a href=3D"tel:%28877%29%20947-3639" value=3D"+18779473639" target=3D"_blan=
k">(877) 947-3639</a><br>
<a href=3D"mailto:+ProCustomerCare@homeadvisor.com" target=3D"_blank">ProCu=
stomerCare@homeadvisor.com</a></p>

        =20
<table cellpadding=3D"0" cellspacing=3D"0" border=3D"0" width=3D"100%" styl=
e=3D"background-color:#efefef;font-size:11px;color:#666">
   <tbody><tr>
      <td height=3D"10" colspan=3D"5"></td>
   </tr>                                                                   =
                                                                           =
                 =20
   <tr valign=3D"top">
      <td width=3D"11"></td>
      <td width=3D"57">
         <img src=3D"http://pro.homeadvisor.com/templates/communications/im=
ages/quick_read_tile_icon.jpg" alt=3D"">
      </td>
      <td width=3D"16"></td>
      <td align=3D"left">
         <img src=3D"http://pro.homeadvisor.com/templates/communications/im=
ages/quick_read_tile_heading.jpg" alt=3D""><br>
         Have you added the HomeAdvisor Seal of Approval to your website? I=
t builds trust with homeowners that you?re a screened and approved member o=
f our network. It?s also quick and easy to add ? and FREE to HomeAdvisor me=
mbers!
        =20
         <img src=3D"http://pro.homeadvisor.com/images/blank.gif" width=3D"=
5" alt=3D""><img src=3D"http://pro.homeadvisor.com/images/SM2/arrows/red_ar=
row_ed2929.jpg" alt=3D"">
         <a href=3D"https://pro.homeadvisor.com/articles/seal-of-approval/s=
eal-download/?entry_point_id=3D27352682&amp;template_id=3D112&amp;todo_id=
=3D1220898960&amp;entityID=3D26320675&amp;entityHash=3D26320675_14219208ba2=
c2f5fa9e1fb9abdd5932a" target=3D"_blank">Add the Seal of Approval today!</a=
>
        =20
      </td>
      <td width=3D"10"></td>
   </tr>
   <tr>
      <td height=3D"10" colspan=3D"5"></td>
   </tr>
</tbody></table>

      <p></p><p></p></td>
      <td width=3D"120" valign=3D"top" style=3D"padding:8px 10px 10px 10px"=
>
        =20














        <table border=3D"0" cellpadding=3D"0" cellspacing=3D"0">
           <tbody><tr><td width=3D"25" rowspan=3D"50"><img src=3D"http://ww=
w.homeadvisor.com/images/clear.gif" width=3D"25" height=3D"1" alt=3D""></td=
></tr>
           <tr><td>
             =20
           </td></tr></tbody></table>
       =20

      </td>
   </tr>
    <tr>
        <td colspan=3D"2">
           =20




<table width=3D"100%" border=3D"0" cellpadding=3D"0" cellspacing=3D"0" styl=
e=3D"font:bold 15px arial,verdana,sans-serif">
    <tbody><tr>
        <td style=3D"color:#f7901e;padding:35px 0 15px;text-align:center;bo=
rder-bottom:2px solid #e4e6e7">
            <p>Helping You Grow Your Business, One Homeowner at a Time. <su=
p style=3D"font-size:8px">TM</sup></p>
        </td>
    </tr>
    <tr>
        <td align=3D"center" style=3D"background-color:#f4f4f4;border-botto=
m:2px solid #e4e6e7">
            <table width=3D"95%" border=3D"0" cellpadding=3D"0" cellspacing=
=3D"0" style=3D"font:bold 12px arial,verdana,sans-serif;color:#566166">
                <tbody><tr>
                    <td width=3D"75%" style=3D"padding:10px 0" align=3D"cen=
ter">
                        <p><a href=3D"http://pro.homeadvisor.com/leads/?ent=
ry_point_id=3D15727941&amp;template_id=3D112&amp;todo_id=3D1220898960&amp;e=
ntityID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f5fa9e1fb9abdd593=
2a" target=3D"_blank">Leads</a> |
                           <a href=3D"http://pro.homeadvisor.com/ratings/?e=
ntry_point_id=3D15727942&amp;template_id=3D112&amp;todo_id=3D1220898960&amp=
;entityID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f5fa9e1fb9abdd5=
932a" target=3D"_blank">Ratings</a> |
                           <a href=3D"http://pro.homeadvisor.com/account/st=
atement/?entry_point_id=3D15727943&amp;template_id=3D112&amp;todo_id=3D1220=
898960&amp;entityID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f5fa9=
e1fb9abdd5932a" target=3D"_blank">Account</a> |
                           <a href=3D"http://pro.homeadvisor.com/home/Priva=
cy-Policy/?entry_point_id=3D15727944&amp;template_id=3D112&amp;todo_id=3D12=
20898960&amp;entityID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f5f=
a9e1fb9abdd5932a" target=3D"_blank">Privacy Statement</a> |
                           <a href=3D"http://pro.homeadvisor.com/home/Terms=
-Conditions/?entry_point_id=3D15727945&amp;template_id=3D112&amp;todo_id=3D=
1220898960&amp;entityID=3D26320675&amp;entityHash=3D26320675_14219208ba2c2f=
5fa9e1fb9abdd5932a" target=3D"_blank">Terms &amp; Conditions</a>
                        </p>
                    </td>
                    <td style=3D"padding:10px 0 10px 10px;border-left:2px s=
olid #e4e6e7">
                        <p>Go Mobile</p>
                    </td>
                    <td style=3D"padding:10px 0">
                        <a href=3D"http://www.homeadvisor.com/servlet/Redir=
ectServlet?D=3DREDIR&amp;urlForward=3Dhttp://itunes.apple.com/us/app/servic=
emagic-pros/id437003175?mt=3D8&amp;entry_point_id=3D15727946&amp;template_i=
d=3D112&amp;todo_id=3D1220898960" target=3D"_blank"><img src=3D"http://pro.=
homeadvisor.com/templates/includes/footers/sp/images/icon_iphone.png" width=
=3D"20" height=3D"18" alt=3D"iTunes" title=3D"iTunes" border=3D"0"></a>
                    </td>
                    <td style=3D"padding:10px 0">
                        <a href=3D"http://www.homeadvisor.com/servlet/Redir=
ectServlet?D=3DREDIR&amp;urlForward=3Dhttps://play.google.com/store/apps/de=
tails?id=3Dcom.servicemagic.pros&amp;entry_point_id=3D15727947&amp;template=
_id=3D112&amp;todo_id=3D1220898960" target=3D"_blank"><img src=3D"http://pr=
o.homeadvisor.com/templates/includes/footers/sp/images/icon_android.png" wi=
dth=3D"19" height=3D"18" alt=3D"Android" title=3D"Android" border=3D"0"></a=
>
                    </td>
                </tr>
            </tbody></table>
        </td>
    </tr>


   =20
    <tr>
        <td style=3D"padding-top:20px">
            <p style=3D"color:#b2b2b2;font-size:12px;font-weight:normal">14=
023 Denver West Parkway, Building 64<br>
               Golden, CO 80401</p>
        </td>
    </tr>
</tbody></table>

        </td>
    </tr>
</tbody></table>
<img src=3D"http://pro.homeadvisor.com/servlet/EmailTracking?todo_id=3D1220=
898960&amp;comm_addr=3Djoshbruno@gmail.com&amp;campaign=3Dpayment_method_1&=
amp;template_id=3D112&amp;image_source=3D/images/clear.gif" width=3D"1" hei=
ght=3D"1">
</div>

</blockquote></div><br><br clear=3D"all"><div><br></div>-- <br><div dir=3D"=
ltr"><br><div>Josh Bruno</div><div><font size=3D"1"><span title=3D"Call wit=
h Google Voice">501.206.6403</span></font></div><div><a href=3D"https://twi=
tter.com/joshbruno" style=3D"font-size:x-small" target=3D"_blank">@joshbrun=
o</a><span style=3D"font-size:x-small"> |=A0</span><a href=3D"http://www.li=
nkedin.com/in/joshbruno/" style=3D"font-size:x-small" target=3D"_blank">Lin=
kedIn</a></div>

</div>
</div>
"""


    sample2_simple="""

</div><div class=3D"gmail_extra"><br><br><div class=3D"gmail_quote">On Sat,=
 Dec 7, 2013 at 9:47 AM, HomeAdvisor Lead <span dir=3D"ltr">&lt;<a href=3D"=
mailto:newlead@pro-lead.homeadvisor.com" target=3D"_blank">newlead@pro-lead=
.homeadvisor.com</a>&gt;</span> wrote:<br>

<blockquote class=3D"gmail_quote" style=3D"margin:0 0 0 .8ex;border-left:1p=
x #ccc solid;padding-left:1ex">


  =20
  =20

<div>
<table width=3D"650" cellpadding=3D"0" cellspacing=3D"0" border=3D"0" style=
=3D"font:11px Arial;color:#666">
   <tbody><tr>
      <td colspan=3D"2">
         =20








<table width=3D"100%" border=3D"0" cellpadding=3D"0" cellspacing=3D"0" styl=
e=3D"font:normal 11px arial,verdana,sans-serif;color:#566166">
  =20
      <tbody><tr>
         <td style=3D"padding:15px 0" colspan=3D"2">
            <p>View a <a href=3D"http://m.homeadvisor.com/ld/2566383_48a5e5=
e8?entry_point_id=3D15727938&amp;template_id=3D112&amp;todo_id=3D1218831848=
" target=3D"_blank">Mobile Version</a></p>
         </td>
      </tr>
  =20
  =20
  =20
  =20
  =20
      <tr>
         <td>
            <p>Don&#39;t miss an important email. Add <a href=3D"mailto:New=
Lead@pro-lead.HomeAdvisor.com" target=3D"_blank">NewLead@pro-lead.HomeAdvis=
or.com</a> to your address book.
              =20
            </p>
         </td>
      </tr>
  =20
   <tr>
     =20
     =20
      <td align=3D"left" style=3D"padding:15px;border-top:2px solid #e4e6e7=
;border-bottom:2px solid #e4e6e7;background:#f4f4f4 url(&#39;http://pro.hom=
eadvisor.com/templates/communications/112/images/header.jpg&#39;)">
        =20
        =20
        =20
         <a href=3D"http://pro.homeadvisor.com/servlet/RedirectServlet?D=3D=
HOMEm=3Dsmcommtemps&amp;template_id=3D112&amp;todo_id=3D1218831848&amp;enti=
tyID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f5fa9e1fb9abdd5932a&=
amp;entry_point_id=3D15727939" target=3D"_blank">
           =20
              =20
                  <img src=3D"http://pro.homeadvisor.com/templates/communic=
ations/images/logos/SeniorCareByPros.png" width=3D"259" height=3D"44" alt=
=3D"My Seniore Care Guide" title=3D"My Seniore Care Guide">
              =20
              =20
           =20
         </a>
      </td>
      <td align=3D"right" valign=3D"bottom" style=3D"background-color:#f4f4=
f4;padding:15px;border-top:2px solid #e4e6e7;border-bottom:2px solid #e4e6e=
7">=A0
        =20
        =20
      </td>
   </tr>
</tbody></table>

      </td>
   </tr>
   <tr>
      <td valign=3D"top" style=3D"padding:8px 10px 10px 10px">
         <p>Dear Vincent McMahon,</p>

         <p>You&#39;ve been matched to a <strong>Senior Companion Care</str=
ong> Lead!<br><br>
        =20
         </p>

        =20




<div style=3D"padding-bottom:10px">
    <h2 style=3D"background:url(&#39;http://pro.homeadvisor.com/templates/c=
ommunications/images/customer_icon.jpg&#39;) left no-repeat;padding:5px 0 5=
px 35px;font-size:14px">Customer Information</h2>

    <table cellpadding=3D"2" cellspacing=3D"0" border=3D"0" width=3D"100%" =
style=3D"font:11px Arial;color:#666;margin-left:34px">
       =20
        <tbody><tr>
            <td width=3D"230"><strong>Customer Name:</strong></td>
            <td>Nancy Torborg</td>
        </tr>
       =20
        <tr>
            <td><strong>Contact Time:</strong></td>
            <td>Any Phone - Anytime</td>
        </tr>
       =20
        <tr>
            <td><strong>Daytime Phone:</strong></td>
            <td><a href=3D"tel:919-261-7549" value=3D"+19192617549" target=
=3D"_blank">919-261-7549</a></td>
        </tr>
       =20
        <tr>
            <td><strong>Email:</strong></td>
            <td><a href=3D"mailto:ntorborg@mac.com" target=3D"_blank">ntorb=
org@mac.com</a></td>
        </tr>
       =20
        <tr>
            <td><strong>Address:</strong></td>
            <td>
               =20
                None,
               =20
                Dobbs Ferry, NY 10522
            </td>
        </tr>
       =20
        <tr>
            <td colspan=3D"2">
                <strong style=3D"background:url(&#39;http://pro.homeadvisor=
.com/images/red_arrow.gif&#39;) left no-repeat;padding-left:8px">
                    <a href=3D"http://pro.homeadvisor.com/servlet/RedirectS=
ervlet?D=3DSTATIC&amp;targetPage=3D/servlet/LeadManagementServlet&amp;reque=
stedPage=3DemailAppt&amp;context=3Dactivity&amp;subContext=3Dsend_email&amp=
;srOID=3D53542680&amp;entityID=3D39216003&amp;entityHash=3D39216003_1421920=
8ba2c2f5fa9e1fb9abdd5932a&amp;consEntityID=3D39770261&amp;entry_point_id=3D=
345802&amp;templateID=3D112&amp;todo_id=3D1218831848&amp;template_id=3D112"=
 target=3D"_blank">Click here to set an appointment</a>
                </strong>
            </td>
        </tr>
       =20
    </tbody></table>
</div>

        =20



        =20


<div style=3D"padding-bottom:10px">
   <h2 style=3D"background:url(&#39;http://pro.homeadvisor.com/templates/co=
mmunications/images/job_info_icon.jpg&#39;) left no-repeat;padding:5px 0 5p=
x 35px;font-size:14px">Job Information</h2>
  =20
   <table cellpadding=3D"2" cellspacing=3D"0" border=3D"0" width=3D"100%" s=
tyle=3D"font:11px Arial;color:#666;margin-left:34px">
     =20
      <tbody><tr>
         <td width=3D"230"><strong>Description:</strong></td>
         <td>Senior Companion Care</td>
      </tr>
     =20
     =20
      <tr>
         <td><strong>Job Number:</strong></td>
         <td>53542680</td>
      </tr>
   </tbody></table>
</div>

<div style=3D"padding-bottom:20px">
   <h2 style=3D"background:url(&#39;http://pro.homeadvisor.com/templates/co=
mmunications/images/service_descrip_icon.jpg&#39;) left no-repeat;padding:5=
px 0 5px 35px;font-size:14px">Service Description</h2>
  =20
  =20
   <table cellpadding=3D"2" cellspacing=3D"0" border=3D"0" style=3D"font:11=
px Arial;color:#666;margin-left:34px">
<tbody><tr style=3D"font-size:1px;height:1px;line-height:1px">
<td width=3D"47%" height=3D"1" style=3D"font-size:1px;height:1px;line-heigh=
t:1px">=A0</td>
<td width=3D"53%" height=3D"1" style=3D"font-size:1px;height:1px;line-heigh=
t:1px">=A0</td>
</tr><tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Gender::</span>
</td>
<td valign=3D"top">
<span>Male<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Living situation::</span>
</td>
<td valign=3D"top">
<span>Home (lives alone)<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Personal services:</span>
</td>
<td valign=3D"top">
<span>None<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Transportation needed:</span>
</td>
<td valign=3D"top">
<span>No<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Care type::</span>
</td>
<td valign=3D"top">
<span>Visiting care<br></span>
</td>
</tr>
<tr>
<td valign=3D"top">
<span style=3D"font-weight:bold">Expected funding:</span>
</td>
<td valign=3D"top">
<span>Private<br></span>
</td>
</tr>
</tbody></table>

</div>

<p><a href=3D"http://pro.homeadvisor.com/rfs/smpros/mobileAppDownload.jsp?t=
odo_id=3D1218831848&amp;template_id=3D112&amp;entityID=3D39216003&amp;spEnt=
ityID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f5fa9e1fb9abdd5932a=
&amp;entry_point_id=3D15480243" target=3D"_blank"><img src=3D"http://pro.ho=
meadvisor.com/images/smpros/comm-moble-app-banner.png" border=3D"0"></a></p=
>

<p>

         </p><p>
            Are you creating a positive initial impression with your HomeAd=
visor profile?
            <a href=3D"http://pro.homeadvisor.com/profile/?m=3Dservicemagic=
&amp;entityID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f5fa9e1fb9a=
bdd5932a&amp;todo_id=3D1218831848&amp;template_id=3D112&amp;entry_point_id=
=3D12531" target=3D"_blank"><strong>Click here to review profile</strong></=
a>
         </p>

         <p>
            Remember, for your benefit, HomeAdvisor will encourage this cus=
tomer to review your performance. Your Rating &amp; Review scores create
            &#39;online word-of-mouth&#39; to set you apart from your compe=
tition!
         </p>

        =20



<p>Thank you for being a part of the HomeAdvisor network. We appreciate you=
r business.</p>
<p>HomeAdvisor<br>
<a href=3D"tel:%28877%29%20947-3639" value=3D"+18779473639" target=3D"_blan=
k">(877) 947-3639</a><br>
<a href=3D"mailto:+ProCustomerCare@homeadvisor.com" target=3D"_blank">ProCu=
stomerCare@homeadvisor.com</a></p>

        =20

      <p></p><p></p></td>
      <td width=3D"120" valign=3D"top" style=3D"padding:8px 10px 10px 10px"=
>
        =20














        <table border=3D"0" cellpadding=3D"0" cellspacing=3D"0">
           <tbody><tr><td width=3D"25" rowspan=3D"50"><img src=3D"http://ww=
w.homeadvisor.com/images/clear.gif" width=3D"25" height=3D"1" alt=3D""></td=
></tr>
           <tr><td>
             =20
           </td></tr></tbody></table>
       =20

      </td>
   </tr>
    <tr>
        <td colspan=3D"2">
           =20




<table width=3D"100%" border=3D"0" cellpadding=3D"0" cellspacing=3D"0" styl=
e=3D"font:bold 15px arial,verdana,sans-serif">
    <tbody><tr>
        <td style=3D"color:#f7901e;padding:35px 0 15px;text-align:center;bo=
rder-bottom:2px solid #e4e6e7">
            <p>Helping You Grow Your Business, One Homeowner at a Time. <su=
p style=3D"font-size:8px">TM</sup></p>
        </td>
    </tr>
    <tr>
        <td align=3D"center" style=3D"background-color:#f4f4f4;border-botto=
m:2px solid #e4e6e7">
            <table width=3D"95%" border=3D"0" cellpadding=3D"0" cellspacing=
=3D"0" style=3D"font:bold 12px arial,verdana,sans-serif;color:#566166">
                <tbody><tr>
                    <td width=3D"75%" style=3D"padding:10px 0" align=3D"cen=
ter">
                        <p><a href=3D"http://pro.homeadvisor.com/leads/?ent=
ry_point_id=3D15727941&amp;template_id=3D112&amp;todo_id=3D1218831848&amp;e=
ntityID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f5fa9e1fb9abdd593=
2a" target=3D"_blank">Leads</a> |
                           <a href=3D"http://pro.homeadvisor.com/ratings/?e=
ntry_point_id=3D15727942&amp;template_id=3D112&amp;todo_id=3D1218831848&amp=
;entityID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f5fa9e1fb9abdd5=
932a" target=3D"_blank">Ratings</a> |
                           <a href=3D"http://pro.homeadvisor.com/account/st=
atement/?entry_point_id=3D15727943&amp;template_id=3D112&amp;todo_id=3D1218=
831848&amp;entityID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f5fa9=
e1fb9abdd5932a" target=3D"_blank">Account</a> |
                           <a href=3D"http://pro.homeadvisor.com/home/Priva=
cy-Policy/?entry_point_id=3D15727944&amp;template_id=3D112&amp;todo_id=3D12=
18831848&amp;entityID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f5f=
a9e1fb9abdd5932a" target=3D"_blank">Privacy Statement</a> |
                           <a href=3D"http://pro.homeadvisor.com/home/Terms=
-Conditions/?entry_point_id=3D15727945&amp;template_id=3D112&amp;todo_id=3D=
1218831848&amp;entityID=3D39216003&amp;entityHash=3D39216003_14219208ba2c2f=
5fa9e1fb9abdd5932a" target=3D"_blank">Terms &amp; Conditions</a>
                        </p>
                    </td>
                    <td style=3D"padding:10px 0 10px 10px;border-left:2px s=
olid #e4e6e7">
                        <p>Go Mobile</p>
                    </td>
                    <td style=3D"padding:10px 0">
                        <a href=3D"http://www.homeadvisor.com/servlet/Redir=
ectServlet?D=3DREDIR&amp;urlForward=3Dhttp://itunes.apple.com/us/app/servic=
emagic-pros/id437003175?mt=3D8&amp;entry_point_id=3D15727946&amp;template_i=
d=3D112&amp;todo_id=3D1218831848" target=3D"_blank"><img src=3D"http://pro.=
homeadvisor.com/templates/includes/footers/sp/images/icon_iphone.png" width=
=3D"20" height=3D"18" alt=3D"iTunes" title=3D"iTunes" border=3D"0"></a>
                    </td>
                    <td style=3D"padding:10px 0">
                        <a href=3D"http://www.homeadvisor.com/servlet/Redir=
ectServlet?D=3DREDIR&amp;urlForward=3Dhttps://play.google.com/store/apps/de=
tails?id=3Dcom.servicemagic.pros&amp;entry_point_id=3D15727947&amp;template=
_id=3D112&amp;todo_id=3D1218831848" target=3D"_blank"><img src=3D"http://pr=
o.homeadvisor.com/templates/includes/footers/sp/images/icon_android.png" wi=
dth=3D"19" height=3D"18" alt=3D"Android" title=3D"Android" border=3D"0"></a=
>
                    </td>
                </tr>
            </tbody></table>
        </td>
    </tr>


   =20
    <tr>
        <td style=3D"padding-top:20px">
            <p style=3D"color:#b2b2b2;font-size:12px;font-weight:normal">14=
023 Denver West Parkway, Building 64<br>
               Golden, CO 80401</p>
        </td>
    </tr>
</tbody></table>

        </td>
    </tr>
</tbody></table>
<img src=3D"http://pro.homeadvisor.com/servlet/EmailTracking?todo_id=3D1218=
831848&amp;comm_addr=3Djoshbruno@gmail.com&amp;campaign=3Dpayment_method_1&=
amp;template_id=3D112&amp;image_source=3D/images/clear.gif" width=3D"1" hei=
ght=3D"1">
</div>

</blockquote></div><br><br clear=3D"all"><div><br></div>-- <br><div dir=3D"=
ltr"><br><div>Josh Bruno</div><div><font size=3D"1"><span title=3D"Call wit=
h Google Voice">501.206.6403</span></font></div><div><a href=3D"https://twi=
tter.com/joshbruno" style=3D"font-size:x-small" target=3D"_blank">@joshbrun=
o</a><span style=3D"font-size:x-small"> |=A0</span><a href=3D"http://www.li=
nkedin.com/in/joshbruno/" style=3D"font-size:x-small" target=3D"_blank">Lin=
kedIn</a></div>

</div>
</div>

"""

    sample1="""
<blockquote class=3D"gmail_quote" style=3D"margin:0 0 0 .8ex;border-left:1p=
x #ccc solid;padding-left:1ex"><u></u>
<div><table border=3D"0" cellspacing=3D"0" style=3D"border:1px solid #a4b84=
7" width=3D"614">
<tbody><tr>
<td>
<img src=3D"http://dir.caring.com/images/lead_notifiers/provideremail-leads=
-header.gif" style=3D"border:0px">
</td>
</tr>
<tr>
<td style=3D"padding:10px;font-size:45px;font-family:helvetica;background-c=
olor:#f3f6e4;color:#a4b847">
<img src=3D"http://dir.caring.com/images/lead_notifiers/icon-newlead.png" s=
tyle=3D"float:left;margin-right:15px"><div style=3D"margin-top:10px">
New Lead
</div>
</td>
</tr>
<tr>
<td style=3D"padding:15px;padding-bottom:0;font-size:12px;font-family:helve=
tica;line-height:20px">

</td>
</tr>
<tr>
<td>
<p style=3D"background-color:#fed9b7;padding:15px;margin:15px;font-size:12p=
x;font-family:helvetica;line-height:20px">
<strong>
Note:
</strong>
Remember to add Reid Martin to your tracking system and credit Caring.com a=
s the source.
</p>
</td>
</tr>
<tr>
<td>
<table style=3D"font-size:12px;padding-left:25px;font-family:helvetica">
<thead>
<tr><td colspan=3D"2" height=3D"20px" width=3D"30%"></td>
</tr></thead>
<tbody>
<tr>
<td>
Name:
</td>
<td>
Reid Martin
</td>
</tr>
<tr>
<td>
Phone Number:
</td>
<td>
<a href=3D"tel:%28917%29%20659-8363" value=3D"+19176598363" target=3D"_blan=
k">(917) 659-8363</a>
</td>
</tr>
<tr>
<td>
E-mail Address:
</td>
<td>
<a href=3D"mailto:denreid@gmail.com" target=3D"_blank">denreid@gmail.com</a=
>
</td>
</tr>
<tr>
<td>
Caring.com Reference #:
</td>
<td>
843653
</td>
</tr>
<tr>
<td>
Relationship:
</td>
<td>
Myself
</td>
</tr>
<tr>
<td>
Provider:
</td>
<td>
Care Guardian
</td>
</tr>
<tr>
<td>
Looking for Care in:
</td>
<td>
New York, New York
</td>
</tr>
<tr>
<td>
Seeking:
</td>
<td>
In-Home Care
</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td style=3D"font-size:12px;line-height:20px;padding-top:15px;padding-left:=
15px;padding-bottom:15px;font-family:helvetica">
To give feedback on this lead, please reply to this e-mail and send us a me=
ssage with as much detail as possible.
</td>
</tr>
<tr>
<td style=3D"font-size:12px;line-height:20px;padding-top:15px;padding-left:=
15px;padding-bottom:15px;padding-right:15px;font-family:helvetica;color:#6b=
6b6b">
<p>
<strong>
Who Is Caring.com?
</strong>
<br>
Caring.com is the Web=92s best directory of senior care providers. With mor=
e than 1.8 million unique visitors per month, we=92re helping caregivers co=
nnect with the information, expertise, support, and local resources they ne=
ed.

</p>
</td>
</tr>
<tr>
<td style=3D"border-top:1px solid #a4b847;font-size:10px;line-height:17px;p=
adding:25px;font-family:helvetica;background-color:#6b6b6b;color:white">
<p>
You received this e-mail because Care Guardian is partnered with Caring.com=
.
</p>
<p>
The material on Caring.com is for informational purposes only and is not a =
substitute for legal, financial, professional, or medical advice or diagnos=
is or treatment. By using our website, you agree to the
<a href=3D"http://p.caring.com/wf/click?upn=3DXP-2FWTDcF-2Bohby4bZVzuHYjkgV=
rOe8hiZ0l-2Byzg3OliSltT2Yz7YpDS03qCXNlrdc_aQIKMZdMso013X8MWWxT0LJrAMuICoszp=
LS4PqsVNEWnT3f1NurWbUAfnPFKYN9zVlMsiZeK7C91fhA8f8Kt7yVt3123uBD4sYcU8oJB3Ki7=
-2Bihr5ddE1pol-2FKohJh9BxtQGBXWzWk6e3N8XlhktL97maws7dc0sd3uUZKsIhHEY1mQprGr=
VRIB-2Fk1EPdr3eghrESwOFD0XKeRs1wiWootn7wMSuNNAsGxcyFm51E2RPODa53TMGS4czZ86q=
yt8hgfNdsicOMqXumZsiD5RxxA-3D-3D" target=3D"_blank">Terms of Use</a>
and
<a href=3D"http://p.caring.com/wf/click?upn=3DXP-2FWTDcF-2Bohby4bZVzuHYjkgV=
rOe8hiZ0l-2Byzg3OliQQJkMRNSVFZmSA5Bujpcr6_aQIKMZdMso013X8MWWxT0LJrAMuICoszp=
LS4PqsVNEWnT3f1NurWbUAfnPFKYN9zvpFq5Egpa98t3KFx2oM6zRKj81aF6r3Nsy5m-2BHC3HV=
q6C2wO2iRDOrUtKdI1bA1UISHZr8fTVO7KGXVueQs9rte65d45Hr-2Fia0QQ0CIJx95O4riOKSY=
LFSaID3NHoCPD3-2FcNC2I0WoaWQL2fc8K30nHJbuNGCwO-2ByZIs6WTO5ur7asf5MLc9Q4JHT1=
4x8y3-2FozVLSxPGgiom0osfntc90w-3D-3D" target=3D"_blank">Privacy Policy.</a>
</p>
<p>
=A9 2007-2014 Caring, Inc., 2600 S. El Camino Real, Suite 300, San Mateo, C=
A 94403. All rights reserved.
</p>
</td>
</tr>
</tbody></table>
<img src=3D"http://p.caring.com/wf/open?upn=3DaQIKMZdMso013X8MWWxT0LJrAMuIC=
oszpLS4PqsVNEWnT3f1NurWbUAfnPFKYN9zQdmEPDyDcfWiUKedkXX8DLxklQJtxdR7JS5lFexg=
GB5QEcFEgikt6pYqooItH5qG-2Bdfd5Wm-2FOcWzpAyMuvZy-2F2HESATVyUshu7KLhg2qxsC3V=
glZ2-2BqPDAobO1Z-2B6E1aC4HP9D7Pwdpsu-2B3sbcwEs29Dajxg-2Fl4a7ehf2SZ1EWrsEwFH=
RTE26y2Vy-2BwvDl1n2Rkx0B1uqE8jy2pzGpT2dw-3D-3D" alt=3D"" width=3D"1" height=
=3D"1" border=3D"0" style=3D"min-height:1px!important;width:1px!important;b=
order-width:0!important;margin-top:0!important;margin-bottom:0!important;ma=
rgin-right:0!important;margin-left:0!important;padding-top:0!important;padd=
ing-bottom:0!important;padding-right:0!important;padding-left:0!important">
</div>

</blockquote></div><br><br clear=3D"all"><div><br></div>-- <br><div dir=3D"=
ltr"><br><div>Josh Bruno</div><div><font size=3D"1"><span title=3D"Call wit=
h Google Voice">501.206.6403</span></font></div><div><a href=3D"https://twi=
tter.com/joshbruno" style=3D"font-size:x-small" target=3D"_blank">@joshbrun=
o</a><span style=3D"font-size:x-small"> |=A0</span><a href=3D"http://www.li=
nkedin.com/in/joshbruno/" style=3D"font-size:x-small" target=3D"_blank">Lin=
kedIn</a></div>

</div>
</div>
"""    

    sample_templates.append(sample3)
    sample_templates.append(sample2)
    sample_templates.append(sample2_simple)
    sample_templates.append(sample1)
    sample_templates.append(sample4)


    return sample_templates




def email_handler2(request,*args,**kwargs):
    #
    # 0v4 JC Jan 21, 2014:  Use in devtable code
    # 0v3 JC Feb 14, 2013:  Unicode style errors continue
    # 0v2 JC June 28, 2012:  Updated to store attachments as mysmallworld Concepts
    # 
    # hal@truthhost.appspotmail.com
    # david@truthhost.appspotmail.com
    ######################################################
    from landingpage.views import api_run_function

    logging.info("Got handler...")
    
    parameter={} # For concept creation
    txtmsg = ""
    message={}
    
    if request.POST:
        
        # STEP 1:  PROCESS EMAIL FIELDS
        #############################
        email_destination = kwargs.pop('email_destination', None) # Posted email address to URL
        try:
            message = mail.InboundEmailMessage(request.raw_post_data)        
        except:
            logging.warning("Could not decode raw_post_data")
            try:
                message = mail.InboundEmailMessage(request.raw_post_data.encode('ascii','ignore')) #Patch Oct 17, 2012
            except:
                # Error exists Feb 14, 2013: UnicodeDecodeError: 'ascii' codec can't decode byte 0x92 in position 4900: ordinal not in range(128)
                logging.warning("Catch email decode message")
                message = unicode(request.raw_post_data, errors='ignore') #0v3
        
        try:
            message.sender=message.sender.encode('ascii','ignore') # utf-8 bug# str(message.sender)
        except:
            logging.warning("Email message arrived without sender!! Set to 'unknown'")
            logging.warning("> "+str(request.raw_post_data))
            #Oct 2, 2013
            # Message is unicode object here (bug)
            logging.warning("[bug] message possibly unicode object so will fail on next line - oct 2, 2013")
            message.sender="unknown" # Bug, potential message is unicode here (error in origin)
        logging.info("DEBUG1 message.sender: "+str(message.sender))
        crawl_people(request,"crawl_people",var_basic_input=message.sender) # Store name (Even though done further on because strips name!)
        message.sender=text_to_email_list(message.sender)[0]
        
        # Normalize data (ie/ blank subject will cause string errors)
        try: message.subject=message.subject.encode('ascii','ignore')  #utf-8 bugstr(message.subject)
        except AttributeError: message.subject=""
        except:
            message.subject=str(message.subject)
            logging.warning("Could not decode utf-8. Converting to string: "+str(message.subject))
            
        try:  #Throws error if no 'to' attribute error
            message_to=message.to.encode('ascii','ignore') #Limit at 500 characters
        except AttributeError: message_to=""
        except: message_to=""
        
        crawl_people(request,"crawl_people",var_basic_input=message_to) # Store name (Even though done further on because strips name!)
        message_to_list=text_to_email_list(message_to)
        
        logging.info("Received a message from: " + str(message.sender))
        logging.info("Subject: " + str(message.subject))
        logging.info("To: (none-listed) " + str(message_to)) # to is a comma-seperated list of the message's primary recipients
        logging.info("Email handler destination: " + str(email_destination))
        #date field#  date returns the message date.
        
        # Handle txt body #######################################
        #original# plaintext = message.bodies(content_type='text/plain')
        plaintext_bodies = message.bodies('text/plain')
        #html_bodies = message.bodies('text/html')
        # Note on html:  The text/html ends up being escaped.  Try on dev server passing html code through
        for text in plaintext_bodies:
            try: 
                txtmsg = text[1].decode()
                txtmsg=txtmsg.encode('ascii','ignore') # Throw out unicode: kills db update
            except:
                try: txtmsg=txtmsg.encode('ascii','ignore') # Throw out unicode: kills db update
                except: logging.warning("DID NOT SAVE MESSAGE as bad type or could not encode")
            logging.info("Body is: %s" % txtmsg)

    delivery_failure = re.search('Delivery Status.*Failure', message.subject,re.IGNORECASE)
    if request.POST and not delivery_failure: #Ignore Delivery Status Notification (Failure)
        
        # Set concept_id based on 'sender' and datetime
        ###############################################
        timenow=str(int(time.time()))  #Current unix style datetime Return the time in seconds since the epoch as a floating point number
        sender=message.sender.lower()
        
        try: results=conceptdb.objects.filter(concept_id=qc_normalize_concept_id(sender))[:1].get()   #query
        except conceptdb.DoesNotExist: results=None
        if results: # Then exists so OVER WRITE!
            concept_id="email_"+str(sender)+"_"+str(timenow) # Set concept name to be related to main concept if exists
            logging.warning("Warning!: TODO:  setup set parent.children pointing here.")
            parameter['myparent']=results.id # Append ID to parents list of children
        else:
            logging.info("Warning: Could not find parent for message with sender: "+str(sender))
            concept_id="email_"+str(message.sender)+"_"+str(timenow)
        #Normalize concept_id
        concept_id=qc_normalize_concept_id(concept_id) #JC# Sept 13, 2012
        
        
        # Debug output
        logging.info("concept: "+concept_id)
        
        # Create new Email Concept
        #####################
        function_id="post_to_create"
        parameter['db']='conceptdb'
        parameter['concept_id']=concept_id
        parameter['description']="Email received by handler: "+email_destination
        parameter['run_local']=True
        # Specifics
        parameter['type']="email"
        parameter['category1']=message_to_list[0]
        # b)  reference_key=from email
        parameter['reference_key']=message.sender
        # e)  mylist=to field
        parameter['mylist']=message_to_list
        parameter['description']=message.subject
        # BUG:  Parameter looking strings will look like dictionary.  Instead, escape encode them [patch trial 4.JC July 4, 2012]
        logging.warning("Trying escape codes, ensure output is created")
        parameter['mytext']=urllib.quote(txtmsg)

        # PATCH:  removed June 21, 2012#        myrequest=add_dict_to_request(request,parameter) # Potential parameters carried through
        myrequest=copy.copy(request)
        myrequest.POST=parameter
        
        response=api_run_function(myrequest,function_id=function_id) # JSON RESPONSE!
        
        # PROCESS EMAIL CREATION RESPONSE
        ################################
        try: data=simplejson.loads(response.content)
        except:
            logging.warning("JC bug catcher:  Could not find response.content")
            data=''
        try: new_id=data['results']['new_id']
        except: new_id=""
        logging.info("GOT new ID: "+str(new_id))
        logging.info("With JSON response: "+str(response))
        email_parent_id=new_id
        
        # Handle attachments
        #######################################
        my_attachment_ids=[]
        if hasattr(message, 'attachments'):
            for file_name, filecontents in message.attachments:
                
                # STEP 1: DECODE ATTACHMENT CONTENT
                if filecontents.encoding and filecontents.encoding.lower() != '7bit':
                    try:
                        payload = filecontents.payload.decode(filecontents.encoding)
                    except LookupError:
                        logging.error('Unknown decoding %s.' % filecontents.encoding)
                    except (Exception), e:
                        logging.error('Could not decode payload: %s' % e)
                else:
                    payload = filecontents.payload
                logging.info("Working with attachment named: "+str(file_name))
                
                # Deal with mimetype
                blob_content_type, encoding = mimetypes.guess_type(file_name)
                if not blob_content_type: 
                    logging.warning("No type found for attachment: "+str(file_name))
                    blob_content_type='application/octet-stream'
                logging.info("contenttype: "+str(blob_content_type))
                
                # STEP 2: Store contents into new blobstore
                file_blob = files.blobstore.create(mime_type=blob_content_type, _blobinfo_uploaded_filename=file_name)
                with files.open(file_blob, 'a') as f: # Open files for writing
                    f.write(payload)
                files.finalize(file_blob) # Finalize the file. Do this before attempting to read it.
                blob_key = files.blobstore.get_blob_key(file_blob) # Get the file's blob key
                
                # Grab image serving url
                if re.search('image', blob_content_type):
                    image_url=images.get_serving_url(blob_key)
                    file_type="image"
                    logging.info("Image url: "+str(image_url))
                else: 
                    image_url=""
                    file_type="file"
            
                logging.info("Blobkey: "+str(blob_key))
                
                # STEP 3:  Create corresponding Concept
                parameter={}
                function_id="post_to_create" # FUNCTION TO CALL FOR POSTING A NEW USER CONCEPT
                parameter['id']=""
                parameter['run_local']=True  # CALL FUNCTION PROGRAMATICALLY
                parameter['db']='conceptdb'  # NECESSARY for API
        
                # Use timestamp as randomizer (though limited as seconds is smallest)
                datey=time.strftime('%Y%m%d%H%M%S')        
                parameter['concept_id']=file_name+"_"+file_type+"_"+datey
        
                parameter['description']="(File upload type: "+file_type+")"
                parameter['myparent']=email_parent_id
                parameter['url_media']=str(image_url)
                parameter['type']=file_type
                parameter['myfield']=str(blob_key)
        
                request2=remove_dict_from_request(request) #JC July 3, 2012 (don't allow nested calls)
                myrequest=add_dict_to_request2(request2,parameter)
                response=api_run_function(myrequest,function_id=function_id)

                #Grab new ID from JSON Responsee
                data=simplejson.loads(response.content)
                try: new_id=data['results']['new_id']
                except: new_id=""
                logging.info("GOT new ID: "+str(new_id))
                
                # STEP 4:  Add these child attachment Concepts to email parent mysmallworld
                my_attachment_ids.append(new_id)
            if my_attachment_ids:
                try: email_record_concept=conceptdb.objects.filter(id=email_parent_id)[:1].get()   #query
                except: email_record_concept=None
                if email_record_concept:
                    email_record_concept.mysmallworld=my_attachment_ids
                    email_record_concept.save()
                    
                # STEP 4:  SPECIAL LOGIC FOR DEALING WITH EMAILS
                # Create new user IF:
                # a)  An attachment is an image
                # b)  Subject is "create"
                #########################################################
                if message.subject.lower()=="create":
                    if image_url:
                        parameter={}
                        function_id="create_user_from_email"
                        parameter['myfunction']="create_user_from_email"
                        parameter['var_basic_input']=str(email_parent_id)
                        
                        logging.info("--------- CREATING USER FROM EMAIL!!! ---------")
                        request2=remove_dict_from_request(request) #JC July 3, 2012 (don't allow nested calls)
                        myrequest=add_dict_to_request2(request2,parameter)
                        response=api_run_function(myrequest,function_id=function_id)
        process_email_concept(request,"process_email_concept",var_basic_input=email_parent_id)
                    
    return http.HttpResponse('ok')



