from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Flyer, Job, Email, Token, Club
from lib import *
import logging
from gaesessions import get_current_session

from google.appengine.dist import use_library
use_library('django', '0.96')

from config import AFFILIATION

# either front page or choose organization
class Index(BaseHandler):
    def get(self):
        # grab relevant orgs
        session = get_current_session()
        if session.is_active():
            token = session["user"]
            token_user = Token.get(token)
            clubs = token_user.clubs
            if len(clubs) == 1:
                self.redirect("/flyer/{0}".format(clubs[0].name))
            values = {"clubs": clubs}
            self.response.out.write(template.render("templates/orgs.html",
                                                    values))
        else:
            # ??? find some way to pull this out to a settings file?
            values = {"affiliation":AFFILIATION}
            self.response.out.write(template.render("templates/index.html",
                                                    values))

# upload flyer
class Flyer(BaseHandler):
    def get(self):
        values = {}
        self.response.out.write(template.render("templates/upload.html", values))

    def post(self):
        flyer = Flyer()
        pdf = self.request.get("flyer")
        flyer.flyer = db.Blob(pdf)
        flyer.name = self.request.get("name")
        flyer.put()
        flyer.id = str(flyer.key().id())
        flyer.put()

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

            job = Job(flyer=flyer, email=email_obj, flyer=flyer, done = False,
                      state=INIT)
            job.put()

        self.response.out.write(template.render("templates/finish.html", {}))

# allow anon downloads (?)
class Pdf(BaseHandler):
    def get(self, flyer_id):
        flyer = Flyer.get(flyer_id)

        if flyer.flyer:
            self.response.headers['Content-Type'] = "application/pdf"
            self.response.headers['Content-Disposition'] = \
                "attachment; filename=%s.pdf" % flyer.name
            self.response.out.write(flyer.flyer)
        else:
            self.error(404)

# track downloads
class PdfPersonal(BaseHandler):
    def get(self, flyer_id, email_id):
        flyer = Flyer.get(flyer_id)
        email = Email.get(email_id)
        job = Job.all().filter("flyer =", flyer).filter("email = ", email).get()

        if flyer.flyer:
            job.state = DOWNLOADED
            job.put()
            self.response.headers['Content-Type'] = "application/pdf"
            self.response.headers['Content-Disposition'] = \
                "attachment; filename=%s.pdf" % flyer.name
            self.response.out.write(flyer.flyer)
        else:
            self.error(404)

class Done(BaseHandler):
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

class ClubEdit(BaseHandler):
    def get(self, club):
        # getting the editor
        club = Club.get(club)
        emails = str(list(club.emails))
        vals = {"emails": emails}
        self.response.out.write(template.render("templates/club_edit.html",
                                                vals))

    # !!!
    def post(self, club):
        # editing the club
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
            
        # create message
        vals = {"emails":"###",
                "message":"Created successfully"}
        self.response.out.write(template.render("templates/club_edit.html",
                                                vals))

class StopClub(BaseHandler):
    def get(self, email_id):
        email = Email.get(email_id)
        q = Job.all()
        q.filter("email =", email)
        jobs = q.fetch(BOUND)
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/sorry.html", {}))

class StopAll(BaseHandler):
    def get(self, email_id):
        email = Email.get(email_id)
        q = Job.all()
        q.filter("email =", email)
        jobs = q.fetch(BOUND)
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/sorry.html", {}))

application = webapp.WSGIApplication(
    [('/', Index), # both front and orgs list
     ('/org/(.*)'), # club edit
     ('/flyer/(.*)', Flyer), # flyer upload (get/post)
     ('/pdf/(\d*)', Pdf), # get flyer
     ('/pdf/(\d*)/(\d*)', PersonalPdf), # get flyer for certain person
     ('/done/(\d*)/(.*)', Done), 
     ('/stop/(.*)/(.*)', StopClub), # stop email from a club
     ('/stop/(.*)', StopAll), # stop all traffic to email
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
