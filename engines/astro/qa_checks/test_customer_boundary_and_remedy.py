"""Regression tests for final customer boundary and remedy cross-reference."""
from __future__ import annotations

from qa_checks.customer_text_sanitizer import validate_customer_text
import remedy_block


def main() -> None:
    bad = """
    <section>
      <p>8th lord Saturn sits here.</p>
      <p>Spouse: Your spouse is...</p>
      <p>boo</p>
      <p>the classical rule-book says...</p>
    </section>
    """
    hits = validate_customer_text(bad)
    assert hits, "raw technical/classical text must fail the customer boundary"
    assert any("boo" in h.lower() for h in hits)

    # The paid remedy footer must never name a hard-coded unrelated gemstone.
    source = open(remedy_block.__file__, encoding="utf8").read()
    assert "test the yellow stone for three days" not in source.lower()
    assert "specific trial period" in source.lower() and "shown for that stone" in source.lower()

    print("customer boundary + remedy regression: PASS")


if __name__ == "__main__":
    main()
