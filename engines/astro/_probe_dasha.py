from astro_precompute import resolve_precompute
import json
pc = resolve_precompute("Ritesh","1985-03-08", birth_time="13:05", latitude=25.5941, longitude=85.1376, timezone=5.5, place_name="Patna, India")
for k in ("vimshottari","yogini","jaimini","chara_dasha"):
    v = pc.get(k)
    print("==== ", k, " type:", type(v))
    if isinstance(v, dict):
        print("  keys:", list(v.keys())[:12])
        # print a small nested sample
        s = json.dumps(v, default=str)[:800]
        print("  sample:", s)
    elif isinstance(v, list):
        print("  len:", len(v), " first:", json.dumps(v[0], default=str)[:600] if v else None)
