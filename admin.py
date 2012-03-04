from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.runtime import apiproxy_errors
from google.appengine.api.app_identity import get_application_id

import datetime, time
import logging

from models import Flyer, Job, EmailToClub
from lib import *
from config import TIMEZONE

class CurrentTimeZone(datetime.tzinfo):
    def utcoffset(self, dt):
        return TIMEZONE
    def dst(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return "US/Eastern"

class Email(BaseHandler):
    def get(self):
        # is it a week day?
        current_date = datetime.datetime.now(CurrentTimeZone)
        day = current_date.weekday() # starts 0=monday... 6=sunday
        if day < 5:
            # weekday
            # get all the active jobs
            job_query = Job.all()
            job_query.filter("active =", True)
            jobs = job_query.fetch(2000)
            # check if the jobs are past their event date
            flyers = set([j.flyer for j in jobs])
            for flyer in flyers:
                if current_date > flyer.event_date:
                    flyer.active = False
                    flyer.put()
            for job in jobs:
                if not(job.flyer.active):
                    job.active = False
                    job.put()
            jobs = [j for j in jobs if j.active]
            # send the emails: bin jobs by email, send
            emails = set([j.email for j in jobs])

            # !!!
            # email sending pre-computation
            domain = "http://%s.appspot.com" % get_application_id()
            fromaddr = "noreply@%s.appspotmail.com" % get_application_id()
            date = time.strftime("%Y/%m/%d")

            # send the emails
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

        elif day == 6:
            # it's sunday
            # check if the flyers are 
            flyer_query = Flyer.all()
            flyer_query.filter("active =", True)
            flyers = flyer.query.fetch(200)
            for flyer in flyers:
                if current_date > flyer.event_date:
                    flyer.active = False
                    flyer.put()
            # deprecate the jobs
            job_query = Job.all()
            job_query.filter("active =", True)
            jobs = job_query.fetch(2000)
            for job in jobs:
                job.active = False
                job.put()
            jobs = [j for j in jobs if j.flyer.active]
            # repopulate all the jobs
            for job in jobs:
                # generate a key
                job_obj, made = None, None
                while not(job_obj) or not(made):
                    # randomly generate a key
                    job_key = generate_random_hash(str(email))
                    job_obj, made = get_or_make(Job, job_key)
                    if made:
                        job_obj.id = job_key
                        job_obj.flyer = job.flyer
                        job_obj.email = job.email
                        job_obj.renewal = job.renewal + 1
                        job_obj.put()
            self.response.out.write("Renewed jobs")

# !!! semesterly cleaning
# clean out the old jobs (month (31 days) or older)
class Clean(BaseHandler):
    def get(self):
        t = list(time.localtime())
        t[2] -= 31
        dt = datetime.datetime.fromtimestamp(time.mktime(t))

        jobs = Job.all()
        jobs.filter("date <", dt)
        jobs = jobs.fetch()
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/task.html",
                                                {"msg": "Removed old ones"}))

# !!! new orgs, bandwidth/email usage
class SendAdminNotifications(BaseHandler):
    def get(self):
        pass

application = webapp.WSGIApplication(
    [('/tasks/email', Email),
     ('/tasks/clean', Clean),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
