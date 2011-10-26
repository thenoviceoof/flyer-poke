from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Flyer, Job
import logging
import urllib

from google.appengine.dist import use_library
use_library('django', '0.96')

class Index(webapp.RequestHandler):
    def get(self):
        values = {"affiliation":"Columbia University"}
        self.response.out.write(template.render("templates/index.html", values))

class Prep(webapp.RequestHandler):
    def get(self):
        self.post()
    def post(self):
        values = {}
        self.response.out.write(template.render("templates/upload.html", values))

class Upload(webapp.RequestHandler):
    def post(self):
        flyer = Flyer()
        pdf = self.request.get("flyer")
        flyer.flyer = db.Blob(pdf)
        flyer.name = self.request.get("name")
        flyer.put()
        flyer.id = str(flyer.key().id())
        flyer.put()

        recipients = self.request.get("content")
        lines = [r.split(" ") for r in recipients.strip(" \t").split("\n")
                 if len(r)>0]
        for line in lines:
            email = line[0]
            msg = " ".join(line[1:])
            job = Job(flyer_id=flyer.id, email=email, msg=msg, count=5,
                      state="init", flyer=flyer)
            job.put()

        self.response.out.write(template.render("templates/finish.html", {}))

class Pdf(webapp.RequestHandler):
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

class Done(webapp.RequestHandler):
    def get(self, flyer_id, email):
        q = Job.all()
        q.filter("email =", urllib.unquote(email))
        q.filter("flyer_id =", flyer_id)
        job = q.get()
        if job:
            job.delete()
            self.response.out.write(template.render("templates/finish.html", {}))
        else:
            self.error(404)

class Stop(webapp.RequestHandler):
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
     ('/pdf/(.*)', Pdf),
     ('/done/(\d*)/(.*)', Done),
     ('/stop/(.*)', Stop),
     ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()


