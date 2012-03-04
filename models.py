from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.api import users

################################################################################
# Organizational models

# key replicates name, but as a slug (letters/numbers only)
class Club(db.Model):
    name = db.StringProperty()
    # internet-friendly short name, also the key
    slug = db.StringProperty()
    # for a cron job that emails the super-admin new clubs
    new  = db.BooleanProperty(default=True)
    # timestamps
    created_at = db.DateTimeProperty(auto_now_add=True)

################################################################################
# Flyer-sending-related models

class Email(db.Model):
    # stores the hash in a easy to access place
    id = db.StringProperty()
    email = db.StringProperty()
    # either banhammer, or request to not have the service
    enable = db.BooleanProperty(default=True)
    # if they have this, they've signed into the service
    user = db.UserProperty()
    user_enable = db.BooleanProperty(default=False)
    # the key for linking through email
    user_request_key = db.StringProperty()
    # when admin rights were requested: timeout for the request key
    user_request_time = db.DateTimeProperty()
    # timestamps
    created_at = db.DateTimeProperty(auto_now_add=True)

class Flyer(db.Model):
    # stores the hash in a easy to access place
    id = db.StringProperty()
    # a flyer belongs to only one club
    club = db.ReferenceProperty(Club)
    # human-readable handle - used in nag emails
    name = db.StringProperty()
    # keeps the blobstore key around
    flyer = blobstore.BlobReferenceProperty()
    # whether the flyer's event_date has passed yet
    active = db.BooleanProperty(default=True)
    # count how many times the jobs have been renewed (aka monday)
    renewal = db.IntegerProperty()
    # timestamps
    upload_date = db.DateTimeProperty(auto_now_add=True)
    last_sent_date = db.DateTimeProperty()
    event_date = db.DateTimeProperty()

# a many-many link between flyers and emails
class Job(db.Model):
    # stores the hash in a easy to access place
    id = db.StringProperty()
    # references
    flyer = db.ReferenceProperty(Flyer, collection_name="jobs")
    email = db.ReferenceProperty(Email, collection_name="jobs")
    # current job renewal
    renewal = db.IntegerProperty(default=0)
    # whether the current renewal is active
    active = db.BooleanProperty(default=True)
    # reporting: init (0), downloaded (1), done (2), error (-1)
    # however, error is never used?
    state = db.IntegerProperty(default=0)
    last_updated = db.DateTimeProperty(auto_now_add=True)
    # timestamps
    created_at = db.DateTimeProperty(auto_now_add=True)

################################################################################
# Mappings

# maps emails to clubs
class EmailToClub(db.Model):
    email = db.ReferenceProperty(Email, required=True, collection_name="clubs")
    club = db.ReferenceProperty(Club, required=True, collection_name="emails")
    # message attached to emails: for instance, flyering locations
    message = db.StringProperty()
    # switch to disable abuse/spam from different clubs
    enable = db.BooleanProperty(default=True)
    # admin
    admin = db.BooleanProperty(default=False)
    # timestamps
    created_at = db.DateTimeProperty(auto_now_add=True)
