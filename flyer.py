from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Flyer, Job, Email
from lib import BaseHandler
import logging
import urllib

from google.appengine.dist import use_library
use_library('django', '0.96')

class Index(BaseHandler):
    def get(self):
        # ??? find some way to pull this out to a settings file?
        values = {"affiliation":"Columbia University"}
        self.response.out.write(template.render("templates/index.html", values))

class Prep(BaseHandler):
    def get(self):
        self.post()
    def post(self):
        values = {}
        self.response.out.write(template.render("templates/upload.html", values))

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

            job = Job(flyer=flyer, email=email_obj, flyer=flyer, done = False, state=0)
            job.put()

        self.response.out.write(template.render("templates/finish.html", {}))

class Pdf(BaseHandler):
    def get(self, id):
        flyers = db.GqlQuery("SELECT * "
                             "FROM Flyer "
                             "WHERE id=:1",
                             id)
        flyer = flyers.get()

        if flyer.flyer:
            self.response.headers['Content-Type'] = "application/pdf"
            self.response.headers['Content-Disposition'] = "attachment; filename=%s.pdf" % flyer.name
            self.response.out.write(flyer.flyer)
        else:
            self.error(404)

class Done(BaseHandler):
    def get(self, flyer_id, email):
        emailq = Email.all()
        emailq.filter("id =", email)
        e = emailq.get()

        q = Job.all()
        q.filter("email =", e)
        q.filter("flyer =", flyer_id) # ??? does this work?
        job = q.get()
        if job:
            job.state = 2 # !!! should pull out to a CONSTANT
            job.put()
            self.response.out.write(template.render("templates/finish.html", {}))
        else:
            self.error(404)

# !!! stop has to handle /stop/email/club, /stop/email
# !!! check email.html
class Stop(BaseHandler):
    def get(self, email):
        q = Job.all()
        q.filter("email =", urllib.unquote(email))
        jobs = q.fetch(BOUND)
        for job in jobs:
            job.delete()
        self.response.out.write(template.render("templates/sorry.html", {}))

application = webapp.WSGIApplication(
    [('/', Index),
     ('/flyer', Prep),
     ('/upload', Upload),
     ('/pdf/(\d*)', Pdf),
     ('/done/(\d*)/(.*)', Done),
     ('/stop/(.*)', Stop),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
