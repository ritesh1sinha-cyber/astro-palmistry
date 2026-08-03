# Swiss Ephemeris data files

Put the `*.se1` files here before building the worker image.

The PyJHora wheel has shipped **without** them since 3.6.6. Without them
`swisseph` silently falls back to its built-in Moshier model — accurate to a
fraction of a degree for modern dates, but not bit-identical to Jagannatha Hora.
On our test chart that showed up as a lagna of 19.4236° instead of 19.4218°.

Source: https://github.com/naturalstupid/pyjhora → `src/jhora/data/ephe`

They are gitignored (large, and licensed separately by Astrodienst), so they are
**not** baked into the image — a `COPY` of this directory would fail in a clean
clone. Instead, install them at runtime:

1. Put the `*.se1` files on a mounted volume, e.g. `/data/ephe`.
2. Set `EPHE_PATH=/data/ephe`.

`deploy/entrypoint.sh` copies them into the jhora package before the server
starts, and logs how many it found. Skip this entirely and everything still
works — positions just come from swisseph's built-in model.
