# Swiss Ephemeris data files

Put the `*.se1` files here before building the worker image.

The PyJHora wheel has shipped **without** them since 3.6.6. Without them
`swisseph` silently falls back to its built-in Moshier model — accurate to a
fraction of a degree for modern dates, but not bit-identical to Jagannatha Hora.
On our test chart that showed up as a lagna of 19.4236° instead of 19.4218°.

Source: https://github.com/naturalstupid/pyjhora → `src/jhora/data/ephe`

They are gitignored (large, and licensed separately by Astrodienst).
