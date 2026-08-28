"""Verify admin order lookup by customer email and order ID, and unlock capability."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment before imports
os.environ.setdefault("DATABASE_URL", "sqlite:///test_admin_lookup.db")
os.environ.setdefault("ADMIN_EMAILS", "admin@graharekha.com")
os.environ.setdefault("APP_ENV", "development")

from core import db, auth, billing
from core.db import engine
from sqlalchemy import text

# Initialize DB schema
db.init_schema()

# Create admin user and normal test user
admin_u = db.upsert_user(email="admin@graharekha.com", name="Admin User")
normal_u = db.upsert_user(email="lostcustomer@example.com", name="Lost Customer")

# Create a couple of orders for normal user
o1 = billing.create_order(normal_u["id"], "user_question", ref_id="rep_test_1")
o2 = billing.create_order(normal_u["id"], "full_report", ref_id="rep_test_2")

print(f"Created order 1: {o1['orderId']} for {normal_u['email']}")
print(f"Created order 2: {o2['orderId']} for {normal_u['email']}")

# Test orders_lookup_admin logic directly
from api import orders_lookup_admin, order_mark_paid_admin

# 1. Look up by exact email
res1 = orders_lookup_admin(q="lostcustomer@example.com", user=admin_u)
print("Lookup by full email result:", len(res1["orders"]), "orders found.")
assert len(res1["orders"]) == 2, f"Expected 2 orders, got {len(res1['orders'])}"
assert res1["orders"][0]["email"] == "lostcustomer@example.com"

# 2. Look up by partial email
res2 = orders_lookup_admin(q="lostcustomer", user=admin_u)
print("Lookup by partial email result:", len(res2["orders"]), "orders found.")
assert len(res2["orders"]) == 2

# 3. Look up by specific Order ID
res3 = orders_lookup_admin(q=o1["orderId"], user=admin_u)
print("Lookup by Order ID result:", len(res3["orders"]), "orders found.")
assert len(res3["orders"]) == 1
assert res3["orders"][0]["orderId"] == o1["orderId"]

# 4. Mark order 1 as paid via admin
unlock_res = order_mark_paid_admin(o1["orderId"], user=admin_u)
print("Unlock result:", unlock_res)
assert unlock_res["status"] == "paid"

# 5. Verify lookup shows order 1 paid and order 2 unpaid
res4 = orders_lookup_admin(q="lostcustomer@example.com", user=admin_u)
status_map = {o["orderId"]: o["status"] for o in res4["orders"]}
print("Statuses after unlock:", status_map)
assert status_map[o1["orderId"]] == "paid"
assert status_map[o2["orderId"]] == "created"

# Cleanup test db
try:
    if os.path.exists("test_admin_lookup.db"):
        os.remove("test_admin_lookup.db")
except Exception:
    pass

print("ALL ADMIN ORDER LOOKUP TESTS PASSED SUCCESSFULLY!")
