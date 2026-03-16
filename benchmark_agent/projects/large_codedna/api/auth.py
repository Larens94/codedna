"""api/auth.py -- JWT authentication decorators.

Depends on: config.py :: JWT_SECRET
Exports: require_admin (decorator), require_auth (decorator)
Used by: api/reports.py, api/admin.py, api/invoices.py, api/subscriptions.py
"""
import jwt
from functools import wraps
from flask import request, jsonify
from config import JWT_SECRET

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            if payload.get("role") != "admin":
                return jsonify({"error": "Forbidden"}), 403
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            request.tenant_id = payload.get("tenant_id")
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
