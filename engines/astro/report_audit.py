"""Audit the generated reports for everything a paying customer should never see.

Four classes of problem, counted per file so the rewrite can be prioritised by
what actually appears rather than by what I imagine appears:

  LEAK      internal paths, session ids, developer instructions, debug flags
  JARGON    untranslated Sanskrit / method shorthand
  SEAM      machine artefacts: "1 planet(s)", bare glyph verdicts, enum values
  REPEAT    the same sentence skeleton used many times in one file

Usage:
    python report_audit.py <dir-or-file> [...]        summary table
    python report_audit.py --detail <dir> [pattern]   every hit with context
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from report_fact_guard import visible_text

# ---------------------------------------------------------------------------

LEAKS = {
    "filesystem path": r"(?:^|[\s:=(\"'])/(?:[\w.\-]+/){2,}[\w.\-]+",
    "windows path": r"[A-Za-z]:\\[\w\\.\-]{6,}",
    "session uuid": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    "internal filename": r"\b\w+_(?:ritxx|ritz)\w*\.(?:html|json|csv|png)\b",
    "'your software'": r"cross[- ]check[^.]{0,40}\b(?:your|the)\s+software",
    "build command": r"\b(?:Rebuild(?:\s+corpus)?:\s*)?python3?\s+\w+\.py\b",
    "internal handoff": r"\bthe (?:plain-language )?version for the client is\b",
    "developer aside": r"\b(?:TODO|FIXME|XXX|debug|placeholder|dummy|sample data)\b",
    "uncalibrated flag": r"(?:⚠|warning)[^<.]{0,30}(?:uncalibrated|first pass|unverified)",
    "precompute source": r"\bSource\s+precomputed\b",
    "raw enum": r"\b[a-z]+_[a-z]+(?:_[a-z]+)?\b(?=\s*(?:<|$|[.,]))",
}

JARGON = {
    "antar/antardasha": r"\bantar(?:dasha)?\b",
    "pratyantar": r"\bpratyantar\w*\b",
    "mahadasha": r"\bmaha ?dasha\b",
    "dasha (bare)": r"\bdasha\b",
    "ayanamsa": r"\bayan[aā][mṃn][sś]a\b",
    "atmakaraka": r"\b[aā]tmak[aā]raka\b",
    "other karakas": r"\b(?:amatya|bhratri|matri|putra|gnati|dara)karaka\b",
    "lagna": r"\blagna\b",
    "bhava": r"\bbhava\b",
    "BAV/SAV": r"\b[BS]AV\b",
    "bindu": r"\bbindus?\b",
    "varga name": r"\bD-?\d{1,2}\s+(?:Rasi|Hora|Drekkana|Chaturthamsha|Panchamsha|"
                  r"Shashthamsha|Saptamsha|Ashtamsha|Navamsha|Dashamsha|"
                  r"Rudramsha|Dwadashamsha|Shodashamsha|Vimshamsha|"
                  r"Chaturvimshamsha|Saptavimshamsha|Trimshamsha|"
                  r"Khavedamsha|Akshavedamsha|Shashtiamsha)\b",
    "table shorthand": r"\b(?:Vim|Jai|Yog):",
    "method initials": r"\b(?:BNN|KP|RTVD)\b",
    "graha/rashi": r"\b(?:graha|rashi|rasi)\b",
    "yoga (untranslated)": r"\byoga\b(?!\s*:)",
    "vimshottari": r"\bvimshottari\b",
    "trikona/kendra": r"\b(?:trikona|kendra|dusthana|upachaya)\b",
}

SEAMS = {
    "(s) plural": r"\b\w+\(s\)",
    "bare glyph verdict": r"[▲▼◆△◐⊕⊖](?!\s*<)(?=\s*(?:[A-Z]|$))",
    "label verdict": r"\b(?:Weak\s*/\s*afflicted|Mixed|Strong)\b",
    "raw percentage label": r"\bconfluence\s+\d{1,3}%",
    "ISO date in prose": r"\b\d{4}-\d{2}-\d{2}\b",
    "double space": r"  +",
    "empty parens": r"\(\s*\)",
    "trailing dash": r"—\s*(?:<|$)",
    "unexpanded template": r"\{\w+\}",
    "sentence starts lowercase": r"(?:^|\. )[a-z]{3,}",
    "note-style colon opener": r"(?:^|\. )(?:Running clock|Linked houses|Day lord|"
                               r"Next dasha windows|Report date|Source)\s*:",
}

# A "skeleton" is a sentence with its variable parts blanked out. Many
# identical skeletons in one file is the signature of a template the reader
# will notice.
_SKELETON_BLANKS = (
    (r"\d+(?:\.\d+)?", "#"),
    (r"\b(?:" + "|".join([
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
        "Rahu", "Ketu"]) + r")\b", "P"),
    (r"\b(?:" + "|".join([
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
        "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]) + r")\b", "S"),
)


def skeleton(sentence: str) -> str:
    s = sentence.strip()
    for pat, sub in _SKELETON_BLANKS:
        s = re.sub(pat, sub, s)
    return re.sub(r"\s+", " ", s)[:90]


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 5]


def audit_file(path: Path) -> dict:
    raw = path.read_text(errors="ignore")
    text = visible_text(raw)

    hits: dict[str, Counter] = {
        "LEAK": Counter(), "JARGON": Counter(), "SEAM": Counter()}
    examples: dict[str, str] = {}

    for kind, table, flags in (("LEAK", LEAKS, re.I),
                               ("JARGON", JARGON, re.I),
                               ("SEAM", SEAMS, 0)):
        for name, pattern in table.items():
            found = re.findall(pattern, text, flags)
            if found:
                hits[kind][name] = len(found)
                m = re.search(pattern, text, flags)
                if m:
                    a = max(0, m.start() - 45)
                    examples[f"{kind}/{name}"] = "…" + text[a:m.end() + 45] + "…"

    skels = Counter(skeleton(s) for s in sentences(text))
    repeats = {k: v for k, v in skels.items() if v >= 3}

    return {
        "path": path,
        "words": len(text.split()),
        "hits": hits,
        "examples": examples,
        "repeats": repeats,
        "worst_repeat": max(repeats.values()) if repeats else 0,
    }


def collect(targets: list[str]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.html")))
        elif p.exists():
            out.append(p)
    return out


def main(argv: list[str]) -> int:
    detail = "--detail" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    files = collect(args or ["."])
    if not files:
        print("no html found")
        return 1

    results = [audit_file(f) for f in files]

    totals = {k: Counter() for k in ("LEAK", "JARGON", "SEAM")}
    for r in results:
        for k in totals:
            totals[k].update(r["hits"][k])

    print(f"\n{'file':<44} {'words':>6} {'leak':>5} {'jarg':>5} "
          f"{'seam':>5} {'rpt':>4}")
    print("-" * 74)
    for r in sorted(results, key=lambda x: -(sum(x["hits"]["LEAK"].values()) * 100
                                             + sum(x["hits"]["JARGON"].values()))):
        name = r["path"].name
        if len(name) > 43:
            name = name[:40] + "..."
        print(f"{name:<44} {r['words']:>6} "
              f"{sum(r['hits']['LEAK'].values()):>5} "
              f"{sum(r['hits']['JARGON'].values()):>5} "
              f"{sum(r['hits']['SEAM'].values()):>5} "
              f"{r['worst_repeat'] or '':>4}")

    print(f"\n{len(files)} files, {sum(r['words'] for r in results):,} words\n")
    for kind in ("LEAK", "JARGON", "SEAM"):
        if not totals[kind]:
            continue
        print(f"{kind}")
        for name, n in totals[kind].most_common():
            in_files = sum(1 for r in results if r["hits"][kind].get(name))
            print(f"  {n:>5}×  {name:<28} in {in_files:>2} files")
        print()

    if detail:
        print("=" * 74)
        for r in results:
            if not r["examples"] and not r["repeats"]:
                continue
            print(f"\n### {r['path'].name}")
            for key, ex in sorted(r["examples"].items()):
                print(f"  {key}")
                print(f"      {ex[:170]}")
            for skel, n in sorted(r["repeats"].items(), key=lambda x: -x[1])[:3]:
                print(f"  REPEAT/{n}×  {skel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
