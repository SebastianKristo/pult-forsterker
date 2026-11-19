W,H=2000,1900
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Sora, Arial, sans-serif">',
'<rect width="100%" height="100%" fill="#f7f6f2"/>',
'<text x="40" y="62" font-size="38" font-weight="700" fill="#1d1d1f">Skjold Fjernkontroll – hullkort-utgaven: slik bygges den</text>',
'<text x="40" y="100" font-size="19" fill="#55554f">XIAO ESP32S3 + MCP23017-modul + 14 brytere på stripekort + 2,8″ skjerm + IR-kort + LiPo. Ingen kretskort å bestille. Detaljer: hullkort/tegning.pdf og skjema.pdf.</text>']
def box(x,y,w,h,fill,stroke,lab,sub="",fs=17,tc="#1d1d1f"):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
    o.append(f'<text x="{x+w/2}" y="{y+h/2+(0 if sub else 6)}" text-anchor="middle" font-size="{fs}" font-weight="700" fill="{tc}">{lab}</text>')
    if sub: o.append(f'<text x="{x+w/2}" y="{y+h/2+22}" text-anchor="middle" font-size="13" fill="{tc}">{sub}</text>')
def panel(x,y,w,h,t):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#fff" stroke="#d6d4cc" stroke-width="2"/><text x="{x+22}" y="{y+40}" font-size="25" font-weight="700" fill="#1d1d1f">{t}</text>')
# ---------- 1: lagene (snitt fra siden)
panel(40,130,600,620,"1 · Lagene, sett fra siden")
lag=[("Taster (hetter) + gullring","printes, settes ovenfra i toppen","#d9a441","#8a6a1e"),
     ("Topp (topp.stl)","skjermlomme + tastehull","#e8e6df","#9a988f"),
     ("2,8″ skjerm HP28030","i lomma øverst, flatkabler ned bak","#2b2f3a","#111"),
     ("Stripekort 19 × 47 hull","14 brytere 6×6 på oppsiden","#c7a46a","#7a5a20"),
     ("Gulvet: XIAO, MCP, adaptere","på tynn tape, ledninger langs sidene","#7f65b8","#4a3680"),
     ("Batteri + IR-kort","batteri i lomma, IR-kort i nesen","#9aa3ad","#58616b"),
     ("Bunn (bunn.stl / bunn_dokk.stl)","5 × M2×10 skrues inn nedenfra","#3a3a3c","#111")]
y=200
for i,(t,s,f,st) in enumerate(lag):
    h=62
    box(80,y,520,h,f,st,t,s,fs=18,tc="#fff" if f in("#2b2f3a","#3a3a3c","#7f65b8") else "#1d1d1f")
    y+=h+16
o.append(f'<text x="80" y="{y+18}" font-size="15" fill="#55554f">16,0 mm tykk · stripene langs fjernkontrollen · USB-C ut i halen</text>')
# ---------- 2: gulvet (ovenfra), skjematisk etter tegning-side2
panel(670,130,460,1000,"2 · I bunnen, ovenfra")
o.append('<g transform="translate(720 215) scale(0.86)">')
X0,Y0,BW,BH=0,10,420,900
o.append(f'<rect x="{X0}" y="{Y0}" width="{BW}" height="{BH}" rx="40" fill="#ecebe5" stroke="#9a988f" stroke-width="3"/>')
o.append(f'<text x="{X0+BW/2}" y="{Y0+70}" text-anchor="middle" font-size="16" fill="#55554f">▲ nesen (IR peker hit)</text>')
box(X0+90,Y0+20,240,28,"#3fae6a","#1f6e3e","IR-kortet",fs=15,tc="#fff")
box(X0+100,Y0+90,220,320,"#b9c0c7","#58616b","LiPo 603450","1200 mAh, JST-PH",fs=19)
box(X0+200,Y0+480,90,95,"#e3c79c","#9b6a2a","FPC 6p","berøring",fs=15)
box(X0+130,Y0+595,150,120,"#e3c79c","#9b6a2a","FPC 18p","skjermen",fs=16)
box(X0+70,Y0+725,150,90,"#9c86c9","#4a3680","MCP23017","CJMCU-2317",fs=16,tc="#fff")
box(X0+270,Y0+700,50,140,"#8b8b86","#444","pogo",fs=13,tc="#fff")
box(X0+150,Y0+825,115,58,"#4a4a4c","#111","XIAO","ESP32S3",fs=15,tc="#fff")
o.append(f'<rect x="{X0+185}" y="{Y0+880}" width="50" height="22" fill="#9a988f"/>')
o.append(f'<rect x="{X0+30}" y="{Y0+450}" width="{BW-60}" height="{BH-470}" rx="6" fill="none" stroke="#7a5a20" stroke-width="2" stroke-dasharray="8 6"/><text x="{X0+40}" y="{Y0+470}" font-size="14" fill="#7a5a20">stripekortet ligger over (stiplet)</text>')
o.append(f'<path d="M{X0+45} {Y0+40} V{Y0+855} H{X0+150}" stroke="#2bb5b0" stroke-width="4" fill="none"/>')
o.append(f'<path d="M{X0+220} {Y0+420} H{X0+370} V{Y0+800} L{X0+270} {Y0+840}" stroke="#d63b2f" stroke-width="4" fill="none"/>')
o.append('</g>')
o.append('<text x="900" y="1022" text-anchor="middle" font-size="15" fill="#55554f">▼ halen: USB-C ut</text>')
o.append('<text x="690" y="1050" font-size="14" fill="#2b8f8a">turkis: IR-ledninger (5) langs venstre side</text>')
o.append('<text x="690" y="1070" font-size="14" fill="#b12a20">rød: batteri → XIAO BAT+ / BAT−</text>')
o.append('<text x="690" y="1090" font-size="14" fill="#55554f">alt på tynn tape; detaljer: tegning-side2.png</text>')
# ---------- 3: koblinger (blokkskjema)
panel(1160,130,800,1000,"3 · Hva kobles til hva")
def wire(x1,y1,x2,y2,c,lab="",lx=None,ly=None):
    o.append(f'<path d="M{x1} {y1} H{(x1+x2)/2} V{y2} H{x2}" stroke="{c}" stroke-width="4" fill="none"/>')
    if lab: o.append(f'<text x="{lx if lx else (x1+x2)/2+6}" y="{ly if ly else y2-6}" font-size="13" fill="#1d1d1f">{lab}</text>')
def bunt(pts,c,w=7):
    o.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" stroke="{c}" stroke-width="{w}" fill="none" stroke-linejoin="round"/>')
def liste(x,y,linjer,c="#1d1d1f",fs=14):
    for i,t in enumerate(linjer): o.append(f'<text x="{x}" y="{y+i*19}" font-size="{fs}" fill="{c}">{t}</text>')
box(1200,560,190,230,"#4a4a4c","#111","XIAO","ESP32S3",fs=22,tc="#fff")
box(1500,190,200,150,"#9c86c9","#4a3680","MCP23017","I²C 0x20",fs=20,tc="#fff")
box(1760,175,180,180,"#c7a46a","#7a5a20","14 taster","GPA0–7, GPB0–5",fs=18)
bunt([(1700,265),(1760,265)],"#1d1d1f",5)
liste(1745,380,["GPA0 av · 1 Skjold · 2 meny","3 opp · 4 ned · 5 venstre","6 høyre · 7 OK","GPB0 tilbake · 1 avslutt · 2 ⏯","3 demp · 4 vol+ · 5 vol−","andre bein → GND-stripe (E, I, O)"],"#55554f",13)
# XIAO → MCP
bunt([(1375,560),(1375,265),(1500,265)],"#2f6fd6")
liste(1205,220,["XIAO → MCP (5 ledn.):","D4 → SDA · D5 → SCL","D1 → INTA · 3V3 → VCC","GND → GND"],"#1d4f9c")
# XIAO → skjerm 18p
box(1500,500,200,120,"#e3c79c","#9b6a2a","FPC 18p","skjermen (SPI)",fs=18)
box(1500,690,200,100,"#e3c79c","#9b6a2a","FPC 6p","berøring (I²C)",fs=18)
box(1760,560,180,190,"#2b2f3a","#111","2,8″ skjerm","HP28030",fs=18,tc="#fff")
bunt([(1390,600),(1500,600)],"#2bb54d")
bunt([(1390,740),(1500,740)],"#e0a400")
bunt([(1700,560),(1730,560),(1730,620),(1760,620)],"#555",4)
bunt([(1700,740),(1730,740),(1730,700),(1760,700)],"#555",4)
liste(1405,430,["XIAO → 18p (skjerm):","D8 SCK · D10 MOSI · D2 D/C","D3 RES · D9 → AO3400A → baklys","+ 3V3 og GND fra MCP-modulen"],"#1f7a33")
liste(1405,815,["→ 6p (berøring): SDA, SCL,","RES, 3V3, GND"],"#8a6a00")
# IR
box(1500,880,200,110,"#3fae6a","#1f6e3e","IR-kortet","2 IR-dioder · VS1838B",fs=18,tc="#fff")
bunt([(1340,790),(1340,935),(1500,935)],"#2bb5b0")
liste(1720,915,["D6 → IR TX (AO3400A)","D7 ← IR RX (VS1838B)","BAT+ → 6,8 Ω → dioder","MCP GPB6 → VS1838B VCC"],"#2b8f8a")
# batteri og dokk
box(1200,870,120,90,"#b9c0c7","#58616b","LiPo","1200 mAh",fs=16)
bunt([(1260,870),(1260,790)],"#d63b2f")
box(1200,995,240,80,"#8b8b86","#444","Pogo (dokk)","+ → 1N5819 → XIAO 5V",fs=16,tc="#fff")
liste(1460,1020,["Pogo+ → 68k/100k → MCP GPB7 (i dokken)","D0: BAT+ → 1 MΩ → D0 → 1 MΩ + 100 nF → GND"],"#1d1d1f",13)
# ---------- 4: steg
Y=1160; panel(40,Y,1920,700,"4 · Byggerekkefølge")
steg=["Print topp.stl, bunn.stl (eller bunn_dokk.stl), hetter og IR-vindu fra stl_hu/ (PLA/PETG, 0,2 mm).",
 "Skjær stripekortet til 19 × 47 hull (stripene på langs). Kutt 3 × 3 hull i hjørnene ved halen, bor Ø2,4 til midtskruen.",
 "Kutt stripene i de 9 hullene på tegningen (3,5 mm bor vridd for hånd). Mål at ingen stripe henger sammen over et kutt.",
 "Lodd de 14 bryterne på oppsiden. Klipp beina 0,8 mm under kortet. Lenk GND-stripene E, I og O, og ett svart til MCP GND.",
 "Lodd 14 tasteledninger (30 AWG, én farge per pinne) i hullene på tegningen – til MCP GPA0–GPA7 og GPB0–GPB5.",
 "XIAO: lodd batteriledningene på BAT-putene bak, R9/R10/C3 (batterimåling) og 1N5819 (dokk) før den limes. Så D0–D10, 3V3, GND, 5V.",
 "MCP-modulen: R3 (VCC→INTA), R11/R12 (dokk→GPB7). Koble SDA, SCL, INTA, VCC, GND til XIAO, og GPB6 til IR-mottakerens VCC.",
 "Skjermadapterne: R8, R16 og AO3400A (Q2) med R6/R7. Ledninger til XIAO (SCK, MOSI, D/C, RES, baklys) og MCP (SDA, SCL, 3V3, GND).",
 "IR-kortet: 2 IR-dioder i serie + 6,8 Ω fra BAT+, AO3400A fra D6, 100 µF, VS1838B til D7. 5 ledninger langs venstre side.",
 "Legg i bunnen: IR-kortet i sporet, batteriet i lomma, XIAO (USB-C i åpningen), MCP og adaptere på tape. Ledninger langs sidene.",
 "Gjennomgangstest med multimeter FØR batteriet: ingen pip 3V3–GND/BAT+–BAT−, hver tast piper bare mot sin MCP-pinne.",
 "Skjermen i lomma i toppen, flatkablene ned i adapterne (kontaktene ned). Hullkortet på stolpene, toppen på, 5 × M2×10 nedenfra.",
 "Flash via USB-C: esphome run esphome/skjold-fjernkontroll-hullkort.yaml. Koble batteriet – sjekk + og − på pluggen først!"]
for i,t in enumerate(steg):
    yy=Y+90+i*46
    o.append(f'<circle cx="80" cy="{yy-6}" r="15" fill="#d9a441"/><text x="80" y="{yy}" text-anchor="middle" font-size="15" font-weight="700" fill="#1d1d1f">{i+1}</text><text x="108" y="{yy}" font-size="19" fill="#1d1d1f">{t}</text>')
o.append('</svg>')
open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'fjernkontroll_hullkort_bygg.svg'),'w').write("\n".join(o))
