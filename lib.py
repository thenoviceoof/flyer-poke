from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api.app_identity import get_application_id

class BaseHandler(webapp.RequestHandler):
  def error(self, code):
    super(BaseHandler, self).error(code)
    if code == 404:
        self.response.out.write(template.render("templates/404.html", {}))
      # Output 404 page
