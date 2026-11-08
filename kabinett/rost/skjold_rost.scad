// Skjold Røst – liten aktiv høyttaler (3″ fullrange, bassrefleks) for bad, kjøkken og barnerom. Parametrisk OpenSCAD.
// Tåler damp (TPU-pakninger i skjøtene front/kropp og bunn, krage rundt EC11, DC-skive og USB-propp, ePTFE-ventil,
// vannavstøtende duk bak grillen, port bakover). Knappene på toppen er vanlige printede knappehetter og er IKKE tette.
// Skjerm og knapper sitter på toppen (flat topp, hevet knappelist og ramme rundt ruta), foran volumhjulet, i et eget rom
// under toppen («takrommet»), adskilt fra lydkammeret. Grillen er en løs del som trykkes på fronten med 4 tapper.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater (montert): x = bredde (−56…56), y = dybde (−fT = forsiden, 0 = skjøten front/kropp, D = bak),
// z = høyde (0 = underkant). Kropp og frontplate er skåret fra samme ytre form, så sidene flukter i skjøten.
// Bruk:  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_rost.scad
// part:  kropp | front | logo | grill | bunn | knott | rute | knapp | knapp_av | knapp_1 … knapp_4 |
//        pakning_front | pakning_bunn | krage | dc_skive | usb_propp | samlet | eksplodert
// STL-ene eksporteres liggende slik de skal printes (se utskriftsretning nederst).

part = "samlet";
ki = 0;                         // hvilken knapp for part="knapp_i"
skjerm = "glass";               // glass | nokkel (aktivt område i ren magenta, så lag_render.sh kan legge inn et skjermbilde)
$fn = 72;

// ---------- ytre mål ----------
// Totalhøyde med bunnbrett og gummiføtter: H + bT + footH = 145,5 mm (flat topp, avrundet bunn).
// Formen: én glatt, myk form. Ytterformen er en Minkowski-sum av en kjerne og en kule (r = 8,5), så alle kanter har
// samme radius og alle overganger er glatte (ingen fasetter). Foran: R8,5 rundt hele fronten, akkurat frontplatens
// tykkelse, så buen ender i skjøten. Bak: R28 i hjørnene sett ovenfra og R8,5 i toppkanten, begge som én bue som
// møter den flate bakveggen i en ren 45°-kant. Kroppen printes med bakveggen ned, og ingen flate står brattere enn 45°.
W = 112; D = 113; H = 134;      // kropp
s = 0;                          // toppen er flat
r = 8.5;                        // kantradius overalt (= frontplatens tykkelse)
Rb = 28;                        // hjørneradius bak sett ovenfra (én bue som møter bakveggen i 45°)
t = 2.6;                        // vegg (6 × 0,42 mm linjer)
zf = 26;  ft = 2.4;             // gulv mellom elektronikkrommet (under) og lydkammeret (over)
fT = 8.5;                       // frontplate (baffel)
// Bunnen er et lyst brett som fortsetter kroppen ned til bordet og runder av med samme R8,5 som toppen (nederst en
// 45°-fas, så brettet printes med gulvet ned uten støtte). Frontplaten går helt ned, så fronten er sort til bordet.
zB = -r;                        // undersiden (brettet er r = 8,5 mm høyt; kroppen begynner fortsatt på z = 0)
bT = -zB; footH = 3;            // (bT = brettets høyde) · selvklebende gummiføtter Ø12 × 3 mm i forsenkninger
flT = 2.4;                      // brettets gulv
bfas = r * (1 - cos(45));       // 45°-fasen nederst: fra der buen står 45° og rett ned til undersiden

// ---------- pakninger (TPU 95A) ----------
gkW = 1.8; gkD = 1.0;           // spor: bredde og dybde
gkB = 1.6; gkT = 1.2;           // pakning: bredde og tykkelse (klemmes 0,2 mm)
rimW = 2.4; rimT = 2.0;         // leppe innvendig i kroppen som frontplaten ligger mot
seamW = 0.5; seamD = 0.4;       // skyggefuge rundt skjøten: 0,5 mm inn, 2 × 0,4 mm bred

// ---------- element og port ----------
// elementet: mål fra malen i ../elementer/elementer.scad (velg med element = "...", eller legg inn ditt eget der)
include <../elementer/elementer.scad>
element = "rs75_4";
E = el_data(element);
drvCut = el_utsp(E);            // utsparing
drvRecD = 2.5;                  // forsenkning for elementets ramme (rammens form og mål fra malen, 0,3 mm klaring)
drvScrew = 2.6;                 // skruehull (M3 selvgjengende)
drvZ = 75;                      // elementets senter
portD = 16; portW = 2.0;        // port innv. Ø og vegg
portL = 78;                     // portlengde fra munningen bak → fb ≈ 84 Hz (se LES_MEG.md)
portZ = 40; portX = -26; portFlare = 8; // lavt i bakveggen, til siden for magneten, peker bakover. Munningen: bue R8 som møter bakveggen i 45°

// ---------- fester ----------
ins = 4.0;  insD = 6.5;         // M3 innpressmutter (Ø4,0 hull, 6,5 dyp)
boss = 8.4;
m3 = 3.4; m3k = 6.4;            // M3 senkeskrue: hull og senkehode
bx = 40;                        // bunnens skruetårn i x (innenfor den avrundede underkanten, så skruehodene ligger i det flate)
by = [9, 84];                   // bunnens skruetårn i y
fz = [36, 109];                 // frontplatens skruer (skjult bak grillen)
fbx = 40;                       // frontskruenes x: senkehodet ligger i grill-lomma, tårnet har ribbe til sideveggen

// ---------- toppen: skrå flate z = topz(y) ----------
kS = s / (D + fT);              // fall per mm
aS = atan(kS);
function topz(y) = H - kS * (D - y);
z0 = topz(0);                   // toppen ved skjøten front/kropp
// Lokal ramme for toppanelet: x som før, v langs toppen (fra y = 0 og bakover), w ut av toppen (w = 0 er overflaten).
module panel() { translate([0, 0, z0]) rotate([aS, 0, 0]) children(); }
tp = 7.5;                       // toppanelets tykkelse over takrommet (rute + skjermlomme / knappehetter)
hR = 8.5;                       // takrommets høyde under panelet
cT = 3.0;                       // takrommets gulv («himling» over lydkammeret)
vB = 63;                        // takrommets bakkant (lokal v); bakveggen heller 45° opp til panelet
fw = 2.0;                       // takrommets frontvegg (y = 0…2) – frontplaten trenger ikke tette takrommet

// ---------- betjening ----------
ec11V = 88; ec11D = 7.2;        // EC11-aksel gjennom toppen, bakerst (står vinkelrett på toppen)
krageD = 12.4; krageS = 1.2;    // forsenkning for TPU-kragen rundt akselen
micX = 40;  micZ = 14; micD = 1.6;   // valgfri INMP441-mikrofon i fronten (ePTFE-akustikkmembran limes på innsiden)

// ---------- skjerm: 2,42″ OLED 128×64 (SSD1309, I²C, hvit) bak klar rute, i toppen ----------
// Mål fra produsentens tegning (mål din modul og juster): kort 70,08 × ca. 39 mm med 4 hull (Ø3, 62 mm i bredden),
// glass ca. 60 × 30,5 mm og 3,25 mm tykt, aktivt område 55,4 × 27,7 mm, flatkabel nederst på midten (12,6 mm),
// pinnerad (GND VDD SCK SDA) øverst. Toppen av modulen («øverst») vender bakover mot volumhjulet.
dispV = 43;                      // senter av det aktive området (lokal v)
actW = 55.4; actH = 27.7;        // aktivt område
winW = actW + 0.6; winH = actH + 0.6;   // vindu (0,3 mm klaring), 45° fas utover mot ruta
glW = 60.0; glH = 30.5; glT = 3.25;     // glass (lomme nedenfra med 0,4 mm klaring)
glOffV = 0;                      // glassets senter i forhold til det aktive området (v)
pcbW = 70.08; pcbH = 39.0;       // kretskort
pcbOffV = 0;                     // kortets senter i forhold til glasset (v)
dHoleX = 31.0; dHoleV = 16.5;    // monteringshull (± fra kortets senter): 62 mm i bredden, mål avstanden i høyden
fpcW = 12.6; fpcL = 3.0;         // flatkabelen bretter rundt glasskanten foran (mot knappene)
ruteW = 64; ruteH = 36; ruteT = 1.5;    // klar rute (akryl 1,5 mm eller klar PETG) i toppen
tapeT = 0.2;                     // tynn dobbeltsidig skumtape / lim under ruta (ikke TPU)
ruteRec = ruteT + tapeT;         // forsenkning for rute + tape (ruta flukter med toppen)
pcbV = dispV + glOffV + pcbOffV; // kortets senter (v)

// ---------- knapper: av/på + favoritt 1–4 som printede knappehetter, foran skjermen ----------
// Hetten går gjennom et hull i toppen og har en flens under toppanelet, så den ikke faller ut. Den hviler med en
// liten nupp på taktbryteren (0,15 mm forspenning) – fjæra i bryteren holder flensen opp mot panelet.
lipB = 1.6;                      // bredden på den hevede rammen rundt ruta og knappelista
barW = 64 + 0.4 + 2 * lipB;      // knappelista er like bred som rammen rundt ruta (ruteW + 0,4 + 2 · lipB)
barH = 9.5 + 2 * lipB;           // capHole + 2 · lipB
btnS = (barW - barH) / 4;        // 13,7 mm mellom knappene
btnV = 11; btnX = [for (i = [0:4]) (i - 2) * btnS];  // [0] = av/på
capD = 9.0; capHole = 9.5;       // hette og hull (0,25 mm klaring rundt)
capUp = 1.1;                     // hetten står 1,1 mm over toppen (0,6 mm over leppa rundt hullet), svakt avrundet
lip = 0.5;                       // knappelista og rammen rundt ruta står 0,5 mm over toppen: vann på den flate toppen renner rundt, ikke ned i hullene
flD = 12.0; flT = 0.9;           // flens under panelet
nubD = 3.0;                      // nupp mot bryterens stempel
tactH = 5.0;                     // 6 × 6 × 5 mm taktbryter (stempel 1,5 mm over huset)
boardW = tp + 6.0;               // hullkortets overside under toppflaten (M2 × 6 mm avstandsstykker)
swTop = -(boardW - tactH);       // toppen av bryterens stempel (w)
nubTip = swTop - 0.15;           // nuppens spiss: 0,15 mm forspenning
boardHoles = [[-38, btnV], [38, btnV]];
// bak: port, DC og USB-C på én loddrett linje (x = ioX) med like store mellomrom, og Skjold-merket preget over dem
ioX = -26;                       // samme x som porten (porten må stå til siden for elementets magnet)
dcD = 8.2;  usbW = 10; usbH = 4.4; dcX = ioX; usbX = ioX; dcZ = 19.5; usbZ = 7;
merkeS = 0.36; merkeT = 1.0; merkeZ = 64;   // Skjold-merket (fem staver), 14,4 × 15 mm, 1 mm dypt
ventD = 12.5; ventP = [25, 60];  // ePTFE-trykkutjevning (M12 × 1,5) i bunnen av elektronikkrommet
knobD = 34; knobH = 14; shaftD = 6.1; shaftFlat = 4.6;
wireV = 50; wireX = 30;          // ledningsgjennomføring takrom → lydkammer → elektronikkrom (tettes med lim)

// ---------- grill: løs del foran frontplaten (som første Røst), festet med 4 tapper ----------
// Tappene har tre små klemribber, så grillen sitter stramt uten å rasle men kan trekkes av. Akustisk duk klemmes
// mellom grillen og frontplaten (gGap = luft til duken).
gT = 2.4; gGap = 0.6; gP = gT + gGap;
pinD = 3.0; pinHole = 3.3; ribH = 0.25; pinL = 3.6;
gW = 93; gZ0 = 31; gZ1 = z0 - r - 2;
gPins = [[-24, gZ0 + 4], [24, gZ0 + 4], [-24, gZ1 - 4], [24, gZ1 - 4]];

c_lys = [0.93,0.92,0.90]; c_mork = [0.13,0.13,0.14]; c_gull = [0.85,0.62,0.25]; c_grill = [0.18,0.18,0.19];
c_tpu = [0.86,0.85,0.82]; c_knapp = [0.18,0.18,0.19]; c_klar = [0.80,0.90,0.95,0.45];   // TPU naturhvit, så den blander seg med den lyse kroppen

// ---------- hjelpere ----------
module rrect(w, h, r) { offset(r) offset(-r) square([w, h], center = true); }
module ytz(y0, y1) { translate([0, y0, 0]) rotate([-90, 0, 0]) linear_extrude(y1 - y0) mirror([0, 1, 0]) children(); } // 2D i (x, z) → y0…y1
// Ytre form S = minkowski(kjerne, K). Kjernen er grunnrisset (skarpe hjørner foran, bue Rb − r bak som ender i 45°)
// ekstrudert langs z. K er en kule med radius r, skåret av der normalen står 45° fra bakveggen. Bakveggen blir flat med
// en jevn 45°-kant rundt, alle andre flater står minst 45° fra den (printes uten støtte med bakveggen ned).
c45 = cos(45);
module K(rr, kutt) { intersection() { sphere(rr / cos(180 / 48), $fn = 48);   // ($fn-kula er innskrevet: skaler så polene og ekvator når rr)
 translate([-rr - 1, -rr - 1, -rr - 1]) cube([2 * rr + 2, rr + 1 + kutt, 2 * rr + 2]); } }
module kjerne2d(yf) {   // y = yf foran; bak ved y = D − r·cos45
  intersection() {
    hull() {
      for (sx = [-1, 1]) translate([sx * (W/2 - Rb), D - Rb * c45]) circle(Rb - r, $fn = 120);
      for (sx = [-1, 1]) translate([sx * (W/2 - r), yf]) square(0.01, center = true);
    }
    translate([-W, yf - 1]) square([2 * W, D - r * c45 - yf + 1]);
  }
}
// grunnrisset (snittet av S under toppkantene): R8,5 foran, R28 bak som møter bakveggen i 45°
module plan2d(o = 0) {
  offset(delta = o) intersection() {
    hull() {
      for (sx = [-1, 1]) translate([sx * (W/2 - Rb), D - Rb * c45]) circle(Rb, $fn = 144);
      for (sx = [-1, 1]) translate([sx * (W/2 - r), -fT + r]) circle(r);
    }
    translate([-W, -fT - 1]) square([2 * W, D + fT + 1]);
  }
}
// tverrsnitt (x, z) foran: rette sider, R8,5 i toppen
module front2d(o = 0) {
  offset(delta = -o) hull() { translate([-W/2, -2]) square([W, 1]); for (sx = [-1, 1]) translate([sx * (W/2 - r), H - r]) circle(r); }
  if (o > 0) translate([-W/2 + o, -5]) square([W - 2 * o, H / 2 + 5]);
}
// skjær z med y, så et flatt lag blir parallelt med toppen (toppen er flat nå, s = 0)
module shear() { multmatrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, kS, 1, 0], [0, 0, 0, 1]]) children(); }
module S() {
  intersection() {
    union() {
      minkowski() { translate([0, 0, zB + r]) linear_extrude(H - zB - 2 * r) kjerne2d(-fT + r); K(r, r * c45); }
      // 45°-fas nederst: fyller under buen fra der den står 45° (bfas over undersiden) rett ned, så den printes uten støtte
      hull() {
        translate([0, 0, zB]) linear_extrude(0.01) plan2d(-2 * bfas + 0.3);
        translate([0, 0, zB + bfas + 0.8]) linear_extrude(0.01) plan2d(-bfas + 1.1);   // 0,3 mm utenfor tangenten og litt forbi: dekker kulefasettene (> 50°)
      }
    }
    translate([-W, -fT - 1, zB]) cube([2 * W, D + fT + 2, H - zB + 1]);
  }
}
// innvendig hulrom: veggene og toppen t (åpent nedover og forover)
module Sin() { minkowski() { translate([0, 0, -20]) linear_extrude(H - r + 20) kjerne2d(-30); K(r - t, r * c45 - t); } }
// tverrsnitt i (x, z) i skjøten (y = 0): rette sider, R8,5 i toppen
module snitt2d(o = 0) { front2d(-o); }
module skyggefuge() { ytz(-seamD, seamD) difference() { snitt2d(1); snitt2d(-seamW); } }
// U-spor og U-pakning i skjøten (sider + under takrommet + over gulvet), i (x, z)
xi = W/2 - t;                   // innsiden av sideveggen
cBot0 = z0 - tp - hR - cT;      // undersiden av takrommets gulv ved y = 0 (lydkammerets tak foran)
gkTop = cBot0 + 0.6;            // øverste pakningslist ligger i forkanten av takrommets gulv
// Frontpakningen (U) ender på bunnpakningen i z = 0; skjøten mellom frontplaten og brettet har solid vegg bak seg,
// og ringen på toppen av brettet tetter mot kroppen (også langs forkanten).
module front_gk2d(w, zs = -1) {
  for (sx = [-1, 1]) translate([sx * (xi - w/2) - w/2, zs]) square([w, gkTop + w - zs]);
  translate([-xi, gkTop]) square([2 * xi, w]);
  translate([-xi, zf + 0.4 - w/2]) square([2 * xi, w]);
}
module bunnplan(o = 0) { offset(delta = o) intersection() { plan2d(); translate([-W, 0]) square([2 * W, D + 1]); } }   // brettet: bak skjøten y = 0
module bunn_gk2d(w) { difference() { bunnplan(-1.5 + w/2); bunnplan(-1.5 - w/2); } }   // ring 1,5 mm inn fra kanten av brettet
// takrommet i panelets ramme: hulrom (w < 0 er under overflaten) og hele blokka (hulrom + gulv + bakvegg)
module tak_hulrom() {   // (1,5 mm fra sideveggene, så de avrundede toppkantene beholder veggtykkelsen)
  translate([0, 0, 0]) rotate([90, 0, 90]) translate([0, 0, -xi + 1.5]) linear_extrude(2 * xi - 3)
    polygon([[fw, -tp], [fw, -tp - hR], [vB, -tp - hR], [vB + hR, -tp]]);
}
module tak_blokk() {
  rotate([90, 0, 90]) translate([0, 0, -xi - 0.01]) linear_extrude(2 * xi + 0.02)
    polygon([[-0.01, 0.5], [-0.01, -tp - hR - cT], [vB + 3 * sqrt(2) - cT, -tp - hR - cT], [vB + 3 * sqrt(2) + hR + tp + 0.5, 0.5]]);   // bakveggen 3 mm, 45°
}

// ---------- kropp ----------
// Den flate toppen har en 0,5 mm hevet knappelist og en like høy ramme rundt skjermruta (samme bredde og radius), og TPU-kragen
// tetter volumhjulet. Vann på toppen blir stående i et tynt lag og renner av over de avrundede kantene, ikke ned i hullene.
module lepper() {
  panel() translate([0, 0, -0.01]) linear_extrude(lip + 0.01) {
    translate([0, dispV]) difference() { rrect(ruteW + 0.4 + 2 * lipB, ruteH + 0.4 + 2 * lipB, 2.2 + lipB); rrect(ruteW + 0.4, ruteH + 0.4, 2.2); }   // ramme rundt ruta
    translate([0, btnV]) difference() { rrect(barW, barH, 2.2 + lipB); for (x = btnX) translate([x, 0]) circle(d = capHole); }       // knappelista
  }
}
module kropp() {
  difference() {
    union() { kropp_basis(); lepper(); }
    panel() for (x = btnX) translate([x, btnV, lip - 0.6]) cylinder(d1 = capHole, d2 = capHole + 1.2, h = 0.61);   // fas i knappehullene
  }
}
// portens munning: bue med radius portFlare fra boringen til 45° mot bakveggen (h = dybde inn fra bakveggen)
module port_munning() {
  hc = portFlare * c45;
  rotate_extrude($fn = 72) polygon(concat([[0, -1], [portD/2 + portFlare * (1 - c45), -1]],
    [for (a = [45:-5:0]) [portD/2 + portFlare * (1 - cos(a)), hc - portFlare * sin(a)]], [[portD/2, hc + 1], [0, hc + 1]]));
}
// Skjold-merket: fem avrundede staver (som branding/skjold/skjold_merke.svg), sentrert
module merke2d(sc) {
  scale(sc) for (b = [[1, 22], [9, 33], [18.7, 42], [28.4, 33], [36.4, 22]])
    translate([b[0] - 21, 21 - b[1]]) hull() for (y = [2.3, b[1] - 2.3]) translate([2.3, y]) circle(2.3, $fn = 24);
}
module kropp_basis() {
  difference() {
    intersection() {
      S();
      translate([-W, 0, 0]) cube([2 * W, D + 1, H + 2]);
      union() {
        difference() { S(); Sin(); }
        intersection() { Sin(); panel() tak_blokk(); }                  // takrommet (fylles, hulrommet trekkes fra under)
        translate([-W/2, 0, zf]) cube([W, D, ft]);                       // gulv
        translate([-xi, 0, zf - 1.6]) cube([2 * xi, 4, ft + 1.6]);      // forkant på gulvet (pakningen ligger her)
        intersection() { Sin(); ytz(0, rimT) difference() { translate([-xi, -1]) square([2 * xi, H]); translate([-xi + rimW, -2]) square([2 * (xi - rimW), cBot0 - rimW + 2]); } }
        // bassrefleksport (bak)
        translate([portX, D - portL, portZ]) rotate([-90, 0, 0]) cylinder(d = portD + 2 * portW, h = portL);
        translate([portX, D - 9, portZ]) rotate([-90, 0, 0]) cylinder(d = portD + 2 * portW + 6, h = 9);   // krage rundt den utvidede munningen
        // frontplatens skruetårn, med ribbe ut til sideveggen
        for (sx = [-1, 1], z = fz) hull() {
          translate([sx * fbx, 0, z]) rotate([-90, 0, 0]) cylinder(d = boss, h = D - t + 0.01);
          translate([sx * (xi + 0.2) - 0.3, 0, z - (xi - fbx)]) cube([0.6, D - t + 0.01, 2 * (xi - fbx)]);   // ribba heller ≤ 45° (printes uten støtte)
        }
        // bunnplatens skruetårn (langs z), 45°-kile mot bakveggen så de printes uten støtte
        for (sx = [-1, 1], y = by) translate([sx * bx, y, 0]) {
          cylinder(d = boss, h = zf);
          hull() { cylinder(d = boss, h = zf); translate([sx * (boss/2 - 0.5), boss/2 + 3, 0]) cube([1, 1, zf]); }   // 45°-kile (under i printretningen)
        }
      }
    }
    // innpressmuttere
    for (sx = [-1, 1], z = fz) translate([sx * fbx, -0.01, z]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD);
    for (sx = [-1, 1], y = by) translate([sx * bx, y, -0.01]) cylinder(d = ins, h = insD);
    // portboring med avrundet munning bak
    translate([portX, D - portL - 1, portZ]) rotate([-90, 0, 0]) cylinder(d = portD, h = portL + 2);
    translate([portX, D, portZ]) rotate([90, 0, 0]) port_munning();
    // takrommet (lukket rom under toppen for skjerm og knapper)
    panel() tak_hulrom();
    panel() {
      // EC11 gjennom toppen + forsenkning for TPU-kragen
      translate([0, ec11V, -t - 1]) cylinder(d = ec11D, h = t + 2);
      translate([0, ec11V, -krageS]) cylinder(d = krageD, h = krageS + 1);
      // skjerm: forsenkning for rute + tape, vindu med fas, lomme nedenfra for glasset og flatkabelen, skruehull
      translate([0, dispV, -ruteRec - 0.03]) linear_extrude(ruteRec + 0.04) rrect(ruteW + 0.4, ruteH + 0.4, 2.2);
      hull() {
        translate([0, dispV, -tp + glT - 0.01]) linear_extrude(0.01) square([winW, winH], center = true);
        translate([0, dispV, -ruteRec - 0.01]) linear_extrude(0.02) square([winW + 2 * (tp - glT - ruteRec), winH + 2 * (tp - glT - ruteRec)], center = true);
      }
      translate([0, dispV + glOffV, -tp - 0.01]) linear_extrude(glT + 0.01) square([glW + 0.8, glH + 0.8], center = true);
      translate([0, dispV + glOffV - glH/2 - fpcL/2, -tp - 0.01]) linear_extrude(glT + 0.01) square([fpcW + 1.0, fpcL + 1.0], center = true);
      for (sx = [-1, 1], sv = [-1, 1]) translate([sx * dHoleX, pcbV + sv * dHoleV, -tp - 0.01]) cylinder(d = 1.8, h = 4.5);   // M2 selvgjengende
      // knapper: hull for hettene (fas på kanten), hull for knappekortets avstandsstykker
      for (x = btnX) translate([x, btnV, -tp - 1]) cylinder(d = capHole, h = tp + 2);
      for (b = boardHoles) translate([b[0], b[1], -tp - 0.01]) cylinder(d = 1.7, h = 4.0);
      // ledninger fra takrommet ned i lydkammeret (tettes med lim)
      translate([wireX, wireV, -tp - hR - cT - 1]) cylinder(d = 6, h = cT + 2);
    }
    // gjennomføring for høyttalerkabel i gulvet (tettes med lim)
    translate([wireX, 85, zf - 1]) cylinder(d = 6, h = ft + 2);
    // bak: DC-kontakt og USB-C (ESP32) i elektronikkrommet
    translate([dcX, D - t - 1, dcZ]) rotate([-90, 0, 0]) cylinder(d = dcD, h = t + 2);
    translate([dcX, D + 0.01, dcZ]) rotate([90, 0, 0]) cylinder(d1 = dcD + 1.2, d2 = dcD, h = 0.61);   // 0,6 mm fas
    translate([usbX, D - t - 1, usbZ]) rotate([-90, 0, 0]) linear_extrude(t + 2) rrect(usbW, usbH, 1.6);
    translate([usbX, D + 0.01, usbZ]) rotate([90, 0, 0]) hull() { linear_extrude(0.01) rrect(usbW + 1.2, usbH + 1.2, 2.2); translate([0, 0, 0.6]) linear_extrude(0.01) rrect(usbW, usbH, 1.6); }
    // spor for frontpakningen og skyggefuge
    ytz(-0.01, gkD) front_gk2d(gkW);
    skyggefuge();
    // Skjold-merket preget i bakveggen, over porten
    translate([ioX, D + 0.01, merkeZ]) rotate([90, 0, 0]) linear_extrude(merkeT + 0.01) merke2d(merkeS);
  }
}

// ---------- frontplate (baffel) ----------
module front() {
  difference() {
    intersection() { S(); translate([-W, -fT - 1, zB - 1]) cube([2 * W, fT + 1, H - zB + 2]); }
    skyggefuge();
    // hull for grillens tapper
    for (p = gPins) translate([p[0], -fT - 0.01, p[1]]) rotate([-90, 0, 0]) cylinder(d = pinHole, h = pinL + 0.3);
    // element: utsparing, forsenkning for rammen og skruehull
    translate([0, 1, drvZ]) rotate([90, 0, 0]) cylinder(d = drvCut, h = fT + 2);
    translate([0, -fT - 0.01, drvZ]) rotate([-90, 0, 0]) linear_extrude(drvRecD) el_ramme2d(E, 0.3);
    for (p = el_hullpos(E)) translate([p[0], 1, drvZ + p[1]]) rotate([90, 0, 0]) cylinder(d = drvScrew, h = fT + 2);
    // frontskruer (senkehode i forsiden, skjult bak grillen)
    for (sx = [-1, 1], z = fz) translate([sx * fbx, 1, z]) rotate([90, 0, 0]) {
      cylinder(d = m3, h = fT + 2);
      translate([0, 0, 1 + fT - 1.8]) cylinder(d1 = m3, d2 = m3k, h = 1.81);
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
      translate([0, -fT - gP, 0]) rotate([-90, 0, 0]) linear_extrude(gT) translate([0, -(gZ0 + gZ1)/2]) rrect(gW, gZ1 - gZ0, 9);
      for (p = gPins) translate([p[0], -fT - gGap - 0.01, p[1]]) rotate([-90, 0, 0]) {
        cylinder(d = pinD, h = gGap + pinL);
        for (a = [0, 120, 240]) rotate([0, 0, a]) translate([pinD/2 - 0.3, -0.35, gGap + 0.6]) cube([0.3 + ribH, 0.7, pinL - 1.0]);   // klemribber
        translate([0, 0, gGap + pinL]) cylinder(d1 = pinD, d2 = pinD - 0.8, h = 0.01);
      }
    }
    // sekskantmønster
    for (i = [-9:9], j = [0:24]) {
      x = i * 5.2 + (j % 2) * 2.6; z = gZ0 + 6 + j * 4.5;
      if (abs(x) < gW/2 - 5 && z < gZ1 - 5 && !(abs(abs(x) - 24) < 3.5 && (abs(z - gZ0 - 4) < 3.5 || abs(z - gZ1 + 4) < 3.5)))
        translate([x, -fT - gP - 1, z]) rotate([-90, 0, 0]) rotate([0, 0, 30]) cylinder(d = 4.2, h = gT + 2, $fn = 6);
    }
  }
}

// ---------- bunn: dryppkant, føtter, spor for TPU-pakning, ePTFE-ventil ----------
module bunn() {
  difference() {
    intersection() {
      S();
      translate([-W, 0, zB]) cube([2 * W, D + 1, -zB]);   // brettet: bak skjøten, under kroppen
      union() {
        difference() {
          translate([-W, 0, zB - 1]) cube([2 * W, D + 1, -zB + 1]);
          // lomma ovenfra: rette vegger t, og et skrått fall mot gulvet langs buen (vegg ≥ t overalt)
          intersection() {
            hull() {
              translate([0, 0, zB + r]) linear_extrude(-zB - r + 1) plan2d(-t);
              translate([0, 0, zB + flT]) linear_extrude(0.01) plan2d(-(r + 0.6));
            }
            translate([-W, t, zB]) cube([2 * W, D, -zB + 2]);
          }
        }
        for (sx = [-1, 1], y = by) translate([sx * bx, y, zB]) cylinder(d = boss, h = -zB);   // skruetårn opp til kroppen
      }
    }
    translate([0, 0, -gkD]) linear_extrude(gkD + 0.01) bunn_gk2d(gkW);                                   // pakningsspor i kanten
    translate([0, 0, zB - 0.01]) linear_extrude(0.8) difference() { bunnplan(-2 * bfas - 1.2); bunnplan(-2 * bfas - 1.7); }   // dryppnese
    for (sx = [-1, 1], y = by) translate([sx * bx, y, zB - 1]) { cylinder(d = m3, h = -zB + 2); cylinder(d1 = m3k + 2, d2 = m3, h = 1 + (m3k + 2 - m3)/2); }
    translate([ventP[0], ventP[1], zB - 1]) cylinder(d = ventD, h = flT + 2);
    for (sx = [-1, 1], y = [14, D - 16]) translate([sx * 32, y, zB - 0.01]) cylinder(d = 12.4, h = 0.6);   // forsenkninger for gummiføttene
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

// ---------- knappehetter (PETG) ----------
// i = 0: av/på, 1–4: favoritter. Pregede ikoner (0,4 mm) i toppen. Printes med toppen ned (flensen opp – ingen overheng
// siden toppen er nesten flat; den svake avrundingen er 0,3 mm).
module knapp_lok(i) {   // i panelets ramme med hullets senter i origo: toppen ved w = capUp
  difference() {
    union() {
      translate([0, 0, -tp]) cylinder(d = capD, h = tp + capUp - 0.3);
      translate([0, 0, capUp - 0.3]) cylinder(d1 = capD, d2 = capD - 0.8, h = 0.3);
      translate([0, 0, -tp - flT]) cylinder(d = flD, h = flT);          // flens under panelet
      translate([0, 0, nubTip]) cylinder(d = nubD, h = -tp - flT - nubTip + 0.01);  // nupp mot bryteren
    }
    translate([0, 0, capUp - 0.4]) linear_extrude(0.41) {
      if (i == 0) power_icon(2.4); else text(str(i), size = 4.6, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
    }
  }
}
module knapper() { panel() for (i = [0:4]) translate([btnX[i], btnV, 0]) knapp_lok(i); }

// ---------- pakninger og små TPU-deler (th = tykkelse; montert vises de sammenklemt) ----------
module pakning_front(th = gkT) { ytz(0, th) front_gk2d(gkB, 0); }
module pakning_bunn(th = gkT) { translate([0, 0, -th]) linear_extrude(th) bunn_gk2d(gkB); }
module rute() { panel() translate([0, dispV, -ruteT]) linear_extrude(ruteT) rrect(ruteW, ruteH, 2); }
module krage() { panel() translate([0, ec11V, -krageS]) difference() { cylinder(d = krageD - 0.4, h = krageS + 0.5); translate([0, 0, -1]) cylinder(d = 5.6, h = 4); } }
module dc_skive() { translate([dcX, D, dcZ]) rotate([-90, 0, 0]) difference() { cylinder(d = 13, h = 1.0); translate([0, 0, -1]) cylinder(d = dcD + 0.1, h = 3); } }
module usb_propp() {
  translate([usbX, D, usbZ]) rotate([-90, 0, 0]) {
    translate([0, 0, -t]) linear_extrude(t + 0.01) rrect(usbW - 0.2, usbH - 0.2, 1.5);
    linear_extrude(1.0) hull() { rrect(usbW + 5, usbH + 4, 2.5); translate([usbW/2 + 6, 0]) circle(d = usbH + 4); }   // flens med grep-flik
  }
}

// aktivt område på OLED-en (55,4 × 27,7 mm, 128 × 64), på glasset – brukes bare i bildene
module skjermflate() { panel() translate([0, dispV, -tp + glT + 0.02]) linear_extrude(0.02) square([actW, actH], center = true); }
// ---------- skjermmodulen (bare for visning og kollisjonssjekk, printes ikke) ----------
module skjerm() {
  panel() {
    translate([0, dispV + glOffV, -tp]) color([0.05,0.05,0.06]) linear_extrude(glT) square([glW, glH], center = true);
    translate([0, pcbV, -tp - 1.6]) color([0.1,0.25,0.15]) difference() {
      linear_extrude(1.6) square([pcbW, pcbH], center = true);
      for (sx = [-1, 1], sv = [-1, 1]) translate([sx * dHoleX, sv * dHoleV, -1]) cylinder(d = 3, h = 4);
    }
  }
}

// lag_render.sh setter fra_stl = true: da hentes de store delene fra asm/ (laget av lag_stl.sh). Forhåndsvisningen av
// render() i OpenSCAD 2021 skygger enkelte store flater feil (mørk bakvegg), de eksporterte nettene gjør det ikke.
fra_stl = false;
module del(navn) { if (fra_stl) import(str("asm/", navn, ".stl")); else render(convexity = 6) children(); }

module foetter() { for (sx = [-1, 1], y = [14, D - 16]) translate([sx * 32, y, zB + 0.6 - footH]) cylinder(d = 12, h = footH); }   // selvklebende gummiføtter
module samlet(ex = 0) {
  color(c_lys) del("kropp") kropp();
  color(c_mork) translate([0, -ex, 0]) del("front") front();
  color(c_grill) translate([0, -2.2 * ex, 0]) del("grill") grill();
  color(c_lys) translate([0, 0, -ex]) del("bunn") bunn();   // bunnen i samme lyse farge som kroppen
  color([0.25, 0.25, 0.26]) translate([0, 0, -1.6 * ex]) foetter();
  color(c_gull) translate([0, 0, 0.8 * ex]) knott();
  color(c_gull) translate([0, -ex, 0]) logo();
  translate([0, 0, -0.6 * ex]) skjerm();
  if (skjerm == "nokkel") color([1, 0, 1]) translate([0, 0, 1.6 * ex]) skjermflate();
  else color(c_klar) translate([0, 0, 1.6 * ex]) rute();
  color(c_tpu) translate([0, -0.5 * ex, 0]) pakning_front(ex > 0 ? gkT : gkD);
  color(c_tpu) translate([0, 0, -0.5 * ex]) pakning_bunn(ex > 0 ? gkT : gkD);
  color(c_knapp) translate([0, 0, 1.2 * ex]) knapper();
  color(c_tpu) translate([0, 0, 0.5 * ex]) krage();
  color(c_tpu) translate([0, 0.5 * ex, 0]) dc_skive();
  color(c_tpu) translate([0, 0.5 * ex, 0]) usb_propp();
}

// ---------- utskriftsretning ----------
module fram_opp() { translate([0, 0, 0]) rotate([-90, 0, 0]) children(); }       // y → −z: baksiden (y = 0) ned, forsiden opp
if (part == "kropp") translate([0, 0, D]) rotate([-90, 0, 0]) kropp();                          // bakveggen ned
else if (part == "front") fram_opp() front();                                                    // baksiden ned, forsiden opp
else if (part == "logo") fram_opp() logo();                                                      // samme stilling som front
else if (part == "grill") translate([0, 0, fT + gP]) rotate([90, 0, 0]) grill();                    // forsiden ned, tappene opp
else if (part == "bunn") translate([0, 0, -zB]) bunn();                                          // gulvet ned (45°-fasen nederst, ingen støtte)
else if (part == "knott") translate([0, 0, 0.6 + knobH]) rotate([180, 0, 0]) knott_lok();
else if (part == "rute") linear_extrude(ruteT) rrect(ruteW, ruteH, 2);
else if (part == "pakning_front") rotate([90, 0, 0]) pakning_front();
else if (part == "pakning_bunn") translate([0, 0, gkT]) pakning_bunn();
else if (part == "knapp") for (i = [0:4]) translate([i * (flD + 3), 0, capUp]) rotate([180, 0, 0]) knapp_lok(i);   // alle fem, toppen ned
else if (part == "knapp_i") translate([0, 0, capUp]) rotate([180, 0, 0]) knapp_lok(ki);
else if (part == "krage") difference() { cylinder(d = krageD - 0.4, h = krageS + 0.5); translate([0, 0, -1]) cylinder(d = 5.6, h = 4); }
else if (part == "dc_skive") translate([0, 0, -D]) rotate([90, 0, 0]) dc_skive();
else if (part == "usb_propp") translate([0, 0, D + 1]) rotate([-90, 0, 0]) usb_propp();
else if (part == "eksplodert") samlet(25);
else if (part == "skjermflate") color([1, 0, 1]) skjermflate();
else if (part == "a_kropp") kropp(); else if (part == "a_front") front(); else if (part == "a_grill") grill();
else if (part == "a_bunn") bunn(); else if (part == "a_knott") knott(); else if (part == "a_logo") logo();
else if (part == "a_skjerm") skjerm(); else if (part == "a_rute") rute();
else if (part == "a_pakning_front") pakning_front(gkD); else if (part == "a_pakning_bunn") pakning_bunn(gkD);
else if (part == "a_knapp") knapper();
else if (part == "a_krage") krage(); else if (part == "a_dc_skive") dc_skive(); else if (part == "a_usb_propp") usb_propp();
else if (part == "takluft") panel() tak_hulrom();
else if (part == "luft") difference() {   // lydkammerets luft (for volumberegning)
  intersection() { Sin(); translate([-W, 0, zf + ft]) cube([2 * W, D, H]); }
  kropp();
  translate([portX, D - portL - 1, portZ]) rotate([-90, 0, 0]) cylinder(d = portD + 0.01, h = portL + 2);
}
else samlet();
