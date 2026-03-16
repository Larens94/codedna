from flask import Blueprint, request, jsonify
from tenants.tenant_service import suspend, reactivate, list_tenants_for_billing
from api.auth import require_admin

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.route("/tenants", methods=["GET"])
@require_admin
def tenants():
    return jsonify(list_tenants_for_billing())

@admin_bp.route("/tenants/<tid>/suspend", methods=["POST"])
@require_admin
def suspend_tenant(tid):
    reason = request.json.get("reason", "")
    suspend(tid, reason)
    return jsonify({"status": "suspended"})

@admin_bp.route("/tenants/<tid>/reactivate", methods=["POST"])
@require_admin
def reactivate_tenant(tid):
    reactivate(tid)
    return jsonify({"status": "active"})
