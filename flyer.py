from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.api.app_identity import get_application_id
from google.appengine.api import mail

import hashlib
import time
import re
import logging
from datetime import datetime

from gaesessions import get_current_session

# to shut gae up
from google.appengine.dist import use_library
use_library('django', '0.96')

# other pieces to import
from models import Flyer, Job, Email, Club
from models import EmailToClub
from lib import *
from config import AFFILIATION, DEBUG, EMAIL_SUFFIX, EMAIL_VERIFY_LIMIT

################################################################################
# utility fns

# YOU WILL HAVE TO REPLACE THIS IF YOU DON'T GO TO COLUMBIA
# this checks the format of the UNI, which all columbia emails adhere to
def check_email(email):
    return re.match("^\w{2,3}\d{4}$", email)

# checks emails for formatting
def normalize_email(email):
    if re.match("^\w{2,3}\d{4}$", email):
        return email+EMAIL_SUFFIX
    if re.match("^\w{2,3}\d{4}@columbia.edu$", email):
        return email
    return False

def generate_hash(base):
    md5 = hashlib.md5()
    md5.update(base)
    return md5.hexdigest()
def generate_random_hash(base):
    return generate_hash(base + str(time.time()))

def slugify(s):
    return re.sub("\W",'', s).lower()

def add_notify(title, body):
    session = get_current_session()
    cur = [{"title":title, "body": body}]
    if session.is_active():
        if session.get("notify", None):
            session["notify"] = session["notify"] + cur
        else:
            session["notify"] = cur
    else:
        session["notify"] = cur

def get_or_make(Obj, key_name):
    """Retrieves or creates the object keyed on key_name
    Returns tuple with object and boolean indicating whether it was created"""
    def txn(key_name):
        made = False
        entity = Obj.get_by_key_name(key_name)
        if entity is None:
            entity = Obj(key_name=key_name)
            entity.put()
            made = True
        return (entity, made)
    return db.run_in_transaction(txn, key_name)

def get_email(user):
    """Get email object associated with user"""
    email_query = Email.all()
    email_query.filter("user = ", user)
    return email_query.get()

def check_admin(club_id):
    """See if we have admin access to a certain club's pages"""
    user = users.get_current_user()
    email = get_email(user)
    club = Club.get_by_key_name(club_id)
    if not(user) or not(email) or not(club) or not(email.user_enable):
        return False
    # do a joint query
    query = EmailToClub.all()
    query.filter("email =", email)
    query.filter("club =", club)
    joint = query.get()
    if not(joint):
        return False
    return joint.admin

################################################################################

# /
# either front page or choose organization
class Index(BaseHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            email_query = Email.all()
            email_query.filter('user = ', user)
            email = email_query.get()
            # if we're not already linked...
            if not(email):
                # display the email-linking page
                self.response.out.write(template.render(
                        "templates/user_link.html", {}))
                return
            if DEBUG:
                email.user_enable = True
                email.put()
            if not(email.user_enable):
                values = {}
                if email.email:
                    values['email'] = email.email
                # handle notifications
                session = get_current_session()
                if session:
                    values['notifications'] = session.get("notify", None)
                    session["notify"] = None
                # display the email-linking page
                self.response.out.write(template.render(
                        "templates/user_link.html", values))
                return
            # otherwise, serve up the listing page
            clubrefs = email.clubs.fetch(20) # 20 chosen arbitrarily
            clubs = [c.club
                     for c in prefetch_refprop(clubrefs, EmailToClub.club)
                     if check_admin(c.club.slug)]
            values = {"clubs": clubs}
            # try getting notifications
            session = get_current_session()
            if session:
                values['notifications'] = session.get("notify", None)
                session["notify"] = None
            self.response.out.write(template.render("templates/orgs.html",
                                                    values))            
        else:
            # otherwise, just display the frontpage
            admin_contact = "support@%s.appspotmail.com" % get_application_id()
            values = {"affiliation": AFFILIATION,
                      "contact_info": admin_contact,
                      "login_url": users.create_login_url(self.request.uri)}
            self.response.out.write(template.render("templates/index.html",
                                                    values))

# /linkemail
class LinkEmail(BaseHandler):
    def post(self):
        user = users.get_current_user()
        if user:
            # find if we're already bound to an email
            email_query = Email.all()
            email_query.filter("user =", user)
            email_obj = email_query.get()
            if email_obj:
                add_notify("Notice", "Already bound to an email")
                self.redirect("/")
                return
            # handle the email input
            email_addr = normalize_email(self.request.get("email"))
            if not(email_addr):
                add_notify("Notice", "Not a correct UNI format")
                self.redirect("/")
                return
            # find the email by the email address
            email_key = generate_hash(email_addr)[:10]
            email, made = get_or_make(Email, email_key)
            if not(email.email):
                email.email = email_addr
                email.put()
            # user already tied, don't allow transfers through this interface
            if email.user_enable:
                add_notify("Notice", "User is already enabled")
                self.redirect("/")
                return
            if not(email.user):
                email.user = user
            # generate a new key
            email.user_request_key = generate_hash(str(email))
            email.user_request_time = datetime.today()
            email.put()

            # send a verification email
            domain = "http://%s.appspot.com" % get_application_id()
            verify_addr = domain + "/linkemail/%s" % email.user_request_key
            msg = mail.EmailMessage()
            fromaddr = "noreply@%s.appspotmail.com" % get_application_id()
            msg.sender  = "Flyer Guy <%s>" % fromaddr
            msg.to      = email.email
            msg.subject = "[Flyer] Verify your email address"
            msg.html    = template.render("templates/email_verify.html",
                                          {'verify_addr':verify_addr})
            self.redirect("/")
        else:
            add_notify("Notice", "Sign in")
            self.redirect("/")

# /linkemail/(\w+)
class VerifyEmail(BaseHandler):
    def get(self, token):
        # find the email with the token
        email_query = Email.all()
        email_query.filter("user_request_key =", token)
        email = email_query.get()
        # no email, die
        if not(email):
            self.error(404)
        # check the date, if it's late wipe it
        if datetime.today() - email.user_request_time > timedelta(days=2):
            email.user = None
            email.user_request_key = None
            email.user_request_time = None
            email.put()
            self.error(404)
        # enable
        email.user_enable = True
        email.user_request_key = None
        email.user_request_time = None
        email.put()
        add_notify("Notice", "Emails linked!")
        self.redirect("/")

# /new-club
class ClubNew(BaseHandler):
    def post(self):
        # check there's someone signed in
        user = users.get_current_user()
        if not(user):
            add_notify("Error", "You do not have the appropriate permissions")
            self.redirect("/")
            return
        # get associated email
        email_query = Email.all()
        email_query.filter("user = ", user)
        email = email_query.get()
        if not(email) or not(email.user_enable):
            add_notify("Error", "You do not have the appropriate permissions")
            self.redirect("/")
            return
        # basic sanity check
        clubname = self.request.get("name")
        if not(clubname):
            add_notify("Error", "Please enter a club name")
            self.redirect("/")
            return
        # convert to slug
        clubslug = slugify(clubname)
        # basics of get_or_insert, with insertion
        club, made = get_or_make(Club, clubslug)
        if not(made):
            # generate an error
            add_notify("Error", "That particular club name is taken. Sorry!")
            self.redirect("/")
            return
        # make a club, add current user as an admin
        club.name = clubname
        club.slug = clubslug
        club.put()
        join = EmailToClub(email=email, club=club, admin=True)
        join.put()
        club_url = "/club/%s" % clubslug
        self.redirect(club_url)

# /club/(\w*)
class ClubEdit(BaseHandler):
    def get(self, club_id):
        """Get the editor page"""
        # check credentials
        if not(check_admin(club_id)):
            add_notify("Error", "You do not have the appropriate permissions")
            self.redirect("/")
            return
        user = users.get_current_user()
        club = Club.get_by_key_name(club_id)
        email = get_email(user)

        # prefetch the emails
        email_refs = club.emails
        emails = [e.email.email
                  for e in prefetch_refprop(email_refs, EmailToClub.email)]
        admins = [e.admin for e in email_refs]
        messages = [e.message for e in email_refs]
        email_info = zip(admins, emails, messages)
        vals = {"emails": email_info,
                "club": club.name}
        # get the notifications
        session = get_current_session()
        if session:
            vals["notifications"] = session["notify"]
            session["notify"] = None
        self.response.out.write(template.render("templates/club_edit.html",
                                                vals))

    def post(self, club_id):
        # check credentials
        if not(check_admin(club_id)):
            add_notify("Error", "You do not have the appropriate permissions")
            self.redirect("/")
            return
        user = users.get_current_user()
        club = Club.get_by_key_name(club_id)
        email = get_email(user)

        # add emails
        email_block = self.request.get("newemails")
        emails_raw = [e for e in re.split("[\s\,\n]", email_block) if e]
        emails = [e for e in emails_raw if check_email(e)]
        for email in emails:
            # add a suffix
            email = normalize_email(email)
            # use a hash for emails, accessed when deleting
            email_obj, made = None, None
            while not(email_obj) or not(made):
                # randomly generate a key
                email_key = generate_hash(email)[:10]
                email_obj, made = get_or_make(Email, email_key)
            if not(email_obj.email):
                email_obj.email = email
                email_obj.put()
            # make sure this pair is unique
            query = EmailToClub.all()
            query.filter('email =', email_obj)
            query.filter('club =', club)
            join = query.fetch(1)
            if not(join):
                join = EmailToClub(email=email_obj, club=club)
                join.put()

        # create message
        if emails:
            add_notify("Notice", "Emails added")
        if len(emails) != len(emails_raw):
            add_notify("Notice", "Not all emails added")
        self.redirect("/club/%s" % club.slug)

# !!! do the club/email link

################################################################################
# non-admin stuff

# upload flyer
class Flyer(BaseHandler):
    # serves up the flyer upload form
    def get(self, club_id):
        # check credentials
        if not(check_admin(club_id)):
            add_notify("Error", "You do not have the appropriate permissions")
            self.redirect("/")
            return
        user = users.get_current_user()
        club = Club.get_by_key_name(club_id)
        email = get_email(user)

        club = Club.get_by_key_name(club_id)

        values = {"name": club.name}
        self.response.out.write(template.render("templates/upload.html", values))

    # handles the flyer upload
    def post(self, club_id):
        # check credentials
        user = users.get_current_user()
        if not(user):
            add_notify("Error", "You're not signed in")            
            self.redirect("/")
            return
        club = Club.get_by_key_name(club_id)
        email = get_email(user)
        check_admin(email, club)

        # get the club
        club = Club.get(club_id)

        # make a flyer
        flyer, made = None, None
        while not(flyer) or not(made):
            # randomly generate a flyer key
            flyer_key = generate_hash(club_id)[:6]
            flyer, made = get_or_make(Flyer, flyer_key)
        flyer.id = flyer_key
        name = self.request.get("name")
        # check if the filename is a pdf
        if name[-3:] != "pdf":
            # !!! replace this with something more useful
            raise Exception("File must be a PDF")
        flyer.name = name[:-4]
        pdf = self.request.get("flyer")
        flyer.flyer = db.Blob(pdf)
        flyer.put()

        # make a bunch of jobs from the club and flyer
        for email in club.emails:
            job = Job(flyer=flyer, email=email, done = False,
                      state=INIT)
            job.put()

        # and write out the response
        self.response.out.write(template.render("templates/finish.html", {}))

class Download(BaseHandler):
    # don't allow "anon" downloads
    def get(self, job_id):
        job = Job.get(job_id)
        flyer = job.flyer
        if flyer.flyer:
            if job.state == INIT:
                job.state = DOWNLOADED
                job.put()
            self.response.headers['Content-Type'] = "application/pdf"
            self.response.headers['Content-Disposition'] = \
                "attachment; filename=%s.pdf" % flyer.name
            self.response.out.write(flyer.flyer)
        else:
            self.error(404)

class Done(BaseHandler):
    # means user is done
    def get(self, job_id):
        job = Job.get(job_id)

        if job:
            job.state = DONE
            job.put()
            self.response.out.write(template.render("templates/finish.html",{}))
        else:
            self.error(404)

# !!! remove emails w/ AJAX?
    
class StopClubMail(BaseHandler):
    def get(self, job_id):
        pass
        # !!! have to delete jobs, set user to no 
        # email = Email.get(email_id)
        # q = Job.all()
        # q.filter("email =", email)
        # jobs = q.fetch(BOUND)
        # for job in jobs:
        #     job.delete()
        # self.response.out.write(template.render("templates/sorry.html", {}))

class StopAllMail(BaseHandler):
    def get(self, email_id):
        pass
        # !!! have to delete jobs, set user to no 
        # email = Email.get(email_id)
        # q = Job.all()
        # q.filter("email =", email)
        # jobs = q.fetch(BOUND)
        # for job in jobs:
        #     job.delete()
        # self.response.out.write(template.render("templates/sorry.html", {}))

class Logout(BaseHandler):
    def get(self):
        session = get_current_session()
        session.terminate()
        self.redirect("/")

application = webapp.WSGIApplication(
    [('/', Index), # both front and orgs list
     ('/linkemail', LinkEmail),
     ('/new-club', ClubNew), # new club
     ('/club/(.*)', ClubEdit), # club edit
     ('/flyer/(.*)', Flyer), # flyer upload (get/post)
     ('/pdf/(.*)', Download), # get flyer for certain person (job)
     ('/done/(.*)', Done), # toggle done for certain person (job)
     ('/stop_club/(.*)', StopClubMail), # stop email from a club
     ('/stop_all/(.*)', StopAllMail), # stop all traffic to email
     ('/logout', Logout),
     ],
    debug=DEBUG)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
