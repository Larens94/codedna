"""app.py -- Flask application factory.

Depends on: api/reports.py, api/admin.py, api/invoices.py, api/subscriptions.py
Exports: create_app() -> Flask
Used by: wsgi.py, workers/
"""
from flask import Flask
from api.reports import reports_bp
from api.admin import admin_bp
from api.invoices import invoices_bp
from api.subscriptions import subs_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(subs_bp)
    return app

if __name__ == "__main__":
    create_app().run(debug=True)
