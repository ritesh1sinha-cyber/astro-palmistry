#!/usr/bin/env python3
"""One-off scrub of personal sample data from dev defaults."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBS = [
    ('default="Sample"', 'default="Sample"'),
    ('default="1990-01-15"', 'default="1990-01-15"'),
    ('default="12:00"', 'default="12:00"'),
    ('default="New Delhi, India"', 'default="New Delhi, India"'),
    ('default="New Delhi, India"', 'default="New Delhi, India"'),
    ('default=28.6139', 'default=28.6139'),
    ('default=77.2090', 'default=77.2090'),
    ('client_name="Sample"', 'client_name="Sample"'),
    ('dob="1990-01-15"', 'dob="1990-01-15"'),
    ('birth_time="12:00"', 'birth_time="12:00"'),
    ('place="New Delhi, India"', 'place="New Delhi, India"'),
    ('latitude=28.6139', 'latitude=28.6139'),
    ('longitude=77.2090', 'longitude=77.2090'),
    ('attach_contexts(pc, latitude=28.6139, longitude=77.2090',
     'attach_contexts(pc, latitude=28.6139, longitude=77.2090'),
    ('default="New Delhi"', 'default="New Delhi"'),
    ('"New Delhi, India"', '"New Delhi, India"'),
    ('e.g. New Delhi, India', 'e.g. New Delhi, India'),
    ('e.g. New Delhi', 'e.g. New Delhi'),
    ('e.g. Sample, Partner', 'e.g. Sample, Partner'),
    ('e.g. Sample User', 'e.g. Sample User'),
    ('DOB: 1990-01-15', 'DOB: 1990-01-15'),
    ('15 January 1990', '15 January 1990'),
    ('1985-03-08 → 15 January 1990', '1990-01-15 → 15 January 1990'),
    ('--name Sample', '--name Sample'),
    ('groom="Sample"', 'groom="Sample"'),
    ('bride="Partner"', 'bride="Partner"'),
    ('Sample &amp; Partner', 'Sample &amp; Partner'),
    ('Sample & Partner', 'Sample & Partner'),
    ('Sample — 1990-01-15 12:00 New Delhi (28.6139, 77.2090, tz 5.5)',
     'Sample — 1990-01-15 12:00 New Delhi (28.6139, 77.2090, tz 5.5)'),
    ('Partner — 1992-06-20 08:30 New Delhi (matching)',
     'Partner — 1992-06-20 08:30 New Delhi (matching)'),
    ('2026-08-03 21:30, New Delhi', '2026-08-03 21:30, New Delhi'),
    ('Sample_8f6a07', 'Sample_8f6a07'),
    ('"name": "Sample User"', '"name": "Sample User"'),
    ('--place "New Delhi, India"', '--place "New Delhi, India"'),
    ('Sample 1990-01-15', 'Sample 1990-01-15'),
]

changed = []
for p in list(ROOT.rglob("*.py")) + [ROOT / "fixtures" / "make_palms.py"]:
    if any(x in str(p) for x in (".git", "__pycache__", "node_modules")):
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        continue
    orig = text
    for a, b in SUBS:
        text = text.replace(a, b)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        changed.append(str(p.relative_to(ROOT)))

print(f"updated {len(changed)} files")
for c in changed:
    print(" ", c)
