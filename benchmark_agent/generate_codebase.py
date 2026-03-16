"""
generate_codebase.py — Genera le due versioni del codebase su disco.

Crea:
  projects/control/   ← 11 file Python, NESSUN docstring navigazionale
  projects/codedna/   ← stessi 11 file, con module docstring architetturali (standard v0.5)

NOTA: i docstring CodeDNA descrivono solo l'ARCHITETTURA (dipendenze, contratti, regole
di sistema). NON contengono hint sui bug. Il bug deve essere scoperto leggendo il codice.
"""

from pathlib import Path

BASE = Path(__file__).parent / "projects"

FILES = {

# ── app.py ────────────────────────────────────────────────────────────────────
"app.py": {
"control": """\
from flask import Flask
from views.dashboard import register as reg_dash
from auth.login import login_bp

def create_app():
    app = Flask(__name__)
    reg_dash(app)
    app.register_blueprint(login_bp)
    return app
""",
"codedna": """\
\"\"\"app.py -- Flask application factory.

Depends on: views/dashboard.py :: register(), auth/login.py :: login_bp
Exports: create_app() -> Flask
Used by: wsgi.py
\"\"\"
from flask import Flask
from views.dashboard import register as reg_dash
from auth.login import login_bp

def create_app():
    app = Flask(__name__)
    reg_dash(app)
    app.register_blueprint(login_bp)
    return app
"""},

# ── auth/login.py ─────────────────────────────────────────────────────────────
"auth/login.py": {
"control": """\
from flask import Blueprint
from users.users import get_user_by_email

login_bp = Blueprint("auth", __name__)

@login_bp.route("/login", methods=["POST"])
def login():
    pass
""",
"codedna": """\
\"\"\"auth/login.py -- User authentication via email/password.

Depends on: users/users.py :: get_user_by_email()
Exports: login_bp (Flask Blueprint)
Used by: app.py :: create_app()
\"\"\"
from flask import Blueprint
from users.users import get_user_by_email

login_bp = Blueprint("auth", __name__)

@login_bp.route("/login", methods=["POST"])
def login():
    pass
"""},

# ── users/users.py ────────────────────────────────────────────────────────────
"users/users.py": {
"control": """\
from db.queries import execute

def get_user_by_email(email):
    return execute("SELECT * FROM users WHERE email = ?", (email,))

def get_user(user_id):
    return execute("SELECT * FROM users WHERE id = ?", (user_id,))

def delete_user(user_id):
    # Soft delete: mantiene la riga, imposta deleted_at
    execute("UPDATE users SET deleted_at = NOW() WHERE id = ?", (user_id,))

def create_user(data):
    execute("INSERT INTO users (email, name) VALUES (?, ?)",
            (data["email"], data["name"]))
""",
"codedna": """\
\"\"\"users/users.py -- User CRUD operations.

Depends on: db/queries.py :: execute()
Exports:
    get_user_by_email(email) -> dict
    get_user(user_id) -> dict
    delete_user(user_id) -> None
    create_user(data) -> None
Used by: auth/login.py, orders/orders.py

Rules:
  - Il sistema usa SOFT DELETE: delete_user() imposta users.deleted_at = NOW().
    La riga rimane nel database. Gli utenti eliminati hanno deleted_at IS NOT NULL.
  - Chi legge o aggrega dati deve considerare se includere utenti con deleted_at != NULL.
\"\"\"
from db.queries import execute

def get_user_by_email(email):
    return execute("SELECT * FROM users WHERE email = ? AND deleted_at IS NULL", (email,))

def get_user(user_id):
    return execute("SELECT * FROM users WHERE id = ?", (user_id,))

def delete_user(user_id):
    execute("UPDATE users SET deleted_at = NOW() WHERE id = ?", (user_id,))

def create_user(data):
    execute("INSERT INTO users (email, name) VALUES (?, ?)",
            (data["email"], data["name"]))
"""},

# ── orders/orders.py ──────────────────────────────────────────────────────────
"orders/orders.py": {
"control": """\
from db.queries import execute

def create_order(user_id, items):
    execute("INSERT INTO orders (user_id, items) VALUES (?, ?)", (user_id, str(items)))

def get_active_orders():
    return execute("SELECT * FROM orders WHERE status != 'cancelled'")

def get_order(order_id):
    return execute("SELECT * FROM orders WHERE id = ?", (order_id,))
""",
"codedna": """\
\"\"\"orders/orders.py -- Order lifecycle management.

Depends on: db/queries.py :: execute(), users/users.py :: get_user()
Exports:
    create_order(user_id, items) -> None
    get_active_orders() -> list[dict]
    get_order(order_id) -> dict
Used by: analytics/revenue.py :: get_revenue_rows(), views/dashboard.py :: render()

Rules:
  - orders.user_id è una FK su users.id.
  - Il sistema utenti usa soft delete (vedi users/users.py :: delete_user() e le sue Rules).
\"\"\"
from db.queries import execute

def create_order(user_id, items):
    execute("INSERT INTO orders (user_id, items) VALUES (?, ?)", (user_id, str(items)))

def get_active_orders():
    return execute("SELECT * FROM orders WHERE status != 'cancelled'")

def get_order(order_id):
    return execute("SELECT * FROM orders WHERE id = ?", (order_id,))
"""},

# ── analytics/revenue.py ──────────────────────────────────────────────────────
"analytics/revenue.py": {
"control": """\
from orders.orders import get_active_orders

def get_revenue_rows(year=None):
    orders = get_active_orders()
    if year:
        orders = [o for o in orders if o.get("year") == year]
    return orders

def get_monthly_totals(year=None):
    rows = get_revenue_rows(year)
    totals = {}
    for row in rows:
        month = row.get("month")
        totals[month] = totals.get(month, 0) + row.get("amount", 0)
    return totals
""",
"codedna": """\
\"\"\"analytics/revenue.py -- Revenue aggregation for dashboards.

Depends on: orders/orders.py :: get_active_orders()
Exports:
    get_revenue_rows(year) -> list[dict]
    get_monthly_totals(year) -> dict
Used by: views/dashboard.py :: render()
\"\"\"
from orders.orders import get_active_orders

def get_revenue_rows(year=None):
    orders = get_active_orders()
    if year:
        orders = [o for o in orders if o.get("year") == year]
    return orders

def get_monthly_totals(year=None):
    rows = get_revenue_rows(year)
    totals = {}
    for row in rows:
        month = row.get("month")
        totals[month] = totals.get(month, 0) + row.get("amount", 0)
    return totals
"""},

# ── views/dashboard.py ────────────────────────────────────────────────────────
"views/dashboard.py": {
"control": """\
from analytics.revenue import get_revenue_rows, get_monthly_totals

def register(app):
    @app.route("/dashboard")
    def dashboard():
        return render()

def render(year=None):
    rows = get_revenue_rows(year)
    totals = get_monthly_totals(year)
    return f"<h1>Dashboard</h1><pre>{totals}</pre>"
""",
"codedna": """\
\"\"\"views/dashboard.py -- Revenue dashboard render.

Depends on: analytics/revenue.py :: get_revenue_rows(), get_monthly_totals()
Exports:
    register(app) -> None
    render(year) -> str (HTML)
Used by: app.py :: create_app()
\"\"\"
from analytics.revenue import get_revenue_rows, get_monthly_totals

def register(app):
    @app.route("/dashboard")
    def dashboard():
        return render()

def render(year=None):
    rows = get_revenue_rows(year)
    totals = get_monthly_totals(year)
    return f"<h1>Dashboard</h1><pre>{totals}</pre>"
"""},

# ── db/queries.py ─────────────────────────────────────────────────────────────
"db/queries.py": {
"control": """\
import sqlite3

_conn = None

def _get_conn():
    global _conn
    if not _conn:
        _conn = sqlite3.connect(":memory:")
    return _conn

def execute(sql, params=()):
    cur = _get_conn().execute(sql, params)
    return [dict(zip([d[0] for d in cur.description or []], row))
            for row in cur.fetchall()]
""",
"codedna": """\
\"\"\"db/queries.py -- Low-level SQL executor.

Depends on: config.py :: DB_URL
Exports:
    execute(sql, params) -> list[dict]
Used by: users/users.py, orders/orders.py, analytics/revenue.py

Rules:
  - Usare SEMPRE query parametrizzate: execute(sql, (p1, p2)).
  - Non mai interpolate user input direttamente nella stringa SQL.
\"\"\"
import sqlite3

_conn = None

def _get_conn():
    global _conn
    if not _conn:
        _conn = sqlite3.connect(":memory:")
    return _conn

def execute(sql, params=()):
    cur = _get_conn().execute(sql, params)
    return [dict(zip([d[0] for d in cur.description or []], row))
            for row in cur.fetchall()]
"""},

# ── config.py ─────────────────────────────────────────────────────────────────
"config.py": {
"control": """\
import os
DB_URL = os.getenv("DB_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
""",
"codedna": """\
\"\"\"config.py -- Environment configuration loader.

Exports: DB_URL, SECRET_KEY
Used by: db/queries.py, auth/login.py

Rules:
  - Non hardcodare secrets. Usare variabili d'ambiente.
\"\"\"
import os
DB_URL = os.getenv("DB_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
"""},

# ── products/catalog.py ───────────────────────────────────────────────────────
"products/catalog.py": {
"control": """\
from db.queries import execute

def get_product(product_id):
    return execute("SELECT * FROM products WHERE id = ?", (product_id,))

def list_products():
    return execute("SELECT * FROM products WHERE active = 1")
""",
"codedna": """\
\"\"\"products/catalog.py -- Product catalog.

Depends on: db/queries.py :: execute()
Exports: get_product(id) -> dict, list_products() -> list
Used by: orders/orders.py, views/dashboard.py
\"\"\"
from db.queries import execute

def get_product(product_id):
    return execute("SELECT * FROM products WHERE id = ?", (product_id,))

def list_products():
    return execute("SELECT * FROM products WHERE active = 1")
"""},

# ── payments/stripe.py ────────────────────────────────────────────────────────
"payments/stripe.py": {
"control": """\
import os
STRIPE_KEY = os.getenv("STRIPE_KEY")

def charge(amount_cents, token):
    return {"status": "ok", "charge_id": "ch_test"}

def refund(charge_id):
    return {"status": "refunded"}
""",
"codedna": """\
\"\"\"payments/stripe.py -- Stripe payment gateway.

Depends on: config.py :: STRIPE_KEY
Exports: charge(amount_cents, token) -> dict, refund(charge_id) -> dict
Used by: orders/orders.py :: create_order()

Rules:
  - amount_cents in CENTESIMI interi (es. 1999 = 19.99 EUR).
\"\"\"
import os
STRIPE_KEY = os.getenv("STRIPE_KEY")

def charge(amount_cents, token):
    return {"status": "ok", "charge_id": "ch_test"}

def refund(charge_id):
    return {"status": "refunded"}
"""},

# ── notifications/email.py ────────────────────────────────────────────────────
"notifications/email.py": {
"control": """\
def send_order_confirm(user_email, order_id):
    print(f"[EMAIL] order {order_id} confirmed to {user_email}")

def send_invoice(user_email, pdf_bytes):
    print(f"[EMAIL] invoice sent to {user_email}")
""",
"codedna": """\
\"\"\"notifications/email.py -- Transactional email sending.

Depends on: config.py :: SMTP_HOST
Exports: send_order_confirm(user_email, order_id), send_invoice(user_email, pdf_bytes)
Used by: orders/orders.py :: create_order()
\"\"\"
def send_order_confirm(user_email, order_id):
    print(f"[EMAIL] order {order_id} confirmed to {user_email}")

def send_invoice(user_email, pdf_bytes):
    print(f"[EMAIL] invoice sent to {user_email}")
"""},

}  # end FILES


def generate(version: str, base: Path):
    """Scrive tutti i file della versione su disco."""
    import shutil
    root = base / version
    if root.exists():
        shutil.rmtree(root)
    for filepath, contents in FILES.items():
        full = root / filepath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(contents[version], encoding="utf-8")
    for pkg in ["auth", "users", "orders", "analytics", "views", "db", "products",
                "payments", "notifications"]:
        (root / pkg / "__init__.py").touch()
    print(f"✅ {version}: {len(FILES)} file in {root}")


if __name__ == "__main__":
    BASE.mkdir(parents=True, exist_ok=True)
    generate("control", BASE)
    generate("codedna", BASE)
    print(f"\n📂 Progetti in {BASE}")
    print("  control/ → nessun docstring (navigazione cieca)")
    print("  codedna/ → module docstring con architettura (Depends on / Used by / Rules)")
    print("\nNOTA: i docstring descrivono l'architettura, NON i bug.")
    print("Il bug va scoperto leggendo la logica del codice.")
