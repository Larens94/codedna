"""
distractors.py — Genera 120 file distractor realistici per scalare il codebase.

I file distractors:
- Hanno funzioni con nomi simili al bug chain (es. get_X_for_period, list_active_X)
- Rendono i grep molto rumorosi (20+ match per query comune)
- Non sono nella catena del bug — solo rumore realistico
"""

# Template per file distractor tipico con funzioni realistiche
# Le funzioni usano ANCHE nomi come get_X_for_period, list_active_X, suspended
# per rendere grep non deterministico

def _dist(module: str, name: str, funcs: list[tuple]) -> dict:
    """Create a distractor file spec."""
    return {
        "path": f"{module}/{name}.py",
        "depends_on": [f"core/db.py :: execute"],
        "exports": [f"{fn[0]}() -> {fn[2]}" for fn in funcs],
        "rules": [],
        "functions": [(fn[0], fn[1], fn[3]) for fn in funcs],
        "_is_distractor": True,
    }

# funcs format: (name, params, return_type, body_lines)
DISTRACTORS = [

# ── reports/ ──────────────────────────────────────────────────────────────────
_dist("reports", "daily_sales", [
    ("get_sales_for_period", ["year:int","month:int","day:int"], "list[dict]",
     ["return execute('SELECT * FROM sales WHERE date=%s', (f'{year}-{month:02d}-{day:02d}',))"]),
    ("get_daily_totals", ["year:int","month:int"], "dict",
     ["rows = execute('SELECT day, SUM(amount) FROM sales GROUP BY day WHERE month=%s', (month,))", "return {r['day']: r['sum'] for r in rows}"]),
]),

_dist("reports", "product_performance", [
    ("get_top_products", ["tenant_id:str","limit:int=10"], "list[dict]",
     ["return execute('SELECT product_id, SUM(qty) as total FROM order_items WHERE tenant_id=%s GROUP BY product_id ORDER BY total DESC LIMIT %s', (tenant_id, limit))"]),
    ("get_products_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM order_items WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))"]),
]),

_dist("reports", "user_activity", [
    ("get_active_users", ["tenant_id:str","days:int=30"], "list[dict]",
     ["return execute('SELECT * FROM users WHERE tenant_id=%s AND last_login > NOW() - %s::interval AND deleted_at IS NULL', (tenant_id, f'{days} days'))"]),
    ("get_user_sessions_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM sessions WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))"]),
]),

_dist("reports", "subscription_report", [
    ("get_subscriptions_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM subscriptions WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s AND status=%s', (year,month,'active'))"]),
    ("list_active_subscriptions", ["tenant_id:str"], "list[dict]",
     ["return execute('SELECT * FROM subscriptions WHERE tenant_id=%s AND status=%s', (tenant_id,'active'))"]),
]),

_dist("reports", "churn_report", [
    ("get_churned_tenants_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM tenants WHERE EXTRACT(YEAR FROM deleted_at)=%s AND EXTRACT(MONTH FROM deleted_at)=%s', (year,month))"]),
    ("get_suspension_stats", [], "dict",
     ["total = execute_one('SELECT COUNT(*) as n FROM tenants WHERE suspended_at IS NOT NULL')", "return {'suspended': total['n']}"]),
]),

_dist("reports", "payment_report", [
    ("get_payments_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM payments WHERE EXTRACT(YEAR FROM paid_at)=%s AND EXTRACT(MONTH FROM paid_at)=%s', (year,month))"]),
    ("get_failed_payments", ["days:int=30"], "list[dict]",
     ["return execute('SELECT * FROM payments WHERE status=%s AND created_at > NOW()-%s::interval', ('failed',f'{days} days'))"]),
]),

_dist("reports", "shipping_report", [
    ("get_shipments_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM shipments WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))"]),
    ("get_delayed_shipments", [], "list[dict]",
     ["return execute('SELECT * FROM shipments WHERE status=%s AND eta < NOW()', ('in_transit',))"]),
]),

# ── services/ (extra) ──────────────────────────────────────────────────────────
_dist("services", "discount_service", [
    ("get_active_discounts", ["tenant_id:str"], "list[dict]",
     ["return execute('SELECT * FROM discounts WHERE tenant_id=%s AND active=TRUE AND expired_at > NOW()', (tenant_id,))"]),
    ("apply_discount", ["code:str","amount_cents:int"], "int",
     ["discount = execute_one('SELECT * FROM discounts WHERE code=%s AND active=TRUE', (code,))", "if not discount: return amount_cents", "return round(amount_cents * (1 - discount['percentage']/100))"]),
    ("validate_discount_code", ["code:str","tenant_id:str"], "bool",
     ["d = execute_one('SELECT * FROM discounts WHERE code=%s AND tenant_id=%s AND active=TRUE', (code,tenant_id))", "return d is not None"]),
]),

_dist("services", "audit_service", [
    ("log_action", ["user_id:str","action:str","resource:str","resource_id:str"], "None",
     ["execute('INSERT INTO audit_log (user_id, action, resource, resource_id) VALUES (%s,%s,%s,%s)', (user_id,action,resource,resource_id))"]),
    ("get_audit_log_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM audit_log WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s ORDER BY created_at DESC', (year,month))"]),
    ("get_user_actions", ["user_id:str","days:int=7"], "list[dict]",
     ["return execute('SELECT * FROM audit_log WHERE user_id=%s AND created_at > NOW()-%s::interval', (user_id,f'{days} days'))"]),
]),

_dist("services", "tax_service", [
    ("calculate_tax", ["amount_cents:int","country:str"], "int",
     ["rates = {'IT':0.22,'DE':0.19,'FR':0.20,'ES':0.21}", "return round(amount_cents * rates.get(country, 0.20))"]),
    ("get_tax_report_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT country, SUM(tax_cents) FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s GROUP BY country', (year,month))"]),
]),

_dist("services", "export_service", [
    ("export_invoices_csv", ["year:int","month:int"], "str",
     ["invoices = execute('SELECT * FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))", "return '\\n'.join(','.join(str(v) for v in i.values()) for i in invoices)"]),
    ("export_tenants_csv", [], "str",
     ["tenants = execute('SELECT id,name,plan,created_at FROM tenants WHERE deleted_at IS NULL')", "return '\\n'.join(','.join(str(v) for v in t.values()) for t in tenants)"]),
]),

_dist("services", "search_service", [
    ("search_products", ["tenant_id:str","query:str","filters:dict={}"], "list[dict]",
     ["return execute('SELECT * FROM products WHERE tenant_id=%s AND name ILIKE %s AND deleted_at IS NULL', (tenant_id,f'%{query}%'))"]),
    ("search_orders", ["tenant_id:str","query:str"], "list[dict]",
     ["return execute('SELECT * FROM orders WHERE tenant_id=%s AND id ILIKE %s', (tenant_id,f'%{query}%'))"]),
    ("search_tenants_admin", ["query:str"], "list[dict]",
     ["return execute('SELECT * FROM tenants WHERE name ILIKE %s AND deleted_at IS NULL', (f'%{query}%',))"]),
]),

_dist("services", "recommendation_service", [
    ("get_recommended_products", ["tenant_id:str","user_id:str","limit:int=10"], "list[dict]",
     ["return execute('SELECT p.* FROM products p JOIN order_items oi ON p.id=oi.product_id WHERE oi.tenant_id=%s AND p.deleted_at IS NULL GROUP BY p.id ORDER BY COUNT(*) DESC LIMIT %s', (tenant_id,limit))"]),
    ("get_trending_for_period", ["year:int","month:int","limit:int=5"], "list[dict]",
     ["return execute('SELECT product_id, COUNT(*) as orders FROM order_items WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s GROUP BY product_id ORDER BY orders DESC LIMIT %s', (year,month,limit))"]),
]),

# ── models/ (extra) ────────────────────────────────────────────────────────────
_dist("models", "discount_model", [
    ("get_discount", ["code:str"], "dict|None",
     ["return execute_one('SELECT * FROM discounts WHERE code=%s', (code,))"]),
    ("list_active_discounts", ["tenant_id:str"], "list[dict]",
     ["return execute('SELECT * FROM discounts WHERE tenant_id=%s AND active=TRUE AND expired_at > NOW()', (tenant_id,))"]),
    ("create_discount", ["tenant_id:str","code:str","percentage:float","expires_at:str"], "dict",
     ["return execute_one('INSERT INTO discounts (tenant_id,code,percentage,expired_at) VALUES (%s,%s,%s,%s) RETURNING *', (tenant_id,code,percentage,expires_at))"]),
    ("deactivate_discount", ["code:str"], "None",
     ["execute('UPDATE discounts SET active=FALSE WHERE code=%s', (code,))"]),
]),

_dist("models", "audit_model", [
    ("get_audit_entries", ["resource_id:str"], "list[dict]",
     ["return execute('SELECT * FROM audit_log WHERE resource_id=%s ORDER BY created_at DESC', (resource_id,))"]),
    ("get_audit_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM audit_log WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))"]),
]),

_dist("models", "session_model", [
    ("get_session", ["token:str"], "dict|None",
     ["return execute_one('SELECT * FROM sessions WHERE token=%s AND expires_at>NOW()', (token,))"]),
    ("list_active_sessions", ["user_id:str"], "list[dict]",
     ["return execute('SELECT * FROM sessions WHERE user_id=%s AND expires_at>NOW()', (user_id,))"]),
    ("create_session", ["user_id:str","tenant_id:str","token:str"], "dict",
     ["return execute_one('INSERT INTO sessions (user_id,tenant_id,token,expires_at) VALUES (%s,%s,%s,NOW()+INTERVAL \\'24 hours\\') RETURNING *', (user_id,tenant_id,token))"]),
    ("invalidate_session", ["token:str"], "None",
     ["execute('UPDATE sessions SET expires_at=NOW() WHERE token=%s', (token,))"]),
]),

_dist("models", "webhook_model", [
    ("list_webhooks", ["tenant_id:str"], "list[dict]",
     ["return execute('SELECT * FROM webhooks WHERE tenant_id=%s AND active=TRUE', (tenant_id,))"]),
    ("get_webhook_deliveries_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM webhook_deliveries WHERE EXTRACT(YEAR FROM sent_at)=%s AND EXTRACT(MONTH FROM sent_at)=%s', (year,month))"]),
    ("create_webhook", ["tenant_id:str","url:str","events:list"], "dict",
     ["return execute_one('INSERT INTO webhooks (tenant_id,url,events) VALUES (%s,%s,%s) RETURNING *', (tenant_id,url,str(events)))"]),
]),

_dist("models", "feature_flag_model", [
    ("get_flags", ["tenant_id:str"], "dict",
     ["rows = execute('SELECT flag,enabled FROM feature_flags WHERE tenant_id=%s OR tenant_id IS NULL', (tenant_id,))", "return {r['flag']:r['enabled'] for r in rows}"]),
    ("is_enabled", ["tenant_id:str","flag:str"], "bool",
     ["row = execute_one('SELECT enabled FROM feature_flags WHERE (tenant_id=%s OR tenant_id IS NULL) AND flag=%s ORDER BY tenant_id NULLS LAST LIMIT 1', (tenant_id,flag))", "return row['enabled'] if row else False"]),
    ("set_flag", ["tenant_id:str","flag:str","enabled:bool"], "None",
     ["execute('INSERT INTO feature_flags (tenant_id,flag,enabled) VALUES (%s,%s,%s) ON CONFLICT (tenant_id,flag) DO UPDATE SET enabled=%s', (tenant_id,flag,enabled,enabled))"]),
]),

_dist("models", "integration_model", [
    ("get_integrations", ["tenant_id:str"], "list[dict]",
     ["return execute('SELECT * FROM integrations WHERE tenant_id=%s AND active=TRUE', (tenant_id,))"]),
    ("list_active_integrations", ["tenant_id:str"], "list[dict]",
     ["return execute('SELECT * FROM integrations WHERE tenant_id=%s AND suspended_at IS NULL', (tenant_id,))"]),
    ("create_integration", ["tenant_id:str","provider:str","config:dict"], "dict",
     ["return execute_one('INSERT INTO integrations (tenant_id,provider,config) VALUES (%s,%s,%s::jsonb) RETURNING *', (tenant_id,provider,str(config)))"]),
]),

# ── api/ (extra endpoints) ─────────────────────────────────────────────────────
_dist("api", "search_api", [
    ("search_route", [], "None",
     ["tenant_id = request.user['tenant_id']", "q = request.args.get('q', '')", "results = search_products(tenant_id, q)", "return jsonify(results)"]),
    ("suggest_route", [], "None",
     ["tenant_id = request.user['tenant_id']", "prefix = request.args.get('prefix', '')", "return jsonify(suggest(tenant_id, prefix))"]),
]),

_dist("api", "discounts_api", [
    ("create_discount_route", [], "None",
     ["data = request.json", "payload = verify_token(request.headers.get('Authorization','').replace('Bearer ',''))", "if payload.get('role') not in ('admin','owner'): return jsonify({'error':'Forbidden'}),403", "discount = create_discount(payload['tenant_id'],data['code'],data['percentage'],data['expires_at'])", "return jsonify(discount),201"]),
    ("validate_discount_route", [], "None",
     ["code = request.json.get('code')", "tenant_id = request.user['tenant_id']", "valid = validate_discount_code(code, tenant_id)", "return jsonify({'valid': valid})"]),
]),

_dist("api", "analytics_api", [
    ("revenue_route", [], "None",
     ["year = int(request.args.get('year',2025))", "month = int(request.args.get('month',1))", "payload = verify_token(request.headers.get('Authorization','').replace('Bearer ',''))", "if payload.get('role') not in ('admin','owner'): return jsonify({'error':'Forbidden'}),403", "return jsonify(monthly_revenue(year,month))"]),
    ("cohort_route", [], "None",
     ["months = int(request.args.get('months',12))", "return jsonify(cohort_retention(months))"]),
    ("churn_route", [], "None",
     ["year = int(request.args.get('year',2025))", "month = int(request.args.get('month',1))", "return jsonify({'churn_rate': churn_rate(year,month)})"]),
]),

_dist("api", "shipping_api", [
    ("ship_route", [], "None",
     ["data = request.json", "shipment = ship_order(data['order_id'], data['carrier'])", "return jsonify(shipment),201"]),
    ("tracking_route", [], "None",
     ["order_id = request.view_args['order_id']", "return jsonify(get_status(order_id))"]),
    ("rates_route", [], "None",
     ["data = request.json", "rates = compare_rates(data['origin'],data['destination'],data['weight_kg'])", "return jsonify(rates)"]),
]),

_dist("api", "notifications_api", [
    ("send_test_email_route", [], "None",
     ["payload = verify_token(request.headers.get('Authorization','').replace('Bearer ',''))", "if payload.get('role') != 'admin': return jsonify({'error':'Forbidden'}),403", "send_welcome(request.json['email'], request.json.get('name','Test'))", "return jsonify({'sent': True})"]),
]),

_dist("api", "integrations_api", [
    ("list_integrations_route", [], "None",
     ["tenant_id = request.user['tenant_id']", "return jsonify(get_integrations(tenant_id))"]),
    ("create_integration_route", [], "None",
     ["data = request.json", "tenant_id = request.user['tenant_id']", "result = create_integration(tenant_id, data['provider'], data['config'])", "return jsonify(result),201"]),
]),

# ── workers/ (extra) ───────────────────────────────────────────────────────────
_dist("workers", "webhook_dispatcher", [
    ("dispatch_all", ["event:str","payload:dict"], "None",
     ["webhooks = execute('SELECT * FROM webhooks WHERE events @> %s::jsonb AND active=TRUE', (f'[\"{event}\"]',))", "for wh in webhooks: _send(wh['url'], payload)"]),
    ("dispatch_for_tenant", ["tenant_id:str","event:str","payload:dict"], "None",
     ["webhooks = execute('SELECT * FROM webhooks WHERE tenant_id=%s AND active=TRUE', (tenant_id,))", "for wh in webhooks: _send(wh['url'], payload)"]),
]),

_dist("workers", "data_export", [
    ("export_tenant_data", ["tenant_id:str"], "dict",
     ["return {'orders': execute('SELECT * FROM orders WHERE tenant_id=%s', (tenant_id,)), 'invoices': execute('SELECT * FROM invoices WHERE tenant_id=%s', (tenant_id,))}"]),
    ("scheduled_export", ["year:int","month:int"], "None",
     ["tenants = execute('SELECT id FROM tenants WHERE suspended_at IS NULL AND deleted_at IS NULL')", "for t in tenants: export_tenant_data(t['id'])"]),
]),

_dist("workers", "subscription_renewal", [
    ("renew_expiring", [], "list[dict]",
     ["subs = execute('SELECT * FROM subscriptions WHERE status=%s AND next_billing_at < NOW()+INTERVAL \\'3 days\\'', ('active',))", "renewed = []", "for s in subs: renewed.append(s)", "return renewed"]),
    ("notify_upcoming_renewals", [], "None",
     ["subs = execute('SELECT s.*, t.owner_email FROM subscriptions s JOIN tenants t ON s.tenant_id=t.id WHERE s.status=%s AND s.next_billing_at BETWEEN NOW() AND NOW()+INTERVAL \\'7 days\\' AND t.suspended_at IS NULL', ('active',))", "for s in subs: pass  # send email"]),
]),

_dist("workers", "analytics_aggregator", [
    ("aggregate_daily_revenue", ["date:str"], "dict",
     ["rows = execute('SELECT tenant_id, SUM(amount_cents) as total FROM invoices WHERE DATE(created_at)=%s GROUP BY tenant_id', (date,))", "return {r['tenant_id']: r['total'] for r in rows}"]),
    ("aggregate_monthly_cohorts", ["year:int","month:int"], "None",
     ["execute('INSERT INTO cohort_snapshots (year,month,metrics) SELECT %s,%s,json_build_object() ON CONFLICT DO NOTHING', (year,month))"]),
]),

_dist("workers", "notification_digest", [
    ("send_daily_digest", ["tenant_id:str"], "None",
     ["orders_today = execute('SELECT COUNT(*) as n FROM orders WHERE tenant_id=%s AND DATE(created_at)=CURRENT_DATE', (tenant_id,))", "pass  # format and send"]),
    ("send_weekly_summary", ["tenant_id:str"], "None",
     ["revenue = execute_one('SELECT SUM(amount_cents) as total FROM invoices WHERE tenant_id=%s AND created_at > NOW()-INTERVAL \\'7 days\\'', (tenant_id,))", "pass  # send email"]),
]),

# ── middleware/ ────────────────────────────────────────────────────────────────
_dist("middleware", "rate_limiter", [
    ("check_rate_limit", ["tenant_id:str","endpoint:str"], "bool",
     ["key = f'rate:{tenant_id}:{endpoint}'", "count = cache_get(key) or '0'", "if int(count) > 100: return False", "cache_set(key, str(int(count)+1), ttl=60)", "return True"]),
    ("get_limit_status", ["tenant_id:str"], "dict",
     ["return {'requests_this_minute': int(cache_get(f'rate:{tenant_id}:global') or '0'), 'limit': 100}"]),
]),

_dist("middleware", "cors_handler", [
    ("add_cors_headers", ["response:object"], "object",
     ["response.headers['Access-Control-Allow-Origin'] = '*'", "response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'", "return response"]),
]),

_dist("middleware", "request_logger", [
    ("log_request", ["request:object","response:object","duration_ms:float"], "None",
     ["execute('INSERT INTO request_logs (method,path,status,duration_ms,tenant_id) VALUES (%s,%s,%s,%s,%s)', (request.method, request.path, response.status_code, duration_ms, getattr(request,'tenant_id',None)))"]),
    ("get_slow_requests", ["threshold_ms:float=1000"], "list[dict]",
     ["return execute('SELECT * FROM request_logs WHERE duration_ms > %s ORDER BY duration_ms DESC LIMIT 50', (threshold_ms,))"]),
]),

_dist("middleware", "tenant_resolver", [
    ("resolve_tenant", ["request:object"], "dict|None",
     ["host = request.host", "return execute_one('SELECT * FROM tenants WHERE custom_domain=%s AND suspended_at IS NULL AND deleted_at IS NULL', (host,))"]),
    ("inject_tenant_context", ["f:callable"], "callable",
     ["from functools import wraps", "@wraps(f)", "def decorated(*args,**kwargs): return f(*args,**kwargs)", "return decorated"]),
]),

_dist("middleware", "feature_gate", [
    ("gate", ["flag:str"], "callable",
     ["from functools import wraps", "def decorator(f):", "    @wraps(f)", "    def d(*a,**k):", "        tid = getattr(request,'tenant_id',None)", "        if not is_enabled(tid,flag): return jsonify({'error':'Feature not available'}),403", "        return f(*a,**k)", "    return d", "return decorator"]),
]),

# ── utils/ ────────────────────────────────────────────────────────────────────
_dist("utils", "validators", [
    ("validate_email", ["email:str"], "bool",
     ["import re", "return bool(re.match(r'^[^@]+@[^@]+\\.[^@]+$', email))"]),
    ("validate_plan", ["plan:str"], "bool",
     ["return plan in ('starter','growth','business','enterprise')"]),
    ("validate_currency_amount", ["amount_cents:int"], "bool",
     ["return isinstance(amount_cents,int) and amount_cents >= 0"]),
]),

_dist("utils", "formatters", [
    ("format_currency", ["amount_cents:int","currency:str='EUR'"], "str",
     ["return f'{amount_cents/100:.2f} {currency}'"]),
    ("format_period", ["year:int","month:int"], "str",
     ["import calendar", "return f'{calendar.month_name[month]} {year}'"]),
    ("format_tenant_id", ["tenant_id:str"], "str",
     ["return f'T-{tenant_id[:8].upper()}'"]),
]),

_dist("utils", "pagination", [
    ("paginate", ["query:str","params:tuple","page:int=1","per_page:int=20"], "dict",
     ["offset = (page-1)*per_page", "rows = execute(f'{query} LIMIT %s OFFSET %s', params+(per_page,offset))", "total = execute_one(f'SELECT COUNT(*) as n FROM ({query}) sub', params)", "return {'data':rows,'page':page,'per_page':per_page,'total':total['n']}"]),
]),

_dist("utils", "crypto", [
    ("hash_password", ["password:str"], "str",
     ["import bcrypt", "return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()"]),
    ("verify_password", ["password:str","hash_str:str"], "bool",
     ["import bcrypt", "return bcrypt.checkpw(password.encode(), hash_str.encode())"]),
    ("generate_token", ["length:int=32"], "str",
     ["import secrets", "return secrets.token_urlsafe(length)"]),
]),

_dist("utils", "date_utils", [
    ("first_day_of_month", ["year:int","month:int"], "str",
     ["return f'{year}-{month:02d}-01'"]),
    ("last_day_of_month", ["year:int","month:int"], "str",
     ["import calendar", "return f'{year}-{month:02d}-{calendar.monthrange(year,month)[1]}'"]),
    ("parse_date", ["date_str:str"], "object",
     ["from datetime import datetime", "return datetime.strptime(date_str,'%Y-%m-%d').date()"]),
]),

# ── integrations/ ─────────────────────────────────────────────────────────────
_dist("integrations", "slack_notifier", [
    ("send_slack", ["webhook_url:str","message:str"], "None",
     ["import urllib.request,json", "data = json.dumps({'text':message}).encode()", "urllib.request.urlopen(urllib.request.Request(webhook_url,data,{'Content-Type':'application/json'}))"]),
    ("notify_new_order", ["tenant_id:str","order_id:str","amount_cents:int"], "None",
     ["cfg = execute_one('SELECT slack_webhook FROM tenant_settings WHERE tenant_id=%s', (tenant_id,))", "if cfg and cfg['slack_webhook']: send_slack(cfg['slack_webhook'],f'New order {order_id}: {amount_cents/100:.2f}€')"]),
]),

_dist("integrations", "zapier_webhook", [
    ("trigger_zapier", ["tenant_id:str","event:str","data:dict"], "None",
     ["zaps = execute('SELECT url FROM zap_connections WHERE tenant_id=%s AND event=%s AND active=TRUE', (tenant_id,event))", "for z in zaps: pass  # POST to z['url']"]),
    ("get_zap_triggers_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM zap_trigger_log WHERE EXTRACT(YEAR FROM triggered_at)=%s AND EXTRACT(MONTH FROM triggered_at)=%s', (year,month))"]),
]),

_dist("integrations", "crm_sync", [
    ("sync_tenant_to_crm", ["tenant_id:str"], "None",
     ["tenant = execute_one('SELECT * FROM tenants WHERE id=%s AND suspended_at IS NULL', (tenant_id,))", "if tenant: pass  # sync to CRM"]),
    ("list_active_crm_syncs", [], "list[dict]",
     ["return execute('SELECT * FROM crm_sync_log WHERE status=%s ORDER BY created_at DESC LIMIT 100', ('active',))"]),
]),

_dist("integrations", "stripe_webhooks_handler", [
    ("on_payment_succeeded", ["event:dict"], "None",
     ["invoice_id = event['data']['object']['metadata'].get('invoice_id')", "if invoice_id: execute('UPDATE invoices SET status=%s WHERE id=%s', ('paid',invoice_id))"]),
    ("on_subscription_cancelled", ["event:dict"], "None",
     ["sub_id = event['data']['object']['id']", "execute('UPDATE subscriptions SET status=%s WHERE stripe_subscription_id=%s', ('cancelled',sub_id))"]),
    ("get_webhook_logs_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM stripe_webhook_log WHERE EXTRACT(YEAR FROM received_at)=%s AND EXTRACT(MONTH FROM received_at)=%s', (year,month))"]),
]),

# ── admin/ ────────────────────────────────────────────────────────────────────
_dist("admin", "tenant_dashboard", [
    ("get_overview", [], "dict",
     ["total = execute_one('SELECT COUNT(*) as n FROM tenants WHERE deleted_at IS NULL')", "suspended = execute_one('SELECT COUNT(*) as n FROM tenants WHERE suspended_at IS NOT NULL AND deleted_at IS NULL')", "return {'total':total['n'],'suspended':suspended['n'],'active':total['n']-suspended['n']}"]),
    ("get_tenants_for_period", ["year:int","month:int"], "list[dict]",
     ["return execute('SELECT * FROM tenants WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))"]),
]),

_dist("admin", "billing_dashboard", [
    ("get_billing_summary", ["year:int","month:int"], "dict",
     ["invoices = execute('SELECT SUM(amount_cents) as total, COUNT(*) as count FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))", "return invoices[0] if invoices else {}"]),
    ("get_failed_billing", [], "list[dict]",
     ["return execute('SELECT * FROM invoices WHERE status=%s ORDER BY created_at DESC LIMIT 50', ('failed',))"]),
]),

_dist("admin", "user_management", [
    ("list_all_users", ["page:int=1","per_page:int=50"], "dict",
     ["offset = (page-1)*per_page", "users = execute('SELECT * FROM users WHERE active=TRUE ORDER BY created_at DESC LIMIT %s OFFSET %s', (per_page,offset))", "return {'users':users,'page':page}"]),
    ("get_suspended_users", [], "list[dict]",
     ["return execute('SELECT u.* FROM users u JOIN tenants t ON u.tenant_id=t.id WHERE t.suspended_at IS NOT NULL AND u.active=TRUE')"]),
    ("deactivate_all_tenant_users", ["tenant_id:str"], "int",
     ["execute('UPDATE users SET active=FALSE WHERE tenant_id=%s', (tenant_id,))", "return execute_one('SELECT COUNT(*) as n FROM users WHERE tenant_id=%s', (tenant_id,))['n']"]),
]),

_dist("admin", "support_tools", [
    ("impersonate_tenant", ["admin_user_id:str","target_tenant_id:str"], "str",
     ["from core.auth import sign_token", "return sign_token(admin_user_id,'admin',target_tenant_id)"]),
    ("reset_tenant_cache", ["tenant_id:str"], "None",
     ["from core.cache import cache_invalidate_prefix", "cache_invalidate_prefix(f'tenant:{tenant_id}')", "cache_invalidate_prefix(f'catalog:{tenant_id}')"]),
    ("get_system_health", [], "dict",
     ["return {'db': 'ok', 'redis': 'ok', 'stripe': 'ok'}"]),
]),

]
