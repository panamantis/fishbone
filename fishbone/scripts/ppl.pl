import re
import mechanize
#Pull ppl
#import cookielib
#
#





br = mechanize.Browser()
br.set_handle_robots(False)
#browser.open("https://www.linkedin.com/")

# browser settings (used to emulate a browser)
#ex br.set_handle_equiv(True)
#ex br.set_handle_redirect(True)
#ex br.set_handle_referer(True)
#ex br.set_handle_robots(False)
#ex br.set_debug_http(False)
#ex br.set_debug_responses(False)
#ex br.set_debug_redirects(False)
#ex br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time = 1)
br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]


br.open("https://canadianopendataexperience.com/users/profile/685")

#br.select_form(id="new_user")
br.select_form(nr=0)

#FIND CONTROLS   for control in br.form.controls:
#FIND CONTROLS       print control
#FIND CONTROLS       print "type=%s, name=%s value=%s" % (control.type, control.name, br[control.name])


br["user[email]"] = "jon@truthkit.com"
br["user[password]"] = "c8yVyXIF"
#br["user_email"] = "jon@truthkit.com"
#br["user_password"] = "c8yVyXIF"
response = br.submit()

#Valid if#  <a href="/people/pymk?trk=nmp-pymk-new_pymk_title">People You May Know</a

loggedin=False

if (re.search('People You May',response.read())):
    loggedin=True


if loggedin:
    print "Yes, loggedin to LinkedIn"
else:
    print "Not loggedin"

    
# View random profile
url="https://canadianopendataexperience.com/users/profile/685"

br.open(url)
print br.title()  # works
print br.geturl()  # works
response=br.response()
print response.read()








