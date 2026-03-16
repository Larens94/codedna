"""
arch.py — Architecture registry for the enterprise codebase generator.

Each entry: (path, depends_on, exports, rules, functions)
  functions = list of (name, params, body_lines)
  rules = list of strings — architectural constraints (NO bug hints)
"""

# ── BUGS hidden in the codebase ───────────────────────────────────────────────
# B1: analytics/revenue.py sums invoices without filtering suspended tenants
# B2: products/inventory.py uses non-atomic check+decrement (race condition)
# B3: api/products.py checks user["is_admin"] but field is user["role"]=="admin"
# B4: payments/invoices.py re-applies TAX_RATE already applied in orders/checkout.py
# B5: orders/fulfillment.py marks order fulfilled but never decrements inventory

# ── TASKS to complete ─────────────────────────────────────────────────────────
# T1: Add discount_code support to orders/cart.py + orders/checkout.py + payments/invoices.py
# T2: Add /admin/tenants/<id>/usage endpoint (api/admin.py + analytics/usage.py)
# T3: Add low-stock email notification in products/inventory.py + notifications/email.py

ARCH = [

# ── core ──────────────────────────────────────────────────────────────────────
{
"path": "core/config.py",
"depends_on": [],
"exports": ["DB_URL", "REDIS_URL", "STRIPE_KEY", "TAX_RATE", "CURRENCY", "MAX_SEATS", "JWT_SECRET", "SMTP_HOST", "LOW_STOCK_THRESHOLD"],
"rules": [
    "Never hardcode secrets. Always load from environment variables.",
    "TAX_RATE is 0.22 (22%). Applied once in payments/invoices.py :: create_invoice().",
    "LOW_STOCK_THRESHOLD = 10 units. Used by products/inventory.py.",
],
"functions": [
    ("_env", ["key", "default=''"], ["return os.getenv(key, default)"]),
]
},

{
"path": "core/db.py",
"depends_on": ["core/config.py :: DB_URL"],
"exports": ["execute(sql, params) -> list[dict]", "execute_one(sql, params) -> dict | None", "transaction()"],
"rules": [
    "Always use parameterized queries: execute(sql, (p1, p2)).",
    "Never interpolate user input into SQL strings directly.",
],
"functions": [
    ("execute", ["sql: str", "params: tuple = ()"], [
        "cur = _get_conn().cursor()",
        "cur.execute(sql, params)",
        "if cur.description:",
        "    cols = [d[0] for d in cur.description]",
        "    return [dict(zip(cols, row)) for row in cur.fetchall()]",
        "_get_conn().commit(); return []",
    ]),
    ("execute_one", ["sql: str", "params: tuple = ()"], [
        "rows = execute(sql, params)",
        "return rows[0] if rows else None",
    ]),
]
},

{
"path": "core/cache.py",
"depends_on": ["core/config.py :: REDIS_URL"],
"exports": ["cache_get(key) -> str | None", "cache_set(key, value, ttl=300)", "cache_del(key)", "cache_invalidate_prefix(prefix)"],
"rules": [
    "TTL default 300s. For user sessions use ttl=3600.",
    "Key naming: '<module>:<entity_id>' e.g. 'product:42'.",
],
"functions": [
    ("cache_get", ["key: str"], ["val = _r().get(key)", "return val.decode() if val else None"]),
    ("cache_set", ["key: str", "value: str", "ttl: int = 300"], ["_r().setex(key, ttl, value)"]),
    ("cache_del", ["key: str"], ["_r().delete(key)"]),
    ("cache_invalidate_prefix", ["prefix: str"], ["keys = _r().keys(f'{prefix}:*')", "if keys: _r().delete(*keys)"]),
]
},

{
"path": "core/events.py",
"depends_on": ["core/cache.py", "core/db.py"],
"exports": ["emit(event_name, payload) -> None", "subscribe(event_name, handler) -> None"],
"rules": [
    "Events are fire-and-forget. Do not rely on them for transactional consistency.",
    "Standard events: order.created, order.fulfilled, payment.received, tenant.suspended.",
],
"functions": [
    ("emit", ["event_name: str", "payload: dict"], [
        "_handlers = _registry.get(event_name, [])",
        "for h in _handlers: h(payload)",
    ]),
    ("subscribe", ["event_name: str", "handler"], [
        "_registry.setdefault(event_name, []).append(handler)",
    ]),
]
},

{
"path": "core/auth.py",
"depends_on": ["core/config.py :: JWT_SECRET"],
"exports": ["sign_token(user_id, role, tenant_id) -> str", "verify_token(token) -> dict", "require_auth (decorator)", "require_admin (decorator)"],
"rules": [
    "JWT payload contains: user_id, role, tenant_id.",
    "role values: 'admin', 'owner', 'member', 'viewer'.",
    "require_admin checks payload['role'] == 'admin'. Do NOT use user['is_admin'].",
],
"functions": [
    ("sign_token", ["user_id: str", "role: str", "tenant_id: str"], [
        "return jwt.encode({'user_id': user_id, 'role': role, 'tenant_id': tenant_id}, JWT_SECRET, algorithm='HS256')",
    ]),
    ("verify_token", ["token: str"], [
        "return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])",
    ]),
]
},

# ── tenants ───────────────────────────────────────────────────────────────────
{
"path": "tenants/models.py",
"depends_on": ["core/db.py :: execute", "core/db.py :: execute_one"],
"exports": [
    "get_tenant(id) -> dict | None",
    "list_active_tenants() -> list[dict]",
    "create_tenant(name, plan, owner_email) -> dict",
    "suspend_tenant(id) -> None",
    "reactivate_tenant(id) -> None",
    "delete_tenant(id) -> None",
    "is_suspended(tenant) -> bool",
],
"rules": [
    "Tenants use SOFT SUSPEND: suspend_tenant() sets suspended_at=NOW(). Row stays in DB.",
    "Tenants use SOFT DELETE: delete_tenant() sets deleted_at=NOW().",
    "list_active_tenants() filters WHERE suspended_at IS NULL AND deleted_at IS NULL.",
    "Any query aggregating data per-tenant MUST decide whether to exclude suspended tenants.",
    "is_suspended(tenant) returns True if tenant['suspended_at'] is not None.",
],
"functions": [
    ("get_tenant", ["tenant_id: str"], ["return execute_one('SELECT * FROM tenants WHERE id = %s', (tenant_id,))"]),
    ("list_active_tenants", [], ["return execute('SELECT * FROM tenants WHERE suspended_at IS NULL AND deleted_at IS NULL')"]),
    ("suspend_tenant", ["tenant_id: str"], ["execute('UPDATE tenants SET suspended_at = NOW() WHERE id = %s', (tenant_id,))"]),
    ("is_suspended", ["tenant: dict"], ["return tenant.get('suspended_at') is not None"]),
]
},

{
"path": "tenants/service.py",
"depends_on": ["tenants/models.py", "subscriptions/models.py :: get_by_tenant", "notifications/email.py :: send_suspension_notice"],
"exports": ["onboard(name, plan, owner_email) -> dict", "suspend(tenant_id, reason) -> None", "reactivate(tenant_id) -> None", "get_details(tenant_id) -> dict"],
"rules": [
    "suspend() calls tenants/models.py :: suspend_tenant() then sends email notification.",
    "Suspended tenants retain their data but cannot login or use the API.",
],
"functions": [
    ("suspend", ["tenant_id: str", "reason: str = ''"], [
        "tenant = get_tenant(tenant_id)",
        "suspend_tenant(tenant_id)",
        "send_suspension_notice(tenant['owner_email'], tenant_id, reason)",
    ]),
]
},

{
"path": "tenants/limits.py",
"depends_on": ["tenants/models.py :: get_tenant", "users/models.py :: count_users_by_tenant", "products/models.py :: count_products_by_tenant"],
"exports": ["check_seat_limit(tenant_id) -> bool", "check_product_limit(tenant_id) -> bool", "get_limits(tenant_id) -> dict"],
"rules": [
    "Plan limits: starter=5 seats/100 products, growth=25/1000, business=100/10000.",
    "check_seat_limit() returns True if under limit (OK to add user).",
],
"functions": [
    ("check_seat_limit", ["tenant_id: str"], [
        "tenant = get_tenant(tenant_id)",
        "plan = tenant['plan']",
        "limit = PLAN_LIMITS[plan]['seats']",
        "current = count_users_by_tenant(tenant_id)",
        "return current < limit",
    ]),
]
},

{
"path": "tenants/billing.py",
"depends_on": ["tenants/models.py :: list_active_tenants", "subscriptions/models.py :: get_by_tenant", "payments/invoices.py :: create_invoice"],
"exports": ["bill_all_tenants(year, month) -> list[dict]", "bill_tenant(tenant_id, year, month) -> dict"],
"rules": [
    "bill_all_tenants() only bills ACTIVE tenants (list_active_tenants() already filters suspended).",
    "Uses subscriptions/models.py :: get_by_tenant() to get current plan price.",
],
"functions": [
    ("bill_all_tenants", ["year: int", "month: int"], [
        "tenants = list_active_tenants()",
        "results = []",
        "for t in tenants:",
        "    try: results.append(bill_tenant(t['id'], year, month))",
        "    except Exception as e: log(f'Billing failed for {t[\"id\"]}: {e}')",
        "return results",
    ]),
]
},

# ── users ─────────────────────────────────────────────────────────────────────
{
"path": "users/models.py",
"depends_on": ["core/db.py :: execute", "core/db.py :: execute_one"],
"exports": [
    "get_user(id) -> dict | None",
    "get_user_by_email(email) -> dict | None",
    "create_user(tenant_id, email, name, role) -> dict",
    "update_user(id, data) -> dict",
    "deactivate_user(id) -> None",
    "count_users_by_tenant(tenant_id) -> int",
],
"rules": [
    "User roles: 'admin', 'owner', 'member', 'viewer'.",
    "The role field is users.role (string). There is NO boolean is_admin field.",
    "To check admin: user['role'] == 'admin'. NEVER check user['is_admin'].",
    "deactivate_user() sets active=False (soft deactivation).",
],
"functions": [
    ("get_user", ["user_id: str"], ["return execute_one('SELECT * FROM users WHERE id = %s', (user_id,))"]),
    ("get_user_by_email", ["email: str"], ["return execute_one('SELECT * FROM users WHERE email = %s AND active = TRUE', (email,))"]),
    ("create_user", ["tenant_id: str", "email: str", "name: str", "role: str = 'member'"], [
        "return execute_one('INSERT INTO users (tenant_id, email, name, role) VALUES (%s,%s,%s,%s) RETURNING *', (tenant_id, email, name, role))",
    ]),
    ("count_users_by_tenant", ["tenant_id: str"], [
        "row = execute_one('SELECT COUNT(*) as n FROM users WHERE tenant_id = %s AND active = TRUE', (tenant_id,))",
        "return row['n'] if row else 0",
    ]),
]
},

{
"path": "users/auth.py",
"depends_on": ["users/models.py :: get_user_by_email", "core/auth.py :: sign_token", "core/cache.py :: cache_set"],
"exports": ["login(email, password) -> dict", "logout(token) -> None", "refresh(token) -> str"],
"rules": [
    "Passwords are bcrypt-hashed. Never store plaintext.",
    "Session tokens are JWTs signed with JWT_SECRET from core/config.py.",
    "login() returns {token, user} dict.",
],
"functions": [
    ("login", ["email: str", "password: str"], [
        "user = get_user_by_email(email)",
        "if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):",
        "    raise ValueError('Invalid credentials')",
        "token = sign_token(user['id'], user['role'], user['tenant_id'])",
        "return {'token': token, 'user': user}",
    ]),
]
},

{
"path": "users/service.py",
"depends_on": ["users/models.py", "tenants/limits.py :: check_seat_limit", "notifications/email.py :: send_welcome"],
"exports": ["invite_user(tenant_id, email, name, role) -> dict", "deactivate(user_id) -> None", "change_role(user_id, new_role) -> None"],
"rules": [
    "invite_user() checks tenants/limits.py :: check_seat_limit() before creating.",
    "Raises SeatLimitError if tenant is at capacity.",
],
"functions": [
    ("invite_user", ["tenant_id: str", "email: str", "name: str", "role: str = 'member'"], [
        "if not check_seat_limit(tenant_id): raise SeatLimitError('Seat limit reached')",
        "user = create_user(tenant_id, email, name, role)",
        "send_welcome(email, name)",
        "return user",
    ]),
]
},

{
"path": "users/permissions.py",
"depends_on": ["users/models.py :: get_user", "tenants/models.py :: get_tenant"],
"exports": ["can_edit_product(user_id) -> bool", "can_manage_users(user_id) -> bool", "can_view_reports(user_id) -> bool", "require_role(role) -> decorator"],
"rules": [
    "Permissions are role-based. admin > owner > member > viewer.",
    "can_edit_product: role in ('admin', 'owner', 'member').",
    "can_manage_users: role in ('admin', 'owner').",
    "can_view_reports: role in ('admin', 'owner').",
],
"functions": [
    ("can_edit_product", ["user_id: str"], [
        "user = get_user(user_id)",
        "return user['role'] in ('admin', 'owner', 'member')",
    ]),
    ("can_manage_users", ["user_id: str"], [
        "user = get_user(user_id)",
        "return user['role'] in ('admin', 'owner')",
    ]),
]
},

{
"path": "users/profiles.py",
"depends_on": ["users/models.py :: get_user", "users/models.py :: update_user", "core/cache.py :: cache_set"],
"exports": ["get_profile(user_id) -> dict", "update_profile(user_id, data) -> dict", "update_avatar(user_id, url) -> None"],
"rules": [
    "Profile data is cached in Redis with key 'profile:<user_id>' TTL=600.",
    "update_profile() invalidates cache.",
],
"functions": [
    ("get_profile", ["user_id: str"], [
        "cached = cache_get(f'profile:{user_id}')",
        "if cached: return json.loads(cached)",
        "user = get_user(user_id)",
        "cache_set(f'profile:{user_id}', json.dumps(user), ttl=600)",
        "return user",
    ]),
]
},

# ── products ──────────────────────────────────────────────────────────────────
{
"path": "products/models.py",
"depends_on": ["core/db.py :: execute", "core/db.py :: execute_one"],
"exports": [
    "get_product(id) -> dict | None",
    "list_products(tenant_id, filters) -> list[dict]",
    "create_product(tenant_id, data) -> dict",
    "update_product(id, data) -> dict",
    "delete_product(id) -> None",
    "count_products_by_tenant(tenant_id) -> int",
],
"rules": [
    "Products are tenant-scoped: always filter by tenant_id.",
    "delete_product() is a soft delete: sets deleted_at=NOW().",
    "price_cents is in INTEGER CENTS (e.g. 2999 = €29.99). Never store floats.",
],
"functions": [
    ("get_product", ["product_id: str"], ["return execute_one('SELECT * FROM products WHERE id = %s AND deleted_at IS NULL', (product_id,))"]),
    ("list_products", ["tenant_id: str", "filters: dict = {}"], [
        "sql = 'SELECT * FROM products WHERE tenant_id = %s AND deleted_at IS NULL'",
        "params = [tenant_id]",
        "if filters.get('category'): sql += ' AND category = %s'; params.append(filters['category'])",
        "return execute(sql, tuple(params))",
    ]),
    ("count_products_by_tenant", ["tenant_id: str"], [
        "row = execute_one('SELECT COUNT(*) as n FROM products WHERE tenant_id = %s AND deleted_at IS NULL', (tenant_id,))",
        "return row['n'] if row else 0",
    ]),
]
},

{
"path": "products/inventory.py",
"depends_on": ["core/db.py :: execute", "core/db.py :: execute_one", "core/config.py :: LOW_STOCK_THRESHOLD"],
"exports": [
    "get_stock(product_id) -> int",
    "check_stock(product_id, qty) -> bool",
    "decrement_stock(product_id, qty) -> None",
    "increment_stock(product_id, qty) -> None",
    "is_low_stock(product_id) -> bool",
],
"rules": [
    "Stock values are stored in products.stock_qty (integer).",
    "check_stock() and decrement_stock() are SEPARATE calls — not atomic.",
    "For high-concurrency safety, use a single UPDATE ... WHERE stock_qty >= qty instead.",
    "is_low_stock() returns True if stock_qty < LOW_STOCK_THRESHOLD (from core/config.py).",
    "T3: When is_low_stock() is True after decrement, emit notification via notifications/email.py.",
],
"functions": [
    ("get_stock", ["product_id: str"], [
        "row = execute_one('SELECT stock_qty FROM products WHERE id = %s', (product_id,))",
        "return row['stock_qty'] if row else 0",
    ]),
    ("check_stock", ["product_id: str", "qty: int"], [
        "return get_stock(product_id) >= qty",
    ]),
    ("decrement_stock", ["product_id: str", "qty: int"], [
        "execute('UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s', (qty, product_id))",
    ]),
    ("is_low_stock", ["product_id: str"], [
        "return get_stock(product_id) < LOW_STOCK_THRESHOLD",
    ]),
]
},

{
"path": "products/catalog.py",
"depends_on": ["products/models.py :: list_products", "core/cache.py :: cache_get", "core/cache.py :: cache_set"],
"exports": ["get_catalog(tenant_id, filters) -> list[dict]", "get_product_detail(product_id) -> dict", "get_featured(tenant_id) -> list[dict]"],
"rules": [
    "Catalog is cached per tenant with key 'catalog:<tenant_id>' TTL=120.",
    "Featured products: products WHERE featured=TRUE AND stock_qty > 0.",
],
"functions": [
    ("get_catalog", ["tenant_id: str", "filters: dict = {}"], [
        "key = f'catalog:{tenant_id}'",
        "cached = cache_get(key)",
        "if cached and not filters: return json.loads(cached)",
        "products = list_products(tenant_id, filters)",
        "if not filters: cache_set(key, json.dumps(products), ttl=120)",
        "return products",
    ]),
]
},

{
"path": "products/pricing.py",
"depends_on": ["products/models.py :: get_product", "tenants/models.py :: get_tenant"],
"exports": ["get_price(product_id, tenant_id) -> int", "apply_volume_discount(base_price, qty) -> int", "get_price_with_tax(product_id) -> int"],
"rules": [
    "All prices are in INTEGER CENTS.",
    "Tax is NOT applied here. Tax is applied in payments/invoices.py :: create_invoice().",
    "Volume discount: qty>=10 -5%, qty>=50 -10%, qty>=100 -15%.",
],
"functions": [
    ("get_price", ["product_id: str", "tenant_id: str | None = None"], [
        "product = get_product(product_id)",
        "return product['price_cents']",
    ]),
    ("apply_volume_discount", ["base_price: int", "qty: int"], [
        "if qty >= 100: return round(base_price * 0.85)",
        "if qty >= 50:  return round(base_price * 0.90)",
        "if qty >= 10:  return round(base_price * 0.95)",
        "return base_price",
    ]),
]
},

{
"path": "products/search.py",
"depends_on": ["products/models.py :: list_products", "core/cache.py :: cache_get"],
"exports": ["search(tenant_id, query) -> list[dict]", "suggest(tenant_id, prefix) -> list[str]"],
"rules": ["Search is case-insensitive. Results limited to 50."],
"functions": [
    ("search", ["tenant_id: str", "query: str"], [
        "from core.db import execute",
        "return execute('SELECT * FROM products WHERE tenant_id = %s AND (name ILIKE %s OR sku ILIKE %s) AND deleted_at IS NULL LIMIT 50', (tenant_id, f'%{query}%', f'%{query}%'))",
    ]),
]
},

{
"path": "products/service.py",
"depends_on": ["products/models.py", "products/inventory.py", "tenants/limits.py :: check_product_limit", "core/events.py :: emit"],
"exports": ["create(tenant_id, data) -> dict", "update(product_id, data) -> dict", "delete(product_id) -> None", "restock(product_id, qty) -> None"],
"rules": [
    "create() checks tenants/limits.py :: check_product_limit() first.",
    "After create/update, emit 'product.updated' event via core/events.py.",
    "restock() calls products/inventory.py :: increment_stock().",
],
"functions": [
    ("create", ["tenant_id: str", "data: dict"], [
        "if not check_product_limit(tenant_id): raise ProductLimitError('Product limit reached')",
        "product = create_product(tenant_id, data)",
        "emit('product.updated', {'tenant_id': tenant_id, 'product_id': product['id']})",
        "return product",
    ]),
]
},

# ── orders ────────────────────────────────────────────────────────────────────
{
"path": "orders/models.py",
"depends_on": ["core/db.py :: execute", "core/db.py :: execute_one"],
"exports": [
    "get_order(id) -> dict | None",
    "list_orders(tenant_id, status) -> list[dict]",
    "create_order(tenant_id, user_id, items, total_cents) -> dict",
    "update_status(order_id, status) -> None",
    "get_orders_for_period(year, month) -> list[dict]",
],
"rules": [
    "Order statuses: 'pending', 'confirmed', 'fulfilled', 'cancelled', 'returned'.",
    "orders.tenant_id is FK on tenants.id (soft-suspend applies).",
    "get_orders_for_period() does NOT filter by tenant.suspended_at.",
    "total_cents includes tax. See payments/invoices.py :: create_invoice() for tax logic.",
],
"functions": [
    ("get_order", ["order_id: str"], ["return execute_one('SELECT * FROM orders WHERE id = %s', (order_id,))"]),
    ("get_orders_for_period", ["year: int", "month: int"], [
        "return execute('SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))",
    ]),
]
},

{
"path": "orders/cart.py",
"depends_on": ["products/models.py :: get_product", "products/inventory.py :: check_stock", "core/cache.py :: cache_get", "core/cache.py :: cache_set"],
"exports": ["add_item(session_id, product_id, qty) -> dict", "remove_item(session_id, product_id) -> None", "get_cart(session_id) -> dict", "clear_cart(session_id) -> None"],
"rules": [
    "Cart is stored in Redis with key 'cart:<session_id>' TTL=3600.",
    "add_item() checks products/inventory.py :: check_stock() before adding.",
    "T1: Cart should support an optional discount_code field stored in the cart dict.",
    "T1: discount_code validation happens in orders/checkout.py :: checkout().",
],
"functions": [
    ("get_cart", ["session_id: str"], [
        "raw = cache_get(f'cart:{session_id}')",
        "return json.loads(raw) if raw else {'items': [], 'session_id': session_id}",
    ]),
    ("add_item", ["session_id: str", "product_id: str", "qty: int"], [
        "if not check_stock(product_id, qty): raise OutOfStockError(product_id)",
        "cart = get_cart(session_id)",
        "existing = next((i for i in cart['items'] if i['product_id'] == product_id), None)",
        "if existing: existing['qty'] += qty",
        "else: cart['items'].append({'product_id': product_id, 'qty': qty})",
        "cache_set(f'cart:{session_id}', json.dumps(cart), ttl=3600)",
        "return cart",
    ]),
]
},

{
"path": "orders/checkout.py",
"depends_on": ["orders/cart.py :: get_cart", "orders/models.py :: create_order", "products/pricing.py :: get_price", "payments/invoices.py :: create_invoice", "core/config.py :: TAX_RATE"],
"exports": ["checkout(session_id, tenant_id, user_id, payment_method) -> dict"],
"rules": [
    "checkout() applies TAX_RATE (from core/config.py) to compute total_with_tax.",
    "Formula: subtotal = sum(price * qty); tax = round(subtotal * TAX_RATE); total = subtotal + tax.",
    "TAX IS APPLIED EXACTLY ONCE HERE. Do not apply tax again in payments/invoices.py.",
    "After creating order, calls payments/invoices.py :: create_invoice(total_already_with_tax).",
    "Does NOT decrement inventory here. Inventory decremented in orders/fulfillment.py.",
    "T1: If cart has discount_code, validate and apply discount before computing tax.",
],
"functions": [
    ("checkout", ["session_id: str", "tenant_id: str", "user_id: str", "payment_method: str"], [
        "cart = get_cart(session_id)",
        "if not cart['items']: raise EmptyCartError()",
        "subtotal = sum(get_price(i['product_id']) * i['qty'] for i in cart['items'])",
        "tax = round(subtotal * TAX_RATE)",
        "total = subtotal + tax",
        "order = create_order(tenant_id, user_id, cart['items'], total)",
        "invoice = create_invoice(order['id'], tenant_id, total)  # total already includes tax",
        "return {'order': order, 'invoice': invoice}",
    ]),
]
},

{
"path": "orders/fulfillment.py",
"depends_on": ["orders/models.py :: get_order", "orders/models.py :: update_status", "products/inventory.py :: decrement_stock", "core/events.py :: emit"],
"exports": ["fulfill_order(order_id) -> dict", "cancel_order(order_id) -> None", "get_fulfillment_status(order_id) -> str"],
"rules": [
    "fulfill_order() must call products/inventory.py :: decrement_stock() for each item.",
    "After fulfillment, emit 'order.fulfilled' event via core/events.py.",
    "cancel_order() calls increment_stock() to return items to inventory.",
],
"functions": [
    ("fulfill_order", ["order_id: str"], [
        "order = get_order(order_id)",
        "if order['status'] != 'confirmed': raise InvalidStatusError()",
        "# TODO: decrement inventory for each item in order['items']",
        "update_status(order_id, 'fulfilled')",
        "emit('order.fulfilled', {'order_id': order_id})",
        "return get_order(order_id)",
    ]),
]
},

{
"path": "orders/returns.py",
"depends_on": ["orders/models.py :: get_order", "products/inventory.py :: increment_stock", "payments/service.py :: refund_payment"],
"exports": ["initiate_return(order_id, items, reason) -> dict", "approve_return(return_id) -> None", "get_return(return_id) -> dict"],
"rules": [
    "Returns can only be initiated within 30 days of fulfillment.",
    "approve_return() calls increment_stock() for returned items and refund_payment().",
],
"functions": [
    ("initiate_return", ["order_id: str", "items: list", "reason: str"], [
        "order = get_order(order_id)",
        "if order['status'] != 'fulfilled': raise InvalidStatusError()",
        "return execute_one('INSERT INTO returns (order_id, items, reason, status) VALUES (%s,%s,%s,%s) RETURNING *', (order_id, json.dumps(items), reason, 'pending'))",
    ]),
]
},

# ── payments ──────────────────────────────────────────────────────────────────
{
"path": "payments/models.py",
"depends_on": ["core/db.py :: execute", "core/db.py :: execute_one"],
"exports": [
    "get_invoice(id) -> dict | None",
    "get_invoices_by_tenant(tenant_id) -> list[dict]",
    "get_invoices_for_period(year, month) -> list[dict]",
    "create_invoice_record(order_id, tenant_id, amount_cents, status) -> dict",
    "mark_paid(invoice_id, charge_id) -> None",
],
"rules": [
    "invoices.tenant_id is FK on tenants.id.",
    "get_invoices_for_period() does NOT filter by tenant.suspended_at.",
    "amount_cents ALREADY includes tax when stored. Do not apply tax on read.",
],
"functions": [
    ("get_invoices_for_period", ["year: int", "month: int"], [
        "return execute('SELECT * FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))",
    ]),
]
},

{
"path": "payments/invoices.py",
"depends_on": ["payments/models.py :: create_invoice_record", "core/config.py :: TAX_RATE"],
"exports": ["create_invoice(order_id, tenant_id, total_cents) -> dict", "void_invoice(invoice_id) -> None"],
"rules": [
    "total_cents passed to create_invoice() ALREADY includes tax (applied in orders/checkout.py).",
    "DO NOT apply TAX_RATE again here. Tax is applied once in orders/checkout.py.",
    "create_invoice() just stores the total and emits the invoice record.",
    "T1: If order has discount_code, store applied_discount_cents on the invoice record.",
],
"functions": [
    ("create_invoice", ["order_id: str", "tenant_id: str", "total_cents: int"], [
        "# total_cents already includes tax from orders/checkout.py",
        "return create_invoice_record(order_id, tenant_id, total_cents, 'outstanding')",
    ]),
]
},

{
"path": "payments/service.py",
"depends_on": ["payments/invoices.py :: create_invoice", "payments/stripe.py :: charge_card", "payments/models.py :: mark_paid"],
"exports": ["collect_payment(invoice_id, payment_method) -> dict", "refund_payment(invoice_id, amount_cents) -> dict"],
"rules": [
    "collect_payment() charges the card and marks invoice as paid atomically.",
    "refund_payment() calls payments/stripe.py :: refund_charge().",
],
"functions": [
    ("collect_payment", ["invoice_id: str", "payment_method: str"], [
        "invoice = get_invoice(invoice_id)",
        "if invoice['status'] != 'outstanding': raise ValueError('Not collectable')",
        "charge = charge_card(invoice['amount_cents'], payment_method)",
        "mark_paid(invoice_id, charge['id'])",
        "return charge",
    ]),
]
},

{
"path": "payments/stripe.py",
"depends_on": ["core/config.py :: STRIPE_KEY"],
"exports": ["charge_card(amount_cents, payment_method) -> dict", "refund_charge(charge_id, amount_cents) -> dict", "create_customer(email, name) -> str"],
"rules": [
    "amount_cents must be INTEGER CENTS (e.g. 2999 = €29.99).",
    "Tax is already included in amount_cents. Do not add tax here.",
],
"functions": [
    ("charge_card", ["amount_cents: int", "payment_method: str"], [
        "intent = stripe.PaymentIntent.create(amount=amount_cents, currency='eur', payment_method=payment_method, confirm=True)",
        "return {'id': intent.id, 'status': intent.status}",
    ]),
]
},

{
"path": "payments/webhooks.py",
"depends_on": ["payments/models.py :: mark_paid", "payments/invoices.py :: void_invoice", "core/events.py :: emit"],
"exports": ["handle_stripe_webhook(payload, signature) -> None"],
"rules": [
    "Verify Stripe signature before processing any event.",
    "Handle: payment_intent.succeeded → mark_paid(); payment_intent.failed → void_invoice().",
],
"functions": [
    ("handle_stripe_webhook", ["payload: bytes", "signature: str"], [
        "event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)",
        "if event['type'] == 'payment_intent.succeeded':",
        "    mark_paid(event['data']['object']['metadata']['invoice_id'], event['data']['object']['id'])",
        "    emit('payment.received', event['data']['object'])",
    ]),
]
},

{
"path": "payments/refunds.py",
"depends_on": ["payments/stripe.py :: refund_charge", "payments/models.py :: get_invoice", "orders/models.py :: update_status"],
"exports": ["process_refund(invoice_id, amount_cents) -> dict", "full_refund(order_id) -> dict"],
"rules": [
    "Partial refunds: amount_cents <= invoice.amount_cents.",
    "full_refund() refunds the entire invoice and marks order as 'returned'.",
],
"functions": [
    ("full_refund", ["order_id: str"], [
        "from orders.models import get_order",
        "order = get_order(order_id)",
        "invoice = get_invoice(order['invoice_id'])",
        "refund = refund_charge(invoice['stripe_charge_id'], invoice['amount_cents'])",
        "update_status(order_id, 'returned')",
        "return refund",
    ]),
]
},

# ── shipping ──────────────────────────────────────────────────────────────────
{
"path": "shipping/models.py",
"depends_on": ["core/db.py :: execute", "core/db.py :: execute_one"],
"exports": ["create_shipment(order_id, carrier, tracking) -> dict", "get_shipment(order_id) -> dict | None", "update_tracking(shipment_id, status) -> None"],
"rules": ["Carriers: 'dhl', 'fedex', 'ups', 'poste_italiane'."],
"functions": [
    ("create_shipment", ["order_id: str", "carrier: str", "tracking: str"], [
        "return execute_one('INSERT INTO shipments (order_id, carrier, tracking_number) VALUES (%s,%s,%s) RETURNING *', (order_id, carrier, tracking))",
    ]),
]
},

{
"path": "shipping/service.py",
"depends_on": ["shipping/models.py", "shipping/carriers.py :: book_shipment", "orders/models.py :: update_status"],
"exports": ["ship_order(order_id, carrier) -> dict", "get_tracking_info(order_id) -> dict"],
"rules": ["ship_order() calls carriers.py :: book_shipment() then creates shipment record."],
"functions": [
    ("ship_order", ["order_id: str", "carrier: str"], [
        "booking = book_shipment(order_id, carrier)",
        "shipment = create_shipment(order_id, carrier, booking['tracking'])",
        "update_status(order_id, 'shipped')",
        "return shipment",
    ]),
]
},

{
"path": "shipping/carriers.py",
"depends_on": ["core/config.py"],
"exports": ["book_shipment(order_id, carrier) -> dict", "get_rates(origin, destination, weight_kg) -> list[dict]"],
"rules": ["All carrier API calls are mocked in testing. Use CARRIER_API_KEY from config."],
"functions": [
    ("book_shipment", ["order_id: str", "carrier: str"], [
        "# Mock carrier integration",
        "return {'tracking': f'TRACK-{order_id[:8].upper()}', 'carrier': carrier, 'eta_days': 3}",
    ]),
]
},

{
"path": "shipping/tracking.py",
"depends_on": ["shipping/models.py :: get_shipment", "shipping/carriers.py"],
"exports": ["get_status(order_id) -> dict", "webhook_update(carrier, payload) -> None"],
"rules": ["Track status: 'booked', 'in_transit', 'delivered', 'exception'."],
"functions": [
    ("get_status", ["order_id: str"], [
        "shipment = get_shipment(order_id)",
        "if not shipment: return {'status': 'not_shipped'}",
        "return {'status': shipment['status'], 'tracking': shipment['tracking_number']}",
    ]),
]
},

{
"path": "shipping/rates.py",
"depends_on": ["shipping/carriers.py :: get_rates"],
"exports": ["compare_rates(origin, destination, weight_kg) -> list[dict]", "cheapest_rate(origin, destination, weight_kg) -> dict"],
"rules": ["Rates are in CENTS. Sort by price ascending."],
"functions": [
    ("compare_rates", ["origin: str", "destination: str", "weight_kg: float"], [
        "rates = get_rates(origin, destination, weight_kg)",
        "return sorted(rates, key=lambda r: r['price_cents'])",
    ]),
]
},

# ── analytics ─────────────────────────────────────────────────────────────────
{
"path": "analytics/revenue.py",
"depends_on": ["payments/models.py :: get_invoices_for_period", "tenants/models.py :: is_suspended"],
"exports": ["monthly_revenue(year, month) -> dict", "annual_summary(year) -> list[dict]", "revenue_by_tenant(year, month) -> dict"],
"rules": [
    "monthly_revenue() sums invoices from payments/models.py :: get_invoices_for_period().",
    "get_invoices_for_period() includes invoices from suspended tenants (see payments/models.py :: Rules).",
    "To get accurate revenue: filter out suspended tenants using tenants/models.py :: is_suspended().",
    "T2: Add breakdown by tenant suspension status to the report output.",
],
"functions": [
    ("monthly_revenue", ["year: int", "month: int"], [
        "invoices = get_invoices_for_period(year, month)",
        "total = sum(i['amount_cents'] for i in invoices)",
        "by_tenant = {}",
        "for i in invoices:",
        "    by_tenant.setdefault(i['tenant_id'], []).append(i)",
        "return {'year': year, 'month': month, 'total_cents': total, 'by_tenant': by_tenant}",
    ]),
]
},

{
"path": "analytics/cohorts.py",
"depends_on": ["core/db.py :: execute", "tenants/models.py :: list_active_tenants"],
"exports": ["cohort_retention(months) -> list[dict]", "churn_rate(year, month) -> float"],
"rules": ["Cohort analysis uses tenants.created_at as cohort date."],
"functions": [
    ("churn_rate", ["year: int", "month: int"], [
        "total = len(list_active_tenants())",
        "churned = len(execute('SELECT id FROM tenants WHERE EXTRACT(YEAR FROM deleted_at)=%s AND EXTRACT(MONTH FROM deleted_at)=%s', (year, month)))",
        "return churned / total if total else 0.0",
    ]),
]
},

{
"path": "analytics/usage.py",
"depends_on": ["tenants/models.py :: get_tenant", "orders/models.py :: list_orders", "products/models.py :: count_products_by_tenant", "users/models.py :: count_users_by_tenant"],
"exports": ["get_tenant_usage(tenant_id) -> dict", "get_all_usage(month) -> list[dict]"],
"rules": [
    "T2: get_tenant_usage() must return: order_count, product_count, user_count, revenue_cents.",
    "T2: New endpoint GET /admin/tenants/<id>/usage should call this function.",
],
"functions": [
    ("get_tenant_usage", ["tenant_id: str"], [
        "orders = list_orders(tenant_id, status=None)",
        "return {",
        "    'tenant_id': tenant_id,",
        "    'order_count': len(orders),",
        "    'product_count': count_products_by_tenant(tenant_id),",
        "    'user_count': count_users_by_tenant(tenant_id),",
        "}",
    ]),
]
},

{
"path": "analytics/funnel.py",
"depends_on": ["core/db.py :: execute"],
"exports": ["cart_to_checkout_rate(tenant_id, days) -> float", "checkout_to_order_rate(tenant_id, days) -> float"],
"rules": ["Funnel metrics use raw events table. Events emitted by core/events.py."],
"functions": [
    ("cart_to_checkout_rate", ["tenant_id: str", "days: int = 30"], [
        "carts = execute('SELECT COUNT(*) as n FROM events WHERE tenant_id=%s AND event=%s AND created_at > NOW()-%s::interval', (tenant_id, 'cart.created', f'{days} days'))",
        "checkouts = execute('SELECT COUNT(*) as n FROM events WHERE tenant_id=%s AND event=%s AND created_at > NOW()-%s::interval', (tenant_id, 'checkout.started', f'{days} days'))",
        "c = carts[0]['n'] if carts else 0",
        "return checkouts[0]['n'] / c if c else 0.0",
    ]),
]
},

{
"path": "analytics/reports.py",
"depends_on": ["analytics/revenue.py :: monthly_revenue", "analytics/cohorts.py :: churn_rate", "analytics/usage.py :: get_all_usage"],
"exports": ["full_monthly_report(year, month) -> dict", "export_csv(report) -> str"],
"rules": [
    "full_monthly_report() aggregates revenue + cohorts + usage.",
    "export_csv() returns a CSV string (no file I/O).",
],
"functions": [
    ("full_monthly_report", ["year: int", "month: int"], [
        "rev = monthly_revenue(year, month)",
        "churn = churn_rate(year, month)",
        "usage = get_all_usage(month)",
        "return {'revenue': rev, 'churn_rate': churn, 'usage': usage}",
    ]),
]
},

# ── notifications ─────────────────────────────────────────────────────────────
{
"path": "notifications/email.py",
"depends_on": ["core/config.py :: SMTP_HOST", "core/config.py :: LOW_STOCK_THRESHOLD"],
"exports": [
    "send_welcome(email, name) -> None",
    "send_suspension_notice(email, tenant_id, reason) -> None",
    "send_invoice_email(tenant_id, invoice) -> None",
    "send_payment_failed(email, invoice_id) -> None",
    "send_low_stock_alert(tenant_id, product_id, current_qty) -> None",
],
"rules": [
    "All emails are async (fire-and-forget via SMTP).",
    "T3: send_low_stock_alert() is called from products/inventory.py after decrement.",
    "T3: Alert sent when stock_qty < LOW_STOCK_THRESHOLD (from core/config.py).",
],
"functions": [
    ("send_low_stock_alert", ["tenant_id: str", "product_id: str", "current_qty: int"], [
        "# TODO T3: send alert to tenant owner email",
        "pass",
    ]),
    ("send_welcome", ["email: str", "name: str"], ["_send(email, f'Welcome {name}!', '<p>Your account is ready.</p>')"]),
    ("send_suspension_notice", ["email: str", "tenant_id: str", "reason: str = ''"], [
        "_send(email, 'Account Suspended', f'<p>Account {tenant_id} suspended. Reason: {reason}</p>')",
    ]),
]
},

{
"path": "notifications/sms.py",
"depends_on": ["core/config.py"],
"exports": ["send_sms(phone, message) -> None", "send_otp(phone) -> str"],
"rules": ["SMS via Twilio. OTP expires in 5 minutes."],
"functions": [
    ("send_otp", ["phone: str"], [
        "otp = str(random.randint(100000, 999999))",
        "send_sms(phone, f'Your OTP: {otp}')",
        "cache_set(f'otp:{phone}', otp, ttl=300)",
        "return otp",
    ]),
]
},

{
"path": "notifications/push.py",
"depends_on": ["core/config.py"],
"exports": ["send_push(user_id, title, body) -> None", "send_bulk_push(user_ids, title, body) -> None"],
"rules": ["Push via FCM. user_id maps to FCM token stored in users.fcm_token."],
"functions": [
    ("send_push", ["user_id: str", "title: str", "body: str"], [
        "token = execute_one('SELECT fcm_token FROM users WHERE id=%s', (user_id,))",
        "if not token or not token['fcm_token']: return",
        "# FCM API call",
    ]),
]
},

{
"path": "notifications/scheduler.py",
"depends_on": ["notifications/email.py", "analytics/revenue.py :: monthly_revenue"],
"exports": ["schedule_monthly_report() -> None", "schedule_payment_reminders() -> None"],
"rules": ["All scheduled jobs run via cron. Times in UTC."],
"functions": [
    ("schedule_monthly_report", [], [
        "from datetime import datetime",
        "now = datetime.utcnow()",
        "report = monthly_revenue(now.year, now.month - 1 or 12)",
        "# send to all admin users",
    ]),
]
},

# ── api ───────────────────────────────────────────────────────────────────────
{
"path": "api/products.py",
"depends_on": ["products/service.py", "products/catalog.py", "core/auth.py :: require_auth", "users/permissions.py :: can_edit_product"],
"exports": ["products_bp (Flask Blueprint)"],
"rules": [
    "Auth: use core/auth.py :: require_auth decorator.",
    "Admin check: verify payload['role'] == 'admin' (from JWT). NOT user['is_admin'].",
    "See core/auth.py :: Rules for correct admin verification.",
],
"functions": [
    ("create_product_route", [], [
        "payload = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))",
        "# BUG B3: checks user['is_admin'] but field is payload['role'] == 'admin'",
        "if not request.user.get('is_admin'):",
        "    return jsonify({'error': 'Forbidden'}), 403",
        "data = request.json",
        "product = create(payload['tenant_id'], data)",
        "return jsonify(product), 201",
    ]),
]
},

{
"path": "api/orders.py",
"depends_on": ["orders/checkout.py :: checkout", "orders/models.py :: list_orders", "core/auth.py :: require_auth"],
"exports": ["orders_bp (Flask Blueprint)"],
"rules": [
    "POST /orders/checkout → orders/checkout.py :: checkout().",
    "GET /orders → list_orders() filtered by tenant from JWT.",
],
"functions": [
    ("checkout_route", [], [
        "payload = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))",
        "data = request.json",
        "result = checkout(data['session_id'], payload['tenant_id'], payload['user_id'], data['payment_method'])",
        "return jsonify(result), 201",
    ]),
]
},

{
"path": "api/reports.py",
"depends_on": ["analytics/reports.py :: full_monthly_report", "core/auth.py :: require_admin"],
"exports": ["reports_bp (Flask Blueprint)"],
"rules": ["All report endpoints require admin role. Use core/auth.py :: require_admin."],
"functions": [
    ("monthly_report_route", [], [
        "year = int(request.args.get('year', 2025))",
        "month = int(request.args.get('month', 1))",
        "report = full_monthly_report(year, month)",
        "return jsonify(report)",
    ]),
]
},

{
"path": "api/admin.py",
"depends_on": ["tenants/service.py :: suspend", "tenants/service.py :: reactivate", "analytics/usage.py :: get_tenant_usage", "core/auth.py :: require_admin"],
"exports": ["admin_bp (Flask Blueprint)"],
"rules": [
    "All admin endpoints require role='admin' from JWT.",
    "T2: Add GET /admin/tenants/<id>/usage endpoint → analytics/usage.py :: get_tenant_usage().",
],
"functions": [
    ("suspend_tenant_route", [], [
        "tid = request.view_args['tenant_id']",
        "reason = request.json.get('reason', '')",
        "suspend(tid, reason)",
        "return jsonify({'status': 'suspended'})",
    ]),
]
},

{
"path": "api/webhooks.py",
"depends_on": ["payments/webhooks.py :: handle_stripe_webhook"],
"exports": ["webhooks_bp (Flask Blueprint)"],
"rules": ["POST /webhooks/stripe → payments/webhooks.py :: handle_stripe_webhook(). Verify signature."],
"functions": [
    ("stripe_webhook_route", [], [
        "payload = request.get_data()",
        "signature = request.headers.get('Stripe-Signature')",
        "handle_stripe_webhook(payload, signature)",
        "return jsonify({'ok': True})",
    ]),
]
},

{
"path": "api/auth_api.py",
"depends_on": ["users/auth.py :: login", "users/auth.py :: logout", "core/auth.py :: verify_token"],
"exports": ["auth_bp (Flask Blueprint)"],
"rules": ["POST /auth/login → users/auth.py :: login(). Returns {token, user}."],
"functions": [
    ("login_route", [], [
        "data = request.json",
        "result = login(data['email'], data['password'])",
        "return jsonify(result)",
    ]),
]
},

# ── workers ───────────────────────────────────────────────────────────────────
{
"path": "workers/billing_runner.py",
"depends_on": ["tenants/billing.py :: bill_all_tenants"],
"exports": ["run(year, month) -> list[dict]"],
"rules": ["Runs on 1st of each month. Uses tenants/billing.py :: bill_all_tenants()."],
"functions": [("run", ["year: int | None = None", "month: int | None = None"], ["from datetime import datetime", "now = datetime.utcnow()", "return bill_all_tenants(year or now.year, month or now.month)"])],
},

{
"path": "workers/report_generator.py",
"depends_on": ["analytics/reports.py :: full_monthly_report", "notifications/email.py"],
"exports": ["generate_and_send(year, month) -> None"],
"rules": ["Sends monthly report to all admin users of each tenant."],
"functions": [("generate_and_send", ["year: int", "month: int"], ["report = full_monthly_report(year, month)", "# send to admins"])],
},

{
"path": "workers/inventory_sync.py",
"depends_on": ["products/inventory.py :: get_stock", "core/db.py :: execute"],
"exports": ["sync_all() -> None", "sync_tenant(tenant_id) -> None"],
"rules": ["Reconciles stock_qty with actual fulfillment records every hour."],
"functions": [("sync_all", [], ["tenants = execute('SELECT id FROM tenants WHERE suspended_at IS NULL')", "for t in tenants: sync_tenant(t['id'])"])],
},

{
"path": "workers/cleanup.py",
"depends_on": ["core/db.py :: execute", "core/cache.py :: cache_del"],
"exports": ["cleanup_expired_carts() -> int", "cleanup_old_events() -> int"],
"rules": ["Runs nightly. Cleanup expired Redis cart keys and events older than 90 days."],
"functions": [("cleanup_expired_carts", [], ["n = execute('DELETE FROM sessions WHERE expires_at < NOW()')", "return len(n)"])],
},

{
"path": "workers/indexer.py",
"depends_on": ["products/models.py :: list_products", "tenants/models.py :: list_active_tenants"],
"exports": ["index_all() -> None", "index_tenant(tenant_id) -> None"],
"rules": ["Rebuilds search index for all active tenants. Uses Elasticsearch or PostgreSQL FTS."],
"functions": [("index_tenant", ["tenant_id: str"], ["products = list_products(tenant_id)", "# index each product"])],
},

# ── app ───────────────────────────────────────────────────────────────────────
{
"path": "app.py",
"depends_on": ["api/products.py", "api/orders.py", "api/reports.py", "api/admin.py", "api/webhooks.py", "api/auth_api.py"],
"exports": ["create_app() -> Flask"],
"rules": ["Flask app factory. All blueprints registered here."],
"functions": [
    ("create_app", [], [
        "app = Flask(__name__)",
        "app.register_blueprint(products_bp)",
        "app.register_blueprint(orders_bp)",
        "app.register_blueprint(reports_bp)",
        "app.register_blueprint(admin_bp)",
        "app.register_blueprint(webhooks_bp)",
        "app.register_blueprint(auth_bp)",
        "return app",
    ]),
]
},
]
