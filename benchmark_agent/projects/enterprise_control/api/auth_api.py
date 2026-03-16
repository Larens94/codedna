import os
import json
import logging
from core.db import execute, execute_one
from core.config import *
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def login_route():
    data = request.json
    result = login(data['email'], data['password'])
    return jsonify(result)
