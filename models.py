from google.appengine.ext import db
from google.appengine.api import users

################################################################################
# Organizational models

# key replicates name, but as a slug (letters/numbers only)
class Club(db.Model):
    name = db.StringProperty()
    # url-friendly name
    slug = db.StringProperty()
    # for a cron job that emails the super-admin new clubs
    new  = db.BooleanProperty()

# token: unique identifier linked to clubs (OpenID or WIND)
class Token(db.Model):
    token = db.StringProperty()
    # a google user, to allow auto sign in
    user = db.UserProperty()

# maps login tokens (admins) to clubs
class Token2Club(db.Model):
    token = db.ReferenceProperty(Club, required=True, collection_name="tokens")
    club = db.ReferenceProperty(Club, required=True, collection_name="clubs")

# maps emails to clubs
class Email2Club(db.Model):
    email = db.ReferenceProperty(Email, required=True, collection_name="emails")
    club = db.ReferenceProperty(Club, required=True, collection_name="clubs")
    # message attached to emails: for instance, flyering locations
    message = db.StringProperty()
    # switch to disable abuse/spam from different clubs
    enable = db.BooleanProperty(default=True)

################################################################################
# Flyer-sending-related models

class Email(db.Model):
    email = db.StringProperty()
    # either banhammer, or request to not have the service
    enable = db.BooleanProperty(default=True)

class Flyer(db.Model):
    id = db.StringProperty()
    # a flyer belongs to only one club
    club = db.ReferenceProperty(Club)
    # human-readable handle - used in nag emails
    name = db.StringProperty()
    # !!! change to blobstore, possibly in branch
    flyer = db.BlobProperty()
    # count how many times the jobs have been renewed (aka monday)
    renewal = db.IntegerProperty()
    # timestamps
    upload_date = db.DateTimeProperty(auto_now_add=True)
    last_sent_date = db.DateTimeProperty()
    event_date = db.DateTimeProperty()
    # for multi-week runs: date, date, date (usually Monday)
    restore_dates = db.StringProperty()

# a many-many link between flyers and emails
class Job(db.Model):
    # references
    flyer = db.ReferenceProperty(Flyer, collection_name="jobs")
    email = db.ReferenceProperty(Email, collection_name="jobs")
    # current job renewal
    renewal = db.IntegerProperty()
    # reporting: init (0), downloaded (1), done (2), error (-1)
    # however, error is never used
    state = db.IntegerProperty()
    last_updated = db.DateTimeProperty(auto_now_add=True)
