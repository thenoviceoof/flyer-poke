from gaesessions import SessionMiddleware
import datetime

def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app,
                            cookie_key="d41d8cd98f00b204e9800998ecf8427e",
                            lifetime=datetime.timedelta(hours=100))
    return app
