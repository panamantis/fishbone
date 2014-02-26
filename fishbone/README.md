# Fishbone with devtable IDE Support

Fishbone is an HTML5-Bootstrap boilerplate web application with django backend.
It is designed to run on Google App Engine and is based on [django-on-appengine](https://github.com/aurorasoftware/django-on-appengine).


----

### Installation

1. Download the App Engine SDK.
2. Install it.
3. Clone the repo, and run `dev_appserver.py .`.
4. Congratulations, you are now running fishbone on App Engine!

----

### Using Fishbone with Devtable

[DevTable](http://devtable.com/) support is built into Fishbone, all you need to do is as follow:

1. Setup your devtable environment then import.  That's it.
2. Ensure your app.yaml file defines dependencies as latest:  ie/ django latest (caution as ends up causing problems if deployed to local development area).

----
### Using Fishbone on your local machine (dev_appserver)

I had a problem with the 'latest' version of Django (ssl type of GAE error) fix:

1. In app.yaml, downgrade the Django version from 'latest' to '1.4'

----

### Customization 

In order to customize client-side code, you need to modify resources under `assets` directory and then build it using grunt.

----
