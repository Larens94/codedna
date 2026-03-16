"""
run.py — Entry point: generates both project versions on disk.

Usage:
    python3 enterprise/run.py

Output:
    projects/enterprise_control/   ← clean Python, no docstrings
    projects/enterprise_codedna/   ← same code + CodeDNA module docstrings

5 BUGS hidden (no hints in docstrings):
  B1: analytics/revenue.py sums ALL invoices including suspended tenants
  B2: products/inventory.py check_stock + decrement_stock are not atomic
  B3: api/products.py checks user['is_admin'] but field is role=='admin'
  B4: payments/invoices.py (no bug here — orders/checkout.py applies tax once)
  B5: orders/fulfillment.py doesn't decrement inventory after fulfillment

3 TASKS to implement:
  T1: Discount code support in cart → checkout → invoice chain
  T2: Tenant usage endpoint: GET /admin/tenants/<id>/usage
  T3: Low-stock email alert after inventory decrement
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from arch import ARCH
from distractors import DISTRACTORS
from codegen import write_project

BASE = Path(__file__).parent.parent / "projects"

# Merge architecture + distractors
FULL_ARCH = ARCH + DISTRACTORS


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    print("🏗️  MarketCore — Enterprise Codebase Generator (LARGE)")
    print("=" * 60)
    print(f"Core files:       {len(ARCH)}")
    print(f"Distractor files: {len(DISTRACTORS)}")
    print(f"Total:            {len(FULL_ARCH)}")
    print("=" * 60)

    ctrl_lines = write_project(FULL_ARCH, "control", BASE / "enterprise_control")
    cdna_lines = write_project(FULL_ARCH, "codedna", BASE / "enterprise_codedna")

    print(f"\n📂 Projects in {BASE}")
    print(f"   enterprise_control/ — {len(FULL_ARCH)} files, ~{ctrl_lines} lines (no docstrings)")
    print(f"   enterprise_codedna/ — {len(FULL_ARCH)} files, ~{cdna_lines} lines (with CodeDNA)")
    print()
    print("═" * 60)
    print("HIDDEN BUGS (no hints in docstrings):")
    print("  B1 analytics/revenue.py      — suspended tenants in revenue total")
    print("  B2 products/inventory.py     — non-atomic check+decrement (race)")
    print("  B3 api/products.py           — user['is_admin'] vs role=='admin'")
    print("  B4 orders/fulfillment.py     — inventory not decremented on fulfill")
    print("  B5 payments/invoices.py area — trace the tax chain yourself")
    print()
    print("TASKS TO IMPLEMENT:")
    print("  T1 discount_code: cart.py → checkout.py → invoices.py")
    print("  T2 usage endpoint: admin.py → analytics/usage.py")
    print("  T3 low-stock alert: inventory.py → notifications/email.py")
    print("═" * 60)


if __name__ == "__main__":
    main()
