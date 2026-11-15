#!/usr/bin/env python3
"""Lager et usynlig musepeker-tema (Xcursor, 1 × 1 gjennomsiktig) for skjold-ui, så cage ikke tegner en peker på skjermen.
Bruk: sudo python3 pi/tools/blank_cursor.py [/usr/share/icons/skjold-blank]  –  og XCURSOR_THEME=skjold-blank i tjenesten."""
import os, struct, sys

root = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/icons/skjold-blank"
cur = os.path.join(root, "cursors")
os.makedirs(cur, exist_ok=True)
# Xcursor: filhode (16) + én innholdsoppføring (12) + bildebit (36 + 1 piksel ARGB = 0)
img = struct.pack("<9I", 36, 0xfffd0002, 1, 1, 1, 1, 0, 0, 0) + struct.pack("<I", 0)
data = b"Xcur" + struct.pack("<3I", 16, 0x10000, 1) + struct.pack("<3I", 0xfffd0002, 1, 16 + 12) + img
names = ["default", "left_ptr", "arrow", "pointer", "hand2", "text", "xterm", "wait", "watch", "progress", "crosshair",
         "grab", "grabbing", "not-allowed", "all-scroll", "col-resize", "row-resize", "move", "help", "context-menu"]
with open(os.path.join(cur, "default"), "wb") as f:
    f.write(data)
for n in names[1:]:
    p = os.path.join(cur, n)
    if os.path.lexists(p):
        os.remove(p)
    os.symlink("default", p)
with open(os.path.join(root, "index.theme"), "w") as f:
    f.write("[Icon Theme]\nName=skjold-blank\nComment=Usynlig peker for skjold-ui\n")
print("usynlig peker:", root)
