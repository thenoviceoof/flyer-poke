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

################################################################################

# either front page or choose organization
class Index(BaseHandler):
    def get(self):
        session = get_current_session()
        if session.is_active():
            # serve up the club list for the user
            token = session["user"]
            token_user = Token.get_by_key_name(token)
            clubs = token_user.clubs
            values = {"clubs": clubs, "notifications": session["notify"]}
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
        club = Club.get(club_id)

        values = {"name": club.name}
        self.response.out.write(template.render("templates/upload.html", values))

    # handles the flyer upload
    def post(self, club_id):
        # get the club
        club = Club.get(club_id)

        # make a flyer
        flyer = None
        while not(flyer):
            # randomly generate a flyer key
            # ?? should we do this? don't want to leak insert times
            flyer_key = generate_hash(club_id)[:5]
            flyer = Flyer.get_or_insert(flyer_key)
            if flyer.name:
                flyer = None
        name = self.request.get("name")
        # check if the filename is a pdf
        if name[-3:] != "pdf":
            # !!! replace this with something more useful
            raise Exception("File must be a PDF")
        flyer.name = name
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
        def txn(key_name):
            made = False
            entity = Club.get_by_key_name(key_name)
            if entity is None:
                entity = Club(key_name=key_name)
                entity.put()
                made = True
            return (entity, made)
        club, made = db.run_in_transaction(txn, clubslug)
        if not(made):
            # generate an error
            add_notify("Error", "That particular name is taken. Sorry!")
            self.redirect("/")
            return
        # make a club, add current user as person
        club.name = clubname
        club.put()
        token = Token.get_or_insert(session["user"])
        join = TokenToClub(token=token, club=club)
        join.put()
        club_url = "/club/%s" % clubslug
        self.redirect(club_url)

class ClubEdit(BaseHandler):
    def get(self, club):
        # getting the editor
        club = Club.get_by_key_name(club)
        emails = list(club.emails)
        vals = {"emails": emails}
        self.response.out.write(template.render("templates/club_edit.html",
                                                vals))

    def post(self, club):
        # !!! have to have: adding, removing, updating
        # editing the club

        # !!! copied code
        recipients = self.request.get("content")
        lines = [r.split(" ") for r in recipients.strip().split("\n")
                 if len(r)>0]
        for line in lines:
            log = logging.getLogger(__name__)
            log.info(line)
            email = line[0]
            msg = " ".join(line[1:])

            email_obj = Email(email=str(email))
            email_obj.put()
            email_obj.id = str(email_obj.key().id())
            email_obj.put()
        # !!! end copied code

        email_list = self.request.get("email_list")
        club = Club.get(club)
        emails = email_list.split(",")
        cur_emails = [e.email for e in club.emails.fetch(100)]
        add_emails = [e for e in emails if not(e in cur_emails)]
        rem_emails = [e for e in cur_emails if not(e in emails)]
        # accumulate var
        email_rels = []
        for email_addr in add_emails:
            email = Email.get_or_insert(email_addr)
            email_rel = Email2Club(email = email, club = club)
            email_rels.append(email_rel)
        db.put(email_rels)
        for email_addr in rem_emails:
            # !!!
            pass
            
        # create message
        vals = {"emails":"###",
                "message":"Created successfully"}
        self.response.out.write(template.render("templates/club_edit.html",
                                                vals))

class AttachGoogleAccount(BaseHandler):
    # for allowing expedient usage: auto-sign in users
    def get(self):
        # !!!
        self.redirect("/")
    
class StopClubMail(BaseHandler):
    # !!! have to add a club_id
    def get(self, email_id):
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

application = webapp.WSGIApplication(
    [('/', Index), # both front and orgs list
     ('/new-club', ClubNew), # new club
     ('/club/(.*)', ClubEdit), # club edit
     ('/flyer/(.*)', Flyer), # flyer upload (get/post)
     ('/pdf/(\d*)/(\d*)', Download), # get flyer for certain person
     ('/done/(\d*)/(.*)', Done), 
     ('/stop/(.*)/(.*)', StopClubMail), # stop email from a club
     ('/stop/(.*)', StopAllMail), # stop all traffic to email
     ],
    debug=DEBUG)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
