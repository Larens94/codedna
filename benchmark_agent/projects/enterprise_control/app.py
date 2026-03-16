import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

from flask import Flask
from api.products import products_bp
from api.orders import orders_bp
from api.reports import reports_bp
from api.admin import admin_bp
from api.webhooks import webhooks_bp
from api.auth_api import auth_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(auth_bp)
    return app
