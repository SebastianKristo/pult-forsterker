#!/usr/bin/env python3
"""Autoruting: build_board.py -> board.dsn -> Freerouting -> board.ses. Deretter: python3 export.py
   FREEROUTING=/sti/til/freerouting.jar python3 route.py [-mp 40]"""
import os, subprocess, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "ki_pultforsterker_main.kicad_pcb")
_env = dict(os.environ, KI_PCB_WIDE="1" if "--power-first" in sys.argv else "0")
subprocess.run([sys.executable, os.path.join(HERE, "build_board.py")], check=True, env=_env)
if "--continue" in sys.argv:
    # legg inn forrige rutingresultat (board.ses) i det nybygde kortet, så Freerouting bare fullfører det som mangler
    import re
    src = open(os.path.join(HERE, "export.py")).read()
    ns = {}; exec(src[src.index("def ses_to_sexpr"):src.index("# 1) regenerer")], ns)
    pcb_txt = open(PCB).read()
    nets = {m.group(2): int(m.group(1)) for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', pcb_txt)}
    body = ns["ses_to_sexpr"](os.path.join(HERE, "board.ses"), nets)
    # GND-ruting (stubber/vias fra export.py) hopper vi over – de lages på nytt
    # --skip NET,NET: nett som har endret seg siden forrige ruting – rutes på nytt
    skip = ([] if "--route-gnd" in sys.argv else ["GND"]) + (sys.argv[sys.argv.index("--skip") + 1].split(",") if "--skip" in sys.argv else [])
    tags = {f"(net {nets[n]})" for n in skip if n in nets}
    body = "\n".join(l for l in body.split("\n") if not any(t in l for t in tags))
    pcb_txt = pcb_txt.rstrip()[:-1] + body + "\n)\n"
    open(PCB, "w").write(pcb_txt)
board = pcbnew.LoadBoard(PCB)
if "--route-gnd" in sys.argv:
    # Uten GND-sonene i DSN-en ruter Freerouting GND som et vanlig nett (spor til hver GND-pad). Sonene kommer tilbake i export.py,
    # så planet ligger oppå – men ingen GND-pad kan havne på en isolert øy.
    for z in [zz for zz in board.Zones() if zz.GetNetname() == "GND"]:
        board.Remove(z)
pcbnew.ExportSpecctraDSN(board, os.path.join(HERE, "board.dsn"))
if "--power-first" in sys.argv:
    # Pass 1: bare strømnettene (POWER_NETS i build_board) i DSN-en, så de brede sporene får plass først. Resten rutes i pass 2 (--continue).
    import re
    sys.path.insert(0, HERE); import build_board as _bb
    keep = set(_bb.POWER_NETS)
    txt = open(os.path.join(HERE, "board.dsn")).read()
    def strip_net(m):
        name = m.group(1).strip('"')
        return m.group(0) if name in keep else ""
    txt = re.sub(r"\n    \(net (\S+)\n      \(pins[^)]*\)\n    \)", strip_net, txt)
    def strip_class(m):
        head, names = m.group(1), m.group(2).split()
        return head + " ".join(n for n in names if n.strip('"') in keep or n == '""') + "\n      (circuit"
    txt = re.sub(r"(\n    \(class \S+ )(.*?)\n      \(circuit", strip_class, txt, flags=re.S)
    # låste spor/vias for nett som ikke er med: fjern dem fra (wiring …) – Freerouting henger på ukjente nett
    txt = re.sub(r"\n\s*\((?:wire|via) [^\n]*\(net (\S+)\)[^\n]*", lambda m: m.group(0) if m.group(1).strip('"') in keep else "", txt)
    open(os.path.join(HERE, "board.dsn"), "w").write(txt)
    print("pass 1: bare strømnett i DSN:", sorted(keep))
jar = os.environ.get("FREEROUTING", os.path.expanduser("~/freerouting.jar"))
mp = sys.argv[sys.argv.index("-mp") + 1] if "-mp" in sys.argv else "40"
os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
with open(os.path.join(HERE, "logs", "freerouting.log"), "w") as log:
    subprocess.run(["xvfb-run", "-a", "java", "-jar", jar, "-de", os.path.join(HERE, "board.dsn"), "-do", os.path.join(HERE, "board.ses"), "-mp", mp, "-dr", "-us", "global"],
                   stdout=log, stderr=subprocess.STDOUT, check=False)
print("SES:", os.path.exists(os.path.join(HERE, "board.ses")))
