#!/usr/bin/env python3
"""Nærbilder (2D, LEGO-stil) av lodding og tilkoblinger -> steps/close_*.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon
ACC="#e8562a"; INK="#1b1c20"; MUTE="#6b6a66"; PCB_G="#2a8a4a"; PCB_B="#2d5fb0"; PCB_P="#7b3fa0"
def fig(w=7,h=4.2): f,ax=plt.subplots(figsize=(w,h)); ax.set_aspect("equal"); ax.axis("off"); return f,ax
def tag(ax,x,y,n): ax.add_patch(Circle((x,y),0.55,fc=ACC,ec="none",zorder=5)); ax.text(x,y,str(n),ha="center",va="center",color="white",fontsize=9,fontweight="bold",zorder=6)
def wire(ax,p0,p1,col,lw=3): ax.plot([p0[0],p1[0]],[p0[1],p1[1]],color=col,lw=lw,solid_capstyle="round",zorder=3)
def pad(ax,x,y,label,side="r"): ax.add_patch(Circle((x,y),0.32,fc="#d4af37",ec="#8a6d12",zorder=4)); ax.text(x+(0.5 if side=="r" else -0.5),y,label,ha="left" if side=="r" else "right",va="center",fontsize=8,family="monospace",color=INK)

# ---- A. DAC PCM5102A: loddebroer på baksiden ----
f,ax=fig(7,4.4)
ax.add_patch(Rectangle((0,0),8,4.2,fc=PCB_P,ec="#333")); ax.text(4,3.85,"PCM5102A  (BAKSIDE)",ha="center",color="white",fontsize=9,fontweight="bold")
for i,(n,st) in enumerate([("FLT","L"),("DMP","L"),("XMT","H"),("FMT","L")]):
    x=1.2+i*1.7; ax.text(x,3.2,n,ha="center",color="white",fontsize=8,family="monospace")
    for j,s in enumerate(["H","L"]):
        y=2.5-j*0.8; ax.add_patch(Rectangle((x-0.55,y-0.18),0.4,0.36,fc="#d4af37",ec="none")); ax.add_patch(Rectangle((x+0.15,y-0.18),0.4,0.36,fc="#d4af37",ec="none"))
        ax.text(x-0.95,y,s,ha="right",va="center",color="white",fontsize=7)
        if s==st: ax.add_patch(Rectangle((x-0.55,y-0.18),1.1,0.36,fc="#c9c9cc",ec=ACC,lw=1.5))
ax.text(1.2,0.9,"SCK",ha="center",color="white",fontsize=8,family="monospace"); ax.add_patch(Rectangle((0.65,0.3),0.4,0.36,fc="#d4af37",ec="none")); ax.add_patch(Rectangle((1.35,0.3),0.4,0.36,fc="#d4af37",ec="none")); ax.text(2.0,0.48,"GND",va="center",color="white",fontsize=7)
ax.add_patch(Rectangle((0.65,0.3),1.1,0.36,fc="#c9c9cc",ec=ACC,lw=1.5))
ax.text(8.6,3.3,"Lodd en dråpe tinn over de\nmarkerte parene (grå):",fontsize=9,va="top"); ax.text(8.6,2.3,"FLT → L   DMP → L\nXMT → H   FMT → L\nSCK → GND",fontsize=9,family="monospace",va="top",color=INK)
ax.text(8.6,0.9,"Sjekk med multimeter at SCK\nhar kontakt til GND.",fontsize=8.5,va="top",color=MUTE)
ax.set_xlim(-0.3,13.5); ax.set_ylim(-0.2,4.4); f.savefig("steps/close_dac.png",dpi=150,bbox_inches="tight"); plt.close(f)

# ---- B. 12/16 mm knapp: pinner ----
f,ax=fig(7,4.4)
ax.add_patch(Circle((2.2,2.2),1.9,fc="#1d1d20",ec="#555")); ax.add_patch(Circle((2.2,2.2),1.3,fc="none",ec="#eef6ff",lw=2)); ax.text(2.2,0.0,"Sett bakfra",ha="center",fontsize=8,color=MUTE)
pins=[(1.5,3.0,"+"),(2.9,3.0,"−"),(1.5,1.4,"C"),(2.9,1.4,"NO")]
for x,y,l in pins: ax.add_patch(Rectangle((x-0.12,y-0.35),0.24,0.7,fc="#d4af37",ec="#8a6d12")); ax.text(x,y,l,ha="center",va="center",fontsize=7,fontweight="bold")
wire(ax,(1.5,3.3),(5.2,3.6),"#c0392b"); wire(ax,(2.9,3.3),(5.2,3.0),"#222"); wire(ax,(1.5,1.1),(5.2,1.6),"#3f7fd9"); wire(ax,(2.9,1.1),(5.2,1.0),"#222")
ax.text(5.4,3.6,"+  →  5 V (buck OUT+)",va="center",fontsize=9); ax.text(5.4,3.0,"−  →  MOSFET-kort OUT−  (sin kanal)",va="center",fontsize=9)
ax.text(5.4,1.6,"C  →  Pi GPIO (AIRPLAY 5 · BT 6 · AUX 12 · USB 13 · POWER 16)",va="center",fontsize=9); ax.text(5.4,1.0,"NO →  Pi GND",va="center",fontsize=9)
ax.text(5.4,0.3,"LED-pinnene er de to ved LED-merket (ofte lengst). Bryterpinnene er C/NO (eller NO1/NO2).\nLodd 20 cm ledning på alle fire FØR knappen settes i fronten. Krympestrømpe på hver.",fontsize=8,va="top",color=MUTE)
ax.set_xlim(-0.2,13.5); ax.set_ylim(-0.9,4.5); f.savefig("steps/close_button.png",dpi=150,bbox_inches="tight"); plt.close(f)

# ---- C. Bananplugg på høyttalerkabel ----
f,ax=fig(7,3.6)
ax.add_patch(Rectangle((0,1.3),3.2,0.9,fc="#c0392b",ec="#7a1d1d")); ax.add_patch(Rectangle((0,0.3),3.2,0.9,fc="#222",ec="#000"))
ax.add_patch(Rectangle((3.2,1.45),0.9,0.6,fc="#c9a227",ec="#8a6d12")); ax.add_patch(Rectangle((3.2,0.45),0.9,0.6,fc="#c9a227",ec="#8a6d12"))
for y in (1.75,0.75):
    ax.add_patch(Rectangle((4.1,y-0.45),2.2,0.9,fc="#c9a227",ec="#8a6d12")); ax.add_patch(Rectangle((6.3,y-0.2),1.6,0.4,fc="#c9a227",ec="#8a6d12")); ax.add_patch(Rectangle((5.0,y-0.55),0.5,1.1,fc="#1d1d20",ec="none"))
ax.text(1.6,1.75,"+ (rød / merket)",ha="center",va="center",color="white",fontsize=8); ax.text(1.6,0.75,"− (svart)",ha="center",va="center",color="white",fontsize=8)
for i,t in enumerate(["Avisoler 8 mm og tvinn lederen","Skru av hylsen, stikk lederen inn, stram settskruen (eller lodd)","Skru hylsen på. Rød = +, svart = −"]):
    tag(ax,8.6,2.2-i*0.75,i+1); ax.text(9.3,2.2-i*0.75,t,va="center",fontsize=8.5)
ax.text(0,-0.4,"Samme polaritet i begge ender: + på forsterkeren → + på høyttaleren. Feil polaritet på én side gir tynn bass.",fontsize=8,color=MUTE)
ax.set_xlim(-0.2,16.5); ax.set_ylim(-0.7,3.0); f.savefig("steps/close_banana.png",dpi=150,bbox_inches="tight"); plt.close(f)

# ---- D. KCD1 + DC-099 ----
f,ax=fig(7,4)
ax.add_patch(FancyBboxPatch((0,1),2.4,1.6,boxstyle="round,pad=0.05",fc="#1d1d20",ec="#555")); ax.text(1.2,1.8,"I  O",ha="center",va="center",color="#ddd",fontsize=9)
for x,l in [(0.6,"1"),(1.8,"2")]: ax.add_patch(Rectangle((x-0.15,0.3),0.3,0.7,fc="#d4af37",ec="#8a6d12")); ax.text(x,0.05,l,ha="center",fontsize=8)
ax.text(1.2,2.9,"KCD1 (bakfra)",ha="center",fontsize=8,color=MUTE)
ax.add_patch(Circle((5.5,1.8),0.9,fc="#1d1d20",ec="#555")); ax.add_patch(Circle((5.5,1.8),0.3,fc="#555",ec="#999"))
for x,y,l in [(6.6,2.4,"senter +"),(6.6,1.8,"hylse −"),(6.6,1.2,"bryter (ubrukt)")]: ax.add_patch(Rectangle((x-0.15,y-0.25),0.3,0.5,fc="#d4af37",ec="#8a6d12")); ax.plot([6.6,9.0],[y,y],color="#999",lw=1,zorder=1); ax.text(x+0.35,y,l,va="center",fontsize=8,bbox=dict(fc="white",ec="none",pad=1),zorder=4)
ax.text(5.5,2.9,"DC-099 (innsiden)",ha="center",fontsize=8,color=MUTE)
wire(ax,(9.0,2.4),(9.0,3.4),"#c0392b"); wire(ax,(9.0,3.4),(0.6,3.4),"#c0392b"); wire(ax,(0.6,3.4),(0.6,1.0),"#c0392b")
wire(ax,(1.8,1.0),(1.8,-0.3),"#c0392b"); wire(ax,(1.8,-0.3),(10.5,-0.3),"#c0392b"); ax.text(10.7,-0.3,"→ relé COM3  +  buck IN+",va="center",fontsize=9)
wire(ax,(9.0,1.8),(10.5,0.4),"#222"); ax.text(10.7,0.4,"→ forsterker GND, buck IN−, relé GND",va="center",fontsize=9)
ax.text(0,-1.0,"18 AWG. Flatstifthylser 4,8 mm på KCD1, lodd + krymp på DC-099. Ikke koble 24 V-adapteren før alt er ferdig.",fontsize=8,color=MUTE)
ax.set_xlim(-0.3,15); ax.set_ylim(-1.3,3.8); f.savefig("steps/close_kcd1.png",dpi=150,bbox_inches="tight"); plt.close(f)

# ---- E. Pi header (40 pinner) ----
f,ax=fig(7.5,5.2)
names={1:"3V3",2:"5V",3:"SDA",4:"5V",5:"SCL",6:"GND",7:"G4",8:"G14",9:"GND",10:"G15",11:"G17",12:"G18",13:"G27",14:"GND",15:"G22",16:"G23",17:"3V3",18:"G24",19:"G10",20:"GND",21:"G9",22:"G25",23:"G11",24:"G8",25:"GND",26:"G7",27:"ID",28:"ID",29:"G5",30:"GND",31:"G6",32:"G12",33:"G13",34:"GND",35:"G19",36:"G16",37:"G26",38:"G20",39:"GND",40:"G21"}
use={2:"5 V inn (buck)",6:"GND",3:"OLED SDA",5:"OLED SCL",7:"OLED RES",8:"X9C U/D",10:"X9C CS",37:"X9C INC",12:"DAC BCK",35:"DAC LCK",40:"DAC DIN",4:"DAC VIN",29:"AIRPLAY",31:"BT",32:"AUX",33:"USB",36:"POWER",16:"enc CLK",18:"enc DT",22:"enc SW",26:"ring AIR",24:"ring BT",21:"ring AUX",19:"ring USB",23:"ring POWER",15:"relé IN1+IN2",13:"relé IN3",1:"enc +",9:"GND"}
ax.add_patch(Rectangle((-0.9,-0.3),5.6,21.2,fc=PCB_G,ec="#333"))
for p in range(1,41):
    col=(p-1)%2; row=(p-1)//2; x=1.2+col*1.4; y=19.8-row
    ax.add_patch(Rectangle((x-0.25,y-0.25),0.5,0.5,fc="#d4af37" if p in use else "#333",ec="#111"))
    ax.text(x,y,str(p),ha="center",va="center",fontsize=5.5,color="white" if p not in use else INK)
    lab=names[p]; ax.text(x+(0.5 if col else -0.5),y,lab,ha="left" if col else "right",va="center",fontsize=6,family="monospace",color="white")
    if p in use: ax.text(5.1 if col else -1.3,y,use[p],ha="left" if col else "right",va="center",fontsize=7,color=ACC if p not in(2,4,6,9,1) else INK,fontweight="bold")
ax.text(1.9,21.4,"Pi Zero 2 W – header sett ovenfra, pinne 1 øverst (SD-kort opp)",ha="center",fontsize=8)
ax.set_xlim(-6.5,11); ax.set_ylim(-0.6,21.9); f.savefig("steps/close_header.png",dpi=150,bbox_inches="tight"); plt.close(f)

# ---- F. Lydvei: AUX/DAC → relé → X9C → forsterker ----
f,ax=fig(8,4.6)
def board(x,y,w,h,col,t): ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.05",fc=col,ec="#222")); ax.text(x+w/2,y+h-0.35,t,ha="center",color="white",fontsize=8,fontweight="bold")
board(0,2.6,2.2,1.6,"#444","AUX-jack"); board(0,0.2,2.2,1.6,PCB_P,"DAC"); board(3.4,0.4,2.8,3.8,"#b03030","Relékort"); board(7.6,2.5,2.2,1.5,PCB_G,"X9C-A (L)"); board(7.6,0.4,2.2,1.5,PCB_G,"X9C-B (R)"); board(11.2,0.6,2.4,3.2,PCB_B,"Forsterker")
for y,l in [(3.4,"tip (L)"),(2.9,"ring (R)")]: ax.text(2.1,y,l,ha="right",va="center",color="white",fontsize=7)
for y,l in [(1.0,"L"),(0.5,"R")]: ax.text(2.1,y,l,ha="right",va="center",color="white",fontsize=7)
for y,l in [(3.6,"NO1"),(3.1,"COM1"),(2.6,"NC1"),(1.9,"NO2"),(1.4,"COM2"),(0.9,"NC2")]: ax.text(3.5,y,l,va="center",color="white",fontsize=7,family="monospace")
wire(ax,(2.2,3.4),(3.4,3.6),"#1aa39a",2.5); wire(ax,(2.2,2.9),(3.4,1.9),"#1aa39a",2.5); wire(ax,(2.2,1.0),(3.4,2.6),"#1aa39a",2.5); wire(ax,(2.2,0.5),(3.4,0.9),"#1aa39a",2.5)
for y,l in [(3.6,"VH"),(3.1,"VW"),(2.6,"VL")]: ax.text(7.7,y,l,va="center",color="white",fontsize=7,family="monospace")
for y,l in [(1.5,"VH"),(1.0,"VW"),(0.5,"VL")]: ax.text(7.7,y,l,va="center",color="white",fontsize=7,family="monospace")
wire(ax,(6.2,3.1),(7.6,3.6),"#1aa39a",2.5); wire(ax,(6.2,1.4),(7.6,1.5),"#1aa39a",2.5)
for y,l in [(3.3,"INL"),(2.3,"INR"),(1.3,"GND")]: ax.text(11.3,y,l,va="center",color="white",fontsize=7,family="monospace")
wire(ax,(9.8,3.1),(11.2,3.3),"#1aa39a",2.5); wire(ax,(9.8,1.0),(11.2,2.3),"#1aa39a",2.5); wire(ax,(9.8,2.6),(11.2,1.3),"#555",2); wire(ax,(9.8,0.5),(11.2,1.3),"#555",2)
ax.text(8.7,4.35,"INC/U/D/CS → Pi 37/8/10 (begge)",ha="center",fontsize=7,color=ACC)
ax.text(0,-0.5,"Relé AV (NC) = DAC → forsterker (AirPlay/BT/USB). Relé PÅ (NO) = AUX → forsterker. Skjermet kabel; skjermen til GND kun i forsterker-enden.",fontsize=8,color=MUTE)
ax.set_xlim(-0.2,13.9); ax.set_ylim(-0.8,4.7); f.savefig("steps/close_audio.png",dpi=150,bbox_inches="tight"); plt.close(f)

# ---- G. Encoder KY-040 ----
f,ax=fig(7,3.4)
ax.add_patch(Rectangle((0,0),3,3,fc=PCB_G,ec="#333")); ax.add_patch(Circle((1.5,1.9),0.7,fc="#999",ec="#555")); ax.add_patch(Rectangle((1.3,1.9),0.4,1.3,fc="#bbb",ec="#555"))
for i,l in enumerate(["CLK","DT","SW","+","GND"]):
    x=0.4+i*0.55; ax.add_patch(Rectangle((x-0.08,-0.6),0.16,0.7,fc="#d4af37",ec="#8a6d12")); ax.text(x,-0.85,l,ha="center",va="top",fontsize=6.5,family="monospace",rotation=90)
for i,(t,c) in enumerate([("CLK → Pi pinne 16 (GPIO 23)","#3f7fd9"),("DT  → Pi pinne 18 (GPIO 24)","#3f7fd9"),("SW  → Pi pinne 22 (GPIO 25)","#3f7fd9"),("+   → Pi pinne 1 (3,3 V)","#c0392b"),("GND → Pi pinne 9","#222")]):
    wire(ax,(0.4+i*0.55,-1.6),(4.2,2.6-i*0.65),c,2); ax.text(4.4,2.6-i*0.65,t,va="center",fontsize=8.5,family="monospace")
ax.text(0,-2.2,"Dupont hunn–hunn rett på pinnelisten. Knotten: sett på D-akselen, settskrue mot flaten.",fontsize=8,color=MUTE)
ax.set_xlim(-0.3,11); ax.set_ylim(-2.5,3.3); f.savefig("steps/close_encoder.png",dpi=150,bbox_inches="tight"); plt.close(f)

# ---- H. MOSFET-kort og LED-ringer ----
f,ax=fig(8,4)
board(0,0.4,4.4,3.4,"#303033","MOSFET-kort 1 (jumper 3.3V)")
for i,l in enumerate(["IN1","IN2","IN3","IN4","GND"]): ax.text(0.15,3.0-i*0.5,l,va="center",color="white",fontsize=7,family="monospace")
for i,l in enumerate(["OUT1−","OUT2−","OUT3−","OUT4−","VCC","GND"]): ax.text(4.25,3.1-i*0.5,l,ha="right",va="center",color="white",fontsize=7,family="monospace")
for i,(t) in enumerate(["Pi 26 (G7) – ring AIRPLAY","Pi 24 (G8) – ring BT","Pi 21 (G9) – ring AUX","Pi 19 (G10) – ring USB","Pi GND"]):
    wire(ax,(-2.6,3.0-i*0.5),(0.1,3.0-i*0.5),"#3f7fd9" if i<4 else "#222",2); ax.text(-2.7,3.0-i*0.5,t,ha="right",va="center",fontsize=7.5)
for i,t in enumerate(["AIRPLAY-ring −","BT-ring −","AUX-ring −","USB-ring −","5 V (buck)","GND (buck)"]):
    wire(ax,(4.4,3.1-i*0.5),(6.6,3.1-i*0.5),"#222" if i<4 else ("#c0392b" if i==4 else "#222"),2); ax.text(6.7,3.1-i*0.5,t,va="center",fontsize=7.5)
ax.text(0,-0.1,"Alle fem ringenes + går samlet til 5 V. Kort 2: IN1 ← Pi 23 (GPIO 11, PWM) → OUT1− ← POWER-ring −. Kanal 2–4 ubrukt.",fontsize=8,color=MUTE)
ax.set_xlim(-7.5,10.5); ax.set_ylim(-0.4,4); f.savefig("steps/close_mosfet.png",dpi=150,bbox_inches="tight"); plt.close(f)
print("ok")
