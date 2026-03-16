"""workers/subscription_renewal.py — Subscription Renewal module.

deps:    core/db.py :: execute
exports: renew_expiring() -> list[dict] | notify_upcoming_renewals() -> None
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def renew_expiring():
    subs = execute('SELECT * FROM subscriptions WHERE status=%s AND next_billing_at < NOW()+INTERVAL \'3 days\'', ('active',))
    renewed = []
    for s in subs: renewed.append(s)
    return renewed

def notify_upcoming_renewals():
    subs = execute('SELECT s.*, t.owner_email FROM subscriptions s JOIN tenants t ON s.tenant_id=t.id WHERE s.status=%s AND s.next_billing_at BETWEEN NOW() AND NOW()+INTERVAL \'7 days\' AND t.suspended_at IS NULL', ('active',))
    for s in subs: pass  # send email
