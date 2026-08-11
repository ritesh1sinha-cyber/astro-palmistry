"""Host-side Docker smoke regen — run generators in api container and copy HTML to ci-storage."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "ci-storage"
REVIEW = CI / "review_html"
OVERSAMPLE = CI / "oversample"

V3_LEGACY_PHRASES = [
    "built by difficulty rather than by encouragement",
    "visibly changed the people who went through it with you",
    "you tend to recover from setbacks with more resilience than people may expect",
    "you are better at earning than at holding",
    "people notice you before you have said anything",
    "government, public-sector or state-funded work has run through your line",
    "openings have come through your reputation rather than through applications",
    "money has reached you at least once from a source you did not earn week by week",
]

CONTAINER = "astro-palmistry-local-api-1"
COMPRESSED_REVIEW = Path(
    r"C:\Users\IN009287\Downloads\Compressed\latest\review_html"
)


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _grep_banned(paths: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8", errors="replace").lower()
        for phrase in V3_LEGACY_PHRASES:
            if phrase in body:
                hits.append(f"{path.name}: {phrase[:50]}")
    return hits


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    OVERSAMPLE.mkdir(parents=True, exist_ok=True)

    # ci-storage is not baked into the image; copy generators into the container.
    for script in ("gen_interactive_review.py", "gen_oversample_reports.py"):
        _run(["docker", "cp", str(CI / script), f"{CONTAINER}:/tmp/{script}"])

    _run(["docker", "exec", CONTAINER, "python", "/tmp/gen_interactive_review.py"])
    _run(["docker", "exec", CONTAINER, "python", "/tmp/gen_oversample_reports.py"])

    copies = [
        (f"{CONTAINER}:/tmp/review_samples/astro_full_report_free.html", CI / "astro_full_report_free.html"),
        (f"{CONTAINER}:/tmp/review_samples/astro_full_report_paid.html", CI / "astro_full_report_paid.html"),
    ]
    for src, dst in copies:
        _run(["docker", "cp", src, str(dst)])
        shutil.copy2(dst, REVIEW / dst.name)

    for slug in ("ramesh_1986-03-08_delhi", "suresh_1990-01-12_delhi", "gyanesh_2012-01-01_hyderabad"):
        for tier in ("free", "paid"):
            src = f"{CONTAINER}:/tmp/review_samples/oversample/{slug}_{tier}.html"
            dst = OVERSAMPLE / f"{slug}_{tier}.html"
            _run(["docker", "cp", src, str(dst)])
            shutil.copy2(dst, REVIEW / dst.name)

    index_src = f"{CONTAINER}:/tmp/review_samples/oversample/index.json"
    _run(["docker", "cp", index_src, str(OVERSAMPLE / "index.json")])

    COMPRESSED_REVIEW.mkdir(parents=True, exist_ok=True)
    for src_dir in (CI, REVIEW, OVERSAMPLE):
        for html in src_dir.glob("*.html"):
            shutil.copy2(html, COMPRESSED_REVIEW / html.name)

    html_files = list(CI.glob("*.html")) + list(OVERSAMPLE.glob("*.html"))
    hits = _grep_banned(html_files)
    if hits:
        print("BANNED PHRASE HITS:", file=sys.stderr)
        for h in hits:
            print(" ", h, file=sys.stderr)
        return 1

    print(
        f"Smoke regen OK — {len(html_files)} HTML files, zero v3 legacy hits; "
        f"copied to {REVIEW} and {COMPRESSED_REVIEW}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
