from google.appengine.ext import db

class Flyer(db.Model):
    id = db.StringProperty()
    flyer = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class Job(db.Model):
    id = db.StringProperty()
    flyer = db.StringProperty()
    email = db.StringProperty()
    msg = db.StringProperty()
    count = db.IntegerProperty() # number of 
    state = db.StringProperty() # init, down, done, error
    date = db.DateTimeProperty(auto_now_add=True)
