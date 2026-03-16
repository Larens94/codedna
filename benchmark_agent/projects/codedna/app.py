"""app.py -- Flask application factory.

Depends on: views/dashboard.py :: register(), auth/login.py :: login_bp
Exports: create_app() -> Flask
Used by: wsgi.py
"""
from flask import Flask
from views.dashboard import register as reg_dash
from auth.login import login_bp

def create_app():
    app = Flask(__name__)
    reg_dash(app)
    app.register_blueprint(login_bp)
    return app
