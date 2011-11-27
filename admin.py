from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.runtime import apiproxy_errors
from google.appengine.api.app_identity import get_application_id

import datetime, time
import logging

from models import Flyer, Job
from lib import BaseHandler

from google.appengine.dist import use_library
use_library('django', '0.96')

# upper bound on number of API calls
BOUND = 1000

class Email(BaseHandler):
    def get(self):
        jobq = Job.all()
        # get both init and downloaded states
        jobs = list(jobq.filter("done =", False))
        # update the flyer list
        flyers = 
        emails = set([j.email for j in jobs])

        if len(emails) > BOUND:
            # figure out which emails to include b/c they're new
            init_flyers = [j.flyer for j in jobs if not(j.flyer.last_sent_date)]
            init_jobs = [j for j in jobs if not(j.flyer.last_sent_date)]
            emails = set([j.email for for j in init_jobs])
            if len(emails) > BOUND:
            # and now calculate on the other emails
            flyers = [j.flyer for j in jobs if j.flyer.last_sent_date]
            # as of now, use a simple longest w/o update first
            flyers = sorted(flyers, key=attrgetter('last_sent_date'))
            for flyer in flyers:
                tmp_email = set([j.email for j in flyer.jobs])
                if len(emails.union(tmp_email)) > BOUND:
                    break
                emails = emails.union(tmp_email)

        # email sending pre-computation
        domain = "http://%s.appspot.com" % get_application_id()
        fromaddr = "noreply@%s.appspotmail.com" % get_application_id()
        date = time.strftime("%Y/%m/%d")

        for email in emails:
            js = [j for j in jobs if j.email == email]
            msg = mail.EmailMessage(sender="Flyer Guy <%s>" % fromaddr,
                                    to=email.email)
            msg.subject = "[Flyer] Reminder (%s)" % date
            msg.html    = template.render("templates/email.html",
                                          {"jobs": js,
                                           "domain": domain,
                                           "email": email.email})
            try:
                msg.send()
            except apiproxy_errors.OverQuotaError, (message,):
                # Log the error.
                logging.error("Could not send email")
                logging.error(message)
        self.response.out.write("Sent emails")

class Clean(BaseHandler):
    def get(self):
        # clean out the old jobs
        t = list(time.localtime())
        t[2] -= 7
        dt = datetime.datetime.fromtimestamp(time.mktime(t))

        jobs = Job.all()
        jobs.filter("date <", dt)
        jobs = jobs.fetch(BOUND)
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/task.html",
                                                {"msg": "Removed old ones"}))

class Purge(BaseHandler):
    def get(self):
        # clean out the old pdfs
        jobs = Job.all().fetch(BOUND)
        for job in jobs:
            job.delete()
        flyers = Flyer.all().fetch(BOUND)
        for flyer in flyers:
            flyer.delete()
        self.response.out.write(template.render("templates/task.html",
                                                {"msg": "Removed everything"}))

class List(BaseHandler):
    def get(self):
        flyerq = Flyer.all()
        flyers = flyerq.fetch(BOUND)
        jobs = Job.all().fetch(BOUND)

        values = {"flyers":flyers, "jobs": jobs}
        self.response.out.write(template.render("templates/list.html", values))

application = webapp.WSGIApplication(
    [('/tasks/email', Email),
     ('/tasks/clean', Clean),
     ('/tasks/purge', Purge),
     ('/tasks/list', List),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
