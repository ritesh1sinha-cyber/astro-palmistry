"""Run inside API container: docker exec astro-palmistry-local-api-1 python /app/scripts/verify_report_ux_container.py"""
from core.pdf_export import entitlement_item_for_kind, report_title, html_to_pdf

assert entitlement_item_for_kind("palm") == "palm_full"
assert entitlement_item_for_kind("numerology") == "numerology_full"
assert entitlement_item_for_kind("full_report") == "full_report"

from engines.astro import report_cards

html_free = report_cards.render({}, name="Test", paid=False)
html_paid = report_cards.render({}, name="Test", paid=True)
assert 'class="buy"' in html_free
assert "Unlock full reading" in html_free
assert 'class="buy"' not in html_paid
assert "Unlock full reading" not in html_paid

from core import palm_cards

pf = palm_cards.render({}, name="X", paid=False)
pp = palm_cards.render({}, name="X", paid=True)
assert "Unlock full reading" in pf
assert "Unlock full reading" not in pp

pdf = html_to_pdf("<html><head></head><body><p>test</p></body></html>")
assert len(pdf) > 500

print("verify_report_ux_container: OK", len(pdf))
