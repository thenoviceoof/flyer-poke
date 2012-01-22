from google.appengine.api import mail
from google.appengine.runtime import apiproxy_errors
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 

from google.appengine.ext import webapp 
from google.appengine.ext.webapp.util import run_wsgi_app

import logging

from config import ADMIN_EMAIL

class SupportEmailHandler(InboundMailHandler):
    def receive(self, mail_message):
        log = logging.getLogger(__name__)
        msg = mail.EmailMessage(sender=mail_message.sender,
                                to=ADMIN_EMAIL)
        msg.subject = "[Floke Support] %s" % mail_message.subject
        msg.html    = "".join([b[1].decode() for b in mail_message.bodies()])
        try:
            msg.send()
        except apiproxy_errors.OverQuotaError, (message,):
            # Log the error
            log.error("Could not forward email")
            log.error(str(mail_message))

application = webapp.WSGIApplication([
        SupportEmailHandler.mapping()
        ], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
