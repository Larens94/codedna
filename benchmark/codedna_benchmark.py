"""
CodeDNA Real Benchmark Suite v2.0
==================================
5 scenari progettati per produrre differenziazione REALE tra Control e CodeDNA.
Ogni scenario costruisce una situazione dove, senza manifest/annotations,
un agente commette errori deterministici.

Scenari:
  S4 — Sliding Window: agente vede solo 50 righe di un file lungo 300
  S5 — Cascade Change: modifica utils.py senza sapere chi la usa
  S6 — Semantic Naming: tipo ambiguo (centesimi vs euro)
  S7 — Broken Dependency: DEPENDS_ON punta a simbolo rinominato
  S8 — Large Codebase Planning: 8 file, solo i manifest, trovare i 2 da modificare

Metriche:
  • quality_score (LLM judge 0-10)
  • cascade_miss (boolean: mancato aggiornamento file dipendente)
  • constraint_violation (boolean: violazione vincolo esplicito)
  • correct_files_identified (S8: set di file corretti identificati)

NOTA SUL MODELLO:
  I modelli "flash" sono ottimizzati per velocità e spesso ignorano vincoli
  embedded nel manifest. Usare modelli "pro" o "thinking" per risultati
  significativi. I modelli flash misureranno l'adozione futura del protocollo.

Usage:
    pip install tiktoken google-genai
    GEMINI_API_KEY=... python codedna_benchmark.py [--model gemini-2.5-pro] [--runs 3]

Modelli raccomandati:
    gemini-2.5-pro          → raccomandato (reasoning, rispetta le regole)
    gemini-2.5-flash        → veloce ma spesso ignora AGENT_RULES
    gemini-1.5-pro          → fallback stabile
"""

import os, sys, time, json, textwrap, re, argparse
import tiktoken
from google import genai
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional

# ── CLI args (override defaults a runtime) ──────────────────────────
_parser = argparse.ArgumentParser(description="CodeDNA Benchmark v2.0")
_parser.add_argument("--model", default="gemini-2.5-pro",
    help="Gemini model to use (default: gemini-2.5-pro)")
_parser.add_argument("--runs",  type=int, default=3,
    help="Runs per scenario (default: 3, use 1 for quick test)")
_args, _ = _parser.parse_known_args()

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
MODEL             = _args.model
RUNS_PER_SCENARIO = _args.runs

# ──────────────────────────────────────────────────────────────────
# FIXTURE S4: SLIDING WINDOW — file lungo, agente vede solo metà
# ──────────────────────────────────────────────────────────────────

# File lungo ~300 righe. Il vincolo MAX_DISCOUNT_RATE è definito SOLO
# nel manifest (header) e nel commento @REQUIRES-READ inline.
# L'agente in sliding window vede solo le righe 200-250.

S4_LARGE_FILE_NO_CODEDNA = """\
# pricing.py
# (placeholder — file lungo 300 righe, nessun manifest)
import math

def get_tier_multiplier(tier: str) -> float:
    tiers = {"basic": 1.0, "silver": 0.9, "gold": 0.85, "premium": 0.8}
    return tiers.get(tier, 1.0)

def format_price(cents: int) -> str:
    return f"€{cents/100:,.2f}"

# ... 150 righe di codice non rilevante ...
""" + "\n".join([f"# filler line {i}" for i in range(150)]) + """

def apply_discount(base_price_cents: int, user_tier: str, promo_code: str = "") -> int:
    \"\"\"
    Applica lo sconto al prezzo base.
    base_price_cents: prezzo in CENTESIMI
    user_tier: livello utente
    promo_code: codice promo opzionale
    \"\"\"
    multiplier = get_tier_multiplier(user_tier)
    discount = 1.0 - multiplier

    if promo_code == "EXTRA10":
        discount += 0.10

    # Applica sconto (nessun cap definito qui)
    final = base_price_cents * (1.0 - discount)
    return int(final)

def calculate_bundle_price(items: list, user_tier: str) -> int:
    \"\"\"Prezzo bundle con 5% extra di sconto.\"\"\"
    total = sum(apply_discount(item["price_cents"], user_tier) for item in items)
    bundle_discount = 0.05
    return int(total * (1.0 - bundle_discount))
"""

S4_LARGE_FILE_CODEDNA = """\
# === CODEDNA:0.4 ==============================================
# FILE: pricing.py
# PURPOSE: Pricing engine with tier discounts and bundle calculation
# CONTEXT_BUDGET: always
# DEPENDS_ON: config.py → MAX_DISCOUNT_RATE = 0.30 (hard cap, absolute maximum)
# EXPORTS: apply_discount(cents, tier, promo) → int, calculate_bundle_price(items, tier) → int
# REQUIRED_BY: checkout.py → build_cart(), api.py → POST /order
# STYLE: none
# DB_TABLES: none
# AGENT_RULES: total discount (tier + promo) must NEVER exceed 0.30 (30%); always cap with min(discount, 0.30)
# LAST_MODIFIED: initial pricing engine implementation
# ==============================================================
import math

def get_tier_multiplier(tier: str) -> float:
    tiers = {"basic": 1.0, "silver": 0.9, "gold": 0.85, "premium": 0.8}
    return tiers.get(tier, 1.0)

def format_price(cents: int) -> str:
    return f"€{cents/100:,.2f}"

# ... 150 righe di codice non rilevante ...
""" + "\n".join([f"# filler line {i}" for i in range(150)]) + """

def apply_discount(base_price_cents: int, user_tier: str, promo_code: str = "") -> int:
    # @REQUIRES-READ: config.py -> MAX_DISCOUNT_RATE = 0.30 (HARD CAP - total discount cannot exceed 30%)
    # @MODIFIES-ALSO: checkout.py -> build_cart() (recalculates totals)
    \"\"\"
    Applica lo sconto al prezzo base.
    base_price_cents: prezzo in CENTESIMI
    \"\"\"
    multiplier = get_tier_multiplier(user_tier)
    discount = 1.0 - multiplier

    if promo_code == "EXTRA10":
        discount += 0.10

    # AGENT_RULES: cap - total discount max 0.30
    discount = min(discount, 0.30)  # 0.30 = MAX_DISCOUNT_RATE from config.py

    final = base_price_cents * (1.0 - discount)
    return int(final)

def calculate_bundle_price(items: list, user_tier: str) -> int:
    \"\"\"Prezzo bundle con 5% extra di sconto.\"\"\"
    total = sum(apply_discount(item["price_cents"], user_tier) for item in items)
    bundle_discount = 0.05
    return int(total * (1.0 - bundle_discount))
"""

# L'agente S4 vede SOLO queste righe (sliding window: ultime 50 del file)
S4_WINDOW_START = "def apply_discount"
S4_TASK = (
    "Aggiungi un codice promo 'SUPER20' che applica il 20% di sconto aggiuntivo. "
    "Assicurati di non superare il limite massimo di sconto consentito."
)

# Il Control non sa di MAX_DISCOUNT_RATE (è solo nel manifest o nel commento @REQUIRES-READ)
# Il CodeDNA vede @REQUIRES-READ: config.py → MAX_DISCOUNT_RATE e lo rispetta


# ──────────────────────────────────────────────────────────────────
# FIXTURE S5: CASCADE CHANGE — modifica utils, chi è dipendente?
# ──────────────────────────────────────────────────────────────────

S5_UTILS_NO_CODEDNA = """\
def calcola_kpi(rows: list) -> dict:
    if not rows:
        return {'totale': '€0', 'media': '€0', 'margine_pct': '0.0'}
    totale = sum(r['fatturato'] for r in rows)
    costi  = sum(r['costo'] for r in rows)
    media  = totale / len(rows)
    margine_pct = round((totale - costi) / totale * 100, 1) if totale else 0
    return {
        'totale': format_currency(totale),
        'media':  format_currency(media),
        'margine_pct': margine_pct
    }

def format_currency(n: float) -> str:
    return f'€{n:,.0f}'.replace(',', '.')
"""

S5_MAIN_NO_CODEDNA = """\
from utils import calcola_kpi, format_currency

def render(execute_query_func):
    rows = execute_query_func("SELECT mese, fatturato, costo FROM ordini ORDER BY mese")
    kpi  = calcola_kpi(rows)
    return f\"\"\"<div>
    <p>Totale: {kpi['totale']}</p>
    <p>Media:  {kpi['media']}</p>
    <p>Margine: {kpi['margine_pct']}%</p>
</div>\"\"\"
"""

S5_UTILS_CODEDNA = """\
# === CODEDNA:0.4 ==============================================
# FILE: utils.py
# PURPOSE: KPI aggregation helpers and currency formatting
# CONTEXT_BUDGET: normal
# DEPENDS_ON: none
# EXPORTS: calcola_kpi(rows) → dict{totale,media,margine_pct,nr_mesi?}, format_currency(n) → str
# REQUIRED_BY: main.py → render(), report.py → export_pdf()
# STYLE: none
# DB_TABLES: none
# AGENT_RULES: dict keys are part of the public API — changing them BREAKS callers in REQUIRED_BY
# LAST_MODIFIED: initial KPI helper implementation
# ==============================================================

def calcola_kpi(rows: list) -> dict:
    # @MODIFIES-ALSO: main.py → render() (uses kpi dict — must match keys)
    # @MODIFIES-ALSO: report.py → export_pdf() (uses kpi dict — must match keys)
    if not rows:
        return {'totale': '€0', 'media': '€0', 'margine_pct': '0.0'}
    totale = sum(r['fatturato'] for r in rows)
    costi  = sum(r['costo'] for r in rows)
    media  = totale / len(rows)
    margine_pct = round((totale - costi) / totale * 100, 1) if totale else 0
    return {
        'totale': format_currency(totale),
        'media':  format_currency(media),
        'margine_pct': margine_pct
    }

def format_currency(n: float) -> str:  # @BREAKS-IF-RENAMED: key used in API response schema
    return f'€{n:,.0f}'.replace(',', '.')
"""

S5_MAIN_CODEDNA = """\
# === CODEDNA:0.4 ==============================================
# FILE: main.py
# PURPOSE: Monthly revenue dashboard render function
# CONTEXT_BUDGET: always
# DEPENDS_ON: utils.py → calcola_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# REQUIRED_BY: app.py → register_views()
# STYLE: tailwind, none
# DB_TABLES: ordini (mese, fatturato, costo)
# AGENT_RULES: none
# LAST_MODIFIED: initial dashboard render
# ==============================================================
from utils import calcola_kpi, format_currency

def render(execute_query_func):
    # @REQUIRES-READ: utils.py → calcola_kpi() (check dict keys before accessing)
    rows = execute_query_func("SELECT mese, fatturato, costo FROM ordini ORDER BY mese")
    kpi  = calcola_kpi(rows)
    return f\"\"\"<div>
    <p>Totale: {kpi['totale']}</p>
    <p>Media:  {kpi['media']}</p>
    <p>Margine: {kpi['margine_pct']}%</p>
</div>\"\"\"
"""

S5_TASK = (
    "Aggiungi il numero di mesi al dizionario ritornato da calcola_kpi() con la chiave 'nr_mesi'. "
    "Modifica SOLO utils.py — indica chiaramente se main.py va aggiornato."
)

# ──────────────────────────────────────────────────────────────────
# FIXTURE S6: SEMANTIC NAMING — tipo ambiguo (centesimi vs euro)
# ──────────────────────────────────────────────────────────────────

S6_FILE_NO_CODEDNA = """\
# order.py
import json

def process_order(request_data: dict) -> dict:
    price   = request_data.get("price")       # euro? centesimi? non si sa
    qty     = request_data.get("quantity", 1)
    data    = get_product(request_data["product_id"])
    result  = apply_tax(price * qty)
    return {"total": result, "currency": "EUR"}

def apply_tax(amount, rate=0.22):
    return round(amount * (1 + rate), 2)

def format_receipt(total):
    return f"Totale da pagare: €{total:.2f}"

def get_product(product_id: str) -> dict:
    # simulazione DB
    return {"id": product_id, "name": "Widget", "price_cents": 1999}
"""

S6_FILE_CODEDNA = """\
# === CODEDNA:0.4 ==============================================
# FILE: order.py
# PURPOSE: Order processing with tax calculation and receipt formatting
# CONTEXT_BUDGET: normal
# DEPENDS_ON: none
# EXPORTS: process_order(request_data) → dict, format_receipt(total_cents) → str
# REQUIRED_BY: api.py → POST /order
# STYLE: none
# DB_TABLES: products (id, name, price_cents)
# AGENT_RULES: ALL prices are in integer CENTS; never mix cents and euros; apply_tax input/output is cents
# LAST_MODIFIED: initial order processing
# ==============================================================
import json

def process_order(request_data: dict) -> dict:
    # @REQUIRES-READ: api_spec.md → price field (ALWAYS in integer cents, e.g. 1999 = €19.99)
    int_cents_price_from_request = request_data.get("price")   # CENTS: e.g. 1999
    int_qty_from_request         = request_data.get("quantity", 1)
    dict_product_from_db         = get_product(request_data["product_id"])
    int_cents_subtotal           = int_cents_price_from_request * int_qty_from_request
    int_cents_total_with_tax     = apply_tax(int_cents_subtotal)
    return {"total_cents": int_cents_total_with_tax, "currency": "EUR"}

def apply_tax(int_cents_amount: int, rate: float = 0.22) -> int:
    # @REQUIRES-READ: config.py → DEFAULT_TAX_RATE (always pass as rate param if different)
    return round(int_cents_amount * (1 + rate))

def format_receipt(int_cents_total: int) -> str:
    # @BREAKS-IF-RENAMED: called by string in email_template.py
    float_euros_total = int_cents_total / 100
    return f"Totale da pagare: €{float_euros_total:.2f}"

def get_product(product_id: str) -> dict:
    return {"id": product_id, "name": "Widget", "price_cents": 1999}
"""

S6_TASK = (
    "Aggiungi uno sconto del 15% al subtotale. "
    "Poi mostra nel receipt il prezzo unitario scontato in euro con 2 decimali (es. \"Prezzo unitario: €9.99\"). "
    "ATTENZIONE alle unità di misura usate internamente."
)

# ──────────────────────────────────────────────────────────────────
# FIXTURE S7: BROKEN DEPENDENCY — simbolo rinominato
# ──────────────────────────────────────────────────────────────────

# utils.py aveva format_revenue(), ora si chiama format_currency()
# Il manifest di main.py lo sa (DEPENDS_ON aggiornato)
# Senza CodeDNA, l'agente inventa il nome che sembra sensato

S7_UTILS_NO_CODEDNA = """\
# utils.py — versione corrente
def calcola_kpi(rows: list) -> dict:
    if not rows:
        return {'totale': 0, 'media': 0}
    totale = sum(r['fatturato'] for r in rows)
    return {'totale': totale, 'media': totale / len(rows)}

def format_currency(n: float) -> str:
    return f'€{n:,.0f}'.replace(',', '.')
"""

S7_MAIN_NO_CODEDNA = """\
# main.py — NON aggiornato dopo il rename
from utils import calcola_kpi
# Nota: lo sviluppatore non sa che format_revenue è stato rinominato

def render(execute_query_func):
    rows = execute_query_func("SELECT mese, fatturato, costo FROM ordini")
    kpi  = calcola_kpi(rows)
    totale_fmt = format_revenue(kpi['totale'])  # ← usa il vecchio nome
    return f"<p>Totale: {totale_fmt}</p>"
"""

S7_UTILS_CODEDNA = """\
# === CODEDNA:0.4 ==============================================
# FILE: utils.py
# PURPOSE: KPI aggregation and currency formatting helpers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: none
# EXPORTS: calcola_kpi(rows) → dict, format_currency(n) → str
# REQUIRED_BY: main.py → render(), report.py → build_pdf()
# STYLE: none
# DB_TABLES: none
# AGENT_RULES: format_currency is the ONLY formatting function; format_revenue was removed in v2
# LAST_MODIFIED: renamed format_revenue to format_currency (breaking rename, all callers updated)
# ==============================================================

def calcola_kpi(rows: list) -> dict:
    if not rows:
        return {'totale': 0, 'media': 0}
    totale = sum(r['fatturato'] for r in rows)
    return {'totale': totale, 'media': totale / len(rows)}

def format_currency(n: float) -> str:  # @BREAKS-IF-RENAMED: used in main.py, report.py, email_template.py
    return f'€{n:,.0f}'.replace(',', '.')
"""

S7_MAIN_CODEDNA = """\
# === CODEDNA:0.4 ==============================================
# FILE: main.py
# PURPOSE: Monthly revenue dashboard render function
# CONTEXT_BUDGET: always
# DEPENDS_ON: utils.py → calcola_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# REQUIRED_BY: app.py → register_views()
# STYLE: tailwind
# DB_TABLES: ordini (mese, fatturato, costo)
# AGENT_RULES: always use format_currency() from utils.py — format_revenue() no longer exists
# LAST_MODIFIED: updated import after format_revenue rename
# ==============================================================
from utils import calcola_kpi, format_currency

def render(execute_query_func):
    # @REQUIRES-READ: utils.py → format_currency() (was format_revenue() before v2 — DO NOT use old name)
    rows = execute_query_func("SELECT mese, fatturato, costo FROM ordini")
    kpi  = calcola_kpi(rows)
    return f"<p>Totale: {format_currency(kpi['totale'])}</p>"
"""

S7_TASK = (
    "Aggiungi una riga al dashboard che mostra la media mensile del fatturato, "
    "formattata allo stesso modo del totale."
)

# ──────────────────────────────────────────────────────────────────
# FIXTURE S8: LARGE CODEBASE PLANNING — 8 file, solo manifest
# ──────────────────────────────────────────────────────────────────

S8_MANIFESTS_CODEDNA = """\
# === CODEDNA:0.4 === FILE: app.py | PURPOSE: Flask app factory, route registration | CONTEXT_BUDGET: always | DEPENDS_ON: views/dashboard.py → register(), auth.py → require_login() | EXPORTS: create_app() → Flask | REQUIRED_BY: wsgi.py → app | AGENT_RULES: none | LAST_MODIFIED: added health check route
# === CODEDNA:0.4 === FILE: views/dashboard.py | PURPOSE: Monthly revenue dashboard view with KPI cards | CONTEXT_BUDGET: always | DEPENDS_ON: utils/kpi.py → calcola_kpi(), utils/fmt.py → format_currency() | EXPORTS: register(app) → None, render(qfn) → HTML | REQUIRED_BY: app.py → create_app() | DB_TABLES: ordini (mese, fatturato, costo) | AGENT_RULES: none | LAST_MODIFIED: added margin column
# === CODEDNA:0.4 === FILE: utils/kpi.py | PURPOSE: KPI aggregation helpers for revenue dashboards | CONTEXT_BUDGET: normal | DEPENDS_ON: none | EXPORTS: calcola_kpi(rows) → dict | REQUIRED_BY: views/dashboard.py → render() | AGENT_RULES: dict keys are public API — changing breaks REQUIRED_BY callers | LAST_MODIFIED: added nr_mesi key
# === CODEDNA:0.4 === FILE: utils/fmt.py | PURPOSE: Number and currency formatting utilities | CONTEXT_BUDGET: minimal | DEPENDS_ON: none | EXPORTS: format_currency(n) → str, format_pct(n) → str | REQUIRED_BY: views/dashboard.py → render(), views/report.py → build_pdf() | AGENT_RULES: none | LAST_MODIFIED: initial release
# === CODEDNA:0.4 === FILE: auth.py | PURPOSE: JWT authentication and session management | CONTEXT_BUDGET: always | DEPENDS_ON: db.py → get_user() | EXPORTS: require_login() → decorator, generate_token(user) → str | REQUIRED_BY: app.py → create_app() | DB_TABLES: users (id, email, token_hash) | AGENT_RULES: never log tokens | LAST_MODIFIED: added refresh token rotation
# === CODEDNA:0.4 === FILE: db.py | PURPOSE: Database connection pool and query executor | CONTEXT_BUDGET: normal | DEPENDS_ON: config.py → DB_URL | EXPORTS: execute_query(sql) → list, get_user(email) → dict | REQUIRED_BY: auth.py → require_login(), views/dashboard.py → render() | AGENT_RULES: always use parameterized queries | LAST_MODIFIED: added connection timeout
# === CODEDNA:0.4 === FILE: config.py | PURPOSE: Application configuration and environment loading | CONTEXT_BUDGET: minimal | DEPENDS_ON: none | EXPORTS: DB_URL, JWT_SECRET, MAX_DISCOUNT_RATE | REQUIRED_BY: db.py, auth.py, pricing.py | AGENT_RULES: never hardcode secrets | LAST_MODIFIED: added MAX_DISCOUNT_RATE constant
# === CODEDNA:0.4 === FILE: views/report.py | PURPOSE: PDF report generation from revenue data | CONTEXT_BUDGET: minimal | DEPENDS_ON: utils/kpi.py → calcola_kpi(), utils/fmt.py → format_currency() | EXPORTS: export_pdf(rows) → bytes | REQUIRED_BY: app.py → /export route | AGENT_RULES: none | LAST_MODIFIED: initial PDF report
"""

S8_MANIFESTS_NO_CODEDNA = """\
# app.py — Flask app, registra le route
# views/dashboard.py — Dashboard mensile con KPI
# utils/kpi.py — Helper aggregazioni
# utils/fmt.py — Formattazione numeri
# auth.py — Autenticazione JWT
# db.py — Pool connessioni DB
# config.py — Configurazione ambiente
# views/report.py — Generazione PDF
"""

S8_TASK = (
    "Devo aggiungere un filtro per anno alla dashboard (es. mostrare solo i dati del 2025). "
    "La query SQL deve cambiare e il form HTML deve aggiungere un campo anno. "
    "Elenca ESATTAMENTE quali file devo modificare e perché, senza aprire nessun file in full."
)


# ──────────────────────────────────────────────────────────────────
# PROMPT BUILDERS
# ──────────────────────────────────────────────────────────────────

def build_control_prompt_s4(window_code: str) -> str:
    # Estrae solo la finestra sliding: le righe dopo S4_WINDOW_START
    lines = window_code.split("\n")
    start = next((i for i, l in enumerate(lines) if S4_WINDOW_START in l), 0)
    window = "\n".join(lines[start:start+55])
    return f"""Sei un code editor. Modifica la funzione seguente (estratta da pricing.py) apportando SOLO la modifica richiesta.

RICHIESTA: {S4_TASK}

FRAMMENTO DI CODICE (righe 200-255 di pricing.py):
```python
{window}
```

Rispondi con blocchi SEARCH/REPLACE. Gestisci il limite massimo di sconto se ne sei a conoscenza."""

def build_codedna_prompt_s4(window_code: str) -> str:
    lines = window_code.split("\n")
    start = next((i for i, l in enumerate(lines) if S4_WINDOW_START in l), 0)
    window = "\n".join(lines[start:start+55])
    # Include anche il manifest (prime 14 righe) simulando che l'agente lo abbia letto
    manifest = "\n".join(lines[:14])
    return f"""Sei un code editor. Modifica la funzione seguente apportando SOLO la modifica richiesta.
Hai già letto il manifest CodeDNA del file (mostrato sotto). Segui i tag @REQUIRES-READ che trovi nel frammento.

RICHIESTA: {S4_TASK}

MANIFEST (letto in precedenza):
```
{manifest}
```

FRAMMENTO DI CODICE (righe 200-255 di pricing.py — sliding window):
```python
{window}
```

Rispondi con blocchi SEARCH/REPLACE. Segui AGENT_RULES e @REQUIRES-READ."""

def build_prompt_s5(approach: str) -> str:
    if approach == "control":
        return f"""Sei un code editor. Modifica utils.py apportando SOLO la modifica richiesta.

RICHIESTA: {S5_TASK}

FILE ATTUALI:
--- utils.py ---
```python
{S5_UTILS_NO_CODEDNA}
```
--- main.py ---
```python
{S5_MAIN_NO_CODEDNA}
```

Rispondi con blocchi SEARCH/REPLACE per ogni file che ritieni necessario modificare."""
    else:
        return f"""Sei un code editor. Modifica utils.py apportando SOLO la modifica richiesta.
Leggi i manifest CodeDNA e segui i tag @MODIFIES-ALSO.

RICHIESTA: {S5_TASK}

FILE ATTUALI (con CodeDNA):
--- utils.py ---
```python
{S5_UTILS_CODEDNA}
```
--- main.py ---
```python
{S5_MAIN_CODEDNA}
```

Rispondi con blocchi SEARCH/REPLACE. Segui @MODIFIES-ALSO obbligatoriamente."""

def build_prompt_s6(approach: str) -> str:
    code = S6_FILE_NO_CODEDNA if approach == "control" else S6_FILE_CODEDNA
    return f"""Sei un code editor. Modifica order.py apportando la modifica richiesta.

RICHIESTA: {S6_TASK}

FILE ATTUALE:
```python
{code}
```

Rispondi con blocchi SEARCH/REPLACE. Attenzione alle unità di misura del prezzo."""

def build_prompt_s7(approach: str) -> str:
    if approach == "control":
        return f"""Sei un code editor. Modifica main.py come richiesto.

RICHIESTA: {S7_TASK}

FILE ATTUALI:
--- utils.py ---
```python
{S7_UTILS_NO_CODEDNA}
```
--- main.py ---
```python
{S7_MAIN_NO_CODEDNA.replace("???", "format_revenue(kpi['totale'])")}
```"""
    else:
        return f"""Sei un code editor. Modifica main.py come richiesto. Leggi i manifest CodeDNA.

RICHIESTA: {S7_TASK}

FILE ATTUALI (con CodeDNA):
--- utils.py ---
```python
{S7_UTILS_CODEDNA}
```
--- main.py ---
```python
{S7_MAIN_CODEDNA}
```"""

def build_prompt_s8(approach: str) -> str:
    manifests = S8_MANIFESTS_CODEDNA if approach == "codedna" else S8_MANIFESTS_NO_CODEDNA
    label = "manifest CodeDNA" if approach == "codedna" else "descrizione"
    return f"""Sei un architetto AI. Usando SOLO i {label} dei file sotto (non aprire nessun file), rispondi alla richiesta.

RICHIESTA: {S8_TASK}

{label.upper()} DEI FILE:
{manifests}

Rispondi con: lista ordinata dei file da modificare + motivazione per ciascuno."""


# ──────────────────────────────────────────────────────────────────
# JUDGE + CHECKER
# ──────────────────────────────────────────────────────────────────

enc = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(enc.encode(text))

def judge_quality(scenario_id: str, scenario_name: str, task: str,
                  must_not_break: list, ai_response: str) -> dict:
    extra = ""
    if scenario_id == "S4":
        extra = (
            "\nCRITICAL CHECK S4: Il limite assoluto è MAX_DISCOUNT_RATE = 0.30 (30%).\n"
            "SUPER20 aggiunge 0.20. Gold tier ha già 0.15 di sconto. Totale grezzo = 0.35 > 0.30.\n"
            "CORRETTO: il codice DEVE fare min(discount, 0.30) DOPO aver sommato tutti gli sconti.\n"
            "VIOLATION = TRUE se il codice non include min(discount, 0.30) o equivalente cap dopo SUPER20.\n"
            "Se il cap min() è presente e applicato correttamente = constraint_violation: false."
        )
    elif scenario_id == "S5":
        extra = "\nCRITICAL CHECK: ha notato che main.py va aggiornato per usare la nuova chiave 'nr_mesi'? Se non menziona main.py = score sicurezza < 5."
    elif scenario_id == "S6":
        extra = "\nCRITICAL CHECK: ha capito che i prezzi sono in CENTESIMI? Se divide/moltiplica per 100 sbagliato = score correttezza < 5."
    elif scenario_id == "S7":
        extra = "\nCRITICAL CHECK: ha usato format_currency() e NON format_revenue()? Se usa format_revenue() = score correttezza = 0."
    elif scenario_id == "S8":
        extra = "\nCRITICAL CHECK: ha identificato views/dashboard.py e db.py (o utils/kpi.py) come i file principali? Se lista >4 file senza giustificazione = score precisione < 6."

    judge_prompt = f"""Sei un valutatore esperto di AI code editing. Valuta oggettivamente la risposta.

SCENARIO: {scenario_name}
RICHIESTA ORIGINALE: {task}
FUNZIONI DA NON ROMPERE: {must_not_break}

RISPOSTA DELL'AI:
{ai_response}

{extra}

Valuta su questi criteri (0-10 ciascuno):
1. CORRETTEZZA: la modifica implementa correttamente quanto richiesto?
2. SICUREZZA: non rompe vincoli o funzioni esistenti?
3. PRECISIONE: modifica solo ciò che serve, senza overhead?

Rispondi SOLO con JSON (no markdown):
{{"correttezza": 0-10, "sicurezza": 0-10, "precisione": 0-10, "note": "commento max 2 righe", "cascade_miss": true/false, "constraint_violation": true/false}}

cascade_miss = true se non ha aggiornato file dipendenti quando necessario (S5)
constraint_violation = true se ha violato un vincolo esplicito (S4: MAX_DISCOUNT_RATE, S6: tipo prezzo, S7: funzione rinominata)"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    r = client.models.generate_content(model=MODEL, contents=judge_prompt)
    raw = r.text.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw.strip())
    except Exception as e:
        return {
            "correttezza": 0, "sicurezza": 0, "precisione": 0,
            "note": f"parse error: {raw[:150]}",
            "cascade_miss": False, "constraint_violation": False
        }


# ──────────────────────────────────────────────────────────────────
# DATACLASS + RUNNER
# ──────────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    scenario_id: str
    scenario_name: str
    approach: Literal["control", "codedna"]
    run: int
    prompt_tokens: int
    response_tokens: int
    total_tokens: int
    time_ms: float
    quality_correttezza: float
    quality_sicurezza: float
    quality_precisione: float
    quality_score: float
    cascade_miss: bool = False
    constraint_violation: bool = False
    note: str = ""

SCENARIOS = [
    {
        "id": "S4",
        "name": "Sliding Window — vincolo non dichiarato",
        "task": S4_TASK,
        "must_not_break": ["apply_discount", "calculate_bundle_price", "MAX_DISCOUNT_RATE cap"],
        "prompt_fn": {
            "control": lambda: build_control_prompt_s4(S4_LARGE_FILE_NO_CODEDNA),
            "codedna": lambda: build_codedna_prompt_s4(S4_LARGE_FILE_CODEDNA),
        }
    },
    {
        "id": "S5",
        "name": "Cascade Change — aggiornamento file dipendente",
        "task": S5_TASK,
        "must_not_break": ["calcola_kpi", "render", "format_currency"],
        "prompt_fn": {
            "control": lambda: build_prompt_s5("control"),
            "codedna": lambda: build_prompt_s5("codedna"),
        }
    },
    {
        "id": "S6",
        "name": "Semantic Naming — tipo ambiguo (€ vs centesimi)",
        "task": S6_TASK,
        "must_not_break": ["process_order", "apply_tax", "format_receipt"],
        "prompt_fn": {
            "control": lambda: build_prompt_s6("control"),
            "codedna": lambda: build_prompt_s6("codedna"),
        }
    },
    {
        "id": "S7",
        "name": "Broken Dependency — simbolo rinominato",
        "task": S7_TASK,
        "must_not_break": ["calcola_kpi", "format_currency (NOT format_revenue)"],
        "prompt_fn": {
            "control": lambda: build_prompt_s7("control"),
            "codedna": lambda: build_prompt_s7("codedna"),
        }
    },
    {
        "id": "S8",
        "name": "Planning — 8 file, solo manifest, trovare i 2 giusti",
        "task": S8_TASK,
        "must_not_break": ["correct file identification"],
        "prompt_fn": {
            "control": lambda: build_prompt_s8("control"),
            "codedna": lambda: build_prompt_s8("codedna"),
        }
    },
]


def run_single(approach: str, prompt: str, scenario: dict, run_idx: int) -> RunResult:
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt_tokens = count_tokens(prompt)
    t0 = time.perf_counter()
    r = client.models.generate_content(model=MODEL, contents=prompt)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    response_text = r.text or ""
    response_tokens = count_tokens(response_text)

    quality = judge_quality(
        scenario["id"], scenario["name"], scenario["task"],
        scenario["must_not_break"], response_text
    )
    quality_score = round(
        (quality["correttezza"] + quality["sicurezza"] + quality["precisione"]) / 3, 2
    )

    return RunResult(
        scenario_id=scenario["id"],
        scenario_name=scenario["name"],
        approach=approach,
        run=run_idx,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        total_tokens=prompt_tokens + response_tokens,
        time_ms=round(elapsed_ms, 1),
        quality_correttezza=quality["correttezza"],
        quality_sicurezza=quality["sicurezza"],
        quality_precisione=quality["precisione"],
        quality_score=quality_score,
        cascade_miss=quality.get("cascade_miss", False),
        constraint_violation=quality.get("constraint_violation", False),
        note=quality.get("note", ""),
    )


def run_benchmarks():
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY non impostata. Esporta: export GEMINI_API_KEY=your_key")
        return

    print(f"\n🧬 CodeDNA Benchmark v2.0")
    print(f"   Modello : {MODEL}")
    print(f"   Run/scenario: {RUNS_PER_SCENARIO}")
    print(f"   Scenari : S4, S5, S6, S7, S8")

    results: list[RunResult] = []

    for s in SCENARIOS:
        print(f"\n{'='*65}")
        print(f"SCENARIO {s['id']}: {s['name']}")
        print(f"TASK: {s['task'][:80]}...")
        print(f"{'='*65}")

        for run_i in range(1, RUNS_PER_SCENARIO + 1):
            print(f"\n  [Run {run_i}/{RUNS_PER_SCENARIO}]")

            for approach in ["control", "codedna"]:
                prompt = s["prompt_fn"][approach]()
                print(f"    {approach.upper():10}: ", end="", flush=True)
                r = run_single(approach, prompt, s, run_i)
                results.append(r)
                violation = "⚠️VIOLATION" if r.constraint_violation else ""
                cascade   = "⚠️CASCADE_MISS" if r.cascade_miss else ""
                print(f"quality={r.quality_score}/10 tokens={r.total_tokens} {violation}{cascade}")
                time.sleep(1)

    # ── REPORT ────────────────────────────────────────────────────
    print(f"\n\n{'='*75}")
    print("RISULTATI CODEDNA BENCHMARK v2.0")
    print(f"{'='*75}")
    print(f"{'Scenario':<8} {'Approach':<10} {'Quality':>8} {'Violations':>12} {'CascadeMiss':>13} {'Tokens':>8}")
    print("-" * 75)

    for r in results:
        v = "YES" if r.constraint_violation else "-"
        c = "YES" if r.cascade_miss else "-"
        print(f"{r.scenario_id:<8} {r.approach:<10} {r.quality_score:>8.1f} {v:>12} {c:>13} {r.total_tokens:>8}")

    print(f"\n{'='*55}")
    print("AGGREGATI PER APPROCCIO")
    print(f"{'='*55}")
    for approach in ["control", "codedna"]:
        subset = [r for r in results if r.approach == approach]
        if subset:
            avg_q   = round(sum(r.quality_score for r in subset) / len(subset), 2)
            n_viol  = sum(1 for r in subset if r.constraint_violation)
            n_casc  = sum(1 for r in subset if r.cascade_miss)
            avg_tok = round(sum(r.total_tokens for r in subset) / len(subset))
            print(f"\n{approach.upper()}:")
            print(f"  Quality score (avg):      {avg_q}/10")
            print(f"  Constraint violations:    {n_viol}/{len(subset)}")
            print(f"  Cascade misses:           {n_casc}/{len(subset)}")
            print(f"  Total tokens (avg):       {avg_tok}")

    out_path = os.path.join(os.path.dirname(__file__), "results_v2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)
    print(f"\n✅ Risultati salvati in: {out_path}")
    return results


if __name__ == "__main__":
    run_benchmarks()
