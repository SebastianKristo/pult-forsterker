import csv
W,H=2400,1600
FARGE={"brun":"#8b5a2b","rød":"#d63b2f","oransje":"#f08a24","gul":"#e0b400","grønn":"#2e9e4f","blå":"#2f6fd6","fiolett":"#8a4fd6",
       "grå":"#8b8b86","svart":"#1d1d1f","hvit":"#bdbdb8","lyseblå":"#5fb4f0","rosa":"#e86aa8","turkis":"#1fb5ad","lysegrønn":"#7fd36a",
       "lilla":"#9b59b6","svart/hvit":"#555","oransje/hvit":"#f5b16a","lilla/hvit":"#c39bd3"}
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Sora, Arial, sans-serif">',
'<rect width="100%" height="100%" fill="#f7f6f2"/>',
'<style>.w{fill:none;stroke-width:5;stroke-linejoin:round;stroke-linecap:round}.t{font-size:17px;font-weight:600;fill:#1d1d1f}.m{font-family:IBM Plex Mono,monospace;font-size:14px;fill:#1d1d1f}.s{font-size:15px;fill:#55554f}</style>',
'<text x="40" y="58" font-size="34" font-weight="700" fill="#1d1d1f">Skjold Fjernkontroll (hullkort) – alle ledningene</text>',
'<text x="40" y="92" class="s">Fargene er ledningsfargene fra hullkort/koblinger.csv. Rød skinne = 3V3, sort skinne = GND: alt som går dit, kobles sammen. Ledningene: 30 AWG wire-wrap, batteri 26 AWG silikon.</text>']
wires=[];top=[]
def w(pts,c,dash=False):
    wires.append(f'<polyline class="w" stroke="{c}" {"stroke-dasharray=\"10 7\"" if dash else ""} points="{" ".join(f"{x},{y}" for x,y in pts)}"/>')
def pin(x,y,lab,side="l",c="#c9a227"):
    top.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{c}" stroke="#1d1d1f" stroke-width="2"/>')
    if side=="l": top.append(f'<text x="{x+14}" y="{y+5}" class="m">{lab}</text>')
    else: top.append(f'<text x="{x-14}" y="{y+5}" class="m" text-anchor="end">{lab}</text>')
def boks(x,y,bw,bh,tit,sub,fill,stroke,tc="#1d1d1f"):
    top.insert(0,f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    top.append(f'<text x="{x+bw/2}" y="{y+30}" text-anchor="middle" font-size="20" font-weight="700" fill="{tc}">{tit}</text>')
    if sub: top.append(f'<text x="{x+bw/2}" y="{y+52}" text-anchor="middle" font-size="14" fill="{tc}">{sub}</text>')
rows=list(csv.DictReader(open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'koblinger.csv'))))
keys=[r for r in rows if r["nett"].startswith("K_")]
Y0,DY=215,52
# skinner
V3=122; GNDY=1470
w([(560,V3),(2330,V3)],"#d63b2f"); top.append(f'<text x="2335" y="{V3+5}" class="t" fill="#d63b2f">3V3</text>')
w([(60,GNDY),(2330,GNDY)],"#1d1d1f"); top.append(f'<text x="2335" y="{GNDY+5}" class="t">GND</text>')
# ---- stripekortet
SX,SW=40,330
boks(SX,140,SW,Y0+DY*14-110,"Stripekortet","14 brytere · hull = tegningen","#efe1c2","#7a5a20")
mcpL=640
for i,r in enumerate(keys):
    y=Y0+i*DY; navn=r["merknad"].split(" →")[0].replace("_"," ")
    hull=r["fra"].replace("hull ","")
    top.append(f'<text x="{SX+16}" y="{y+5}" class="m">{hull:>4}  {navn}</text>')
    pin(SX+SW,y,"","r","#c7a46a")
    w([(SX+SW,y),(mcpL,y)],FARGE[r["farge"]])
yg=Y0+14*DY+10
top.append(f'<text x="{SX+16}" y="{yg+5}" class="m">E/I/O  GND-stripene</text>'); pin(SX+SW,yg,"","r","#555")
w([(SX+SW,yg),(SX+SW+40,yg),(SX+SW+40,GNDY)],"#1d1d1f")
# ---- MCP
MX=mcpL; MW=230
boks(MX,140,MW,Y0+DY*16-80,"MCP23017","modul (CJMCU-2317)","#d8cdee","#4a3680")
mpins=["GPA0","GPA1","GPA2","GPA3","GPA4","GPA5","GPA6","GPA7","GPB0","GPB1","GPB2","GPB3","GPB4","GPB5","GPB6","GPB7"]
for i,p in enumerate(mpins): pin(MX,Y0+i*DY,p,"l","#9c86c9")
R=MX+MW
right=["VCC","GND","SDA","SCL","INTA"]
RY={p:Y0+i*DY for i,p in enumerate(right)}
for p in right: pin(R,RY[p],p,"r","#9c86c9")
# ---- XIAO
XX,XW=1040,230
boks(XX,420,XW,540,"XIAO ESP32S3","USB-C ned mot halen","#55555a","#111","#fff")
XL=["D0","D1","D2","D3","D4","D5","D6"]; XR=["5V","GND","3V3","D10","D9","D8","D7"]
XY={}
for i,p in enumerate(XL): XY[p]=(XX,500+i*62); pin(XX,500+i*62,p,"l","#c9c9c4")
for i,p in enumerate(XR): XY[p]=(XX+XW,500+i*62); pin(XX+XW,500+i*62,p,"r","#c9c9c4")
top.append(f'<text x="{XX+XW/2}" y="{960-18}" text-anchor="middle" font-size="13" fill="#ddd">BAT+ / BAT− på baksiden</text>')
XB=(XX+XW/2,960)
# MCP → XIAO
w([(R,RY["SDA"]),(R+60,RY["SDA"]),(R+60,XY["D4"][1]),(XX,XY["D4"][1])],FARGE["blå"])
w([(R,RY["SCL"]),(R+90,RY["SCL"]),(R+90,XY["D5"][1]),(XX,XY["D5"][1])],FARGE["gul"])
w([(R,RY["INTA"]),(R+30,RY["INTA"]),(R+30,XY["D1"][1]),(XX,XY["D1"][1])],FARGE["hvit"])
w([(R,RY["VCC"]),(R+20,RY["VCC"]),(R+20,V3)],"#d63b2f")
w([(R,RY["GND"]),(R+120,RY["GND"]),(R+120,GNDY)],"#1d1d1f")
for p,txt in (("SDA","SDA → D4"),("SCL","SCL → D5"),("INTA","INTA → D1")):
    pass
w([(XY["3V3"][0],XY["3V3"][1]),(XY["3V3"][0]+40,XY["3V3"][1]),(XY["3V3"][0]+40,V3)],"#d63b2f")
w([(XY["GND"][0],XY["GND"][1]),(XY["GND"][0]+25,XY["GND"][1]),(XY["GND"][0]+25,GNDY)],"#1d1d1f")
# MCP GPB6 → IR VCC, GPB7 ← dokk
gb6=Y0+14*DY; gb7=Y0+15*DY
# ---- skjermadapter 18p
FX=1560; FW=250
boks(FX,180,FW,420,"FPC 18p-adapter","skjermen (SPI)","#f1dfc0","#9b6a2a")
f18=[("2","RESET"),("3","SCK"),("4","D/C"),("6","MOSI"),("9+10","VDD"),("12–15","LED-K"),("1,5,8,16,18","GND")]
F18={}
for i,(n,l) in enumerate(f18):
    y=250+i*50; F18[l]=y; pin(FX,y,f"{n} {l}","l","#e3c79c")
def til(xp,yp,lane,xd,yd,c):
    w([(xp,yp),(lane,yp),(lane,yd),(xd,yd)],c)
til(*XY["D3"],XX-60,FX,F18["RESET"],FARGE["grå"])   # D3 venstre side → rundt
til(*XY["D8"],XX+XW+70,FX,F18["SCK"],FARGE["grønn"])
til(*XY["D2"],XX-40,FX,F18["D/C"],FARGE["brun"])
til(*XY["D10"],XX+XW+100,FX,F18["MOSI"],FARGE["lyseblå"])
w([(FX,F18["VDD"]),(FX-40,F18["VDD"]),(FX-40,V3)],"#d63b2f")
w([(FX,F18["GND"]),(FX-25,F18["GND"]),(FX-25,GNDY)],"#1d1d1f")
# baklys: D9 → R6 100Ω → Q2 G ; Q2 D → LED-K ; S → GND
QX,QY=1420,520
top.append(f'<rect x="{QX-55}" y="{QY-28}" width="110" height="56" rx="8" fill="#fff" stroke="#e86aa8" stroke-width="3"/><text x="{QX}" y="{QY-4}" text-anchor="middle" font-size="14" font-weight="700">Q2 AO3400A</text><text x="{QX}" y="{QY+16}" text-anchor="middle" font-size="12" fill="#55554f">G←100 Ω · S→GND</text>')
w([(XY["D9"][0],XY["D9"][1]),(XX+XW+130,XY["D9"][1]),(XX+XW+130,QY),(QX-55,QY)],FARGE["rosa"])
w([(QX+55,QY),(QX+80,QY),(QX+80,F18["LED-K"]),(FX,F18["LED-K"])],"#555")
w([(QX,QY+28),(QX,GNDY)],"#1d1d1f")
# ---- 6p
SXp=1560
boks(SXp,640,FW,300,"FPC 6p-adapter","berøring (I²C)","#f1dfc0","#9b6a2a")
f6=[("1","VDD"),("2","GND"),("3","SDA"),("4","SCL"),("6","RST")]
F6={}
for i,(n,l) in enumerate(f6):
    y=710+i*46; F6[l]=y; pin(SXp,y,f"{n} {l}","l","#e3c79c")
w([(SXp,F6["VDD"]),(SXp-60,F6["VDD"]),(SXp-60,V3)],"#d63b2f")
w([(SXp,F6["GND"]),(SXp-25,F6["GND"]),(SXp-25,GNDY)],"#1d1d1f")
# SDA/SCL fra MCP (deles med D4/D5): stiplet
w([(R+60,XY["D4"][1]),(R+60,975),(SXp-110,975),(SXp-110,F6["SDA"]),(SXp,F6["SDA"])],FARGE["blå"],True)
w([(R+90,XY["D5"][1]),(R+90,960),(SXp-90,960),(SXp-90,F6["SCL"]),(SXp,F6["SCL"])],FARGE["gul"],True)
w([(FX-60,F18["RESET"]),(FX-140,F18["RESET"]),(FX-140,F6["RST"]),(SXp,F6["RST"])],FARGE["grå"])
# ---- IR-kortet
IX=1960; IW=330
boks(IX,180,IW,400,"IR-kortet (nesen)","2 IR-dioder · VS1838B · AO3400A","#cfeedd","#1f6e3e")
irp=[("R13 / Q3 G","IR_TX"),("VS1838B OUT","IR_RX"),("R15 + C4","VBAT"),("VS1838B VCC","IR_STROM"),("GND","GND")]
IRY={}
for i,(l,n) in enumerate(irp):
    y=260+i*60; IRY[n]=y; pin(IX,y,l,"l","#3fae6a")
w([XY["D6"],(XX-80,XY["D6"][1]),(XX-80,1010),(1900,1010),(1900,IRY["IR_TX"]),(IX,IRY["IR_TX"])],FARGE["turkis"])
w([XY["D7"],(XX+XW+160,XY["D7"][1]),(XX+XW+160,990),(1880,990),(1880,IRY["IR_RX"]),(IX,IRY["IR_RX"])],FARGE["lysegrønn"])
w([(MX,gb6),(MX-20,gb6),(MX-20,1435),(1940,1435),(1940,IRY["IR_STROM"]),(IX,IRY["IR_STROM"])],FARGE["oransje/hvit"])
w([(IX,IRY["GND"]),(IX-30,IRY["GND"]),(IX-30,GNDY)],"#1d1d1f")
top.append(f'<text x="{IX+12}" y="560" class="s">2 dioder i serie: BAT+ → 6,8 Ω → dioder → Q3</text>')
# ---- batteri og pogo
BX,BY=1040,1050
boks(BX,BY,230,120,"LiPo 1200 mAh","JST-PH: rød +, sort −","#dfe3e7","#58616b")
top.append(f'<text x="{BX+115}" y="{BY+150}" text-anchor="middle" class="s">+ → XIAO BAT+ (bak) og IR-kortet</text>')
w([(BX+70,BY),(BX+70,XB[1])],FARGE["oransje"])
w([(BX+160,BY),(BX+160,GNDY)],"#1d1d1f")
w([(BX+70,1030),(1920,1030),(1920,IRY["VBAT"]),(IX,IRY["VBAT"])],FARGE["oransje"])
PX,PY=1400,1230
boks(PX,PY,300,140,"Pogo (dokken)","+ → 1N5819 → XIAO 5V","#cfcfcb","#444")
w([(PX+60,PY),(PX+60,1180),(XY["5V"][0]+15,1180),(XY["5V"][0]+15,XY["5V"][1]),(XY["5V"][0],XY["5V"][1])],FARGE["lilla"])
w([(PX+240,PY+140),(PX+240,GNDY)],"#1d1d1f")
w([(PX,PY+70),(MX-50,PY+70),(MX-50,gb7),(MX,gb7)],FARGE["fiolett"])
top.append(f'<text x="{PX+10}" y="{PY+110}" class="s">+ → 68 kΩ → GPB7 → 100 kΩ → GND</text>')
# småkomponenter
top.append(f'<text x="40" y="{GNDY+60}" class="s">Småkomponenter (loddes på pinnene, krympestrømpe over): R3 10 kΩ MCP VCC→INTA · R16 1 MΩ 6p pinne 1→6 · R8 10 Ω 18p pinne 10→11 · R9/R10 1 MΩ + C3 100 nF: BAT+→D0→GND · D1 1N5819 pogo+→5V · R11/R12 68k/100k pogo→GPB7.</text>')
o+=wires+top+['</svg>']
open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'fjernkontroll_hullkort_ledninger.svg'),'w').write("\n".join(o))
