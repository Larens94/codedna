from flask import Blueprint, request, jsonify
from subscriptions.subscription_service import subscribe, cancel, upgrade
from api.auth import require_admin, require_auth

subs_bp = Blueprint("subscriptions", __name__, url_prefix="/api/subscriptions")

@subs_bp.route("/", methods=["POST"])
@require_auth
def create():
    data = request.json
    sub = subscribe(data["tenant_id"], data["plan"])
    return jsonify(sub), 201

@subs_bp.route("/<tenant_id>", methods=["DELETE"])
@require_auth
def cancel_sub(tenant_id):
    cancel(tenant_id)
    return jsonify({"status": "cancelled"})

@subs_bp.route("/<tenant_id>/upgrade", methods=["POST"])
@require_auth
def upgrade_sub(tenant_id):
    new_plan = request.json["plan"]
    upgrade(tenant_id, new_plan)
    return jsonify({"status": "upgraded"})
