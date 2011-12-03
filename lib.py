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
    # otherwise, let it slide

# http://blog.notdot.net/2010/01/ReferenceProperty-prefetching-in-App-Engine
def prefetch_refprop(entities, prop):
    ref_keys = [prop.get_value_for_datastore(x) for x in entities]
    ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
    for entity, ref_key in zip(entities, ref_keys):
        prop.__set__(entity, ref_entities[ref_key])
    return entities

# useful constants
ERROR = -1
INIT = 0
DOWNLOADED = 1
DONE = 2
