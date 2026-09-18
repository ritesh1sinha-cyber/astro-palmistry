"""Pre-release smoke test: every report kind, free and paid, production flags.

Run before cutting an APK. Calls the handlers the API routes call, so a crash
or an empty section here is a crash or an empty section for a paying customer.

    PYTHONUTF8=1 python prod_smoke.py
"""
from __future__ import annotations

import html as html_lib
import os
import re
import sys
import traceback
from datetime import date

# Production flags, set before core.config is imported.
os.environ.setdefault("CHAT_ENABLED", "0")
os.environ.setdefault("APP_ENV", "production")

sys.path[:0] = ["engines/astro", "."]

FAIL: list[str] = []
WARN: list[str] = []

BIRTH = {
    "name": "Meera Sharma",
    "dob": "1985-03-08",
    "tob": "14:30",
    "place": "Mumbai, India",
    "lat": 19.0760,
    "lon": 72.8777,
    "tz": 5.5,
    "gender": 0,
}

# Text that means a renderer fell through to a placeholder or leaked internals.
# "None" is deliberately absent: "None stand out strongly" is real report copy.
LEAKS = [
    "{}", "nan", "undefined", "Traceback", "NoneType",
    "sub-lord", "sublord", "Bhardwaj", "OCR", "Vimshottari",
    "insufficient_evidence", "moolatrikona", "dusthana", "dhanistha_raw",
]
# Sample-data fingerprints from the hardcoded sections that shipped in 72f022e.
SAMPLE = [
    "31 Aug 2026 (10:07 PM)",
    "Charming domestic atmosphere",
    "Om Ketave Namah",
    "Sudden public recognition drives",
]


def visible(doc: str) -> str:
    body = re.split(r"</style>", doc, flags=re.I)[-1]
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", body)))


def check(name: str, doc: str, *, min_chars: int, paid: bool) -> None:
    if not doc or len(doc) < min_chars:
        FAIL.append(f"{name}: {len(doc or '')} chars, expected >= {min_chars}")
        return
    txt = visible(doc)
    for leak in LEAKS:
        if leak == "\x00":
            continue
        if re.search(rf"\b{re.escape(leak)}\b", txt):
            FAIL.append(f"{name}: leaked internal term {leak!r}")
    for s in SAMPLE:
        if s in doc:
            FAIL.append(f"{name}: SAMPLE DATA {s!r}")
    if re.search(r"<[a-z]+[^>]*>", txt):
        WARN.append(f"{name}: raw HTML tag visible in body text")
    if not paid and "data-unlock" not in doc:
        FAIL.append(f"{name}: free view has no unlock CTA")
    print(f"  ok   {name:44} {len(doc):>7} chars")


def run(label, fn, *, min_chars=3000, paid=False):
    try:
        doc = fn()
    except Exception:
        FAIL.append(f"{label}: raised\n{traceback.format_exc()}")
        print(f"  FAIL {label:44} raised")
        return None
    check(label, doc, min_chars=min_chars, paid=paid)
    return doc


print("=" * 72)
print("1. config flags")
print("=" * 72)
import core.config as C  # noqa: E402

print(f"  chat_enabled            : {C.S.chat_enabled}")
if C.S.chat_enabled:
    FAIL.append("chat_enabled is True with CHAT_ENABLED=0")
print(f"  llm_tab_enabled('chat') : {C.S.llm_tab_enabled('chat')}")
if C.S.llm_tab_enabled("chat"):
    FAIL.append("chat tab enabled in production")

print()
print("=" * 72)
print("2. precompute")
print("=" * 72)
import astro_precompute as AP  # noqa: E402

pc = AP.resolve_precompute(
    BIRTH["name"], BIRTH["dob"], birth_time=BIRTH["tob"],
    latitude=BIRTH["lat"], longitude=BIRTH["lon"], timezone=BIRTH["tz"],
    place_name=BIRTH["place"])
pc.setdefault("meta", {}).update({"dob": BIRTH["dob"], "gender": BIRTH["gender"]})
print(f"  lagna    : {pc.get('lagna')}")
print(f"  planets  : {len(pc.get('planets') or {})}")
if len(pc.get("planets") or {}) < 9:
    FAIL.append("precompute produced fewer than 9 planets")

print()
print("=" * 72)
print("3. full report (the conversational page) — free and paid")
print("=" * 72)
import report_conversational as RConv  # noqa: E402

TODAY = date.today()
free_doc = run("full_report free", lambda: RConv.render(
    pc, name=BIRTH["name"], today=TODAY, paid=False, price=298),
    min_chars=15000, paid=False)
paid_doc = run("full_report paid", lambda: RConv.render(
    pc, name=BIRTH["name"], today=TODAY, paid=True, price=298),
    min_chars=15000, paid=True)

if free_doc and paid_doc:
    print()
    print("  -- regression checks on the conversational page --")
    for probe, doc, want in (
        ("YOUR CHART SIGNATURE", free_doc, True),
        ("WHO YOU ARE", free_doc, True),
        ('id="sec-who-you-are"', free_doc, True),
        ('id="sec-your-current-chapter"', free_doc, True),
        ('id="sec-life-domains"', free_doc, True),
        ("Natal Chart Foundations", free_doc, True),
        ("Active Planetary Transits", free_doc, True),
        ("Remedial Guidance", paid_doc, True),
    ):
        got = probe in doc
        flag = "ok  " if got == want else "FAIL"
        if got != want:
            FAIL.append(f"conversational page: {probe!r} present={got}, want={want}")
        print(f"  {flag} {probe:44} {got}")

    # Free must prove itself on the past and stay silent on the future.
    from free_dates import is_past  # noqa: E402
    MY = re.compile(r"(?:January|February|March|April|May|June|July|August|"
                    r"September|October|November|December)\s+20\d\d")
    ftxt = visible(free_doc)
    future = [d for d in MY.findall(ftxt) if not is_past(d, TODAY)]
    past = [d for d in MY.findall(ftxt) if is_past(d, TODAY)]
    print(f"  {'FAIL' if future else 'ok  '} free page future dates{'':22} {future[:5]}")
    print(f"  {'FAIL' if not past else 'ok  '} free page past-date proof{'':19} {past[:5]}")
    if future:
        FAIL.append(f"free page leaks future dates: {future[:5]}")
    if not past:
        FAIL.append("free page has no past date as proof")

    # Two different charts must not produce the same page.
    pc2 = AP.resolve_precompute(
        "Ravi Kumar", "1992-11-21", birth_time="06:05",
        latitude=17.3850, longitude=78.4867, timezone=5.5, place_name="Hyderabad")
    other = RConv.render(pc2, name="Ravi Kumar", today=TODAY, paid=True, price=298)
    same = visible(other) == visible(paid_doc)
    print(f"  {'FAIL' if same else 'ok  '} two charts differ{'':26} {not same}")
    if same:
        FAIL.append("two different charts rendered identical pages")

print()
print("=" * 72)
print("4. horary — free and paid")
print("=" * 72)
import report_render as RD  # noqa: E402


class _Plain:
    answer = "It leans towards yes, provided you move inside the window."
    verdict = "leaning_yes"
    confidence = "moderate"
    why = ["The ruling influences back the question.",
           "Support outweighs the obstacles this cycle."]
    what_to_do = "Move on it inside the window below."
    reason = ""


verdicts = {"western": {"label": "Leaning yes", "favourable": True,
                        "confidence": "moderate"},
            "vedic": {"label": "Leaning yes", "favourable": True,
                      "confidence": "moderate"}}
wj = {"label": "Leaning yes", "favourable": True, "confidence": "moderate",
      "steps": [{"title": "Querent and quesited", "detail": "Both are placed."}]}
kp = {"sub_lord": "Venus", "ruling_planets": ["Moon", "Venus", "Mercury"],
      "promise": True, "blocking_planet": "Saturn"}

try:
    hfree, hpaid, hmeta = RD.horary(
        question="Will I get the new role?", verdicts=verdicts,
        western_judgment=wj, asked="2026-09-18 10:00", name=BIRTH["name"],
        kp_evidence=kp, plain=_Plain(),
        # _kp_judgment reads window/starts, not start/end.
        timing={"window": "Oct–Dec 2026", "starts": "2026-10-01",
                "ends": "2026-12-15"})
    check("horary free", hfree, min_chars=8000, paid=False)
    check("horary paid", hpaid, min_chars=8000, paid=True)
    print()
    print("  -- horary keeps the rich format --")
    # The dated window is what a paid horary is bought for; the horary page
    # prints it as a list item, not the conversational page's timing-badge.
    for probe in ("Planetary dynamics", "Key timing & dated windows",
                  "Oct–Dec 2026", "In this reading"):
        in_paid = probe in hpaid
        print(f"  {'ok  ' if in_paid else 'FAIL'} paid has {probe:32} {in_paid}")
        if not in_paid:
            FAIL.append(f"horary paid view lost {probe!r}")
    if "Oct–Dec 2026" in hfree:
        FAIL.append("horary free view leaks the dated window")
    if "lock-blur" not in hfree:
        FAIL.append("horary free view has no blurred locked sections")
    print(f"  {'ok  ' if 'lock-blur' in hfree else 'FAIL'} "
          f"free has blurred locked cards{'':13} {'lock-blur' in hfree}")
    verdict_free = "leans towards yes" in hfree.lower()
    verdict_paid = "leans towards yes" in hpaid.lower()
    print(f"  {'FAIL' if verdict_free else 'ok  '} free hides verdict"
          f"{'':26} {not verdict_free}")
    print(f"  {'ok  ' if verdict_paid else 'FAIL'} paid shows verdict"
          f"{'':25} {verdict_paid}")
    if verdict_free:
        FAIL.append("horary free view leaks the verdict")
    if not verdict_paid:
        FAIL.append("horary paid view is missing the verdict")
    print(f"  paidSections: {hmeta.get('paidSections')}")
except Exception:
    FAIL.append(f"horary raised\n{traceback.format_exc()}")
    print("  FAIL horary raised")

print()
print("=" * 72)
print("5. plain-English summary — every kind, free and paid")
print("=" * 72)
import llm.summary as SM  # noqa: E402

for kind, doc in (("full_report", free_doc), ("horary", hfree)):
    for paid in (False, True):
        try:
            out = SM.build_plain_summary(
                kind=kind, html=doc or "<p>x</p>",
                meta={"language": "en"}, paid=paid)
            secs = out.get("sections") or []
            gen = out.get("generated")
            blob = " ".join(str(s.get("body", "")) for s in secs)
            ok = bool(secs)
            print(f"  {'ok  ' if ok else 'FAIL'} summary {kind:12} "
                  f"paid={str(paid):5} {len(secs)} sections via {gen}")
            if not ok:
                FAIL.append(f"summary {kind} paid={paid} produced no sections")
            if not paid and re.search(r"\b20(2[7-9]|[3-9]\d)\b", blob):
                FAIL.append(f"summary {kind} free leaks a future year")
            if not paid and kind == "horary" and re.search(
                    r"leans towards yes|the answer is yes", blob, re.I):
                FAIL.append("summary horary free leaks the verdict")
        except Exception:
            FAIL.append(f"summary {kind} paid={paid} raised\n"
                        f"{traceback.format_exc()}")
            print(f"  FAIL summary {kind} paid={paid} raised")

print()
print("=" * 72)
print("6. localized pages (Hinglish / Tenglish) must not crash")
print("=" * 72)
for lang in ("hi_en", "te_en"):
    for paid in (False, True):
        run(f"full_report {lang} paid={paid}", lambda l=lang, p=paid: RConv.render(
            pc, name=BIRTH["name"], today=TODAY, paid=p, price=298, lang=l),
            min_chars=12000, paid=paid)
    try:
        out = SM.build_plain_summary(
            kind="full_report", html=free_doc, meta={"language": lang}, paid=False)
        n = len(out.get("sections") or [])
        print(f"  {'ok  ' if n else 'FAIL'} summary {lang} free{'':22} "
              f"{n} sections via {out.get('generated')}")
        if not n:
            FAIL.append(f"summary {lang} produced no sections")
    except Exception:
        FAIL.append(f"summary {lang} raised\n{traceback.format_exc()}")
        print(f"  FAIL summary {lang} raised")

print()
print("=" * 72)
print("7. frontend shell (site/index.html)")
print("=" * 72)
from pathlib import Path  # noqa: E402

idx = Path("site/index.html").read_text(encoding="utf-8")
checks = [
    ("chat defaults off", bool(re.search(r"chatEnabled\s*:\s*false", idx))),
    # 23f9a01 made KP the live horary engine and h_horary now rejects a
    # request without a 1-249 number, so the input has to be on the page.
    ("KP number input present", "kpNumber" in idx),
    ("summary button present", "openPlainSummary" in idx),
    ("razorpay checkout present", "checkout.razorpay.com" in idx),
    ("unlock handler present", "data-unlock" in idx),
]
for label, got in checks:
    print(f"  {'ok  ' if got else 'FAIL'} {label:44} {got}")
    if not got:
        FAIL.append(f"site/index.html: {label} failed")

print()
print("=" * 72)
if WARN:
    print(f"{len(WARN)} WARNING(S)")
    for w in WARN:
        print(f"  warn {w}")
if FAIL:
    print(f"{len(FAIL)} FAILURE(S) — DO NOT SHIP")
    for f in FAIL:
        print(f"  FAIL {f}")
    sys.exit(1)
print("ALL SMOKE CHECKS PASSED")
