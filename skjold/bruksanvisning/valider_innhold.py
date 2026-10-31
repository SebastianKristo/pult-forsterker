import json, sys
d = json.load(open(sys.argv[1])); err = []
FIELDS = {"cover": {"lead", "img"}, "inventory": {"title", "groups"}, "tools": {"title", "tools", "note"},
          "section": {"n", "title", "sub", "img"}, "step": {"n", "title", "parts", "img", "wires", "tips", "warn"},
          "check": {"n", "title", "checks", "img"}, "end": {"title", "body", "img"}}
inv = {}
for pg in d["pages"]:
    if pg["type"] == "inventory":
        cnt = sum(len(g["parts"]) for g in pg["groups"])
        if cnt > 30: err.append(f"{pg['title']}: {cnt} parts")
        for g in pg["groups"]:
            for p in g["parts"]:
                if p["id"] in inv and inv[p["id"]] != p["name"]: err.append("dup id " + p["id"])
                inv[p["id"]] = p["name"]
n = 0; sec = 0
for i, pg in enumerate(d["pages"]):
    t = pg["type"]
    if t not in FIELDS: err.append(f"p{i}: type {t}"); continue
    if set(pg) - {"type"} != FIELDS[t]: err.append(f"p{i}: fields {sorted(set(pg) ^ FIELDS[t] - {'type'})}")
    if t in ("step", "check"):
        n += 1
        if pg["n"] != n: err.append(f"p{i}: n={pg['n']} expected {n}")
    if t == "section":
        sec += 1
        if pg["n"] != sec: err.append(f"p{i}: section n")
    if t == "step":
        if len(pg["parts"]) > 5: err.append(f"step {pg['n']}: parts")
        if len(pg["wires"]) > 5: err.append(f"step {pg['n']}: wires")
        if len(pg["tips"]) > 2: err.append(f"step {pg['n']}: tips")
        for p in pg["parts"]:
            if p["id"] not in inv: err.append(f"step {pg['n']}: id {p['id']} not in inventory")
        for w in pg["wires"]:
            if set(w) != {"from", "to", "color", "colorName", "awg", "len"}: err.append(f"step {pg['n']}: wire fields")
    if t == "check" and len(pg["checks"]) > 6: err.append(f"check {pg['n']}: checks")
print("pages", len(d["pages"]), "steps", n, "inventory ids", len(inv))
print("\n".join(err) or "OK"); sys.exit(1 if err else 0)
