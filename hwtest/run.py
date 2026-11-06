#!/usr/bin/env python3
"""Kjør maskinvaretestene: python3 hwtest/run.py [pytest-argumenter]. Skriver JUnit (hwtest-out/junit.xml) og et
Markdown-sammendrag (hwtest-out/summary.md) som workflowen legger i jobbsammendraget."""
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

here = os.path.dirname(os.path.abspath(__file__))
out = os.environ.setdefault("HWTEST_OUT", os.path.join(os.getcwd(), "hwtest-out"))
os.makedirs(out, exist_ok=True)
junit = os.path.join(out, "junit.xml")
rc = subprocess.call([sys.executable, "-m", "pytest", "-v", "-rs", f"--junitxml={junit}", "-p", "no:cacheprovider",
                      os.path.join(here, "test_hw.py"), *sys.argv[1:]], cwd=here)

rows, tot = [], {"ok": 0, "feil": 0, "hoppet over": 0}
try:
    for tc in ET.parse(junit).iter("testcase"):
        name = tc.get("name")
        if tc.find("failure") is not None or tc.find("error") is not None:
            el = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
            res, why = "❌ feil", (el.get("message") or "").splitlines()[0][:160]
            tot["feil"] += 1
        elif tc.find("skipped") is not None:
            res, why = "⏭ hoppet over", (tc.find("skipped").get("message") or "")[:160]
            tot["hoppet over"] += 1
        else:
            res, why = "✅ ok", ""
            tot["ok"] += 1
        rows.append(f"| {name} | {res} | {why.replace('|', '/')} |")
except Exception as e:  # noqa: BLE001
    rows.append(f"| (kunne ikke lese JUnit: {e}) | | |")
with open(os.path.join(out, "summary.md"), "w") as fh:
    fh.write(f"## Maskinvaretester – {tot['ok']} ok, {tot['feil']} feil, {tot['hoppet over']} hoppet over\n\n")
    fh.write("| Test | Resultat | Merknad |\n|---|---|---|\n" + "\n".join(rows) + "\n")
print(open(os.path.join(out, "summary.md")).read())
sys.exit(rc)
