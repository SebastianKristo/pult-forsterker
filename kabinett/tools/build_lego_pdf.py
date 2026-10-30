#!/usr/bin/env python3
"""Bildeveiledning (LEGO-stil) -> KI_Pultforsterker_Bildeveiledning.pdf"""
import base64, asyncio
from pathlib import Path
K=Path("/home/claude/pultforsterker/kabinett"); ST=K/"steps"
def b64(p): return "data:image/png;base64,"+base64.b64encode(Path(p).read_bytes()).decode()
def img(p,cls=""): return f'<img class="{cls}" src="{b64(p)}" alt="">'
COVER="/tmp/claude-0/-home-claude/ece3d3ea-154f-58a2-bd86-590c14f979fd/scratchpad/z.png"

PARTS=[("Raspberry Pi Zero 2 W",1),("PCM5102A I2S-DAC",1),("XH-M562 TPA3116D2 2×50 W",1),("X9C103S digitalpot",2),("Relékort 4-ch 5 V",1),("MOSFET-kort 4-ch (3.3V)",2),("Buck 24→5 V",1),("OLED 2,42\" SSD1309",1),
("KY-040 encoder (gjenget)",1),("Knott 30×17 mm, 6 mm D",1),("12 mm LED-knapp",4),("16 mm POWER-knapp",1),("KCD1 vippebryter",1),("DC-099 kontakt",1),("USB-C panelflens → micro-USB",1),("PJ392 3,5 mm jack",1),
("Bananterminal 4 mm",4),("Bananplugg 4 mm",4),("24 V 4 A adapter",1),("Røykfarget akryl 70×38×2",1),("M3 varmeinnsats",4),("M3×8 senkskrue",8),("M2,5×6 skrue",6),("M2 avstandsstykke 6 mm + mutter",4),
("18 AWG rød/svart",1),("22 AWG rød/svart",1),("USB-isolator ADuM3160/4160 (eller ground-loop-isolator 3,5 mm)",1),("Elektrolyttkondensator 2200 µF / 35 V",1),("Inline sikringsholder 5×20 + sikring 5 A",1),("Ferrittklips Ø 5–7 mm",2),("Dupont-sett hunnhus + crimpstifter",1),("Skjermet lydkabel 1 m",2),("Dupont hunn–hunn 20 cm",1),("VHB-tape, kabelstrips, gummiføtter",1),("Treskrue 4×25",4)]

def step(n,title,img_path,parts,lines,extra="",cls=""):
    parts_html="".join(f"<li>{p}</li>" for p in parts)
    lines_html="".join(f"<li>{l}</li>" for l in lines)
    return f"""<section class="step {cls}"><div class="head"><span class="n">{n}</span><h2>{title}</h2></div>
    <div class="row"><div class="pic">{img(img_path)}</div><aside class="parts"><b>Du trenger</b><ul>{parts_html}</ul></aside></div>
    <ol class="do">{lines_html}</ol>{extra}</section>"""

def closeup(p,cap,cls="close"): return f'<figure class="{cls}">{img(p)}<figcaption>{cap}</figcaption></figure>'

S=[]
S.append(f"""<section class="cover"><div><div class="kicker">Bildeveiledning · steg for steg</div><h1>Pultforsterker</h1>
<p class="sub">Fra tom kasse til ferdig forsterker under pulten. Hvert steg viser hva som settes inn, hvor det skal, og hva som loddes.</p></div>
{img(COVER,"hero")}
<div class="spec"><div><b>Kabinett</b>200 × 120 × 48 mm · 3 printede deler</div><div><b>Elektronikk</b>Pi Zero 2 W · PCM5102A · TPA3116D2</div><div><b>Innganger</b>AirPlay 2 · Bluetooth · AUX · USB</div></div></section>""")

S.append("""<section class="plain"><h2>Slik leser du veiledningen</h2>
<div class="legend"><div><span class="n">7</span> Stegnummer – følg rekkefølgen</div><div><span class="arrow">→</span> Oransje pil = delen i dette steget og hvor den skal</div><div><span class="box">Du trenger</span> Deler til akkurat dette steget</div><div><span class="dim">grå ledning</span> = allerede lagt i et tidligere steg</div></div>
<p>Målene i figurene er i millimeter fra kassens senter. Fronten er mot deg, baksiden vender inn under pulten. Bokstavene A–H på kortene brukes gjennom hele veiledningen.</p>
<div class="warn"><b>Før du kobler 24 V:</b> Alle 24 V-ledninger skal være ferdig loddet og krympet. Pi-en tåler maks 5,25 V – mål buck-utgangen før den kobles til. En kortslutning på forsterkeren kan smelte en tynn ledning.</div>
<h2>Alle delene</h2><ul class="partlist">"""+"".join(f"<li><span>{q} ×</span>{n}</li>" for n,q in PARTS)+"""</ul>
<p class="muted">Verktøy: loddebolt, loddetinn, avbiter, avisoleringstang, krympestrømpe, 2 mm og 1,5 mm unbrako, liten stjerneskrutrekker, multimeter, 2,5/3 mm bor, hobbykniv.</p></section>""")

S.append("""<section class="plain"><div class="head"><span class="n">0</span><h2>Forbered kortene på bordet</h2></div>
<p>Alt som skal loddes på selve kortene gjøres nå, mens de ligger fritt. Deretter testes Pi + DAC + OLED før noe skrus fast.</p>
"""+closeup(ST/"close_dac.png","DAC PCM5102A: fire loddebroer på baksiden + SCK til GND.")+"""
<ol class="do"><li><b>DAC:</b> lodd broene som vist. Lodd pinnelisten på (eller bruk Dupont rett i hullene).</li>
<li><b>Pi:</b> skriv SD-kort (Raspberry Pi OS Lite 64-bit, vertsnavn <code>pultamp</code>, Wi-Fi + SSH). Lodd 40-pinners header på Pi-en hvis den ikke har.</li>
<li><b>X9C-modulene:</b> lodd 5 Dupont-ledninger på hver (VCC, GND, INC, U/D, CS) og 3 lydledninger (VH, VW, VL).</li>
<li><b>MOSFET-kortene:</b> sett jumperen på <b>3.3V</b> på begge.</li>
<li><b>Relékortet:</b> jumper VCC–JD-VCC <b>på</b>. Kortet skal være «high level trigger» (eller sett jumper til H).</li>
<li><b>Test:</b> koble DAC (pinne 4/6/12/35/40) og OLED (1/9/3/5/7) til Pi med Dupont, start fra USB-lader, kjør <code>install.sh</code>. Skjermen viser oppstartsbildet; <code>aplay -l</code> viser <code>sndrpihifiberry</code>.</li></ol></section>""")

S.append(step(1,"Kassen",ST/"step_01.png",["Kasse (v2_body.stl), printet med åpningen opp"],
 ["Rens alle hull i front og bak med bor i riktig diameter – roter for hånd.","Prøv at KCD1, DC-099, USB-C-flensen, jacken og terminalene passer i sine hull. Fil litt om nødvendig.","Prøv frontplaten mot fronten; akrylet skal ligge plant i forsenkningen."]))
S.append(step(2,"Varmeinnsatser",ST/"step_02.png",["4 × M3 varmeinnsats"],
 ["Loddebolt 200–220 °C med flat spiss.","Sett en innsats oppå hvert tårn, press den rett ned til den er plan med toppen.","La kjøle 30 s før du skrur i. Test med en M3-skrue."]))
S.append(step(3,"Hovedbryter og strøminngang",ST/"step_03.png",["KCD1 vippebryter","DC-099 kontakt","2 × flatstifthylse 4,8 mm","18 AWG rød 15 cm + 10 cm, svart 20 cm"],
 ["Lodd/krymp ledningene på begge FØR montering (se figur).","KCD1: trykk inn i utsparingen fra baksiden til den klikker. «I» opp.","DC-099: inn fra utsiden, mutter innvendig, stram for hånd + ¼ omdreining."],
 closeup(ST/"close_kcd1.png","Ledninger på KCD1 og DC-099. Ledningene legges løst innover i kassen foreløpig.")))
S.append(step(4,"USB-C og AUX",ST/"step_04.png",["USB-C panelflens med micro-USB-kabel","PJ392 3,5 mm jack","2 × M2,5 × 6","Skjermet kabel 20 cm"],
 ["Lodd skjermet kabel på jacken: leder 1 → tip, leder 2 → ring, skjerm → sleeve (den lange tungen). Krymp.","USB-C: fra innsiden, flensen ut gjennom det rektangulære hullet; skru ørene fast med M2,5 × 6 (forbor 2 mm).","Jack: inn fra utsiden, mutter innvendig."]))
S.append(step(5,"Høyttalerterminaler",ST/"step_05.png",["4 × bananterminal (2 røde, 2 svarte)","18 AWG rød 2 × 15 cm, svart 2 × 15 cm"],
 ["Rød ved x −30 og −65, svart ved x −45 og −80 (sett bakfra: R-paret til venstre for L-paret).","Isolasjonsskive på begge sider av veggen. Stram mutteren innvendig.","Lodd 18 AWG på loddetungen innvendig (rød på rød, svart på svart).","Mål med multimeter: ingen kontakt mellom noen av de fire terminalene."],
 closeup(ST/"close_banana.png","Bananplugger på høyttalerkabelen (den andre enden går til høyttaleren).")))
S.append(step(6,"OLED-kortet innvendig",ST/"step_06.png",["OLED 2,42\" SSD1309","4 × M2 avstandsstykke 6 mm + mutter","7 × Dupont/ledning 20 cm"],
 ["Lodd 7 ledninger på OLED-en: VCC, GND, SDA, SCL, RES, DC→GND, CS→GND.","Skru avstandsstykkene i kortets hjørnehull.","Hold kortet mot innsiden av frontveggen med glasset sentrert i vinduet (x = −30). En dråpe superlim/VHB under hvert avstandsstykke, trykk på plass.","Glasset skal ligge 1–2 mm bak veggen – ikke presse mot akrylet."]))
S.append(step(7,"Akryl og frontplate",ST/"step_07.png",["Akryl 70 × 38 × 2 mm","Frontplate (v2_frontplate.stl)","4 × M3 × 8 senkskrue"],
 ["Ta folien av én side av akrylet og legg det i forsenkningen på baksiden av frontplaten.","Hold platen mot fronten, sett de fire senkskruene i hjørnene og skru rett i veggens 2,6 mm-hull.","Stram kryssvis til platen ligger an – ikke mer, plasten gjenger seg selv."]))
S.append(step(8,"Knappene",ST/"step_08.png",["16 mm POWER-knapp","4 × 12 mm LED-knapp","4 ledninger 20 cm per knapp (22 AWG / Dupont)"],
 ["Lodd fire ledninger på hver knapp FØR montering (se figur) og merk dem med tape: P / A / B / X / U.","POWER i hullet ved x −80, mutter innvendig. Drei så strømsymbolet står rett.","AIRPLAY øverst venstre, BT øverst høyre, AUX nederst venstre, USB nederst høyre. Mutter innvendig."],
 closeup(ST/"close_button.png","Pinnene på 12/16 mm-knappene og hvor hver ledning går.")))
S.append(step(9,"Encoder og knott",ST/"step_09.png",["KY-040 encoder","Knott 30 × 17 mm","5 × Dupont hunn–hunn"],
 ["Legg KY-040-kortet i utsparingen på innsiden ved x 70 med akselen ut gjennom hullet. Mutter utvendig.","Sett knotten på D-akselen, 1 mm fra platen, stram settskruen mot flaten på akselen.","Koble Dupont på pinnelisten (se figur). Prøv alle knappene – de skal gå fritt og klikke tydelig."],
 closeup(ST/"close_encoder.png","KY-040: fem pinner til Pi-en.")))
S.append(step(10,"Forsterker (A) og Pi (B)",ST/"step_10.png",["XH-M562 forsterker","Pi Zero 2 W med SD-kort","2 × M3 × 6, 4 × M2,5 × 6"],
 ["A: forsterkeren på de to stolpene til høyre, pinnelisten (IN / SP / VCC) mot bakveggen. 2 × M3 × 6.","B: Pi-en på de fire stolpene bak til venstre, micro-USB-portene mot bakveggen, SD-kortet mot sideveggen. 4 × M2,5 × 6.","<b>USB-isolator:</b> USB-C-flensens kabel → isolatorens inngang; isolatorens utgang → Pi-ens innerste micro-USB (USB, ikke PWR). Isolatoren får egen 5 V på Pi-siden fra buck OUT (jumper/terminal på kortet). VHB ved Pi-en."]))
S.append(step(11,"Små kort med VHB-tape",ST/"step_11.png",["C DAC · D buck · E relékort · F 2 × MOSFET-kort · G 2 × X9C","VHB-tape, nylon-avstandsstykker"],
 ["Lodd alle ledninger på modulene på bordet før de festes.","E relékort midt bak, skruterminalene mot forsterkeren. D buck i hjørnet ved DC-099.","C DAC foran Pi-en med pinnene mot Pi-en. G X9C × 2 side om side midt i kassen, rett foran forsterkerens IN-pinner.","F: MOSFET-kort 1 foran til høyre, kort 2 stablet oppå med nylon-avstandsstykker.","VHB: trykk hardt i 10 s, ikke flytt etterpå. Isolasjonstape under Pi og DAC hvis de ligger nær et tårn."]))
S.append(step(12,"24 V og 5 V",ST/"step_12.png",["18 AWG rød/svart","22 AWG rød/svart","Sikringsholder + 5 A","2200 µF / 35 V kondensator"],
 ["<b>Sikring:</b> sikringsholderen i den røde ledningen rett etter DC-099 senter (+), før KCD1.","<b>24 V:</b> DC-099 senter (+) → sikring → KCD1 pinne 1. KCD1 pinne 2 → relé COM3 <i>og</i> buck IN+. Relé NO3 → forsterker VCC.","DC-099 hylse (−) → forsterker GND, buck IN− og relékortets GND.","<b>Kondensator:</b> 2200 µF rett på forsterkerens VCC/GND-terminal, stripen (−) mot GND, kortest mulige bein.","<b>Mål:</b> slå på hovedbryteren med adapteren i – buck OUT skal vise 5,0 V. Slå av igjen.","<b>5 V (22 AWG):</b> buck OUT+/− → Pi pinne 2/6, relékort VCC/GND, MOSFET-kort VCC/GND, og én samleledning til alle LED-ringenes +."]))
S.append(step(13,"Høyttalerledninger",ST/"step_13.png",["De fire 18 AWG-ledningene fra terminalene"],
 ["Forsterker SPR+ / SPR− → høyre rød / svart terminal.","Forsterker SPL+ / SPL− → venstre rød / svart terminal.","Aldri koble SPL− og SPR− sammen eller til jord – forsterkeren er bro-koblet.","Klem en ferrittklips rundt hvert høyttalerpar like innenfor terminalene.","Legg 24 V- og høyttalerledningene langs høyre side, fest med kabelstrips."]))
S.append(step(14,"Lydveien",ST/"step_14.png",["Skjermet kabel","X9C-modulenes VH/VW/VL-ledninger"],
 ["AUX tip/ring → relé NO1 / NO2. DAC L/R → relé NC1 / NC2.","Relé COM1 → X9C-A VH, relé COM2 → X9C-B VH.","X9C-A VW → forsterker INL, X9C-B VW → INR. Begge VL → forsterker GND (IN-siden).","Skjermen i lydkablene til GND <b>bare</b> i forsterker-enden."],
 closeup(ST/"close_audio.png","Signalvei fra AUX/DAC via relé og digitalpot til forsterkeren.")))
S.append(step(15,"Signal fra Pi-en",ST/"step_15.png",["Dupont hunn–hunn 20 cm","Knappenes og encoderens ledninger"],
 ["Følg pinnekartet: OLED (3/5/7), DAC (12/35/40 + 4/6), knapper (29/31/32/33/36 + GND), encoder (16/18/22 + 1/9).","MOSFET-kort 1 IN1–IN4 ← Pi 26/24/21/19. Kort 2 IN1 ← Pi 23. GND på signalsiden → Pi GND.","Relé IN1 + IN2 brus sammen ← Pi 15. Relé IN3 ← Pi 13.","X9C INC / U/D / CS ← Pi 37 / 8 / 10 (begge modulene parallelt). X9C VCC/GND ← Pi 5 V/GND."],
 closeup(ST/"close_header.png","Pi Zero 2 W: alle 40 pinner og hva som kobles hvor.","close tall")+closeup(ST/"close_mosfet.png","MOSFET-kort 1: fire inngangsringer. Kort 2 brukes bare til POWER-ringen (PWM).")))
S.append(step(16,"Test, lokk og montering",ST/"step_16.png",["Lokk (v2_lid.stl)","4 × M3 × 8","4 × treskrue 4 × 25","Gummiføtter (hvis den skal stå)"],
 ["<b>Test i åpen kasse</b> med høyttalere og volum 0: hovedbryter på → POWER-ring lyser, oppstartsbilde, relé 3 klikker. Trykk gjennom kildene; spill AirPlay og vri volumet sakte opp. Hold AIRPLAY 2 s → parring. USB: PC-en ser «UAC2 Gadget». AUX: relé 1+2 klikker.","Lokket på, 4 × M3 × 8 kryssvis. Ingen ledninger i klem.","Under pulten: hold lokket mot undersiden (front mot deg, 2–3 cm inn), merk slissene, forbor 3 mm, skru lokket fast med treskruene. Heng kassen i lokket og skru M3-skruene fra undersiden.","Kabler til adapter, høyttalere og PC bakover gjennom kabelutsparingen."]))

S.append("""<section class="plain"><h2>Daglig bruk</h2><table><tr><th>Handling</th><th>Gjør</th></tr>
<tr><td>Velg kilde</td><td>trykk AIRPLAY / BT / AUX / USB – ringen lyser på aktiv</td></tr><tr><td>Volum</td><td>vri knotten; trykk = mute</td></tr><tr><td>Standby</td><td>kort trykk POWER; kort trykk igjen = på</td></tr>
<tr><td>Omstart</td><td>hold POWER 3 s</td></tr><tr><td>Bluetooth-parring</td><td>hold AIRPLAY 2 s; synlig som «Pultforsterker»</td></tr><tr><td>Helt av</td><td>hovedbryter bak</td></tr></table>
<h2>Feilsøking</h2><table><tr><th>Symptom</th><th>Sjekk</th></tr>
<tr><td>Skjermen svart</td><td><code>i2cdetect -y 1</code> viser 3c? RES på GPIO 4? <code>systemctl status oled-display</code></td></tr>
<tr><td>Lyd på AUX, ikke AirPlay/BT/USB</td><td>DAC-broer (SCK→GND), <code>aplay -l</code>, relé 1+2 i NC</td></tr>
<tr><td>Ingen lyd på AUX</td><td>relé 1+2 klikker? jackens sleeve til jord</td></tr>
<tr><td>Lyd i én kanal</td><td>X9C for den kanalen: VH/VW/VL, INC/UD/CS</td></tr>
<tr><td>Volum virker ikke</td><td><code>journalctl -u ki-amp</code>; serial console av (GPIO 14/15)</td></tr>
<tr><td>Brum på AUX/USB</td><td>jordsløyfe mot PC: ground-loop-isolator / USB-isolator</td></tr>
<tr><td>Pi starter på nytt</td><td>buck under 4,8 V under last – tykkere 5 V-ledning</td></tr>
<tr><td>LED-ring lyser ikke</td><td>MOSFET-jumper 3.3V, ring + på 5 V, − på OUT−</td></tr>
<tr><td>Ikke funnet i HA/Homey</td><td><code>curl http://pultamp.local:8765/api/status</code>; samme nett som HA</td></tr></table></section>""")

CSS="""
@page{size:A4;margin:14mm 14mm 16mm 14mm}
:root{--ink:#1b1c20;--mute:#6b6a66;--line:#d9d7d1;--acc:#e8562a;--soft:#f4f3ef}
*{box-sizing:border-box}body{font-family:Inter,"Liberation Sans",sans-serif;color:var(--ink);font-size:10.3pt;line-height:1.45;margin:0}
code{font-family:"DejaVu Sans Mono",monospace;font-size:8.6pt;background:var(--soft);padding:0 3px;border-radius:3px}
section{page-break-after:always}section:last-child{page-break-after:auto}
.cover{height:262mm;display:flex;flex-direction:column;justify-content:space-between;border-left:6px solid var(--acc);padding-left:10mm}
.cover .kicker{font-size:10pt;letter-spacing:.14em;text-transform:uppercase;color:var(--mute)}
.cover h1{font-size:40pt;line-height:1.02;margin:5mm 0 4mm;font-weight:700;letter-spacing:-.02em}.cover .sub{font-size:13pt;color:var(--mute);max-width:130mm}
.cover .hero{width:160mm;display:block;border-radius:4px}
.cover .spec{display:grid;grid-template-columns:repeat(3,1fr);gap:6mm;border-top:1px solid var(--line);padding-top:5mm;font-size:9.5pt}.spec b{display:block;font-size:8pt;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);margin-bottom:1mm}
.head{display:flex;align-items:center;gap:5mm;border-bottom:2px solid var(--ink);padding-bottom:2mm;margin-bottom:4mm}
.n{display:inline-flex;align-items:center;justify-content:center;width:16mm;height:16mm;border-radius:50%;background:var(--acc);color:#fff;font-size:22pt;font-weight:800;flex:none}
h2{font-size:20pt;margin:0;letter-spacing:-.01em}.plain h2{font-size:16pt;margin:4mm 0 3mm}
.row{display:grid;grid-template-columns:1fr 50mm;gap:5mm;align-items:start}
.pic img{width:100%;border:1px solid var(--line);border-radius:4px;background:#fff}
.parts{background:var(--soft);border-radius:6px;padding:3mm 4mm;font-size:9pt}.parts b{display:block;font-size:8pt;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);margin-bottom:2mm}
.parts ul{margin:0;padding-left:4mm}.parts li{margin-bottom:1.2mm}
ol.do{margin:4mm 0 0;padding-left:6mm;font-size:10.5pt}ol.do li{margin-bottom:2mm;padding-left:1mm}ol.do li::marker{color:var(--acc);font-weight:700}
figure.close{margin:4mm 0 0;page-break-inside:avoid;border:1px solid var(--line);border-radius:4px;padding:2mm 3mm;background:#fff}figure.close img{width:100%;display:block;max-height:80mm;object-fit:contain}
figure.tall img{max-height:120mm}
figcaption{font-size:8.5pt;color:var(--mute);margin-top:1.5mm}
.legend{display:grid;grid-template-columns:1fr 1fr;gap:3mm 6mm;margin:3mm 0 5mm;font-size:9.5pt}.legend .n{width:9mm;height:9mm;font-size:12pt;margin-right:2mm;vertical-align:middle}
.legend .arrow{color:var(--acc);font-weight:800;font-size:16pt;margin-right:2mm}.legend .box{background:var(--soft);padding:1mm 2mm;border-radius:3px;font-size:8pt;text-transform:uppercase;letter-spacing:.1em;color:var(--mute);margin-right:2mm}.legend .dim{color:#9a9a9e}
.warn{border-left:3px solid var(--acc);background:var(--soft);padding:3mm 4mm;margin:3mm 0 5mm}
ul.partlist{columns:2;column-gap:8mm;margin:0;padding:0;list-style:none;font-size:9.3pt}ul.partlist li{border-bottom:1px solid var(--line);padding:1.2mm 0;break-inside:avoid}ul.partlist span{display:inline-block;width:10mm;color:var(--acc);font-weight:700;font-variant-numeric:tabular-nums}
.muted{color:var(--mute);font-size:9pt}
table{border-collapse:collapse;width:100%;margin:2mm 0 5mm;font-size:9.3pt}th{text-align:left;font-size:8pt;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);border-bottom:1.5px solid var(--ink);padding:1.5mm 2mm}td{padding:1.6mm 2mm;border-bottom:1px solid var(--line);vertical-align:top}tr:nth-child(even) td{background:var(--soft)}
"""
page=f'<!doctype html><html lang="nb"><head><meta charset="utf-8"><title>Pultforsterker – Bildeveiledning</title><style>{CSS}</style></head><body>{"".join(S)}</body></html>'
out=K/"KI_Pultforsterker_Bildeveiledning.pdf"; out.with_suffix(".html").write_text(page)
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(); await pg.set_content(page); await pg.emulate_media(media="print")
        await pg.pdf(path=str(out),format="A4",print_background=True,display_header_footer=True,header_template="<div></div>",
            footer_template='<div style="width:100%;font-family:Inter,sans-serif;font-size:7.5pt;color:#6b6a66;padding:0 14mm;display:flex;justify-content:space-between"><span>Pultforsterker – Bildeveiledning</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
            margin={"top":"14mm","bottom":"16mm","left":"14mm","right":"14mm"})
        await b.close()
asyncio.run(main()); print("ok")
