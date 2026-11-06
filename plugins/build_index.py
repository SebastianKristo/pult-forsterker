"""Lager plugins/index.json (katalogen i plugin-butikken) med sha256 for hver fil. Kjør etter endring i et plugin:
    python3 plugins/build_index.py
"""
import hashlib
import json
import os

HER = os.path.dirname(os.path.abspath(__file__))
FELT = ("id", "navn", "versjon", "forfatter", "beskrivelse", "ikon", "kategori", "minSkjold", "tillatelser")


def main():
    out = []
    for pid in sorted(os.listdir(HER)):
        d = os.path.join(HER, pid)
        if not os.path.isfile(os.path.join(d, "plugin.json")):
            continue
        m = json.load(open(os.path.join(d, "plugin.json")))
        files = []
        for root, _dirs, names in os.walk(d):
            for n in sorted(names):
                if n.endswith(".pyc") or n.startswith("."):
                    continue
                p = os.path.join(root, n)
                files.append({"path": os.path.relpath(p, d), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()})
        out.append({**{k: m[k] for k in FELT if k in m}, "files": sorted(files, key=lambda f: f["path"])})
    idx = {"format": 1, "base": "https://raw.githubusercontent.com/SebastianKristo/pult-forsterker/main/plugins/", "plugins": out}
    with open(os.path.join(HER, "index.json"), "w") as fh:
        json.dump(idx, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"{len(out)} plugins i index.json")


if __name__ == "__main__":
    main()
