W,H=2400,1640
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Sora, Arial, sans-serif">',
'<rect width="100%" height="100%" fill="#f7f6f2"/>',
'<style>.w{fill:none;stroke-width:5;stroke-linejoin:round;stroke-linecap:round}.m{font-family:IBM Plex Mono,monospace;font-size:15px;fill:#1d1d1f}.s{font-size:15px;fill:#55554f}.t{font-size:17px;font-weight:700;fill:#1d1d1f}</style>',
'<text x="40" y="58" font-size="34" font-weight="700" fill="#1d1d1f">Skjold Røst – slik kobles alt</text>',
'<text x="40" y="92" class="s">ESP32-S3-DevKitC-1 N16R8 · PCM5102A (DAC) · TPA3118D2 mono (PBTL) · MP1584EN 12→5 V · 2,42″ OLED (I²C) · EC11 · 5 knapper på hullkort. Pinnene = fastvaren i firmware/rost.</text>']
wires=[];top=[]
def w(pts,c,dash=False,wd=5,lag=None):
    (lag if lag is not None else wires).append(f'<polyline class="w" stroke="{c}" stroke-width="{wd}" {"stroke-dasharray=\"10 7\"" if dash else ""} points="{" ".join(f"{x},{y}" for x,y in pts)}"/>')
def pin(x,y,lab,side="l",c="#c9a227",tc="#1d1d1f"):
    top.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{c}" stroke="#1d1d1f" stroke-width="2"/>')
    if side=="l": top.append(f'<text x="{x+14}" y="{y+5}" class="m" style="fill:{tc}">{lab}</text>')
    else: top.append(f'<text x="{x-14}" y="{y+5}" class="m" text-anchor="end" style="fill:{tc}">{lab}</text>')
def boks(x,y,bw,bh,tit,sub,fill,stroke,tc="#1d1d1f"):
    top.insert(0,f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    top.append(f'<text x="{x+bw/2}" y="{y+30}" text-anchor="middle" font-size="20" font-weight="700" fill="{tc}">{tit}</text>')
    if sub: top.append(f'<text x="{x+bw/2}" y="{y+52}" text-anchor="middle" font-size="14" fill="{tc}">{sub}</text>')
R,O,Y,B,G,GR,P,T,BR,K,PK,LB="#d63b2f","#f08a24","#e0b400","#2f6fd6","#2e9e4f","#8b8b86","#8a4fd6","#1fb5ad","#8b5a2b","#1d1d1f","#e86aa8","#5fb4f0"
# skinner
Y12=128; Y5=150; Y33=172; GND=1540
for y,c,t in ((Y12,"#b8860b","12 V"),(Y5,R,"5 V"),(Y33,O,"3V3")):
    w([(60,y),(2300,y)],c); top.append(f'<text x="2310" y="{y+6}" class="t" fill="{c}">{t}</text>')
w([(60,GND),(2300,GND)],K); top.append(f'<text x="2310" y="{GND+6}" class="t">GND</text>')
# ---- strøm: DC-kontakt og MP1584
boks(60,230,250,150,"DC-kontakt 12 V","5,5/2,1 · senter +","#e6e3da","#555")
pin(310,290,"+","r","#b8860b"); pin(310,340,"−","r","#555")
w([(310,290),(340,290),(340,Y12)],"#b8860b"); w([(310,340),(360,340),(360,GND)],K)
boks(60,440,250,170,"MP1584EN","12 V → 5,0 V (still inn først!)","#dfe7f1","#2f5f9a")
pin(60,510,"IN+","l","#b8860b"); pin(60,560,"IN−","l","#555"); pin(310,510,"OUT+","r",R); pin(310,560,"OUT−","r","#555")
w([(60,510),(40,510),(40,Y12),(60,Y12)],"#b8860b"); w([(60,560),(30,560),(30,GND)],K)
w([(310,510),(380,510),(380,Y5)],R); w([(310,560),(395,560),(395,GND)],K)
# ---- ESP32
EX,EW=900,300
boks(EX,260,EW,980,"ESP32-S3","DevKitC-1 N16R8","#55555a","#111","#fff")
L=[("5V",None),("GND",None),("3V3",None),("GPIO4","BCK"),("GPIO5","LCK"),("GPIO6","DIN"),("GPIO7","SDZ"),("GPIO11","SDA"),("GPIO12","SCL")]
Rr=[("GPIO8","⏻"),("GPIO9","1"),("GPIO18","2"),("GPIO39","3"),("GPIO47","4"),("GPIO15","EC11 A"),("GPIO16","EC11 B"),("GPIO17","EC11 trykk"),("GPIO41/42/40","mik (valgfri)")]
EY={}
for i,(p,_) in enumerate(L): EY[p]=(EX,360+i*95); pin(EX,360+i*95,p,"l","#c9c9c4")
for i,(p,_) in enumerate(Rr): EY[p]=(EX+EW,360+i*95); pin(EX+EW,360+i*95,p,"r","#c9c9c4")
w([EY["5V"],(860,EY["5V"][1]),(860,Y5)],R); w([EY["GND"],(845,EY["GND"][1]),(845,GND)],K); w([EY["3V3"],(830,EY["3V3"][1]),(830,Y33)],O)
top.append(f'<text x="{EX+EW/2}" y="1225" text-anchor="middle" font-size="13" fill="#ddd">USB-C bak: flashing</text>')
# ---- PCM5102A
PX,PW=440,320
boks(PX,560,PW,330,"PCM5102A (DAC)","SCK, FMT, FLT, DEMP → GND · XSMT → 3V3","#e8e0f6","#6d28d9")
pp=[("BCK",B),("LCK",Y),("DIN",G)]
for i,(p,c) in enumerate(pp):
    y=640+i*50; pin(PX+PW,y,p,"r","#b9a7e6"); w([(PX+PW,y),(820-i*20,y),(820-i*20,EY["GPIO"+str(4+i)][1]),(EX,EY["GPIO"+str(4+i)][1])],c)
pin(PX+PW,800,"VIN","r","#b9a7e6"); w([(PX+PW,800),(790,800),(790,Y5)],R)
pin(PX+PW,850,"GND","r","#b9a7e6"); w([(PX+PW,850),(775,850),(775,GND)],K)
pin(PX,700,"OUT L","l","#b9a7e6"); pin(PX,760,"AGND","l","#b9a7e6")
# ---- TPA3118
TX,TW=60,300
boks(TX,690,TW,330,"TPA3118D2","mono PBTL · 12 V","#f8e3cf","#b45309")
pin(TX+TW,745,"IN +","r","#f0b27a"); pin(TX+TW,795,"IN −","r","#f0b27a")
pin(TX+TW,860,"SDZ","r","#f0b27a"); pin(TX,760,"PVCC","l","#f0b27a"); pin(TX,810,"GND","l","#f0b27a")
pin(TX+TW,930,"OUT +","r","#f0b27a"); pin(TX+TW,980,"OUT −","r","#f0b27a")
w([(TX+TW,745),(400,745),(400,700),(PX,700)],"#9b9b9b"); w([(TX+TW,795),(415,795),(415,760),(PX,760)],K)
w([(TX+TW,860),(430,860),(430,1060),(810,1060),(810,EY["GPIO7"][1]),(EX,EY["GPIO7"][1])],PK)
w([(TX,760),(45,760),(45,Y12)],"#b8860b"); w([(TX,810),(30,810),(30,GND)],K)
boks(80,1110,260,150,"Element 4 Ω","Dayton RS75-4","#d9d9d4","#444")
w([(TX+TW,930),(380,930),(380,1170),(340,1170)],R,wd=7); w([(TX+TW,980),(370,980),(370,1210),(340,1210)],K,wd=7)
top.append('<text x="90" y="1300" class="s">Høyttalerledningene: 0,5 mm², ikke til GND</text>')
# ---- OLED
OX,OW=1500,330
boks(OX,230,OW,250,"2,42″ OLED","SSD1309 · I²C · lodd på baksiden","#2b2f3a","#111","#fff")
op=[("VDD",O),("GND",K),("SDA",B),("SCL",Y)]
OYp={}
for i,(p,c) in enumerate(op): OYp[p]=300+i*45; pin(OX,300+i*45,p,"l","#8b8b86","#fff")
w([(OX,OYp["VDD"]),(1460,OYp["VDD"]),(1460,Y33)],O); w([(OX,OYp["GND"]),(1445,OYp["GND"]),(1445,GND)],K)
w([EY["GPIO11"],(870,EY["GPIO11"][1]),(870,215),(1420,215),(1420,OYp["SDA"]),(OX,OYp["SDA"])],B)
w([EY["GPIO12"],(885,EY["GPIO12"][1]),(885,205),(1405,205),(1405,OYp["SCL"]),(OX,OYp["SCL"])],Y)
# ---- knapper på hullkort
KX,KW=1500,700
boks(KX,488,KW,382,"Knappene på hullkortet","64 × 20 mm · 5 brytere 6×6, 12,7 mm (5 hull) mellom","#efe1c2","#7a5a20")
names=["⏻","1","2","3","4"]; gp=["GPIO8","GPIO9","GPIO18","GPIO39","GPIO47"]; kc=[R,O,Y,G,B]
bx0=KX+110
for i in range(5):
    x=bx0+i*120
    top.append(f'<rect x="{x-30}" y="640" width="60" height="60" rx="6" fill="#3a3a3c"/><circle cx="{x}" cy="670" r="15" fill="#6b6a64"/><text x="{x}" y="676" text-anchor="middle" font-size="16" font-weight="700" fill="#fff">{names[i]}</text>')
    for dx in (-24,24):
        top.append(f'<circle cx="{x+dx}" cy="722" r="5" fill="#1d1d1f"/>')   # fremre bein: GND
    top.append(f'<circle cx="{x+24}" cy="618" r="6" fill="{kc[i]}" stroke="#1d1d1f" stroke-width="1.5"/>')   # bakre høyre: signal
    top.append(f'<line x1="{x-30}" y1="612" x2="{x-18}" y2="624" stroke="#d63b2f" stroke-width="3"/>')
    yy=EY[gp[i]][1]
    w([(x+24,618),(x+24,598-i*7),(KX-20+i*0,598-i*7)],kc[i],lag=top)
    w([(KX,598-i*7),(1400+i*12,598-i*7),(1400+i*12,yy),(EX+EW,yy)],kc[i])
w([(bx0-40,722),(bx0+4*120+40,722)],"#9a9a96",wd=4,lag=top)
w([(bx0-40,722),(KX,722)],K,lag=top); w([(KX,722),(1490,722),(1490,GND)],K)
top.append(f'<text x="{KX+20}" y="770" class="s">Sølvstrek = bar fortinnet tråd over de FREMRE beina (GND-bussen) → GND.</text>')
top.append(f'<text x="{KX+20}" y="795" class="s">Farget prikk = BAKRE HØYRE bein → ledning til ESP32. Rød strek = klipp BAKRE VENSTRE bein.</text>')
top.append(f'<text x="{KX+20}" y="820" class="s">⏻ til venstre sett forfra. Sjekk med multimeter at fremre og bakre bein er hver sin pol.</text>')
top.append(f'<text x="{KX+20}" y="845" class="s">Knappene trekkes til GND (intern pull-up i ESP-en) – ingen motstander.</text>')
# ---- EC11
CXb=1500
boks(CXb,930,330,250,"EC11 volumknott","med trykk","#d8e8f5","#2f6fd6")
ec=[("A","GPIO15",T),("B","GPIO16",LB),("C (midt)","GND",K),("trykk 1","GPIO17",P),("trykk 2","GND",K)]
for i,(l,t,c) in enumerate(ec):
    y=990+i*40; pin(CXb,y,l,"l","#7fb2ff")
    if t=="GND": w([(CXb,y),(1470-i*4,y),(1470-i*4,GND)],K)
    else:
        yy=EY[t][1]; w([(CXb,y),(1350+i*15,y),(1350+i*15,yy),(EX+EW,yy)],c)
# ---- mikrofon valgfri
boks(1900,930,330,250,"INMP441 (valgfri)","mikrofon","#e7f5ec","#2e9e4f")
for i,(l,t) in enumerate((("SCK","GPIO41"),("WS","GPIO42"),("SD","GPIO40"),("VDD","3V3"),("GND, L/R","GND"))):
    pin(1900,1000+i*38,f"{l} → {t}","l","#7fd36a")
top.append('<text x="1915" y="1205" class="s">Kobles bare hvis du vil ha mikrofon.</text>')
# notater
nt=["Still MP1584EN til 5,0 V med multimeter FØR ESP-en og lydkortet kobles til.",
    "TPA3118-kortet må stå i PBTL (mono): sjekk jumperne/loddebroene på ditt kort.",
    "PCM5102A: SCK, FMT, FLT og DEMP til GND, XSMT til 3V3 (loddebroene H1L–H4L bak på kortet).",
    "Bruk ikke GPIO0, 3, 19, 20, 26–32, 35–37, 45, 46 eller 38/48 (oppstart, USB, flash, PSRAM, RGB-LED).",
    "Flash fastvaren fra skjold-lab.com/flasher/rost/ før alt skrus sammen, og test knapper og skjerm."]
for i,t in enumerate(nt):
    top.append(f'<text x="1500" y="{1260+i*30}" class="s">• {t}</text>')
o+=wires+top+['</svg>']
open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'rost_koblinger.svg'),'w').write("\n".join(o))
