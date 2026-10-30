#!/usr/bin/env python3
"""Autoruting: build_board.py -> board.dsn -> Freerouting -> board.ses. Deretter: python3 export.py
   FREEROUTING=/sti/til/freerouting.jar python3 route.py [-mp 40]"""
import os, subprocess, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "ki_pultforsterker_main.kicad_pcb")
subprocess.run([sys.executable, os.path.join(HERE, "build_board.py")], check=True)
if "--continue" in sys.argv:
    # legg inn forrige rutingresultat (board.ses) i det nybygde kortet, så Freerouting bare fullfører det som mangler
    import re
    src = open(os.path.join(HERE, "export.py")).read()
    ns = {}; exec(src[src.index("def ses_to_sexpr"):src.index("# 1) regenerer")], ns)
    pcb_txt = open(PCB).read()
    nets = {m.group(2): int(m.group(1)) for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', pcb_txt)}
    body = ns["ses_to_sexpr"](os.path.join(HERE, "board.ses"), nets)
    # GND-ruting (stubber/vias fra export.py) hopper vi over – de lages på nytt
    body = "\n".join(l for l in body.split("\n") if f"(net {nets['GND']})" not in l)
    pcb_txt = pcb_txt.rstrip()[:-1] + body + "\n)\n"
    open(PCB, "w").write(pcb_txt)
board = pcbnew.LoadBoard(PCB)
pcbnew.ExportSpecctraDSN(board, os.path.join(HERE, "board.dsn"))
jar = os.environ.get("FREEROUTING", os.path.expanduser("~/freerouting.jar"))
mp = sys.argv[sys.argv.index("-mp") + 1] if "-mp" in sys.argv else "40"
os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
with open(os.path.join(HERE, "logs", "freerouting.log"), "w") as log:
    subprocess.run(["xvfb-run", "-a", "java", "-jar", jar, "-de", os.path.join(HERE, "board.dsn"), "-do", os.path.join(HERE, "board.ses"), "-mp", mp, "-dr", "-us", "global"],
                   stdout=log, stderr=subprocess.STDOUT, check=False)
print("SES:", os.path.exists(os.path.join(HERE, "board.ses")))
