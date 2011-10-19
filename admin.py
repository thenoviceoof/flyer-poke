from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from apiproxy_errors import 

import datetime
import logging

from models import Flyer, Job

from google.appengine.dist import use_library
use_library('django', '0.96')

class Email(webapp.RequestHandler):
    def get(self):
        msg = mail.EmailMessage(sender="beta.entity.k@gmail.com",
                                to="nyh2105@columbia.edu")
        msg.subject = "Hello world"
        msg.body    = "Testing"
        try:
            msg.send()
        except apiproxy_errors.OverQuotaError, message:
            # Log the error.
            logging.error(message)
            # Display an informative message to the user.
            self.response.out.write('The email could not be sent. '
                                    'Please try again later.')
        self.response.out.write(template.render("templates/upload.html", {}))

class Clean(webapp.RequestHandler):
    def get(self):
        # clean out the old pdfs
        jobs = Job.all()
        jobs.filter("date <", datetime.datetime.now())
        logging.debug(str(jobs))
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/upload.html", {}))

class List(webapp.RequestHandler):
    def get(self):
        flyer_req = db.GqlQuery("SELECT * "
                                "FROM Flyer")
        flyers = flyer_req.fetch(10)

        values = {"flyers":flyers}
        self.response.out.write(template.render("templates/list.html", values))

application = webapp.WSGIApplication(
    [('/tasks/email', Email),
     ('/tasks/clean', Clean),
     ('/tasks/list', List),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
