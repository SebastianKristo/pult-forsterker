// Skjold Mini – liten aktiv høyttaler (3″ fullrange, bassrefleks) for bad, kjøkken og barnerom. Parametrisk OpenSCAD.
// Tåler damp og sprut (mål: omtrent IPX4 – ikke vanntett): TPU-pakninger i alle skjøter, TPU-membran over knappene,
// skjerm bak klar rute, vannavstøtende akustisk duk bak grillen og bassrefleksporten vendt bakover.
// Skjerm og knapper sitter på toppen («dashbord» som heller svakt mot brukeren), foran volumhjulet. De ligger i et
// eget, lukket rom under toppen («takrommet»), adskilt fra lydkammeret, så membranen ikke vibrerer med bassen.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater (montert): x = bredde (−50…50), y = dybde (−fT = forsiden, 0 = skjøten front/kropp, D = bak),
// z = høyde (0 = underkant). Kropp og frontplate er skåret fra samme ytre form, så sidene flukter i skjøten.
// Bruk:  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_mini.scad
// part:  kropp | front | logo | grill | bunn | knott | skjermklemme | rute |
//        pakning_front | pakning_bunn | pakning_skjerm | membran | krage | dc_skive | usb_propp | samlet | eksplodert
// STL-ene eksporteres liggende slik de skal printes (se utskriftsretning nederst).

part = "samlet";
$fn = 72;

// ---------- ytre mål ----------
// Totalhøyde med bunn og føtter: H + bT + footH = 144 mm (samme som første Mini, uten knott).
W = 106; D = 113; H = 136;      // kropp: H er høyden bak; toppen heller s mm ned mot fronten
s = 5;                          // fall på toppen fra bak til forkant (≈ 2,4°): vann renner av, skjermen vender mot deg
R = 12;                         // hjørneradius bak (som Node)
Rf = 6;                         // hjørne foran: 45°-fas som går over i R6 (frontplaten printes uten støtte)
c = 2;                          // fas på toppkanten
t = 2.6;                        // vegg (6 × 0,42 mm linjer)
zf = 26;  ft = 2.4;             // gulv mellom elektronikkrommet (under) og lydkammeret (over)
fT = 8.5;                       // frontplate (baffel)
bT = 4;  footH = 4;  drip = 0.8; // bunnplate, føtter og dryppkant (bunnen stikker 0,8 mm ut)

// ---------- pakninger (TPU 95A) ----------
gkW = 1.8; gkD = 1.0;           // spor: bredde og dybde
gkB = 1.6; gkT = 1.2;           // pakning: bredde og tykkelse (klemmes 0,2 mm)
rimW = 2.4; rimT = 2.0;         // leppe innvendig i kroppen som frontplaten ligger mot
seamW = 0.5; seamD = 0.4;       // skyggefuge rundt skjøten: 0,5 mm inn, 2 × 0,4 mm bred

// ---------- element og port ----------
drvCut = 72;                    // utsparing for 3″-element (sjekk ditt element, typisk 70–74 mm)
drvRec = 86; drvRecD = 2.5;     // forsenkning for elementets ramme
drvPCD = 82; drvScrew = 2.6;    // skruehull (M3 selvgjengende)
drvZ = 75;                      // elementets senter
portD = 16; portW = 2.0;        // port innv. Ø og vegg
portL = 78;                     // portlengde fra munningen bak → fb ≈ 86 Hz (se LES_MEG.md)
portZ = 40; portX = -26; portFlare = 3; // lavt i bakveggen, til siden for magneten, peker bakover (ikke mot dusjen)

// ---------- fester ----------
ins = 4.0;  insD = 6.5;         // M3 innpressmutter (Ø4,0 hull, 6,5 dyp)
boss = 8.4;
m3 = 3.4; m3k = 6.4;            // M3 senkeskrue: hull og senkehode
bx = W/2 - t - boss/2 + 0.6;    // bunnens skruetårn i x (tårnet går inn i sideveggen)
by = [8, D - t - boss/2 + 0.6]; // bunnens skruetårn i y
fz = [36, 109];                 // frontplatens skruer (skjult bak grillen)
fbx = 40;                       // frontskruenes x: senkehodet ligger i grill-lomma, tårnet har ribbe til sideveggen

// ---------- toppen: skrå flate z = topz(y) ----------
kS = s / (D + fT);              // fall per mm
aS = atan(kS);
function topz(y) = H - kS * (D - y);
z0 = topz(0);                   // toppen ved skjøten front/kropp
// Lokal ramme for toppanelet: x som før, v langs toppen (fra y = 0 og bakover), w ut av toppen (w = 0 er overflaten).
module panel() { translate([0, 0, z0]) rotate([aS, 0, 0]) children(); }
tp = 7.5;                       // toppanelets tykkelse over takrommet (rute + skjermlomme / membran + stempler)
hR = 8.5;                       // takrommets høyde under panelet
cT = 3.0;                       // takrommets gulv («himling» over lydkammeret)
vB = 63;                        // takrommets bakkant (lokal v); bakveggen heller 45° opp til panelet
fw = 2.0;                       // takrommets frontvegg (y = 0…2) – frontplaten trenger ikke tette takrommet

// ---------- betjening ----------
ec11V = 88; ec11D = 7.2;        // EC11-aksel gjennom toppen, bakerst (står vinkelrett på toppen)
krageD = 12.4; krageS = 1.2;    // forsenkning for TPU-kragen rundt akselen
micX = 40;  micZ = 14; micD = 1.6;   // valgfri INMP441-mikrofon i fronten (ePTFE-akustikkmembran limes på innsiden)

// ---------- skjerm: 1,54″ IPS 240×240 (ST7789, SPI) bak klar rute, i toppen ----------
// Mål for den vanlige 7-pinners modulen (sjekk din: pcbW/pcbH og hvor det aktive feltet sitter).
dispV = 38;                      // senter av det aktive feltet (lokal v)
winW = 28.4;                     // vindu (aktivt felt 27,72 × 27,72 mm)
pcbW = 31.8; pcbH = 40.0;        // kretskort (glasset ligger innenfor)
pcbOffV = 3.0;                   // kortets senter i forhold til det aktive feltet (pinneraden bakover)
pocketD = 3.4;                   // lomme nedenfra for glass + kort
ruteW = 34.6; ruteT = 1.5;       // klar rute (akryl 1,5 mm eller klar PETG) i toppen
skjT = 0.8; skjS = 0.6;          // TPU-ramme under ruta: 0,8 mm, klemmes til 0,6
ruteRec = ruteT + skjS;          // forsenkning for rute + pakning (ruta flukter med toppen)
clampX = pcbW/2 + 4.0;           // skruehull for skjermklemmen (M2,5 selvgjengende rett i panelet)

// ---------- knapper: av/på + favoritt 1–4 under én TPU-membran, foran skjermen ----------
btnV = 10.5; btnX = [-32, -16, 0, 16, 32];  // [0] = av/på
memW = 84; memH = 15; memR = 3; memT = 1.4; // membranen flukter med toppen
keyD = 10;                       // tastefelt (markert med preget ring og ikon)
plD = 4.4; plHole = 6.0;         // stempel på undersiden av membranen og hullet det går gjennom
tactH = 5.0;                     // 6 × 6 × 5 mm taktbryter (stempel 1,5 mm over huset)
boardW = tp + 6.0;               // hullkortets overside under toppflaten (M2 × 6 mm avstandsstykker)
plTip = boardW - tactH - 0.2;    // stempelspissen: 0,2 mm forspenning mot bryteren
boardHoles = [[-41, btnV], [41, btnV]];
dcD = 8.2;  usbW = 10; usbH = 4.4; dcX = -25; usbX = 15; connZ = 13;
ventD = 12.5; ventP = [25, 60];  // ePTFE-trykkutjevning (M12 × 1,5) i bunnen av elektronikkrommet
knobD = 34; knobH = 14; shaftD = 6.1; shaftFlat = 4.6;
wireV = 50; wireX = 30;          // ledningsgjennomføring takrom → lydkammer → elektronikkrom (tettes med lim)

// ---------- grill ----------
gT = 2.4; gGap = 0.6; gP = gT + gGap;      // grillen ligger i en lomme og flukter med fronten; duken ligger i luften bak
gW = 93; gZ0 = 31; gZ1 = z0 - fT * kS - 6;
gPins = [[-24, gZ0 + 4], [24, gZ0 + 4], [-24, gZ1 - 4], [24, gZ1 - 4]];

c_lys = [0.93,0.92,0.90]; c_mork = [0.13,0.13,0.14]; c_gull = [0.85,0.62,0.25]; c_grill = [0.18,0.18,0.19];
c_tpu = [0.30,0.55,0.75]; c_klar = [0.80,0.90,0.95,0.45];

// ---------- hjelpere ----------
module rrect(w, h, r) { offset(r) offset(-r) square([w, h], center = true); }
module ytz(y0, y1) { translate([0, y0, 0]) rotate([-90, 0, 0]) linear_extrude(y1 - y0) mirror([0, 1, 0]) children(); } // 2D i (x, z) → y0…y1
// grunnriss: R12 bak, 45°-fas + R6 foran, fra y = −fT til D
xa = W/2 - Rf + Rf * sin(45) - Rf * (1 - cos(45));
module plan2d(o = 0) {
  offset(delta = o) hull() {
    for (sx = [-1, 1]) translate([sx * (W/2 - R), D - R]) circle(R);
    for (sx = [-1, 1]) translate([sx * (W/2 - Rf), -fT + Rf]) circle(Rf);
    for (sx = [-1, 1]) translate([sx * xa, -fT + 0.005]) square(0.01, center = true);
  }
}
// skjær z med y, så et flatt lag blir parallelt med den skrå toppen
module shear() { multmatrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, kS, 1, 0], [0, 0, 0, 1]]) children(); }
module S() {
  hull() {
    linear_extrude(1) plan2d();
    shear() translate([0, 0, H - kS * D - c]) hull() { linear_extrude(0.01) plan2d(); translate([0, 0, c]) linear_extrude(0.01) plan2d(-c); }
  }
}
// innvendig hulrom: veggene t, toppen t (følger skråningen)
module Sin() { hull() { translate([0, 0, -1]) linear_extrude(1) plan2d(-t); shear() translate([0, 0, H - kS * D - t - 0.01]) linear_extrude(0.01) plan2d(-t); } }
// tverrsnitt i (x, z) i skjøten (y = 0): rett side, fas i toppen
module snitt2d(o = 0) { offset(delta = o) polygon([[-W/2, -2], [W/2, -2], [W/2, z0 - c], [W/2 - c, z0], [-W/2 + c, z0], [-W/2, z0 - c]]); }
module skyggefuge() { ytz(-seamD, seamD) difference() { snitt2d(1); snitt2d(-seamW); } }
// U-spor og U-pakning i skjøten (sider + under takrommet + over gulvet), i (x, z)
xi = W/2 - t;                   // innsiden av sideveggen
cBot0 = z0 - tp - hR - cT;      // undersiden av takrommets gulv ved y = 0 (lydkammerets tak foran)
gkTop = cBot0 + 0.6;            // øverste pakningslist ligger i forkanten av takrommets gulv
module front_gk2d(w, zs = -1) {
  for (sx = [-1, 1]) translate([sx * (xi - w/2) - w/2, zs]) square([w, gkTop + w - zs]);
  translate([-xi, gkTop]) square([2 * xi, w]);
  translate([-xi, zf + 0.4 - w/2]) square([2 * xi, w]);
}
module bunn_gk2d(w) { difference() { plan2d(-1.5 + w/2); plan2d(-1.5 - w/2); } }   // ring 1,5 mm inn fra kanten
module skjerm_gk2d() { difference() { rrect(ruteW - 0.4, ruteW - 0.4, 1.5); square(winW + 1.0, center = true); } }
// takrommet i panelets ramme: hulrom (w < 0 er under overflaten) og hele blokka (hulrom + gulv + bakvegg)
module tak_hulrom() {
  translate([0, 0, 0]) rotate([90, 0, 90]) translate([0, 0, -xi]) linear_extrude(2 * xi)
    polygon([[fw, -tp], [fw, -tp - hR], [vB, -tp - hR], [vB + hR, -tp]]);
}
module tak_blokk() {
  rotate([90, 0, 90]) translate([0, 0, -xi - 0.01]) linear_extrude(2 * xi + 0.02)
    polygon([[-0.01, 0.5], [-0.01, -tp - hR - cT], [vB + 3 * sqrt(2) - cT, -tp - hR - cT], [vB + 3 * sqrt(2) + hR + tp + 0.5, 0.5]]);   // bakveggen 3 mm, 45°
}

// ---------- kropp ----------
module kropp() {
  difference() {
    intersection() {
      S();
      translate([-W, 0, -1]) cube([2 * W, D + 1, H + 2]);
      union() {
        difference() { S(); Sin(); }
        intersection() { Sin(); panel() tak_blokk(); }                  // takrommet (fylles, hulrommet trekkes fra under)
        translate([-W/2, 0, zf]) cube([W, D, ft]);                       // gulv
        translate([-xi, 0, zf - 1.6]) cube([2 * xi, 4, ft + 1.6]);      // forkant på gulvet (pakningen ligger her)
        intersection() { Sin(); ytz(0, rimT) difference() { translate([-xi, -1]) square([2 * xi, H]); translate([-xi + rimW, -2]) square([2 * (xi - rimW), cBot0 - rimW + 2]); } }
        // bassrefleksport (bak)
        translate([portX, D - portL, portZ]) rotate([-90, 0, 0]) cylinder(d = portD + 2 * portW, h = portL);
        // frontplatens skruetårn, med ribbe ut til sideveggen
        for (sx = [-1, 1], z = fz) hull() {
          translate([sx * fbx, 0, z]) rotate([-90, 0, 0]) cylinder(d = boss, h = D - t + 0.01);
          translate([sx * (xi + 0.2) - 0.3, 0, z - 2.5]) cube([0.6, D - t + 0.01, 5]);
        }
        // bunnplatens skruetårn (langs z), 45°-kile mot bakveggen så de printes uten støtte
        for (sx = [-1, 1], y = by) translate([sx * bx, y, 0]) {
          cylinder(d = boss, h = zf);
          if (y < D/2) hull() { cylinder(d = boss, h = zf); translate([sx * (boss/2 - 0.5), boss/2 + 3, 0]) cube([1, 1, zf]); }
        }
      }
    }
    // innpressmuttere
    for (sx = [-1, 1], z = fz) translate([sx * fbx, -0.01, z]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD);
    for (sx = [-1, 1], y = by) translate([sx * bx, y, -0.01]) cylinder(d = ins, h = insD);
    // portboring med avrundet munning bak
    translate([portX, D - portL - 1, portZ]) rotate([-90, 0, 0]) cylinder(d = portD, h = portL + 2);
    translate([portX, D - portFlare, portZ]) rotate([-90, 0, 0]) cylinder(d1 = portD, d2 = portD + 2 * portFlare, h = portFlare + 0.01);
    // takrommet (lukket rom under toppen for skjerm og knapper)
    panel() tak_hulrom();
    panel() {
      // EC11 gjennom toppen + forsenkning for TPU-kragen
      translate([0, ec11V, -t - 1]) cylinder(d = ec11D, h = t + 2);
      translate([0, ec11V, -krageS]) cylinder(d = krageD, h = krageS + 1);
      // skjerm: forsenkning for rute + TPU-ramme, vindu, lomme nedenfra for glass og kort, hull for klemmen
      translate([0, dispV, -ruteRec - 0.03]) linear_extrude(ruteRec + 0.04) rrect(ruteW + 0.4, ruteW + 0.4, 1.7);
      translate([0, dispV, -tp - 1]) linear_extrude(tp + 2) square(winW, center = true);
      translate([0, dispV + pcbOffV, -tp - 0.01]) linear_extrude(pocketD + 0.01) offset(0.6) offset(-0.6) square([pcbW + 0.6, pcbH + 0.6], center = true);
      for (sx = [-1, 1]) translate([sx * clampX, dispV + pcbOffV, -tp - 0.01]) cylinder(d = 2.2, h = 4.0);
      // knapper: lomme for TPU-membranen, hull for stemplene, hull for knappekortets avstandsstykker
      translate([0, btnV, -memT - 0.03]) linear_extrude(memT + 0.04) rrect(memW + 0.4, memH + 0.4, memR + 0.2);
      for (x = btnX) translate([x, btnV, -tp - 1]) cylinder(d = plHole, h = tp + 2);
      for (b = boardHoles) translate([b[0], b[1], -tp - 0.01]) cylinder(d = 1.7, h = 4.0);
      // ledninger fra takrommet ned i lydkammeret (tettes med lim)
      translate([wireX, wireV, -tp - hR - cT - 1]) cylinder(d = 6, h = cT + 2);
    }
    // gjennomføring for høyttalerkabel i gulvet (tettes med lim)
    translate([wireX, 85, zf - 1]) cylinder(d = 6, h = ft + 2);
    // bak: DC-kontakt og USB-C (ESP32) i elektronikkrommet
    translate([dcX, D - t - 1, connZ]) rotate([-90, 0, 0]) cylinder(d = dcD, h = t + 2);
    translate([usbX, D - t - 1, connZ]) rotate([-90, 0, 0]) linear_extrude(t + 2) rrect(usbW, usbH, 1.6);
    // spor for frontpakningen og skyggefuge
    ytz(-0.01, gkD) front_gk2d(gkW);
    skyggefuge();
    // gravert navn bak
    translate([0, D - 0.59, 100]) rotate([90, 0, 180]) linear_extrude(0.6) text("SKJOLD MINI", size = 5, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
  }
}

// ---------- frontplate (baffel) ----------
module front() {
  difference() {
    intersection() { S(); translate([-W, -fT - 1, -1]) cube([2 * W, fT + 1, H + 2]); }
    skyggefuge();
    // grill-lomme (grillen flukter med fronten; akustisk duk i luften bak)
    translate([0, -fT - 0.01, 0]) rotate([-90, 0, 0]) linear_extrude(gP + 0.01) translate([0, -(gZ0 + gZ1)/2]) rrect(gW + 0.6, gZ1 - gZ0 + 0.6, 9.3);
    for (p = gPins) translate([p[0], -fT + gP - 0.01, p[1]]) rotate([-90, 0, 0]) cylinder(d = 3.3, h = 3.5);
    // element: utsparing, forsenkning for rammen (i bunnen av lomma) og skruehull
    translate([0, 1, drvZ]) rotate([90, 0, 0]) cylinder(d = drvCut, h = fT + 2);
    translate([0, -fT + gP - 0.01, drvZ]) rotate([-90, 0, 0]) cylinder(d = drvRec, h = drvRecD);
    for (a = [45, 135, 225, 315]) translate([drvPCD/2 * cos(a), 1, drvZ + drvPCD/2 * sin(a)]) rotate([90, 0, 0]) cylinder(d = drvScrew, h = fT + 2);
    // frontskruer (senkehode i bunnen av grill-lomma)
    for (sx = [-1, 1], z = fz) translate([sx * fbx, 1, z]) rotate([90, 0, 0]) {
      cylinder(d = m3, h = fT + 2);
      translate([0, 0, 1 + fT - gP - 1.8]) cylinder(d1 = m3, d2 = m3k, h = 1.81);
    }
    // mikrofon
    translate([micX, 1, micZ]) rotate([90, 0, 0]) cylinder(d = micD, h = fT + 2);
    // innfelt logo (eget legeme i egen farge, se logo())
    logo_shape(0.01);
  }
}

// ---------- grill ----------
module grill() {
  difference() {
    union() {
      translate([0, -fT, 0]) rotate([-90, 0, 0]) linear_extrude(gT) translate([0, -(gZ0 + gZ1)/2]) rrect(gW, gZ1 - gZ0, 9);
      for (p = gPins) translate([p[0], -fT + gT - 0.01, p[1]]) rotate([-90, 0, 0]) cylinder(d = 3.0, h = gGap + 3.2);
    }
    // sekskantmønster
    for (i = [-9:9], j = [0:24]) {
      x = i * 5.2 + (j % 2) * 2.6; z = gZ0 + 6 + j * 4.5;
      if (abs(x) < gW/2 - 5 && z < gZ1 - 5 && !(abs(abs(x) - 24) < 3.5 && (abs(z - gZ0 - 4) < 3.5 || abs(z - gZ1 + 4) < 3.5)))
        translate([x, -fT - 1, z]) rotate([-90, 0, 0]) rotate([0, 0, 30]) cylinder(d = 4.2, h = gT + 2, $fn = 6);
    }
  }
}

// ---------- bunn: dryppkant, føtter, spor for TPU-pakning, ePTFE-ventil ----------
module bunn() {
  difference() {
    union() {
      translate([0, 0, -bT]) linear_extrude(bT) plan2d(drip);
      for (sx = [-1, 1], y = [-fT + 14, D - 14]) translate([sx * 32, y, -bT - footH]) cylinder(d = 12, h = footH + 0.01);
    }
    translate([0, 0, -gkD]) linear_extrude(gkD + 0.01) bunn_gk2d(gkW);                                  // pakningsspor
    translate([0, 0, -bT - 0.01]) linear_extrude(0.8) difference() { plan2d(drip - 0.25); plan2d(drip - 0.75); } // dryppnese
    for (sx = [-1, 1], y = by) translate([sx * bx, y, -bT - 1]) { cylinder(d = m3, h = bT + 2); cylinder(d1 = m3k + 2, d2 = m3, h = 1 + (m3k + 2 - m3)/2); }
    translate([ventP[0], ventP[1], -bT - 1]) cylinder(d = ventD, h = bT + 2);
  }
}

// ---------- knott ----------
module knott() { panel() translate([0, ec11V, 0]) knott_lok(); }
module knott_lok() {   // i panelets ramme, med akselen i origo
  translate([0, 0, 0.6]) difference() {
    union() {
      cylinder(d = knobD - 2, h = knobH);
      cylinder(d = knobD, h = knobH - 1.5);
      translate([0, 0, knobH - 1.5]) cylinder(d1 = knobD, d2 = knobD - 3, h = 1.5);
    }
    for (a = [0:10:350]) rotate([0, 0, a]) translate([knobD/2 + 0.2, 0, -1]) cylinder(d = 1.4, h = knobH - 2, $fn = 12);
    translate([0, 0, knobH - 0.8]) cylinder(d = knobD - 8, h = 1);
    translate([0, 0, -0.01]) intersection() { cylinder(d = shaftD, h = 12); translate([-shaftD/2, -shaftD/2 + (shaftD - shaftFlat), 0]) cube([shaftD, shaftFlat, 12]); }
    translate([0, knobD/2 - 3.5, knobH - 0.6]) cylinder(d = 1.6, h = 1);
  }
}

// ---------- logo: «SKJOLD» som eget innfelt legeme ----------
// 0,6 mm dypt (3 lag), flukter med forsiden. Fet skrift 6,5 mm: strekene er ≥ 1 mm brede (0,4 mm dyse).
logoZ = 15.5; logoDepth = 0.6;               // under grillen, foran elektronikkrommet
module logo_2d() { text("SKJOLD", size = 6.5, font = "Liberation Sans:style=Bold", spacing = 1.25, halign = "center", valign = "center"); }
module logo_shape(e = 0) { translate([0, -fT - e, logoZ]) rotate([-90, 0, 0]) mirror([0, 1, 0]) linear_extrude(logoDepth + e) offset(e) logo_2d(); }
module logo() { logo_shape(0); }

// av/på-symbol (2D)
module power_icon(r) {
  difference() { circle(r); circle(r - 0.8); translate([-1.0, 0]) square([2.0, r + 1]); }
  translate([-0.4, -0.3]) square([0.8, r + 0.8]);
}

// ---------- TPU-membran over knapperaden ----------
// Flat forside med preget ring og ikon for hver tast (printes med forsiden ned); stempler bak trykker på taktbryterne.
module membran() { panel() membran_lok(); }
module membran_lok() {   // i panelets ramme: forsiden ved w = 0, stemplene ned
  difference() {
    union() {
      translate([0, btnV, -memT]) linear_extrude(memT) rrect(memW, memH, memR);
      for (x = btnX) translate([x, btnV, -plTip - tp]) cylinder(d = plD, h = plTip + tp - memT + 0.01);
    }
    for (i = [0:4]) translate([btnX[i], btnV, -0.4]) linear_extrude(0.41) {
      difference() { circle(d = keyD); circle(d = keyD - 1.0); }
      if (i == 0) power_icon(2.4); else text(str(i), size = 4.2, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
    }
  }
}

// ---------- pakninger og små TPU-deler (th = tykkelse; montert vises de sammenklemt) ----------
module pakning_front(th = gkT) { ytz(0, th) front_gk2d(gkB, 0); }
module pakning_bunn(th = gkT) { translate([0, 0, -th]) linear_extrude(th) bunn_gk2d(gkB); }
module pakning_skjerm(th = skjT) { panel() translate([0, dispV, -ruteT - th]) linear_extrude(th) skjerm_gk2d(); }
module rute() { panel() translate([0, dispV, -ruteT]) linear_extrude(ruteT) rrect(ruteW, ruteW, 1.5); }
module krage() { panel() translate([0, ec11V, -krageS]) difference() { cylinder(d = krageD - 0.4, h = krageS + 0.5); translate([0, 0, -1]) cylinder(d = 5.6, h = 4); } }
module dc_skive() { translate([dcX, D, connZ]) rotate([-90, 0, 0]) difference() { cylinder(d = 13, h = 1.0); translate([0, 0, -1]) cylinder(d = dcD + 0.1, h = 3); } }
module usb_propp() {
  translate([usbX, D, connZ]) rotate([-90, 0, 0]) {
    translate([0, 0, -t]) linear_extrude(t + 0.01) rrect(usbW - 0.2, usbH - 0.2, 1.5);
    linear_extrude(1.0) hull() { rrect(usbW + 5, usbH + 4, 2.5); translate([usbW/2 + 6, 0]) circle(d = usbH + 4); }   // flens med grep-flik
  }
}

// ---------- skjermklemme ----------
// Flat bøyle som presser skjermkortet inn i lomma (2 × M2,5 × 8 selvgjengende rett i frontplaten).
module skjermklemme() { panel() translate([0, dispV + pcbOffV, -tp - 2.4]) skjermklemme_lok(); }
module skjermklemme_lok() {
  difference() {
    linear_extrude(2.4) offset(2) offset(-2) square([2 * clampX + 8, 8], center = true);
    for (sx = [-1, 1]) translate([sx * clampX, 0, -1]) cylinder(d = 2.9, h = 5);
    translate([0, 0, -1]) linear_extrude(5) square([10, 3.2], center = true);   // plass til ledninger
  }
}

module samlet(ex = 0) {
  color(c_lys) kropp();
  color(c_mork) translate([0, -ex, 0]) front();
  color(c_grill) translate([0, -2.2 * ex, 0]) grill();
  color(c_mork) translate([0, 0, -ex]) bunn();
  color(c_gull) translate([0, 0, 0.8 * ex]) knott();
  color(c_gull) translate([0, -ex, 0]) logo();
  color(c_mork) translate([0, 0, -0.6 * ex]) skjermklemme();
  color(c_klar) translate([0, 0, 1.6 * ex]) rute();
  color(c_tpu) translate([0, -0.5 * ex, 0]) pakning_front(ex > 0 ? gkT : gkD);
  color(c_tpu) translate([0, 0, -0.5 * ex]) pakning_bunn(ex > 0 ? gkT : gkD);
  color(c_tpu) translate([0, 0, 1.1 * ex]) pakning_skjerm(ex > 0 ? skjT : skjS);
  color(c_tpu) translate([0, 0, 1.2 * ex]) membran();
  color(c_tpu) translate([0, 0, 0.5 * ex]) krage();
  color(c_tpu) translate([0, 0.5 * ex, 0]) dc_skive();
  color(c_tpu) translate([0, 0.5 * ex, 0]) usb_propp();
}

// ---------- utskriftsretning ----------
module fram_opp() { translate([0, 0, 0]) rotate([-90, 0, 0]) children(); }       // y → −z: baksiden (y = 0) ned, forsiden opp
if (part == "kropp") translate([0, 0, D]) rotate([-90, 0, 0]) kropp();                          // bakveggen ned
else if (part == "front") fram_opp() front();                                                    // baksiden ned, forsiden opp
else if (part == "logo") fram_opp() logo();                                                      // samme stilling som front
else if (part == "grill") translate([0, 0, fT]) rotate([90, 0, 0]) grill();                         // forsiden ned
else if (part == "bunn") rotate([180, 0, 0]) bunn();                                             // innsiden ned, føttene opp
else if (part == "knott") translate([0, 0, 0.6 + knobH]) rotate([180, 0, 0]) knott_lok();
else if (part == "skjermklemme") skjermklemme_lok();
else if (part == "rute") linear_extrude(ruteT) rrect(ruteW, ruteW, 1.5);
else if (part == "pakning_front") rotate([90, 0, 0]) pakning_front();
else if (part == "pakning_bunn") translate([0, 0, gkT]) pakning_bunn();
else if (part == "pakning_skjerm") linear_extrude(skjT) skjerm_gk2d();
else if (part == "membran") rotate([180, 0, 0]) membran_lok();                                   // forsiden ned, stemplene opp
else if (part == "krage") difference() { cylinder(d = krageD - 0.4, h = krageS + 0.5); translate([0, 0, -1]) cylinder(d = 5.6, h = 4); }
else if (part == "dc_skive") translate([0, 0, -D]) rotate([90, 0, 0]) dc_skive();
else if (part == "usb_propp") translate([0, 0, D + 1]) rotate([-90, 0, 0]) usb_propp();
else if (part == "eksplodert") samlet(25);
else if (part == "a_kropp") kropp(); else if (part == "a_front") front(); else if (part == "a_grill") grill();
else if (part == "a_bunn") bunn(); else if (part == "a_knott") knott(); else if (part == "a_logo") logo();
else if (part == "a_skjermklemme") skjermklemme(); else if (part == "a_rute") rute();
else if (part == "a_pakning_front") pakning_front(gkD); else if (part == "a_pakning_bunn") pakning_bunn(gkD);
else if (part == "a_pakning_skjerm") pakning_skjerm(skjS); else if (part == "a_membran") membran();
else if (part == "a_krage") krage(); else if (part == "a_dc_skive") dc_skive(); else if (part == "a_usb_propp") usb_propp();
else if (part == "takluft") panel() tak_hulrom();
else if (part == "luft") difference() {   // lydkammerets luft (for volumberegning)
  intersection() { Sin(); translate([-W, 0, zf + ft]) cube([2 * W, D, H]); }
  kropp();
  translate([portX, D - portL - 1, portZ]) rotate([-90, 0, 0]) cylinder(d = portD + 0.01, h = portL + 2);
}
else samlet();
