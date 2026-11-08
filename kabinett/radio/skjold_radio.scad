// Skjold Radio – bordradio med skjerm, seks favorittknapper, navigasjonshjul og volumknott. Parametrisk OpenSCAD.
// Eget Skjold-design: en lav, liggende bordradio der alt vender mot deg. Den loddrette fronten er delt i to av en
// tynn, loddrett gullist: til venstre en grill trukket med mørkt høyttalerstoff foran ett 3″-element (mono), til høyre et rolig
// betjeningspanel i tre lag – skjermen øverst, favoritt 1–6 i én rad rett under, og nederst av/på, volumknotten og
// det store gullhjulet. Myke hjørner (R14) sett forfra som Node/Røst, faset frontkant, lys (eller matt sort) kropp,
// mørk grill og knapper, gull hjul, volumknott og list, og SKJOLD preget over skjermen. Symbolene på knappene
// (1–6, av/på ⏻, høyttaler på volum, spill/pause på hjulet) er innfelt i flukt i kontrastfarge (flerfarget med CFS).
// Bakdelen er myk: kassa smalner svakt bakover og rundes av med R26 over toppen og ned langs sidene (maks 42° heling).
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater: x = bredde (0 … W), y = dybde (0 = fronten, D = bak), z = høyde (0 = innsiden av gulvet).
// Bruk:  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_radio.scad
// part:  kropp | bak | kammer | lokk | grill | brakett | list | knott | volum | knapp (6 favoritter + av/på) |
//        knapp_symbol | knott_symbol | volum_symbol (innfelte symboler i kontrastfarge, samme plassering som delen) |
//        samlet | eksplodert | A_<del> (montert stilling, for sjekk_modell.py)
// STL-ene eksporteres liggende slik de skal printes (FDM) – samme filer kan bestilles i resin/MJF (se LES_MEG.md).
// Alle deler er åpne skall (ingen lukkede hulrom), så resin renner ut uten egne dreneringshull.

part = "samlet";
ex = 0;                          // eksplosjonsavstand (eksplodert visning)
farge = "lys";                   // lys | mork
skjerm = "glass";                // glass | nokkel (aktivt område i ren magenta, så lag_render.sh kan legge inn et skjermbilde)
skjermE = 0;                     // part="skjermflate": samme eksplosjonsavstand som bildet (eksplodert = 40)
$fn = 64;

// ---------- ytre mål ----------
W = 240; D = 115; H = 137;       // bredde, dybde (125 → 115: lydkammeret og Pi-en får fortsatt plass), høyde over gulvets innside (utvendig høyde H + t = 140)
R = 14;                          // hjørnene sett forfra (alle fire)
t = 3.0;                         // vegg og gulv (≥ 2 mm for resin/MJF; 7 linjer à 0,42 mm på FDM)
c = 2.5;                         // fas rundt frontkanten
bkT = 3;                         // bakplata (ligger inne i åpningen bak, flukt med kanten)

// Profilen sett forfra (x, z), forskjøvet o innover
module prof(o = 0) { translate([o, -t + o]) rrect(W - 2*o, H + t - 2*o, max(1, R - o)); }
// ---------- avrundet og avsmalnende bakparti ----------
// Fronten (R14 og fasen) er som før. Bakover smalner kassa svakt (kvadratisk, sL) og rundes til slutt av med en stor
// radius Rb på toppen og sidene. Buen stopper ved aB = 42°, så ingen flate heller mer enn ca. 45° når kroppen printes
// med fronten ned. Toppen senkes s(y), sidene trekkes inn s(y)/2 og de øvre hjørnene vokser til R + s/2. Gulvet og de nedre
// hjørnene (R14) er uendret, så radioen står stødig og innmaten på gulvet (kammerørene, forsterkeren) får plass.
sL = 6; Rb = 26; aB = 42;
Lb = Rb * sin(aB);                          // buens lengde i dybden (17,4 mm)
function s_av(y) = y <= c ? 0 : sL * pow((y - c) / (D - c), 2)
  + (y > D - Lb ? Rb - sqrt(Rb*Rb - pow(y - (D - Lb), 2)) : 0);
sD = s_av(D);                               // 12,7 mm lavere og 2 × 6,35 mm smalere helt bak
Ys = concat([for (i = [0:10]) c + (D - Lb - c) * i / 10], [for (i = [1:8]) D - Lb + Lb * i / 8]);
module profil(s, o = 0) {   // tverrsnittet (x, z) med innsving s, forskjøvet o innover
  rt = max(1, R + s/2 - o); rb = max(1, R - o);
  x0 = s/2 + o; x1 = W - s/2 - o; z0 = -t + o; z1 = H - s - o;
  hull() {
    for (x = [x0 + rb, x1 - rb]) translate([x, z0 + rb]) circle(rb);
    for (x = [x0 + rt, x1 - rt]) translate([x, z1 - rt]) circle(rt);
  }
}
module skall(o, y0) {   // det avrundede skallet fra y0 bakover (o = 0: utsiden, o = t: innsiden)
  hull() {
    ext_y(y0, y0 + 0.01) profil(0, o);
    for (y = Ys) if (y > y0) ext_y(y - 0.01, y) profil(s_av(y), o);
    if (o > 0) ext_y(D, D + 1) profil(sD, o);
  }
}
module ext_y(y0, y1) { translate([0, y1, 0]) rotate([90, 0, 0]) linear_extrude(y1 - y0) children(); }   // 2D (x, z) → y0 … y1
// Lokal ramme på frontflaten: u = x, v = z, w ut av fronten (w = 0 = frontflaten, w = −t = innsiden av frontveggen).
module front_ramme() { rotate([90, 0, 0]) children(); }

// ---------- høyttaler og lydkammer (mono: ett 3″-element i ett lukket kammer bak venstre halvdel) ----------
drvCut = 72;  drvF = 86;  drvFT = 4;      // 3″ fullrange (Dayton Audio RS75-4): utsparing, rammens Ø og tykkelse – mål ditt element
drvPCD = 82;                              // skruehullsirkel
kX0 = 22;  kW = 86;                       // kammer: x 22 … 108
kY0 = t + 5.6;  kD = 92;                  // baffelens forside 5,6 mm bak fronten (plass til grill, stoff og elementrammen)
kZ0 = 0;  kH = 124;                       // står på gulvet, 124 mm høyt
kT = 2.8;  baffT = 7;                     // kammervegg og baffel
drvX = kX0 + kW/2;  drvZ = kZ0 + kH/2;    // elementet midt på baffelen
kOff = kT + 2.5;                          // innpressmutter-tårnene for lokket ligger langs sideveggene (smelter inn i veggene)
kBx = [kX0 + kOff, kX0 + kW - kOff];
kBz = [kZ0 + kOff, kZ0 + kH/2, kZ0 + kH - kOff];
kOre = 8;                                 // ører langs gulvet på utsiden (skrues fra undersiden)
kOreY = [kY0 + 12, kY0 + kD - 12];
// netto volum ≈ 80,4 × 85 × 118,4 mm − tårn og element ≈ 0,75 l (lukket, mono)

// ---------- grill (venstre halvdel av fronten) ----------
gX0 = 14;  gX1 = 114;  gZ0 = 8;  gZ1 = 126;  gR = 6;   // grillåpningen: 100 × 118 mm, samme marg oppe og nede
gT = 3.0;  gFl = 2.5;                      // grillens tykkelse = veggen, flens bak
// Grillen er en printet ramme trukket med akustisk høyttalerstoff. Stoffet legges over forsiden, brettes rundt kanten
// og limes på baksiden av flensen. Rammen er 0,8 mm mindre enn åpningen rundt hele, så stoffet (≤ 0,5 mm) får plass.
// Som på Skjold Røst står grillen 3 mm ut fra fronten (Røst: 2,4 mm plate + 0,6 mm luft = 3 mm). Forkanten er rundet
// (R 1,5), så stoffet legger seg mykt rundt den utstikkende kanten. Gullista og panelet ligger i flukt som før.
stM = 7;                                   // rammekant rundt vinduene (ribbene mot baffelen sitter oppe og nede)
gUt = 3.0;                                 // grillen (med stoffet) stikker 3 mm ut fra fronten, som på Røst
gRk = 1.5;                                 // rundet forkant på rammen (stoffet får R 2 utvendig)
stTyk = 0.5;                               // stoffets tykkelse (illustrasjon)
gF = -gUt + stTyk;                         // rammens forside (y = −2,5): stoffet utenpå havner 3 mm foran fronten
stBar = [44, 82];                          // to vannrette stag som holder stoffet stramt (z, midt i staget), 3 mm brede
ribX = [drvX - 15, drvX + 15];             // ribber som holder grillen mot baffelen
// ---------- loddrett gullist mellom grill og panel ----------
lX0 = 118;  lZ0 = gZ0;  lH = 3.5;  lDyp = 1.2;   // spor i fronten (z 8 … 126), lista står 0,4 mm ut

// ---------- betjeningspanel (høyre halvdel av fronten) ----------
scrAW = 96;  scrAH = 56;                   // synlig vindu (4,3″ DSI 800×480, aktivt område ≈ 95 × 54)
scrGW = 106; scrGH = 68;                   // glass/LCD på modulen (lomme bak frontveggen) – mål din skjerm!
scrX = 175;  scrZ = 98;                    // vinduets senter: vindu x 127 … 223, z 70 … 126 (flukt med grillens overkant)
scrB = [[-57, -20], [57, -20], [-57, 20], [57, 20]];   // skruetårn på hver side av modulen (brakett)
btnZ = 57.5; btnP = 16; btnX0 = scrX - 2.5*btnP;   // favoritter 1–6: rad rett under skjermen (x 135 … 215)
capFlat = 3.3;                             // flensens rette overkant 3,3 mm over aksen
capD = 11; capHole = 11.6; capUp = 0.8; capFl = 15; capFlT = 1.0;
kortX = [btnX0 - 12, btnX0 + 5*btnP + 12]; // tårn for knappekortet (hullkort ca. 110 × 16 mm)
botZ = 28;                                 // nederste rad: av/på, volum og hjulet
pwX = btnX0;                               // av/på under favoritt 1
pwKort = [pwX - 12, pwX + 12];             // tårn for av/på-kortet (lite hullkort ca. 30 × 16 mm)
volX = 161; volZ = botZ;                   // volumknott
volD = 22; volH = 13;
whD = 42;  whH = 15;                       // navigasjonshjul (EC11 med trykk) nede til høyre, flukt med vinduets høyre kant
whX = scrX + scrAW/2 - whD/2; whZ = botZ;
logoZ = 131.6;                             // SKJOLD preget over skjermen
ec11 = 7.2;                                // EC11 M7-gjenge
// symbolene er innfelt i flukt: egne legemer (innlegg) i en lomme med samme form, printes i kontrastfarge (CFS)
symD = 0.6;                                // innleggsdybde (3 lag à 0,2 mm)
knappIkon = ["1", "2", "3", "4", "5", "6", "av"];
// ---------- fester ----------
ins = 4.0; insD = 6.0; boss = 8.4; m3 = 3.4; m3k = 6.4;
// tårn for bakplata (x, z) og retningen ut mot veggen: plassert i den smalere bakåpningen, 4,4 mm fra innerveggen.
// Oppe i hjørnene på diagonalen, nede på sideveggen over kammerørene, og ett midt i toppen.
bkX0 = sD/2 + t; bkX1 = W - sD/2 - t; bkZ1 = H - sD - t; bkRt = R + sD/2 - t;
bkD = (bkRt - 4.4) / sqrt(2);
bakB = [[bkX0 + 4.4, R, [-1, 0]], [bkX1 - 4.4, R, [1, 0]],
        [bkX0 + bkRt - bkD, bkZ1 - bkRt + bkD, [-1, 1]/sqrt(2)], [bkX1 - bkRt + bkD, bkZ1 - bkRt + bkD, [1, 1]/sqrt(2)],
        [W/2, bkZ1 - 4.4, [0, 1]]];
bakY0 = 44;                                // tårnene starter 44 mm bak fronten (avstiverne skrås av foran, klar av skjermbraketten)
fotXY = [[30, 22], [W - 30, 22], [30, D - 22], [W - 30, D - 22]];             // selvklebende gummiføtter Ø 12
// ---------- helling: fronten lener 6° bakover, så skjermen og knappene peker litt opp mot ansiktet ----------
// Kassa er en kile: alt over gulvet er som før (kassas eget koordinatsystem), og under gulvet er det et skjørt som
// fortsetter yttersidene ned til bordplanet. Bordplanet går gjennom bakre underkant og ligger hS = D·tan(6°) ≈ 12,1 mm
// under gulvet foran. Inni er alt uendret; bare hele radioen står 6° bakover (plassert()).
tilt = 6;
hS = D * tan(tilt);
module over_bord(o = 0) {   // alt over bordplanet (o mm over det), i kassas koordinater
  translate([0, D, -t]) rotate([tilt, 0, 0]) translate([-50, -400, o]) cube([W + 100, 600, 400]);
}
module plassert() { translate([0, D, -t]) rotate([-tilt, 0, 0]) translate([0, -D, t]) children(); }   // står på bordet
// Raspberry Pi 4 på baksiden av skjermbraketten (85 × 56, hull 58 × 49), sentrert bak skjermen
piH = [[-29, -24.5], [29, -24.5], [-29, 24.5], [29, 24.5]];
piSt = 5;                                  // avstandsstykker
// ---------- bak ----------
dcD = 8.2; jackD = 6.4; usbW = 10; usbH = 4.4;
bakKZ = 22;                                // kontaktene (DC, linje ut, USB-C) nede til høyre, bak forsterkeren
dcX = 128; jackX = 144; usbX = 166; usbHull = 28;   // DC-022, PJ-392 og USB-C-skjøten (2 × M3, 28 mm mellom hullene – mål din)

// ---------- innmaten (referansedeler, kjøpes – ikke printet; mål dine egne kort) ----------
// Kort uten sikre hullmål ligger på stolper og holdes med strips; kortmålene er variabler her.
pcb = 1.6;
tact = [6, 6, 4.3];                        // taktbryter 6 × 6 × 4,3 (høyde over kortet med stempel), vandring 0,25 mm
favKort = [110, 16];                       // hullkort for favoritt 1–6 (x 120 … 230), på tårnene i kortX
pwKortM = [30, 16];                        // hullkort for av/på (x 120 … 150)
kortY = t + 7;                             // kortenes forside (y 10): tårnene er 7 mm
ecBody = [12, 12, 6.5];                    // EC11: hus 12 × 12, 6,5 mm fra kortet til gjengeskulderen
ecKort = [20, 34];                         // eget lite hullkort per dreieknapp, to tårn 13 mm over og under aksen
ecT = 13;
ecY = t + ecBody[2];                       // kortet ligger an mot tårnene i y 9,5; huset står mot frontens innside (tar trykket)
// TPA3116D2 2 × 50 W (XH-M189-type): 83 × 50 × 20 mm, 4 × Ø3 ca. 3,5 mm fra hjørnene (76 × 43) – på gulvet over spaltene
forstP = [128, 38]; forstM = [83, 50, 20]; forstH = 5; forstHull = 3.5;
// PCM5102A (GY-PCM5102): 32 × 17 mm, uten festehull – på fire stolper, holdes med strips
dacP = [118, 14]; dacM = [32, 17]; dacH = 4;
// 5 V / 5 A nedtrapper (XL4015-type, ca. 54 × 23 × 18) og relémodul (ca. 50 × 26 × 19) på innsiden av bakplata,
// i hjørneholdere (5 mm høye) og med strips. (x, z) = nedre venstre hjørne sett bakfra i x
buckP = [118, 46]; buckM = [54, 23, 18];
releP = [176, 45]; releM = [50, 26, 19];
holdH = 5;
// strips-fester (bredde 8, for strips ≤ 3,6 × 1,8 mm): på gulvet langs høyre side og ved DAC-en
stripsGulv = [[134, 9.5], [220, 30], [220, 60], [220, 95]];
ventGulv = [136, 8, 9, 40, 46];            // luftespalter i gulvet under forsterkeren: x0, deling, antall, y0, lengde
                                           // (26 mm fri gulvflate bak spaltene til kontaktene i bakplata)

// ---------- farger ----------
lys = farge == "lys";
c_kropp = lys ? [0.93, 0.92, 0.90] : [0.13, 0.13, 0.14];
c_grill = lys ? [0.17, 0.17, 0.18] : [0.30, 0.30, 0.31];
c_stoff = lys ? [0.25, 0.24, 0.23] : [0.20, 0.20, 0.21];   // høyttalerstoff, varm antrasitt
c_vev   = lys ? [0.33, 0.32, 0.30] : [0.27, 0.27, 0.28];
c_gull  = [0.85, 0.62, 0.25];
c_knapp = lys ? [0.18, 0.18, 0.19] : [0.85, 0.62, 0.25];
c_sym_knapp = lys ? c_gull : [0.16, 0.16, 0.17];   // symbolene i knappehettene (gull på mørk hette, mørk på gull hette)
c_sym_knott = [0.16, 0.16, 0.17];                   // symbolene i hjulet og volumknotten (mørk på gull)
c_glass = [0.05, 0.07, 0.10];
c_inne  = [0.40, 0.40, 0.42];

// ---------- grunnformer ----------
module rrect(w, d, r) { translate([r, r]) offset(r) square([w - 2*r, d - 2*r]); }
module ytre() { hull() { ext_y(0, 0.01) prof(c); skall(0, c); } }   // fas rundt frontkanten, avrundet bak
module front_hull(o = 0) {   // grillåpningen sett forfra (x, z)
  offset(-o) hull() for (x = [gX0 + gR, gX1 - gR], z = [gZ0 + gR, gZ1 - gR]) translate([x, z]) circle(gR);
}
module list2d(o = 0) { translate([lX0 + o, lZ0 + o]) rrect(lH - 2*o, gZ1 - gZ0 - 2*o, lH/2 - o - 0.05); }

// ---------- festeelementer som printes på gulvet i kroppen (kroppen printes med fronten ned, så gulvet står loddrett:
// alt som stikker opp fra gulvet er dråpeformet sett ovenfra, med spissen mot fronten, så undersiden heller 45°) ----------
module drape2d(p, d) { hull() { translate(p) circle(d = d); translate(p - [0, d/2 * sqrt(2)]) square(0.01, center = true); } }
module gulvstolpe(p, h, d = 6, hull_d = 0) {
  difference() {
    translate([0, 0, -0.01]) linear_extrude(h + 0.01) drape2d(p, d);
    if (hull_d > 0) translate([0, 0, h - 6]) linear_extrude(7)   // skruehull med spiss tak (mot +y), M3 selvgjengende
      hull() { translate(p) circle(d = hull_d); translate(p + [0, hull_d/2 * sqrt(2)]) square(0.01, center = true); }
  }
}
module gulvstrips(p) {   // strips-feste: kloss med tunnel på tvers (langs x) og spisst tak
  difference() {
    translate([0, 0, -0.01]) linear_extrude(4.01) hull() { translate(p - [4, 2.5]) square([8, 5]); translate(p - [0, 6.5]) square(0.01, center = true); }
    translate([p[0] - 5, 0, 0]) rotate([90, 0, 90]) linear_extrude(10)
      polygon([[p[1] - 1.75, 1], [p[1] + 0.5, 1], [p[1] + 1.75, 1.9], [p[1] + 0.5, 2.8], [p[1] - 1.75, 2.8]]);
  }
}
function kort_hjorner(p, m, inn) = [for (u = [inn, m[0] - inn], v = [inn, m[1] - inn]) p + [u, v]];

// ---------- skjørtet under gulvet (kilen) ----------
// Yttersidene fortsetter rett ned til bordplanet (veggtykkelse t), og fire føtter (dråpeformet, spissen mot fronten)
// går fra gulvet ned til bordplanet med forsenkning for gummiføttene. Undersiden er åpen, så skruene i kammerørene
// og luftespaltene i gulvet er tilgjengelige og får luft. Printes med fronten ned uten støtte: skjørtet er en
// forlengelse av veggene, og bordplanet heller oppover i printretningen.
module ytre_kile() { intersection() { hull() { ytre(); translate([0, 0, -hS - 1]) ytre(); } over_bord(0); } }   // kassa forlenget ned til bordet
module skjort() {
  intersection() {
    union() {
      difference() {
        ytre_kile();
        hull() { skall(t, t); translate([0, 0, -hS - 5]) skall(t, t); }
      }
      for (p = fotXY) translate([0, 0, -t - hS - 1]) linear_extrude(hS + 1.01) drape2d(p, 14);
    }
    over_bord(0);
    translate([-1, -1, -t - hS - 5]) cube([W + 2, D - bkT + 1, hS + 5 + t + R]);   // under gulvet og opp forbi de nedre hjørnene (R14), foran bakplata
  }
}

// ---------- kropp (ett skall: front, sider, topp og gulv; åpen bak; printes med fronten ned på platen) ----------
module kropp() {
  difference() {
    union() {
      difference() { ytre(); skall(t, t); }
      // tårn for bakplata (innpressmuttere bakfra), med kjegle foran så de printes uten støtte
      // Veggen smalner bakover, så hvert tårn får en avstiver ut til veggen. Under (mot fronten) skrås den av mot en spiss,
      // så den printes uten støtte (≤ 45°).
      for (p = bakB) intersection() {
        ytre();
        hull() {
          ext_y(bakY0, D - bkT) hull() { translate([p[0], p[1]]) circle(d = boss); translate([p[0], p[1]] + 30 * p[2]) circle(d = boss); }
          for (k = [0, 30]) ext_y(bakY0 - 12 - k, bakY0 - 11.99 - k) translate([p[0], p[1]] + k * p[2]) circle(d = 1);   // 45° ned mot veggen
        }
      }
      front_ramme() {
        for (p = scrB) translate([scrX + p[0], scrZ + p[1], -t - 6]) cylinder(d = 7, h = 7);      // skjermbrakett
        for (x = concat(kortX), z = [btnZ]) translate([x, z, -t - 7]) cylinder(d = 7, h = 8);   // knappekort
        for (x = pwKort) translate([x, botZ, -t - 7]) cylinder(d = 7, h = 8);                    // av/på-kort
        for (k = [[volX, volZ], [whX, whZ]], s = [-1, 1])                                         // dreieknappkortene
          translate([k[0], k[1] + s*ecT, -ecY]) cylinder(d = 7, h = ecY - t + 0.01);
      }
      // gulvet: stolper for forsterkeren (M3) og DAC-en, og strips-fester
      for (q = kort_hjorner(forstP, forstM, forstHull)) gulvstolpe(q, forstH, 6.5, 2.6);
      for (q = kort_hjorner(dacP, dacM, 2.5)) gulvstolpe(q, dacH, 5);
      for (q = stripsGulv) gulvstrips(q);
      render(convexity = 4) skjort();
    }
    for (p = bakB) translate([p[0], D - bkT - insD, p[1]]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD + 0.1);
    translate([-1, D - bkT, -t - 1]) cube([W + 2, bkT + 1, H + t + 2]);   // kroppen slutter der bakplata begynner
    // grillåpningen og fals for grillens flens på innsiden
    ext_y(-1, t + 1) front_hull();
    ext_y(t - 0.6, t + 1.0) offset(gFl) front_hull();   // (dyp nok til flensen med stoffet brettet rundt)
    // spor for gullista
    ext_y(-1, lDyp) list2d();
    front_ramme() {
      // skjermvindu med fas, og lomme for glasset bak
      translate([scrX - scrAW/2, scrZ - scrAH/2, -t - 1]) cube([scrAW, scrAH, t + 2]);
      translate([scrX - scrAW/2 - 1, scrZ - scrAH/2 - 1, -0.8]) cube([scrAW + 2, scrAH + 2, 1]);
      translate([scrX - scrGW/2 - 0.3, scrZ - scrGH/2 - 0.3, -t - 1]) cube([scrGW + 0.6, scrGH + 0.6, t - 0.2]);
      for (p = scrB) translate([scrX + p[0], scrZ + p[1], -t - 6.1]) cylinder(d = 2.2, h = 5);   // M2,5 selvgjengende
      // favoritt 1–6 og av/på
      for (i = [0:5]) translate([btnX0 + i*btnP, btnZ, -t - 1]) cylinder(d = capHole, h = t + 2);
      translate([pwX, botZ, -t - 1]) cylinder(d = capHole, h = t + 2);
      for (x = kortX) translate([x, btnZ, -t - 7.1]) cylinder(d = 2.2, h = 6);
      for (x = pwKort) translate([x, botZ, -t - 7.1]) cylinder(d = 2.2, h = 6);
      for (k = [[volX, volZ], [whX, whZ]], s = [-1, 1]) translate([k[0], k[1] + s*ecT, -ecY - 0.1]) cylinder(d = 2.2, h = 5);
      // hjulet og volumknotten
      for (k = [[whX, whZ, whD], [volX, volZ, volD]]) {
        translate([k[0], k[1], -t - 1]) cylinder(d = ec11, h = t + 2);
        translate([k[0], k[1], -0.6]) cylinder(d = k[2] + 3, h = 1);    // grunn ring under knotten
      }
      // logo SKJOLD preget over skjermen
      translate([scrX, logoZ, -0.6]) linear_extrude(1)
        text("SKJOLD", size = 4, font = "Liberation Sans:style=Bold", halign = "center", valign = "center", spacing = 1.4);
    }
    // gulvet: kammerørene (senkeskruer nedenfra), gummiføtter og lufting under forsterkeren
    for (x = [kX0 - kOre/2, kX0 + kW + kOre/2], y = kOreY)
      translate([x, y, -t - 1]) { cylinder(d = m3, h = t + 2); cylinder(d = m3k, h = 1 + 1.7); }
    for (p = fotXY) difference() {                                                     // 0,8 mm forsenkning for gummiføttene i bordplanet
      translate([p[0], p[1], -t - hS - 2]) cylinder(d = 12.6, h = hS + 2);
      over_bord(0.8);
    }
    for (i = [0:ventGulv[2] - 1]) translate([ventGulv[0] + i*ventGulv[1], ventGulv[3], -t - 1]) cube([3, ventGulv[4], t + 2]);
  }
}

// ---------- bakplate (DC, linje ut, USB-C og lufting; skrus i fem tårn) ----------
// Bakplata er de siste 3 mm av den avrundede kassa: kroppen slutter 3 mm før, og plata ligger an mot kanten utenpå
// og fortsetter formen uten spalte. En smal krage (1,5 mm) går inn i åpningen og sentrerer den, utenom tårnene.
yBak = D - bkT;
kragD = 1.5;
module bak_krage() {
  difference() {
    intersection() { skall(t + 0.5, t); translate([-1, yBak - kragD, -t - 1]) cube([W + 2, kragD + 0.01, H + t + 2]); }   // samme form som åpningen
    skall(t + 1.5, t);
    for (p = bakB) ext_y(yBak - kragD - 1, yBak + 1)
      hull() { translate([p[0], p[1]]) circle(d = boss + 1); translate([p[0], p[1]] + 30 * p[2]) circle(d = boss + 1); }
  }
}
module bak() {
  difference() {
    union() {
      intersection() { ytre_kile(); translate([-1, yBak, -t - hS - 1]) cube([W + 2, bkT, H + t + hS + 2]); }   // fortsetter kassas form (kilen)
      bak_krage();
      // hjørneholdere for nedtrapperen og releet (printes oppover fra bakplata), og strips-fester
      for (b = [[buckP, buckM], [releP, releM]]) {
        for (u = [0, 1], v = [0, 1]) let(c = [b[0][0] + u*b[1][0], b[0][1] + v*b[1][1]])
          difference() {
            translate([c[0] - (u ? 1.5 : 3), yBak - holdH - pcb - 1.5, c[1] - (v ? 1.5 : 3)]) cube([4.5, holdH + pcb + 1.5 + 0.01, 4.5]);
            translate([b[0][0] - 0.3, yBak - holdH - pcb - 2, b[0][1] - 0.3]) cube([b[1][0] + 0.6, pcb + 2, b[1][1] + 0.6]);
          }
        for (x = [b[0][0] + b[1][0]/2 - 4]) for (z = [b[0][1] - 7, b[0][1] + b[1][1] + 3])
          difference() { translate([x, yBak - 4, z]) cube([8, 4.01, 4]); translate([x - 1, yBak - 3, z + 1]) cube([10, 1.8, 2]); }
      }
    }
    for (p = bakB) translate([p[0], D - bkT - 1, p[1]]) rotate([-90, 0, 0]) {
      cylinder(d = m3, h = bkT + 2); translate([0, 0, bkT + 1 - 1.7]) cylinder(d1 = m3, d2 = m3k, h = 1.71);   // senkeskrue
    }
    translate([dcX, D - bkT - 1, bakKZ]) rotate([-90, 0, 0]) cylinder(d = dcD, h = bkT + 2);
    translate([jackX, D - bkT - 1, bakKZ]) rotate([-90, 0, 0]) cylinder(d = jackD, h = bkT + 2);
    translate([usbX - usbW/2, D - bkT - 1, bakKZ - usbH/2]) cube([usbW, bkT + 2, usbH]);
    for (s = [-1, 1]) translate([usbX + s*usbHull/2, D - bkT - 1, bakKZ]) rotate([-90, 0, 0]) cylinder(d = 3.2, h = bkT + 2);   // M3 for USB-skjøten
    for (i = [0:3]) translate([184 + i*7, D - bkT - 1, 10]) cube([4, bkT + 2, 26]);    // nede: forsterker (godt klar av tårnet i hjørnet)
    for (i = [0:8]) translate([128 + i*10, D - bkT - 1, 78]) cube([4, bkT + 2, 40]);   // oppe: Pi
  }
}

// ---------- lydkammer (mono, lukket) ----------
module kammer() {
  difference() {
    union() {
      difference() {
        translate([kX0, kY0, kZ0]) cube([kW, kD, kH]);
        translate([kX0 + kT, kY0 + baffT, kZ0 + kT]) cube([kW - 2*kT, kD, kH - 2*kT]);
      }
      // tårn for lokkets innpressmuttere – går hele veien fra baffelen (printes som søyler)
      for (x = kBx, z = kBz) translate([x, kY0 + 1, z]) rotate([-90, 0, 0]) cylinder(d = boss, h = kD - 1);
      // ører langs gulvet på utsiden, skrues fast nedenfra gjennom gulvet
      // (det venstre øret følger det avrundede hjørnet nede i kroppen bakover, med 0,2 mm klaring)
      intersection() { for (x = [kX0 - kOre, kX0 + kW]) translate([x, kY0, kZ0]) cube([kOre, kD, 8]); skall(t + 0.2, t); }
    }
    translate([drvX, kY0 - 1, drvZ]) rotate([-90, 0, 0]) cylinder(d = drvCut, h = baffT + 2);
    for (k = [0:3]) translate([drvX + drvPCD/2*cos(45 + 90*k), kY0 - 1, drvZ + drvPCD/2*sin(45 + 90*k)])
      rotate([-90, 0, 0]) cylinder(d = 2.6, h = baffT);                     // M3 selvgjengende
    for (x = kBx, z = kBz) translate([x, kY0 + kD - insD, z]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD + 0.1);
    for (x = [kX0 - kOre/2, kX0 + kW + kOre/2], y = kOreY) translate([x, y, kZ0 - 0.01]) cylinder(d = ins, h = insD);
    // kabelhull bak i høyre sidevegg, rett mot forsterkeren (tettes med silikon etter at ledningene er trukket)
    translate([kX0 + kW - kT - 1, kY0 + kD - 14, kZ0 + 14]) rotate([0, 90, 0]) cylinder(d = 4, h = kT + 2);
  }
}
module lokk() {   // bakveggen på kammeret (tetning: 1–2 mm skumtape rundt kanten, klemmes flat)
  difference() {
    translate([kX0, kY0 + kD, kZ0]) cube([kW, 3, kH]);
    for (x = kBx, z = kBz) translate([x, kY0 + kD - 1, z]) rotate([-90, 0, 0]) cylinder(d = m3, h = 5);
  }
}

// ---------- grill (settes inn fra innsiden; holdes av flensen og to ribber mot baffelen) ----------
module grill() {
  difference() {
    union() {
      rundet_blokk(gF, gT, 0.8, gRk);                                   // rammen: stikker 3 mm ut med rundet forkant
      ext_y(t - 0.1, t + 0.4) offset(gFl - 0.6) front_hull();          // flens bak (i falsen, med 0,5 mm til stoffet foran og rundt)
      for (z = [gZ0 + 4.5, gZ1 - 6.9]) translate([ribX[0], t, z]) cube([ribX[1] - ribX[0], kY0 - t - 0.4, 2.4]);   // ribber mot baffelen
    }
    // tre store vinduer bak stoffet, delt av to vannrette stag
    for (w = [[gZ0 + stM, stBar[0] - 1.5], [stBar[0] + 1.5, stBar[1] - 1.5], [stBar[1] + 1.5, gZ1 - stM]])
      translate([gX0 + stM, -gUt - 1, w[0]]) cube([gX1 - gX0 - 2*stM, gT + gUt + 2, w[1] - w[0]]);
  }
}
// høyttalerstoffet (illustrasjon, kjøpes): over forsiden, rundt kanten og brettet inn bak flensen, med vevd struktur
// Rund forkant: et konvekst skall fra y0 (forsiden) til y1, forskjøvet o innover fra grillåpningen, med radius r på forkanten
module rundet_blokk(y0, y1, o, r) {
  hull() {
    for (a = [0:15:90]) ext_y(y0 + r*(1 - cos(a)), y0 + r*(1 - cos(a)) + 0.01) front_hull(o + r*(1 - sin(a)));
    ext_y(y0 + r, y1) front_hull(o);
  }
}
module stoff() {
  d = t - 0.6;                                                                       // falsens forside (y 2,4)
  difference() {                                                                     // over forsiden og rundt den utstikkende kanten
    rundet_blokk(-gUt, d + stTyk, 0.3, gRk + stTyk);
    rundet_blokk(gF, d + stTyk + 1, 0.8, gRk);
  }
  ext_y(d, d + stTyk) difference() { offset(gFl - 0.6) front_hull(); front_hull(0.8); }   // mellom falsen og flensen
  ext_y(d, t + 0.4 + stTyk) difference() { offset(gFl - 0.15) front_hull(); offset(gFl - 0.6) front_hull(); }   // rundt flensen
  ext_y(t + 0.4, t + 0.4 + stTyk) difference() { offset(gFl - 0.6) front_hull(); front_hull(2); }   // limt bak flensen
}
module stoff_vev() {   // trådene i vevingen, litt lysere (bare for bildene)
  pitch = 1.2;
  intersection() {
    ext_y(-gUt - 0.15, -gUt + 0.01) front_hull(0.3 + gRk + stTyk);
    union() {
      for (x = [gX0 : pitch : gX1]) translate([x, -gUt - 0.2, gZ0]) cube([0.45, 0.25, gZ1 - gZ0]);
      for (z = [gZ0 + pitch/2 : pitch : gZ1]) translate([gX0, -gUt - 0.2, z]) cube([gX1 - gX0, 0.25, 0.45]);
    }
  }
}
module list() { translate([0, -0.4, 0]) ext_y(0, lDyp + 0.35) list2d(0.15); }   // gullista, står 0,4 mm ut

// ---------- skjermbrakett (klemmer skjermmodulen inn i lomma; Pi 4 skrus på baksiden) ----------
module brakett() {
  front_ramme() translate([0, 0, -t - 6]) {
    difference() {
      hull() for (p = scrB) translate([scrX + p[0], scrZ + p[1], -2.4]) cylinder(d = 8, h = 2.4);
      for (p = scrB) translate([scrX + p[0], scrZ + p[1], -3]) cylinder(d = 2.9, h = 4);
      translate([scrX - 14, scrZ - 30, -3]) cube([28, 6, 4]);                                // slisse for DSI-flatkabelen
      for (s = [-1, 1]) translate([scrX + s*46 - 4, scrZ - 14, -3]) cube([8, 28, 4]);          // lufting
    }
    for (p = piH) translate([scrX + p[0], scrZ + p[1], -2.4 - piSt]) difference() {
      cylinder(d = 6, h = piSt + 0.01); translate([0, 0, -1]) cylinder(d = 2.2, h = piSt);      // M2,5 selvgjengende
    }
  }
}

// ---------- knotter og knapper ----------
module knott_form(d, h, riller, ikon) {   // hul nedenfra (mindre resin, ingen lukkede hulrom), D-aksel 6 mm
  difference() {
    union() {
      cylinder(d = d, h = h - 1.2);
      translate([0, 0, h - 1.2]) cylinder(d1 = d, d2 = d - 2.4, h = 1.2);
    }
    for (k = [0:riller - 1]) rotate([0, 0, k * 360 / riller]) translate([d/2, 0, -1]) cylinder(d = 1.6, h = h - 2, $fn = 12);
    translate([0, 0, h - 0.5]) cylinder(d = d - 8, h = 1);                       // grunn skål i toppen
    translate([0, 0, h - 0.5 - symD]) linear_extrude(symD + 0.01) ikon2d(ikon);   // lomme for symbolet i skålbunnen
    translate([0, 0, -0.01]) difference() { cylinder(d = d - 5, h = h - 3); cylinder(d = 10, h = h); }
    translate([0, 0, -0.01]) difference() { cylinder(d = 6.2, h = 11); translate([1.55, -4, -1]) cube([8, 8, 13]); }
    translate([0, 0, -0.01]) cylinder(d = 7.8, h = 2.5);                          // plass til gjengehylsen på EC11
  }
}
module knott_symbol_form(h, ikon) { translate([0, 0, h - 0.5 - symD]) linear_extrude(symD) ikon2d(ikon); }   // i flukt med skålbunnen
module knott() { knott_form(whD, whH, 48, "spill"); }
module volum() { knott_form(volD, volH, 24, "volum"); }
module knott_symbol() { knott_symbol_form(whH, "spill"); }
module volum_symbol() { knott_symbol_form(volH, "volum"); }

// ---------- symbolene (2D, sentrert; strek ≥ 0,9 mm for 0,4 mm dyse) ----------
module bue(r, w, a0, a1) {   // bue med runde ender, fra vinkel a0 til a1 (0° = opp, med klokka positiv)
  intersection() {
    difference() { circle(r + w/2); circle(r - w/2); }
    polygon(concat([[0, 0]], [for (a = [a0 : (a1 - a0)/24 : a1]) 2*(r + w)*[sin(a), cos(a)]]));
  }
  for (a = [a0, a1]) translate(r*[sin(a), cos(a)]) circle(d = w, $fn = 24);
}
module av_pa() {   // IEC 60417-5009 (⏻): åpen sirkel med loddrett strek gjennom åpningen
  bue(2.65, 1.0, 42, 318);
  hull() for (y = [0.1, 3.2]) translate([0, y]) circle(d = 1.0, $fn = 24);
}
module hoyttaler() {   // høyttaler med to lydbølger
  translate([-0.25, 0]) {
    polygon([[-3.4, -1.1], [-1.8, -1.1], [0.2, -2.9], [0.2, 2.9], [-1.8, 1.1], [-3.4, 1.1]]);
    for (r = [1.8, 3.3]) translate([0.2, 0]) bue(r, 0.8, 50, 130);
  }
}
module spill_pause() {   // ⏯ spill/pause: trekant og to streker
  translate([-1.1, 0]) {
    offset(r = 0.4) offset(delta = -0.4) polygon([[-5, -4], [-5, 4], [1.6, 0]]);
    for (x = [3.0, 5.6]) translate([x, -4]) square([1.6, 8]);
  }
}
module ikon2d(ikon) {
  if (ikon == "av") av_pa();
  else if (ikon == "volum") scale(1.25) hoyttaler();
  else if (ikon == "spill") scale(1.2) spill_pause();
  else offset(r = 0.1) text(ikon, size = 5.4, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
}
module knapp_lok(ikon) {
  difference() {
    union() {
      translate([0, 0, -t - 0.21]) cylinder(d = capD, h = t + capUp + 0.21);
      // flensen er rett avskåret oppe (under skjermmodulen): holder tallet på rett kjøl og gir 0,7 mm luft til skjermen
      translate([0, 0, -t - 0.2 - capFlT]) intersection() { cylinder(d = capFl, h = capFlT); translate([-capFl, -capFl, -1]) cube([2*capFl, capFl + capFlat, capFlT + 2]); }
      translate([0, 0, -t - capFlT - 1.6]) cylinder(d = 3, h = 1.41);  // nupp mot taktbryteren: 0,1 mm luft (overlapper flensen 0,01)
    }
    translate([0, 0, capUp - symD]) linear_extrude(symD + 0.01) ikon2d(ikon);    // lomme for symbolet
  }
}
module knapp_symbol(ikon) { translate([0, 0, capUp - symD]) linear_extrude(symD) ikon2d(ikon); }   // innlegget, i flukt med toppen
module knapper(symbol = false) {
  front_ramme() for (i = [0:6]) translate(i < 6 ? [btnX0 + i*btnP, btnZ, 0] : [pwX, botZ, 0])
    if (symbol) knapp_symbol(knappIkon[i]); else knapp_lok(knappIkon[i]);
}

// ---------- montert / eksplodert ----------
module montert(e = 0) {   // eksplodert: fronten ut mot deg, innmaten ut bakover gjennom den åpne baksiden
  color(c_kropp) render(convexity = 6) kropp();
  color(c_kropp) translate([0, 8.0*e, 0]) bak();
  color(c_inne) translate([0, 4.6*e, 0]) kammer();
  color(c_inne) translate([0, 5.6*e, 0]) lokk();
  translate([0, 4.6*e, 0]) elementer();
  color(c_grill) translate([0, -1.6*e, 0]) grill();
  translate([0, -2.4*e, 0]) { color(c_stoff) stoff(); color(c_vev) stoff_vev(); }          // høyttalerstoff (foran grillrammen)
  color(c_gull) translate([0, -1.0*e, 0]) list();
  color(c_glass) translate([0, 4.0*e, 0]) front_ramme() translate([scrX - scrGW/2, scrZ - scrGH/2, -t - 0.7]) cube([scrGW, scrGH, 0.6]);
  if (skjerm == "nokkel") color([1, 0, 1]) translate([0, 4.0*e, 0]) skjermflate();
  color(c_inne) translate([0, 5.0*e, 0]) brakett();
  translate([0, 5.8*e, 0]) pi_kort();
  color(c_knapp) translate([0, -0.8*e, 0]) knapper();
  color(c_sym_knapp) translate([0, -0.8*e, 0]) knapper(true);
  color(c_gull) translate([0, -1.2*e, 0]) front_ramme() translate([whX, whZ, 0.6]) knott();
  color(c_gull) translate([0, -1.2*e, 0]) front_ramme() translate([volX, volZ, 0.6]) volum();
  color(c_sym_knott) translate([0, -1.2*e, 0]) front_ramme() { translate([whX, whZ, 0.6]) knott_symbol(); translate([volX, volZ, 0.6]) volum_symbol(); }
}
// aktivt område på skjermen (95,04 × 53,86 mm, 800 × 480), rett foran glasset – brukes bare i bildene
scrPW = 95.04; scrPH = 53.86;
module skjermflate() { front_ramme() translate([scrX - scrPW/2, scrZ - scrPH/2, -t - 0.1]) cube([scrPW, scrPH, 0.02]); }
module elementer() {   // høyttalerelementet (illustrasjon): ramme foran baffelen, magnet bak
  color([0.22, 0.22, 0.23]) translate([drvX, kY0 - drvFT, drvZ]) rotate([-90, 0, 0]) {
    difference() { cylinder(d = drvF, h = drvFT); translate([0, 0, 1]) cylinder(d = drvCut - 6, h = drvFT); }
    translate([0, 0, drvFT + baffT]) cylinder(d = 50, h = 30);
  }
}
module pi_kort() {   // Raspberry Pi 4 (illustrasjon) på braketten
  front_ramme() translate([scrX - 42.5, scrZ - 28, -t - 8.4 - piSt - 1.4]) {
    color([0.12, 0.42, 0.22]) cube([85, 56, 1.4]);
    color([0.75, 0.75, 0.77]) translate([85 - 21, 2, -16]) cube([21, 52, 16]);      // USB/nett
    color([0.15, 0.15, 0.16]) translate([28, 18, -2.5]) cube([15, 15, 2.5]);         // SoC med kjøleribbe
  }
}

// ---------- referansedeler (kjøpes, ikke printet) – for bildene og kollisjonssjekken i sjekk_modell.py ----------
c_kort = [0.10, 0.40, 0.22]; c_metall = [0.72, 0.72, 0.74]; c_svart = [0.12, 0.12, 0.13];
module fk(p0, p1) { translate(p0) cube(p1 - p0); }   // boks fra hjørne til hjørne (x, y, z)
module ref(n) {
  if (n == "favkort") {   // hullkort med seks taktbrytere
    color(c_kort) fk([btnX0 - 55 + 2.5*btnP + 0, kortY, btnZ - favKort[1]/2], [btnX0 + 2.5*btnP + 55, kortY + pcb, btnZ + favKort[1]/2]);
    for (i = [0:5]) taktbryter([btnX0 + i*btnP, btnZ]);
  } else if (n == "pwkort") {
    color(c_kort) fk([pwX - 15, kortY, botZ - 8], [pwX + 15, kortY + pcb, botZ + 8]);
    taktbryter([pwX, botZ]);
  } else if (n == "ec_volum" || n == "ec_hjul") {
    k = n == "ec_volum" ? [volX, volZ] : [whX, whZ];
    color(c_kort) fk([k[0] - ecKort[0]/2, ecY, k[1] - ecKort[1]/2], [k[0] + ecKort[0]/2, ecY + pcb, k[1] + ecKort[1]/2]);
    color(c_metall) fk([k[0] - 6, t, k[1] - 6], [k[0] + 6, ecY, k[1] + 6]);                        // hus mot frontens innside
    color(c_metall) translate([k[0], t + 0.01, k[1]]) rotate([90, 0, 0]) cylinder(d = 7, h = 5);  // gjengehylse M7 (uten mutter)
    color(c_metall) translate([k[0], 0, k[1]]) rotate([90, 0, 0]) intersection() {               // D-aksel, kappes 11 mm foran fronten
      translate([0, 0, -2]) cylinder(d = 6, h = 0.6 + 10.8 + 2); translate([-4, -4, -3]) cube([5.45, 8, 20]); }
  } else if (n == "skjermmodul") {   // Waveshare 4,3″ DSI (glass + LCD + kort), i lomma bak vinduet, klemt av braketten
    color(c_svart) front_ramme() translate([scrX - scrGW/2, scrZ - scrGH/2, -t - 6]) cube([scrGW, scrGH, 7.8]);
  } else if (n == "pi") pi_kort();
  else if (n == "dac") {
    color([0.35, 0.15, 0.55]) fk([dacP[0], dacP[1], dacH], [dacP[0] + dacM[0], dacP[1] + dacM[1], dacH + pcb]);
    color(c_svart) fk([dacP[0] + 2, dacP[1] + dacM[1] - 4, dacH + pcb], [dacP[0] + dacM[0] - 2, dacP[1] + dacM[1] - 1.5, dacH + pcb + 8.5]);   // stiftlist
  } else if (n == "forsterker") {
    color(c_kort) fk([forstP[0], forstP[1], forstH], [forstP[0] + forstM[0], forstP[1] + forstM[1], forstH + pcb]);
    color(c_metall) fk([forstP[0] + 20, forstP[1] + 10, forstH + pcb], [forstP[0] + 63, forstP[1] + 40, forstH + forstM[2]]);   // kjøleribbe
    color([0.15, 0.35, 0.75]) fk([forstP[0] + 8, forstP[1] + forstM[1] - 9, forstH + pcb], [forstP[0] + 75, forstP[1] + forstM[1] - 1, forstH + 12]);   // skrueklemmer
  } else if (n == "nedtrapper" || n == "rele") {
    b = n == "nedtrapper" ? [buckP, buckM] : [releP, releM];
    color(n == "rele" ? [0.10, 0.25, 0.60] : [0.15, 0.30, 0.65]) fk([b[0][0], yBak - holdH - pcb, b[0][1]], [b[0][0] + b[1][0], yBak - holdH, b[0][1] + b[1][1]]);
    color(n == "rele" ? [0.15, 0.35, 0.80] : c_svart)
      fk([b[0][0] + 8, yBak - holdH - b[1][2], b[0][1] + 4], [b[0][0] + b[1][0] - 12, yBak - holdH - pcb, b[0][1] + b[1][1] - 4]);
  } else if (n == "kontakter") {   // DC-022, PJ-392 og USB-C-skjøten, sett inn fra baksiden
    union() {
      translate([dcX, yBak, bakKZ]) rotate([90, 0, 0]) cylinder(d = 10, h = 14);
      translate([dcX, yBak - 0.01, bakKZ]) rotate([-90, 0, 0]) cylinder(d = 7.9, h = bkT + 0.02);
      fk([jackX - 5, yBak - 12, bakKZ - 6], [jackX + 5, yBak, bakKZ + 6]);
      translate([jackX, yBak - 0.01, bakKZ]) rotate([-90, 0, 0]) cylinder(d = 6, h = bkT + 0.02);
      fk([usbX - 7, yBak - 18, bakKZ - 4], [usbX + 7, yBak, bakKZ + 4]);
    }
      fk([usbX - 3, yBak - 24, bakKZ + 3.9], [usbX + 3, yBak - 17.9, bakKZ + 18]);   // kabelen opp mot Pi-en (første bit)
  } else if (n == "element") elementer();
}
module taktbryter(p) {
  color(c_svart) fk([p[0] - 3, kortY - 3.5, p[1] - 3], [p[0] + 3, kortY, p[1] + 3]);
  color(c_metall) translate([p[0], kortY - 3.5 + 0.01, p[1]]) rotate([90, 0, 0]) cylinder(d = 3.5, h = tact[2] - 3.5);
}
REFS = ["favkort", "pwkort", "ec_volum", "ec_hjul", "skjermmodul", "pi", "dac", "forsterker", "nedtrapper", "rele", "kontakter", "element"];
module inni() { for (n = REFS) ref(n); }

// ---------- utskriftsretning for STL ----------
module print(p) {
  if (p == "kropp") translate([0, H, 0]) rotate([90, 0, 0]) kropp();                     // fronten ned
  else if (p == "bak") translate([0, t, D]) rotate([-90, 0, 0]) bak();                    // baksiden ned
  else if (p == "kammer") translate([0, 0, -kY0]) rotate([90, 0, 0]) kammer();            // baffelen ned
  else if (p == "lokk") translate([0, 0, -(kY0 + kD)]) rotate([90, 0, 0]) lokk();
  else if (p == "grill") translate([0, gZ1 + gFl, -gF]) rotate([90, 0, 0]) grill();   // forsiden ned
  else if (p == "list") translate([0, 0, 0.4]) rotate([90, 0, 0]) list();                 // forsiden ned (118 mm lang)
  else if (p == "brakett") translate([0, H, -(t + 6)]) rotate([90, 0, 0]) brakett();      // forsiden ned, Pi-tårn opp
  else if (p == "knott") knott();
  else if (p == "volum") volum();
  else if (p == "knott_symbol") knott_symbol();                                            // samme plassering som knott.stl
  else if (p == "volum_symbol") volum_symbol();                                            // samme plassering som volum.stl
  else if (p == "knapp") for (i = [0:6]) translate([i * (capFl + 3), 0, capUp]) rotate([180, 0, 0]) knapp_lok(knappIkon[i]);
  else if (p == "knapp_symbol") for (i = [0:6]) translate([i * (capFl + 3), 0, capUp]) rotate([180, 0, 0]) knapp_symbol(knappIkon[i]);
}

if (part == "samlet") plassert() montert(0);
else if (part == "eksplodert") plassert() montert(40);
else if (part == "A_kropp") kropp();
else if (part == "A_bak") bak();
else if (part == "A_kammer") kammer();
else if (part == "A_lokk") lokk();
else if (part == "A_grill") grill();
else if (part == "A_list") list();
else if (part == "A_brakett") brakett();
else if (part == "A_knapper") knapper();
else if (part == "A_knapp_symboler") knapper(true);
else if (part == "A_knott_symbol") front_ramme() translate([whX, whZ, 0.6]) knott_symbol();
else if (part == "A_volum_symbol") front_ramme() translate([volX, volZ, 0.6]) volum_symbol();
else if (part == "A_knott") front_ramme() translate([whX, whZ, 0.6]) knott();
else if (part == "A_volum") front_ramme() translate([volX, volZ, 0.6]) volum();
else if (part == "A_element") elementer();
else if (part == "A_stoff") stoff();
else if (part == "A_pi") pi_kort();
else if (part == "inni") plassert() {   // innmaten: bakplata er felt ned bakover (innsiden opp) med nedtrapperen, releet og kontaktene
  color(c_kropp) render(convexity = 6) kropp(); color(c_inne) { kammer(); lokk(); brakett(); } color(c_knapp) knapper();
  color(c_gull) front_ramme() { translate([whX, whZ, 0.6]) knott(); translate([volX, volZ, 0.6]) volum(); }
  for (n = REFS) if (n != "nedtrapper" && n != "rele" && n != "kontakter") ref(n);
  translate([0, D + 20, -t]) rotate([-90, 0, 0]) translate([0, -D, t]) { color(c_kropp) bak(); ref("nedtrapper"); ref("rele"); ref("kontakter"); }
}
else if (len(part) > 2 && part[0] == "R" && part[1] == "_") ref(chr([for (i = [2:len(part) - 1]) ord(part[i])]));
else if (part == "skjermflate") plassert() color([1, 0, 1]) translate([0, 4.0*skjermE, 0]) skjermflate();   // bare det aktive området (hjørnene til lag_render.sh)
else print(part);
