#!/usr/bin/env python3
"""Lager en GLB av hovedkortet med KiCads offisielle 3D-modeller (VRML) for alle komponenter,
pluss kortet selv med toppen/bunnen som tekstur (kobber, maske, silketrykk fra kicad-cli svg).
Resultat: produksjon/ki_pultforsterker_main.glb + board_top_tex.png / board_bottom_tex.png
"""
import os, re, math, subprocess
import numpy as np
import pcbnew, trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "ki_pultforsterker_main.kicad_pcb")
OUT = os.path.join(HERE, "produksjon")
MODELS = "/usr/share/kicad/3dmodels"
VRML_UNIT = 2.54   # 1 VRML-enhet = 0,1 tomme i KiCad-bibliotekene

# ---------------------------------------------------------------- VRML-parser (KiCad-undersett)
tok_re = re.compile(r'#[^\n]*|"[^"]*"|[\[\]{}]|[^\s\[\]{}]+')


def tokenize(txt):
    return [t for t in tok_re.findall(txt.replace(",", " ")) if not t.startswith("#")]


class VRML:
    def __init__(self, tokens):
        self.t = tokens; self.i = 0; self.defs = {}; self.meshes = []   # (verts Nx3, faces Mx3, rgba)

    def peek(self): return self.t[self.i] if self.i < len(self.t) else None
    def next(self): v = self.t[self.i]; self.i += 1; return v

    def parse(self):
        while self.peek() is not None:
            self.node(np.eye(4))

    def skip_block(self):
        depth = 0
        while True:
            v = self.next()
            if v in ("{", "["): depth += 1
            elif v in ("}", "]"):
                depth -= 1
                if depth <= 0: return

    def read_floats(self):
        assert self.next() == "["
        vals = []
        while self.peek() != "]":
            vals.append(float(self.next().rstrip(",")))
        self.next(); return vals

    def read_num(self): return float(self.next().rstrip(","))

    def node(self, M, name=None):
        v = self.next()
        if v == "DEF":
            name = self.next(); return self.node(M, name)
        if v == "USE":
            ref = self.defs.get(self.next()); return ref
        if v in (",",): return None
        if v in ("Transform", "Group", "Collision", "Switch"):
            return self.transform(M, name, v)
        if v == "Shape":
            return self.shape(M, name)
        if v == "Material":
            return self.material(name)
        if v == "Appearance":
            return self.appearance(name)
        if v == "IndexedFaceSet":
            return self.ifs(name)
        if v == "Coordinate":
            assert self.next() == "{"; pts = None
            while self.peek() != "}":
                k = self.next()
                if k == "point": pts = self.read_floats()
                else: self.skip_value()
            self.next(); r = ("coord", pts)
            if name: self.defs[name] = r
            return r
        # ukjent node: hopp over
        if self.peek() == "{": self.skip_block()
        return None

    def skip_value(self):
        if self.peek() in ("{", "["): self.skip_block()
        else: self.next()

    def transform(self, M, name, kind):
        assert self.next() == "{"
        T = np.zeros(3); R = (0, 0, 1, 0); S = np.ones(3); C = np.zeros(3); children = []
        while self.peek() != "}":
            k = self.next()
            if k == "translation": T = np.array([self.read_num() for _ in range(3)])
            elif k == "rotation": R = tuple(self.read_num() for _ in range(4))
            elif k == "scale": S = np.array([self.read_num() for _ in range(3)])
            elif k == "center": C = np.array([self.read_num() for _ in range(3)])
            elif k in ("children", "choice"):
                if self.peek() == "[":
                    self.next()
                    while self.peek() != "]":
                        if self.peek() == ",": self.next(); continue
                        children.append(self.i); self.node(self.compose(M, T, R, S, C))
                    self.next()
                else:
                    self.node(self.compose(M, T, R, S, C))
            else: self.skip_value()
        self.next()
        return None

    @staticmethod
    def compose(M, T, R, S, C):
        ax = np.array(R[:3], float); ang = R[3]
        n = np.linalg.norm(ax); ax = ax / n if n > 0 else np.array([0, 0, 1.0])
        x, y, z = ax; c, s = math.cos(ang), math.sin(ang); t = 1 - c
        Rm = np.array([[t*x*x+c, t*x*y-s*z, t*x*z+s*y], [t*x*y+s*z, t*y*y+c, t*y*z-s*x], [t*x*z-s*y, t*y*z+s*x, t*z*z+c]])
        L = np.eye(4); L[:3, :3] = Rm @ np.diag(S); L[:3, 3] = T + C - Rm @ np.diag(S) @ C
        return M @ L

    def material(self, name):
        assert self.next() == "{"; d = (0.8, 0.8, 0.8); tr = 0.0
        while self.peek() != "}":
            k = self.next()
            if k == "diffuseColor": d = tuple(self.read_num() for _ in range(3))
            elif k == "transparency": tr = self.read_num()
            else: self.skip_value()
        self.next(); r = ("mat", d, tr)
        if name: self.defs[name] = r
        return r

    def appearance(self, name):
        assert self.next() == "{"; m = ("mat", (0.8, 0.8, 0.8), 0.0)
        while self.peek() != "}":
            k = self.next()
            if k == "material": r = self.node(np.eye(4)); m = r if r and r[0] == "mat" else m
            else: self.skip_value()
        self.next(); r = ("app", m)
        if name: self.defs[name] = r
        return r

    def ifs(self, name):
        assert self.next() == "{"; pts = None; idx = None
        while self.peek() != "}":
            k = self.next()
            if k == "coord": r = self.node(np.eye(4)); pts = r[1] if r else None
            elif k == "coordIndex": idx = self.read_floats()
            elif k in ("color", "normal", "texCoord"): self.node(np.eye(4)) if self.peek() not in ("{", "[") else self.skip_block()
            elif k in ("colorIndex", "normalIndex", "texCoordIndex"): self.read_floats()
            else: self.skip_value()
        self.next(); r = ("ifs", pts, idx)
        if name: self.defs[name] = r
        return r

    def shape(self, M, name):
        assert self.next() == "{"; app = None; geo = None
        while self.peek() != "}":
            k = self.next()
            if k == "appearance": app = self.node(np.eye(4))
            elif k == "geometry": geo = self.node(np.eye(4))
            else: self.skip_value()
        self.next()
        if geo and geo[0] == "ifs" and geo[1] and geo[2]:
            pts = np.array(geo[1]).reshape(-1, 3); faces = []; poly = []
            for v in geo[2]:
                if v < 0:
                    for j in range(1, len(poly) - 1): faces.append((poly[0], poly[j], poly[j + 1]))
                    poly = []
                else: poly.append(int(v))
            if poly:
                for j in range(1, len(poly) - 1): faces.append((poly[0], poly[j], poly[j + 1]))
            if faces:
                P = np.c_[pts, np.ones(len(pts))] @ M.T
                mat = app[1] if app and app[0] == "app" else ("mat", (0.8, 0.8, 0.8), 0.0)
                self.meshes.append((P[:, :3], np.array(faces), mat[1], mat[2]))
        return None


def load_wrl(path):
    v = VRML(tokenize(open(path, encoding="utf-8", errors="ignore").read())); v.parse(); return v.meshes


# ---------------------------------------------------------------- kortet
def board_scene():
    board = pcbnew.LoadBoard(PCB)
    W, H, T = 150.0, 100.0, 1.6
    scene = trimesh.Scene()
    # kortets kropp, teksturert topp/bunn
    import cairosvg
    from PIL import Image, ImageChops
    def layer_png(layers, name):
        svg = os.path.join(OUT, f"tex_{name}.svg"); png = os.path.join(OUT, f"tex_{name}.png")
        subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "2", "--exclude-drawing-sheet", "--black-and-white",
                        "-o", svg, PCB], check=True, capture_output=True)
        cairosvg.svg2png(url=svg, write_to=png, output_width=2400, background_color="white")
        im = Image.open(png).convert("L"); return ImageChops.invert(im)   # hvitt = tegnet
    for side in ("F", "B"):
        cu = layer_png(f"{side}.Cu,Edge.Cuts", f"{side}_cu"); mask = layer_png(f"{side}.Mask,Edge.Cuts", f"{side}_mask"); silk = layer_png(f"{side}.SilkS,Edge.Cuts", f"{side}_silk")
        W_, H_ = cu.size
        base = Image.new("RGB", (W_, H_), (18, 72, 36))                      # grønn loddemaske over laminat
        over_cu = Image.new("RGB", (W_, H_), (34, 112, 56))                   # kobber under maske
        gold = Image.new("RGB", (W_, H_), (205, 170, 90))                     # eksponert kobber (HASL)
        white = Image.new("RGB", (W_, H_), (240, 240, 235))
        img = Image.composite(over_cu, base, cu.point(lambda v: 255 if v > 40 else 0))
        img = Image.composite(gold, img, mask.point(lambda v: 255 if v > 40 else 0))
        img = Image.composite(white, img, silk.point(lambda v: 255 if v > 60 else 0))
        name = "top" if side == "F" else "bottom"
        img.save(os.path.join(OUT, f"board_{name}_tex.png"))
    # enkel boks + separate flater med UV
    body = trimesh.creation.box((W, H, T)); body.apply_translation((W / 2, H / 2, T / 2))
    body.visual = trimesh.visual.ColorVisuals(body, face_colors=[20, 80, 40, 255])
    scene.add_geometry(body, node_name="board_body")
    for name, z, n in [("top", T + 0.01, 1), ("bottom", -0.01, -1)]:
        from PIL import Image
        img = Image.open(os.path.join(OUT, f"board_{name}_tex.png")).convert("RGB")
        verts = np.array([[0, 0, z], [W, 0, z], [W, H, z], [0, H, z]], float)
        faces = np.array([[0, 1, 2], [0, 2, 3]]) if n > 0 else np.array([[0, 2, 1], [0, 3, 2]])
        uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float) if n > 0 else np.array([[1, 0], [0, 0], [0, 1], [1, 1]], float)
        m = trimesh.Trimesh(verts, faces, process=False)
        m.visual = trimesh.visual.TextureVisuals(uv=uv, image=img)
        scene.add_geometry(m, node_name=f"board_{name}")
    # komponenter
    n_ok = n_miss = 0
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H"): continue
        pos = fp.GetPosition(); px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
        rot = fp.GetOrientationDegrees(); flipped = fp.IsFlipped()
        for mdl in fp.Models():
            path = mdl.m_Filename.replace("${KICAD6_3DMODEL_DIR}", MODELS).replace("${KICAD7_3DMODEL_DIR}", MODELS)
            if path.lower().endswith(".step") or path.lower().endswith(".stp"):
                path = os.path.splitext(path)[0] + ".wrl"
            SUBST = {"Package_TO_SOT_SMD.3dshapes/SOT-23-3.wrl": "Package_TO_SOT_SMD.3dshapes/SOT-23.wrl",
                     "Inductor_SMD.3dshapes/L_12x12mm_H8mm.wrl": "Inductor_SMD.3dshapes/L_Bourns_SRR1260.wrl",
                     "Inductor_SMD.3dshapes/L_Bourns_SRP1245A.wrl": "Inductor_SMD.3dshapes/L_Bourns_SRR1260.wrl",
                     "Package_SO.3dshapes/HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm.wrl": "Package_SO.3dshapes/HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm.wrl",
                     "TerminalBlock.3dshapes/TerminalBlock_bornier-2_P5.08mm.wrl": "TerminalBlock_Phoenix.3dshapes/TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.wrl",
                     "Fuse.3dshapes/Fuseholder_Clip-5x20mm_Keystone_3512P_Inline_P23.62x7.27mm_D1.02x2.41x1.02x1.57mm_Horizontal.wrl": "Fuse.3dshapes/Fuseholder_Cylinder-5x20mm_Bulgin_FX0457_Horizontal_Closed.wrl"}
            for k, v in SUBST.items():
                if path.endswith(k): path = os.path.join(MODELS, v)
            if not os.path.exists(path):
                n_miss += 1; print("mangler modell:", ref, path); continue
            try:
                meshes = load_wrl(path)
            except Exception as e:
                print("parsefeil", ref, path, e); n_miss += 1; continue
            off = np.array([mdl.m_Offset.x, mdl.m_Offset.y, mdl.m_Offset.z]); sc = np.array([mdl.m_Scale.x, mdl.m_Scale.y, mdl.m_Scale.z])
            rx, ry, rz = mdl.m_Rotation.x, mdl.m_Rotation.y, mdl.m_Rotation.z
            def rotm(a, axis):
                a = math.radians(a); c, s = math.cos(a), math.sin(a)
                return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]), "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]
            # KiCad: modell-rotasjon (x,y,z, grader, negativt fortegn i KiCad-konvensjonen), skalering, offset (mm), så footprint-rotasjon og evt. flipp
            Rm = rotm(-rz, "z") @ rotm(-ry, "y") @ rotm(-rx, "x")
            Rf = rotm(rot, "z")
            for verts, faces, rgb, tr in meshes:
                v = verts * VRML_UNIT * sc
                v = v @ Rm.T + off
                if flipped:
                    v = v * np.array([1, -1, -1]) ; v = v @ rotm(-rot, "z").T
                else:
                    v = v @ Rf.T
                v = v + np.array([px, H - py, T if not flipped else 0.0])   # KiCad y nedover -> y oppover
                m = trimesh.Trimesh(v, faces, process=False)
                col = [int(255 * c) for c in rgb] + [int(255 * (1 - tr))]
                m.visual = trimesh.visual.ColorVisuals(m, face_colors=col)
                scene.add_geometry(m, node_name=f"{ref}_{len(scene.geometry)}")
            n_ok += 1
    print("modeller:", n_ok, "mangler:", n_miss, "geometrier:", len(scene.geometry))
    glb = os.path.join(OUT, "ki_pultforsterker_main.glb")
    scene.export(glb); print("->", glb, round(os.path.getsize(glb) / 1e6, 1), "MB")


if __name__ == "__main__":
    board_scene()
