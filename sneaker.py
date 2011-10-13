from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class Flyer(db.Model):
    id = db.StringProperty()
    flyer = db.BlobProperty()
    recipients = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class Index(webapp.RequestHandler):
    def get(self):
        values = {}
        self.response.out.write(template.render("templates/upload.html", values))

class Upload(webapp.RequestHandler):
    def post(self):
        flyer = Flyer()
        flyer.recipients = self.request.get("content")
        pdf = self.request.get("flyer")
        flyer.flyer = db.Blob(pdf)
        flyer.put()
        flyer.id = str(flyer.key().id())
        flyer.put()

        values = {}
        self.response.out.write(template.render("templates/finish.html", values))

class Admin(webapp.RequestHandler):
    def get(self):
        flyer_req = db.GqlQuery("SELECT * "
                                "FROM Flyer")
        flyers = flyer_req.fetch(10)

        values = {"flyers":flyers}
        self.response.out.write(template.render("templates/list.html", values))

class Pdf(webapp.RequestHandler):
    def get(self, id):
        flyers = db.GqlQuery("SELECT * "
                             "FROM Flyer "
                             "WHERE id=:1",
                             id)
        flyer = flyers.fetch(1)[0]

        if flyer.flyer:
            self.response.headers['Content-Type'] = "application/pdf"
            self.response.out.write(flyer.flyer)
        else:
            self.error(404)


application = webapp.WSGIApplication(
    [('/', Index),
     ('/upload', Upload),
     ('/admin', Admin),
     ('/pdf/(\d*)',Pdf)],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

