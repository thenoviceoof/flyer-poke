from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.runtime import apiproxy_errors
from google.appengine.api.app_identity import get_application_id

from datetime import datetime, tzinfo, timedelta
import time
import logging

from models import Club, Flyer, Job, Email, EmailToClub
from lib import *
from config import TIMEZONE, ADMIN_EMAIL

class CurrentTimeZone(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=TIMEZONE)
    def dst(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return "US/Eastern"

class EmailHandler(BaseHandler):
    def get(self):
        # is it a week day?
        current_date = datetime.now(CurrentTimeZone())
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
                flyer_date = flyer.event_date.replace(tzinfo=CurrentTimeZone())
                if current_date > flyer_date:
                    flyer.active = False
                    flyer.put()
            for job in jobs:
                if not(job.flyer.active):
                    job.active = False
                    job.put()
            # only get the un-done jobs
            jobs = [j for j in jobs if j.active and j.state != 2]
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
            # check if the flyers should be rolled over
            flyer_query = Flyer.all()
            flyer_query.filter("active =", True)
            flyers = flyer_query.fetch(200)
            for flyer in flyers:
                if current_date > flyer.event_date.replace(tzinfo=CurrentTimeZone()):
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
        dt = datetime.fromtimestamp(time.mktime(t))

        jobs = Job.all()
        jobs.filter("date <", dt)
        jobs = jobs.fetch()
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/task.html",
                                                {"msg": "Removed old ones"}))

# new orgs, bandwidth/email usage
class SendAdminNotifications(BaseHandler):
    def get(self):
        timestamp = time.mktime(datetime.now().timetuple())-24*3600
        yesterday = datetime.fromtimestamp(timestamp)
        # count how many flyers are going out
        current_date = datetime.now(CurrentTimeZone())
        day = current_date.weekday() # starts 0=monday... 6=sunday
        if day < 5:
            job_query = Job.all()
            job_query.filter("active =", True)
            job_query.filter("state !=", DONE)
            flyer_count = job_query.count()
        else:
            flyer_count = 0
        # get new clubs
        club_query = Club.all()
        club_query.filter("created_at >", yesterday)
        new_clubs = club_query.fetch(20)
        # get new emails
        email_query = Email.all()
        email_query.filter("created_at >", yesterday)
        new_emails = email_query.fetch(100)
        # get new flyers
        flyer_query = Flyer.all()
        flyer_query.filter("created_at >", yesterday)
        new_flyers = flyer_query.fetch(50)
        # get new EmailToClub
        joint_query = EmailToClub.all()
        joint_query.filter("created_at >", yesterday)
        new_joints = joint_query.fetch(100)
        # and get the newly disabled links
        joint_query = EmailToClub.all()
        joint_query.filter("updated_at >", yesterday)
        joint_query.filter("enable =", False)
        dead_joints = joint_query.fetch(100)

        if (not(new_clubs) and not(new_emails) and not(new_flyers)
            and not(new_joints)):
            self.response.out.write("Nothing to email")
            return

        # email sending pre-computation
        fromaddr = "noreply@%s.appspotmail.com" % get_application_id()
        date = time.strftime("%Y/%m/%d")

        # send the emails
        msg = mail.EmailMessage(sender = "Flyer Guy <%s>" % fromaddr,
                                to = ADMIN_EMAIL)
        msg.subject = "[Flyer] Admin stats (%s)" % date
        msg.html    = template.render("templates/email_stats.html",
                                      {"flyer_count": flyer_count,
                                       "clubs": new_clubs,
                                       "emails": new_emails,
                                       "flyers": new_flyers,
                                       "joints": new_joints,
                                       "dead_joints": dead_joints})
        try:
            msg.send()
        except apiproxy_errors.OverQuotaError, (message,):
            # Log the error.
            logging.error("Could not send email")
            logging.error(message)
        self.response.out.write("Sent emails")

application = webapp.WSGIApplication(
    [('/tasks/email', EmailHandler),
     ('/tasks/clean', Clean),
     ('/tasks/admin_stats', SendAdminNotifications)
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
