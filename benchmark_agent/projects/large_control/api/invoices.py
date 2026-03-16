from flask import Blueprint, request, jsonify
from invoices.invoice_service import get_revenue_for_period, collect_payment, void_invoice
from api.auth import require_admin, require_auth

invoices_bp = Blueprint("invoices", __name__, url_prefix="/api/invoices")

@invoices_bp.route("/period", methods=["GET"])
@require_admin
def period():
    year = int(request.args.get("year", 2025))
    month = int(request.args.get("month", 1))
    return jsonify(get_revenue_for_period(year, month))

@invoices_bp.route("/<invoice_id>/pay", methods=["POST"])
@require_auth
def pay(invoice_id):
    pm = request.json["payment_method"]
    charge = collect_payment(invoice_id, pm)
    return jsonify(charge)

@invoices_bp.route("/<invoice_id>/void", methods=["POST"])
@require_admin
def void(invoice_id):
    void_invoice(invoice_id)
    return jsonify({"status": "voided"})
