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

# useful constants
ERROR = -1
INIT = 0
DOWNLOADED = 1
DONE = 2

# http://blog.notdot.net/2010/01/ReferenceProperty-prefetching-in-App-Engine
def prefetch_refprop(entities, prop):
    ref_keys = [prop.get_value_for_datastore(x) for x in entities]
    ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
    for entity, ref_key in zip(entities, ref_keys):
        prop.__set__(entity, ref_entities[ref_key])
    return entities

# generate hashes
def generate_hash(base):
    md5 = hashlib.md5()
    md5.update(base)
    return md5.hexdigest()
def generate_random_hash(base):
    return generate_hash(base + str(time.time()))

# slugs
def slugify(s):
    return re.sub("\W",'', s).lower()

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
