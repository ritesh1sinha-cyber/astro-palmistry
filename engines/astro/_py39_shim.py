"""
SANDBOX-ONLY test shim. Not part of the delivered integration.

The astro engine targets Python 3.10+ and uses `str | None` in annotations that
are evaluated at def time. This sandbox has only Python 3.9 (and no C compiler,
so pyswisseph can't be built for a 3.12 venv). PEP 563 makes annotations lazy,
so prepending `from __future__ import annotations` to each module makes the
engine importable on 3.9 without touching a line of logic.

Import this before importing any engine module.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FUTURE = "from __future__ import annotations\n"


class _Loader(importlib.machinery.SourceFileLoader):
    def get_source(self, fullname):
        src = super().get_source(fullname)
        # never double-prepend: a second __future__ import is a SyntaxError
        if src is None or "from __future__ import annotations" in src:
            return src
        return FUTURE + src

    def get_code(self, fullname):
        src = self.get_source(fullname)
        return compile(src, self.get_filename(fullname), "exec", dont_inherit=False)


def _jhora_root():
    for p in sys.path:
        c = Path(p) / "jhora"
        if (c / "__init__.py").is_file():
            return c.parent
    return None


JHORA_BASE = _jhora_root()


class _Finder(importlib.abc.MetaPathFinder):
    """Serve engine modules AND the jhora package through the rewriting loader."""

    def _candidates(self, fullname):
        parts = fullname.split(".")
        if len(parts) == 1:
            yield ROOT / (fullname + ".py"), False
        if parts[0] == "jhora" and JHORA_BASE:
            base = JHORA_BASE.joinpath(*parts)
            yield base / "__init__.py", True
            yield base.with_suffix(".py"), False

    def find_spec(self, fullname, path=None, target=None):
        for f, is_pkg in self._candidates(fullname):
            if not f.is_file():
                continue
            spec = importlib.util.spec_from_file_location(
                fullname, str(f), loader=_Loader(fullname, str(f)),
                submodule_search_locations=[str(f.parent)] if is_pkg else None,
            )
            return spec
        return None


if not any(isinstance(f, _Finder) for f in sys.meta_path):
    sys.meta_path.insert(0, _Finder())


def patch_pyjhora() -> None:
    """
    The engine calls PyJHora with `dhasa_level_index=`, which exists in the
    version the author pins but not in 4.5.5 (the newest release that imports
    on 3.9 — 4.8.x itself needs 3.10+). Map it onto `include_antardhasa` so the
    pipeline runs here. Sandbox-only; the author's own env needs no such patch.
    """
    from jhora.horoscope.dhasa.graha import vimsottari

    orig = getattr(vimsottari, "_orig_gvdb", None) or vimsottari.get_vimsottari_dhasa_bhukthi
    vimsottari._orig_gvdb = orig

    def wrapper(jd, place, *a, **kw):
        lvl = kw.pop("dhasa_level_index", None)
        if lvl is not None and "include_antardhasa" not in kw:
            try:
                return orig(jd, place, *a, dhasa_level_index=lvl, **kw)
            except TypeError:
                kw["include_antardhasa"] = lvl >= 2
        return orig(jd, place, *a, **kw)

    vimsottari.get_vimsottari_dhasa_bhukthi = wrapper

    # 4.8.x returns dhasa rows whose first element is a (lord, ...) tuple, while
    # the engine indexes planet_list with it directly. Make the list tolerant.
    from jhora.horoscope.chart import house as pj_house

    class _TolerantList(list):
        def __getitem__(self, k):
            while isinstance(k, tuple) and k:
                k = k[0]
            return list.__getitem__(self, k)

    if not isinstance(pj_house.planet_list, _TolerantList):
        pj_house.planet_list = _TolerantList(pj_house.planet_list)
