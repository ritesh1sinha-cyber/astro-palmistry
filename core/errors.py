"""Errors whose text is safe to show a customer.

`friendly()` in worker.py used to pass through any short ValueError or
KeyError, on the theory that those are validation problems worth explaining.
End-to-end testing showed what that actually produces:

    We could not complete this: invalid literal for int() with base 10: 'male'

A Python exception, verbatim, in a paid astrology report. The distinction the
old rule was reaching for is not "short" or "ValueError" — it is *intent*.
A message is safe when someone wrote it for a reader.

So: raise UserError when you have written the sentence yourself. Everything
else gets a generic apology, and the real exception goes to the log where it
belongs.
"""

from __future__ import annotations


class UserError(Exception):
    """An error whose message was written to be read by a customer."""


def gender_code(value, *, default: int = 0) -> int:
    """Normalise however gender arrived into the 0/1 the engines expect.

    The two front-end flows disagree: the palm form posts pill values
    ("male"/"female"), the astrology form posts a <select> with 0/1. Both are
    reasonable; both reach the same chart record. Coercing here means neither
    form has to change and a third caller cannot break it again.
    """
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return 1 if int(value) == 1 else 0
    text = str(value).strip().lower()
    if text in ("1", "f", "female", "woman", "girl", "she"):
        return 1
    if text in ("0", "m", "male", "man", "boy", "he"):
        return 0
    if text in ("other", "x", "nonbinary", "non-binary", "prefer not to say"):
        return default
    raise UserError(
        "Please choose male or female — the classical rules for a few "
        "readings are calculated differently for each.")
