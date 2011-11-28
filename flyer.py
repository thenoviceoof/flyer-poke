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
            values = {"affiliation":"Columbia University"}
            self.response.out.write(template.render("templates/index.html",
                                                    values))

# upload page
class Flyer(BaseHandler):
    def get(self):
        values = {}
        self.response.out.write(template.render("templates/upload.html", values))

# upload handler
class Upload(BaseHandler):
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
            self.response.out.write(template.render("templates/finish.html", {}))
        else:
            self.error(404)

# !!!
class ClubEdit(BaseHandler):
    # getting the editor
    def get(self):
        pass
    # editing the club
    def post(self):
        pass

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
    # !!! out of sync, fix
    [('/', Index),
     ('/flyer/(.*)', Flyer),
     ('/upload/(.*)', Upload),
     ('/pdf/(\d*)', Pdf),
     ('/done/(\d*)/(.*)', Done),
     ('/stop/(.*)', Stop),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
