from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.api.app_identity import get_application_id

import hashlib
import time
import re
import logging

from gaesessions import get_current_session

# to shut gae up
from google.appengine.dist import use_library
use_library('django', '0.96')

# other pieces to import
from models import Flyer, Job, Email, Token, Club
from models import TokenToClub, EmailToClub
from lib import *
from config import AFFILIATION, SIGNIN_TEXT, DEBUG

################################################################################
# utility fns

def generate_hash(base):
    seed = base + str(time.time())
    md5 = hashlib.md5()
    md5.update(seed)
    return md5.hexdigest()

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

def check_admin(club_id):
    """See if we have admin access to a certain club's pages"""
    session = get_current_session()
    if not(session.is_active()):
        raise Exception("Session is not active")
    token_id = session.get("user", None)
    if not(token_id):
        raise Exception("No user in the session")
    token = Token.get_by_key_name(token_id)
    club = Club.get_by_key_name(club_id)
    # do a joint query
    query = TokenToClub.all()
    query.filter("token =", token)
    query.filter("club =", club)
    joint = query.fetch(1)
    if not(joint):
        raise Exception("Not an admin")

################################################################################

# either front page or choose organization
class Index(BaseHandler):
    def get(self):
        session = get_current_session()
        if session.is_active():
            # serve up the club list for the user
            token = session["user"]
            token_user = Token.get_by_key_name(token)
            # make sure the token_user actually exists
            if not(token_user):
                session.terminate()
                self.redirect("/")
            clubrefs = token_user.clubs.fetch(20) # 20 chosen arbitrarily
            clubs = [c.club
                     for c in prefetch_refprop(clubrefs, TokenToClub.club)]
            notifications = session.get("notify", None)
            values = {"clubs": clubs, "notifications": notifications}
            session["notify"] = None
            self.response.out.write(template.render("templates/orgs.html",
                                                    values))
        else:
            # find out if signed in to google account
            user = users.get_current_user()
            if user:
                # find out if the user is in the db or not
                q = db.GqlQuery("SELECT * FROM Token WHERE user = :1", user)
                user_token = q.get()
                if user_token:
                    # if so, log the user in, reroute them back to "/"
                    session["user"] = user_token.key().name()
                    self.redirect("/")
            # otherwise, just display the frontpage
            admin_contact = "support@%s.appspotmail.com" % get_application_id()
            values = {"affiliation": AFFILIATION,
                      "sign_in_button": SIGNIN_TEXT,
                      "contact_info": admin_contact}
            self.response.out.write(template.render("templates/index.html",
                                                    values))

# upload flyer
class Flyer(BaseHandler):
    # serves up the flyer upload form
    def get(self, club_id):
        # check credentials
        check_admin(club_id)

        club = Club.get(club_id)

        values = {"name": club.name}
        self.response.out.write(template.render("templates/upload.html", values))

    # handles the flyer upload
    def post(self, club_id):
        # check credentials
        check_admin(club_id)

        # get the club
        club = Club.get(club_id)

        # make a flyer
        flyer = None
        while not(flyer):
            # randomly generate a flyer key
            flyer_key = generate_hash(club_id)[:6]
            flyer, made = get_or_make(Flyer, flyer_key)
            if not(made):
                flyer = None
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
    def get(self, flyer_id, email_id):
        flyer = Flyer.get(flyer_id)
        email = Email.get(email_id)
        q = Job.all()
        q.filter("email =", email)
        q.filter("flyer =", flyer)
        job = q.get()

        if flyer.flyer:
            if job.state < DOWNLOADED:
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
    def get(self, flyer_id, email_id):
        flyer = Flyer.get(flyer_id)
        email = Email.get(email_id)

        q = Job.all()
        q.filter("email =", email)
        q.filter("flyer =", flyer)
        job = q.get()
        if job:
            job.state = DONE
            job.put()
            self.response.out.write(template.render("templates/finish.html",
                                                    {}))
        else:
            self.error(404)

class ClubNew(BaseHandler):
    def post(self):
        # check there's someone signed in
        session = get_current_session()
        if session.is_active():
            if not(session["user"]):
                self.error(404)
        else:
            self.error(404)
        clubname = self.request.get("name")
        # basic sanity check
        if not(clubname):
            self.error(500)
        # convert to slug
        clubslug = slugify(clubname)
        # basics of get_or_insert, with insertion
        club, made = get_or_make(Club, clubslug)
        if not(made):
            # generate an error
            add_notify("Error", "That particular name is taken. Sorry!")
            self.redirect("/")
            return
        # make a club, add current user as person
        club.name = clubname
        club.slug = clubslug
        club.put()
        token = Token.get_or_insert(session["user"])
        join = TokenToClub(token=token, club=club)
        join.put()
        club_url = "/club/%s" % clubslug
        self.redirect(club_url)

class ClubEdit(BaseHandler):
    def get(self, club_id):
        # check credentials
        check_admin(club_id)
        session = get_current_session()

        # getting the editor
        club = Club.get_by_key_name(club_id)
        email_refs = club.emails
        # prefetch the emails
        emails = [e.email
                  for e in prefetch_refprop(email_refs, EmailToClub.email)]
        vals = {"emails": emails,
                "club": club.name,
                "notifications": session["notify"]}
        session["notify"] = None
        self.response.out.write(template.render("templates/club_edit.html",
                                                vals))

    def post(self, club_id):
        # check credentials
        check_admin(club_id)
        
        # get club
        club = Club.get_by_key_name(club_id)
        # add emails
        email_block = self.request.get("newemails")
        emails = [e for e in re.split("[\s\,\n]", email_block) if e]
        for email in emails:
            # don't use hashes for emails, never access anyways
            email_obj = Email.get_or_insert(email)
            if not(email_obj.email):
                email_obj.email = email
            # make sure this pair is unique
            query = EmailToClub.all()
            query.filter('email =', email_obj)
            query.filter('club =', club)
            join = query.fetch(1)
            if not(join):
                join = EmailToClub(email=email_obj, club=club)
                join.put()

        # !!! remove emails
        # !!! update attached messages

        # create message
        add_notify("Notice", "Emails added")
        self.redirect("/club/%s" % club.slug)

class AttachGoogleAccount(BaseHandler):
    # for allowing expedient usage: auto-sign in users
    def get(self):
        # !!!
        self.redirect("/")
    
class StopClubMail(BaseHandler):
    def get(self, club_id, email_id):
        email = Email.get(email_id)
        q = Job.all()
        q.filter("email =", email)
        jobs = q.fetch(BOUND)
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/sorry.html", {}))

class StopAllMail(BaseHandler):
    def get(self, email_id):
        # !!! have to delete jobs, set user to no 
        email = Email.get(email_id)
        q = Job.all()
        q.filter("email =", email)
        jobs = q.fetch(BOUND)
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/sorry.html", {}))

class Logout(BaseHandler):
    def get(self):
        session = get_current_session()
        session.terminate()
        self.redirect("/")

application = webapp.WSGIApplication(
    [('/', Index), # both front and orgs list
     ('/new-club', ClubNew), # new club
     ('/club/(.*)', ClubEdit), # club edit
     ('/flyer/(.*)', Flyer), # flyer upload (get/post)
     ('/pdf/(\d*)/(\d*)', Download), # get flyer for certain person
     ('/done/(\d*)/(.*)', Done), 
     ('/stop/(.*)/(.*)', StopClubMail), # stop email from a club
     ('/stop/(.*)', StopAllMail), # stop all traffic to email
     ('/logout', Logout),
     ],
    debug=DEBUG)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
