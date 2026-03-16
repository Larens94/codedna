from flask import Blueprint
from users.users import get_user_by_email

login_bp = Blueprint("auth", __name__)

@login_bp.route("/login", methods=["POST"])
def login():
    pass
