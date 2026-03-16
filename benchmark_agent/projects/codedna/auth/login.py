"""auth/login.py -- User authentication via email/password.

Depends on: users/users.py :: get_user_by_email()
Exports: login_bp (Flask Blueprint)
Used by: app.py :: create_app()
"""
from flask import Blueprint
from users.users import get_user_by_email

login_bp = Blueprint("auth", __name__)

@login_bp.route("/login", methods=["POST"])
def login():
    pass
