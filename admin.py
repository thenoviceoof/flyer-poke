from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class Email(webapp.RequestHandler):
    def get(self):
        self.response.out.write("Hello world!")

application = webapp.WSGIApplication(
    [('/email', Email),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
