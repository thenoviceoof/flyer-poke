from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Token2Club
from lib import BaseHandler
import logging
import urllib, urllib2

from gaesessions import get_current_session

from google.appengine.dist import use_library
use_library('django', '0.96')

def WINDCallback(BaseHandler):
    def get(self):
        token = self.request.get("token")
        url = "https://wind.columbia.edu/validate?ticketid={0}".format(token)
        r = urllib2.Request(url=url)
        lines = urllib2.urlopen(r).split("\n")
        if lines[0] == "yes":
            ident = lines[1]

            # make sure we have a mapping
            token_user = Token2Club.get_or_insert(ident)
            token_user.token = ident
            token_user.put()
            # and set the session cookie
            session = get_current_sesssion()
            if session.is_active():
                session["user"] = indent
                session.regenerate_id()            
        self.redirect("/")

application = webapp.WSGIApplication(
    [('/callback', Index),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
