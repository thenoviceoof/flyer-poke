from google.appengine.ext import db

class Flyer(db.Model):
    id = db.StringProperty()
    name = db.StringProperty()
    flyer = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class Email(db.Model):
    id = db.StringProperty()
    email = db.StringProperty()

class Job(db.Model):
    id = db.StringProperty()
    flyer_id = db.StringProperty()
    flyer = db.ReferenceProperty(Flyer)
    email = db.ReferenceProperty(Email)
    msg = db.StringProperty()
    count = db.IntegerProperty() # number of times
    days = db.StringProperty() # list of days
    state = db.StringProperty() # init, downloaded, done, error
    date = db.DateTimeProperty(auto_now_add=True)
