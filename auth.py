from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.app_identity import get_application_id

from models import Token
from lib import BaseHandler
import logging
import urllib, urllib2

from gaesessions import get_current_session

from config import DEBUG

from google.appengine.dist import use_library
use_library('django', '0.96')

class WINDRedirect(BaseHandler):
    def get(self):
        if DEBUG:
            session = get_current_session()
            token_user = Token.get_or_insert("test")
            session["user"] = token_user.key().name()
            self.redirect("/")
            return
        callback = "http://%s.appspot.com/auth/callback" % get_application_id()
        options = urllib.urlencode([("destination", callback)])
        url = "https://wind.columbia.edu/login?%s" % (options)
        self.redirect(url)

class WINDCallback(BaseHandler):
    def get(self):
        token = self.request.get("token")
        url = "https://wind.columbia.edu/validate?ticketid={0}".format(token)
        r = urllib2.Request(url=url)
        lines = urllib2.urlopen(r).split("\n")
        if lines[0] == "yes":
            # ident is unique
            ident = lines[1]

            # make sure we have a mapping
            token_user = Token.get_or_insert(ident)
            token_user.token = ident
            token_user.put()
            # and set the session cookie
            session = get_current_sesssion()
            if session.is_active():
                session["user"] = indent
                session.regenerate_id()            
        self.redirect("/")

application = webapp.WSGIApplication(
    [('/auth/', WINDRedirect),
     ('/auth/callback', WINDCallback),
     ],
    debug=DEBUG)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
