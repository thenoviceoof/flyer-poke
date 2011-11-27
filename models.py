from google.appengine.ext import db
from google.appengine.api import users

################################################################################
# Organizational models

# key_name replicates name
class Club(db.Model):
    name = db.StringProperty()

# token: unique identifier linked to clubs (OpenID or WIND)
class Token2Club(db.Model):
    token = db.StringProperty()
    club = db.ReferenceProperty(Club)
    # a google user, to request push rights to clubs
    user = db.UserProperty()

# many-to-many
class Email2Club(db.Model):
    email = db.ReferenceProperty(Email, required=True, collection_name="emails")
    club = db.ReferenceProperty(Club, required=True, collection_name="clubs")

################################################################################
# Flyer-sending-related models

class Email(db.Model):
    id = db.StringProperty()
    email = db.StringProperty()

class Flyer(db.Model):
    id = db.StringProperty()
    club = db.ReferenceProperty(Club)
    name = db.StringProperty()
    flyer = db.BlobProperty()
    # dates
    upload_date = db.DateTimeProperty(auto_now_add=True)
    last_sent_date = db.DateTimeProperty()
    event_date = db.DateTimeProperty()
    # for multi-week runs: date, date, date (usually Monday)
    restore_dates = db.StringProperty()

# a many-many link between flyers and emails
class Job(db.Model):
    id = db.StringProperty()
    # references
    flyer = db.ReferenceProperty(Flyer, collection_name="jobs")
    email = db.ReferenceProperty(Email, collection_name="jobs")
    # for selecting jobs not yet done
    done = db.BooleanProperty()
    # reporting: init (0), downloaded (1), done (2), error (-1)
    state = db.IntegerProperty()
    last_updated = db.DateTimeProperty(auto_now_add=True)
