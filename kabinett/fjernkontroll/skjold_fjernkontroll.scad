// Skjold Fjernkontroll – universell fjernkontroll med 2,8″ fargeberøringsskjerm, 14 taster (full variant 30), IR og Wi-Fi. Parametrisk OpenSCAD.
// Eget Skjold-design: en rett, flat «plate» med myke R11-hjørner sett ovenfra og 45°-fas rundt topp- og bunnkanten
// (ingen innsnevring på midten). Toppen er lys (eller mørk), bunnen mørk, delt i en rett skjøt rundt hele siden.
// Gullring rundt OK, gull Skjold-tast under skjermen, SKJOLD i gull felt inn nederst. Tastene er egne hetter som holdes
// av toppen (flens under), og trykker rett på lavprofil SMD-brytere (4 × 4 × 1,5 mm) på et 1,0 mm tastekort.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater: x = tvers (0 … W), y = langs (0 = halen med USB-C, L = nesen med IR), z = høyde (0 = undersiden).
// Tastene ligger i taster.scad (laget av taster.py), målt fra nesen: y = L − n.
// Bruk:  openscad -D 'part="topp"' -o stl/topp.stl skjold_fjernkontroll.scad   (-D 'variant="full"' for full variant)
// part:  topp | bunn | logo | ir_vindu | knapper | knapper_lys | gull | symboler_lyse | symboler_morke |
//        farge_rod | farge_gronn | farge_gul | farge_bla | bryterbrett | samlet | eksplodert | planet |
//        A_<del> (montert stilling, for sjekk_modell.py) | skjermflate | kort_omriss (2D, DXF)
include <taster.scad>
include <hovedkort/hovedkort_data.scad>
include <enkel/enkel_data.scad>
include <hullkort/hullkort_data.scad>

part = "samlet";
variant = "kort";               // kort (standard: 14 taster, 201,5 mm) | full (valgfri, med talltaster og smarthus-rad: 30 taster, 244,5 mm)
kortv = variant == "kort";
elektronikk = "handkoblet";     // handkoblet (SuperMini + TP4056 + tastekort) | hovedkort («alt på ett kort», se hovedkort/) |
                                // enkel (XIAO ESP32S3 + MCP23017 på et enkelt bærekort, se enkel/) |
                                // hullkort (XIAO, MCP23017-modul og 6 × 6-brytere på hullkort, uten kretskort, se hullkort/)
hk_hk = elektronikk == "hovedkort" && kortv;   // hovedkortet (KMR2-brytere, ESP-modul med antenne ved kanten)
en = elektronikk == "enkel" && kortv;          // enkel utgave (4 × 4 × 1,5-brytere, XIAO i halen)
hu = elektronikk == "hullkort" && kortv;       // hullkort-utgaven (6 × 6 × 4,3 THT-brytere på 1,6 mm hullkort, delene på gulvet)
hk = hk_hk || en || hu;                        // kortet har ferdige data (omriss, deler) fra KiCad eller hullkort/
D_OMRISS = hu ? HU_OMRISS : en ? EN_OMRISS : HK_OMRISS;  D_HULL = hu ? HU_HULL : en ? EN_HULL : HK_HULL;  D_USB_X = hu ? HU_USB_X : en ? EN_USB_X : HK_USB_X;  D_DELER = hu ? [] : en ? EN_DELER : HK_DELER;
oppsett = "rutenett";           // tasteoppsett under D-paden: rutenett (A) | vannrett (B) | stor (C) – se OPPSETT i taster.py
farge = "lys";                  // lys | mork | bone (Bone White PLA + mørk PETG) | bone_gra (Bone White PLA + grå PETG)
skjerm = "glass";               // glass | nokkel (aktivt område i magenta, så lag_render.sh kan legge inn et skjermbilde)
skjermE = 0;                    // part="skjermflate": samme eksplosjonsavstand som bildet
$fn = 48;

// ---------- ytre mål ----------
W = 55; L = kortv ? L_KORT : L_FULL;   // bredde og lengde (fra taster.py: 201,5 mm standard, 244,5 mm full)
HETTER = kortv ? HETTER_KORT : HETTER_FULL;
BRYTERE = kortv ? BRYTERE_KORT : BRYTERE_FULL;
PCB_N1 = kortv ? PCB_N1_KORT : PCB_N1_FULL;
DN = 22;                        // alt under skjermen er flyttet 22 mm mot halen for 2,8″-skjermen (taster.py: DN)
H = hu ? HU_H : 13.5;           // høyde uten taster (tastene står 1,2 mm opp, gullringen 1,5 mm: 15,0 mm totalt; hullkort: 16,1 mm)
R = 11;                         // hjørneradius sett ovenfra
c = 1.4;                        // 45°-fas rundt topp- og bunnkanten
t = 1.8;                        // sidevegg
tT = 1.6;                       // toppflaten (taster og skjerm sitter i den)
tB = 1.6;                       // gulvet
zs = 7.0;                       // skjøten mellom bunn og topp (USB-C og IR-vinduet ligger i bunnen)
lipH = 1.6; lipT = 1.2; lipG = 0.1;   // leppe på bunnen som går inn i toppen

// ---------- taster ----------
spill = 0.35;                   // klaring rundt hetta i hullet
fl = 0.9;  flT = 1.0;           // flens under toppen: bredde og tykkelse
zKort = hu ? HU_Z_KORT : hk_hk ? 7.8 : 8.2; kortT = hu ? HU_KORT_T : 1.0;   // tastekortet/hovedkortet (1,0 mm), undersiden (hovedkort: 0,4 mm lavere, høyere brytere)
swH = hu ? HU_SW_H : hk_hk ? 1.9 : 1.5;           // SMD-bryter 4 × 4 × 1,5 mm (hovedkortet: C&K KMR2, 4,2 × 2,8 × 1,9 mm)
zHb = zKort + kortT + swH + 0.1;  // hettens underside (0,1 mm over bryteren) = 10,8
opp = 1.2;                      // tastene står 1,2 mm over toppen
ringOpp = 1.5;                  // gullringen 1,5 mm
okOpp = 1.1;
ink = 0.4;                      // symbolene: 0,4 mm innfelt, fylt med annen farge (2 lag à 0,2 mm)
kf = 0.5;                       // (ikke brukt lenger: toppkanten er rundet, kr)
kr = 1.0;                       // myk toppkant: R1,0 rundt hver hette (printes med toppen opp, uten støtte)

// ---------- skjerm ----------
// 2,8″ 240 × 320 naken FPC-modul med dekkglass: HP28030-DCT IPS med kapasitiv berøring (innplugg-versjonen).
// Selgerens tegning: 47,80 × 66,50 × 3,56 mm, aktivt område 43,20 × 57,60 mm 2,43 mm fra overkanten (motsatt
// flatkabelen) og 2,30 mm fra sidene (6,47 mm nede). Skjermkabelen (18 p, 0,5 mm, 9,5 mm bred, 42,58 mm lang) bøyes
// ned bak glasset og går bakover under tastekortet til J1; berøringens egen kabel (ca. 35,2 mm) går til J2.
// Vinduet følger det aktive området med 0,9 mm kant rundt. Budsjett-skjermen (50 × 69,2 mm) krever andre mål.
modN0 = 8.4;                    // modulens nesekant fra nesen (R11-hjørnet bestemmer hvor nær den kan gå)
modW = 47.8; modH = 66.5; modT = 3.56; // HP28030-DCT IPS (innplugg-versjon, selgerens tegning): 47,80 × 66,50 × 3,56 mm uten tape
                                // (lomme under toppen med 0,3 mm klaring; 1 mm skumtape under, mot batteriet)
modC = modN0 + modH/2;          // modulens senter fra nesen (41,65)
aktivTopp = 2.43;               // fra glassets overkant (mot nesen) til det aktive området; 2,30 på sidene, 6,47 nede ved FPC-en
scrAW = 43.2; scrAH = 57.6;     // aktivt område
scrN = modN0 + aktivTopp + scrAH/2;   // det aktive områdets og vinduets senter fra nesen (39,63)
vKant = 0.9;                    // vinduet går 0,9 mm utenfor det aktive området rundt (svart glasskant synes)
scrWW = scrAW + 2*vKant; scrWH = scrAH + 2*vKant;   // vindu i toppen: 45,0 × 59,4 mm; 1,4 mm leppe på sidene, 1,5 oppe, 5,6 nede
pinD = 0.95; pinH = 0.65; pinInn = 0.675;   // styrepinner bak på modulen (46,45 × 65,60 mm mellom senterne)
fpcX = W/2 - modW/2 + 17.96 + 9.5/2;   // skjermens FPC-hale: 9,5 mm bred, 17,96 mm fra glassets venstre kant
fpcN = modN0 + modH + 37.0;     // J1 (senter, n): halen er 42,58 mm (ca. 6,3 ned og rundt, 36,3 bakover, 2,5 inn i kontakten)
tpX = W/2 + (hk_hk ? 10.6 : en ? 8.3 : 8);      // berøringens FPC (ca. 5,2 mm bred, 35,2 mm lang)
tpN = modN0 + modH + 29.6;      // J2 (senter, n)
jW1 = 13.4; jW2 = 7.4; jD = 5.4; jH = 2.0;   // FH12-stil 0,5 mm, 18 p og 6 p: bredde, dybde, høyde
lepT = 0.8;                     // toppflaten over glasset rundt vinduet
zGlass = H - lepT;              // glassets overside (12,7)

// ---------- skruer (M2 × 10 selvgjengende, 5 stk) ----------
bossD = 5.0;  bossBD = 6.0;     // tårn i toppen og bunnen
pilot = 1.7;  klar = 2.3;  hodeD = 4.3;  hodeH = 2.5;
zMot = zs + lipH;               // hjørnetårnene møtes her (8,6)
SKRUER = [[7.5, L - 5.5], [W - 7.5, L - 5.5], [4.9, 8], [W - 4.9, 8], [W - 7, L - 95]];   // nese ×2 (foran skjermen), hale ×2, midt (til høyre ved D-paden, n = 95)
MIDT = 4;                       // skrue nr. 4 (midt) klemmer tastekortet
FRONT = hu ? HU_FRONT : oppsett == "vannrett" ? OPPSETT_VANNRETT : oppsett == "stor" ? OPPSETT_STOR : OPPSETT_RUTENETT;
ALLE = concat(HETTER, FRONT);   // faste hetter og oppsettets hetter
PINNER = hu ? HU_PINNER : [for (p = FRONT_STOTTER) p];   // pinner fra toppen og stolper fra bunnen klemmer kortet (x, n)

// ---------- innmat ----------
bat = [34, 50, 6.0];  batN = 12;    // LiPo 603450 (1200 mAh) under skjermen, fra n = 11
mcu = [18, 22.6, 4.6];              // ESP32-S3 SuperMini (antennen mot halen)
mcuN = kortv ? 124 : 166;            // til venstre, foran laderen (USB-C mot nesen, fri vei 22 mm for pluggen)
mcuX = kortv ? 13.5 : 15.5;   // full: litt mot høyre, så USB-pluggen går klar av stolpen ved sideveggen
mcuZ = tB + 1.0;                     // kortet ligger på en 1,0 mm hylle, så USB-C-pluggen går klar av gulvet
STOLPER = hu ? HU_STOLPER : en ? [[20, 92], [W/2 + 15, 92], [10, 178], [W - 4.2, 184]] : hk ? [[20, 92], [W/2 + 15, 92], [24, 190], [W - 4.2, 184]] : kortv ? [[W/2 - 15, 70 + DN], [W/2 + 15, 70 + DN], [W/2 - 15, 178], [W/2 + 15, 178]]
                : [[W/2 - 15, 70 + DN], [W/2 + 15, 70 + DN], [W/2 - 15, 222], [W/2 + 15, 222]];
TCA = kortv ? [[W/2 + 13, 145], [W/2 + 13, 157], [W/2 + 13, 169]] : [[W/2 - 13, 150], [W/2, 150], [W/2 + 13, 150], [W/2 + 13, 162]];   // TCA9555 under kortet
ladX = W/2;                        // laderens senter
usbX = hk ? D_USB_X : ladX;       // USB-C i halen (hovedkortet: kontakten sitter på kortet, til høyre for midten)
lad = [17, 28, 4.4];                // TP4056 Type-C-modul med beskyttelse (PCB 17 × 28 × 1,2, USB-C 9 × 7,3 × 3,2), mot halen
ladY = t + 0.6;                     // laderens bakkant (USB-C-kontaktens front 0,35 mm bak veggen)
spill_inni = 0.5;                   // klaring rundt kort og batteri i lommene
// vibrasjonsbryter SW-18010P (Ø 5 × 12, liggende) og vibrasjonsmotor 1027 (Ø 10 × 2,7), begge på gulvet til høyre
vibX = W - 8; vibN = 118;           // bryteren: n 118 … 130
motX = W - 9.5; motN = 105;         // motoren: senter n 105
// ledningskanaler (1,5 × 1,5 mm) på gulvet: batteri → lader i midten, IR-kort → ESP langs venstre side
KANAL_BAT = hk ? [] : [[W/2 + 4, 65.5], [W/2 + 4, L - ladY - lad[1] - 1]];        // x, n fra … til (batteriets bakkant → laderens nesekant)
KANAL_IR  = [[3.75, 10.5], [3.75, hk ? 80 : 123]];            // IR-kortet → ESP
kanalZ = tB + 0.4;                                  // ledningsbuntens underkant
usbW = 9.4; usbH = 3.6; usbZ = hu ? HU_USB_Z : en ? zKort - 1.0 - 1.6 : hk ? zKort - 1.65 : tB + 1.2 + 1.6;   // USB-C-åpningen (senter z ≈ 4,4)
usbFW = 13.6; usbFH = 7.4; usbFD = 1.2;          // forsenkning utvendig rundt USB-C (pluggens støpte del går 1,2 mm inn, veggen er 0,6 mm der)
irW = 30; irH = 3.8; irZ = 4.3;     // IR-vinduet i nesen (z 2,4 … 6,2)
irT = 1.2;                          // IR-vinduets tykkelse (veggen er t = 1,8; 0,6 mm krage inni)

// ---------- farger ----------
// bone: topp i «Bone White» matt PLA (ca. #CEC6B4, litt varmere enn Bambu PLA Matte Bone White #CBC6B8),
//       bunn i mørk koksgrå matt PETG (#2B2B2D) · bone_gra: samme topp, bunn i natur/grå matt PETG (#8E8C87)
bone = farge == "bone" || farge == "bone_gra";
lys = farge == "lys" || bone;
c_bone  = [0.808, 0.776, 0.706];
c_topp  = bone ? c_bone : lys ? [0.93, 0.91, 0.87] : [0.15, 0.15, 0.16];
c_bunn  = farge == "bone_gra" ? [0.557, 0.549, 0.529] : bone ? [0.169, 0.169, 0.176] : lys ? [0.20, 0.19, 0.19] : [0.82, 0.79, 0.74];
c_knapp = lys ? [0.19, 0.19, 0.20] : [0.26, 0.26, 0.27];
c_lysk  = bone ? c_bone : lys ? [0.93, 0.91, 0.87] : [0.82, 0.79, 0.74];
c_gull  = [0.85, 0.62, 0.25];
c_sym_l = bone ? c_bone : [0.93, 0.91, 0.87];
c_sym_m = [0.18, 0.18, 0.19];
c_glass = [0.04, 0.05, 0.07];
c_ir    = [0.10, 0.06, 0.09];
c_kort  = [0.10, 0.36, 0.20];
FARGER  = [["rod", [0.80, 0.18, 0.16]], ["gronn", [0.20, 0.60, 0.30]], ["gul", [0.92, 0.75, 0.20]], ["bla", [0.18, 0.38, 0.78]]];
function fargen(f) = [for (p = FARGER) if (p[0] == f) p[1]][0];

// ---------- grunnformer ----------
module rrect(w, d, r) { translate([r, r]) offset(r) square([w - 2*r, d - 2*r]); }
module omriss(o = 0) { translate([o, o]) rrect(W - 2*o, L - 2*o, max(0.5, R - o)); }
module skive(z, o) { translate([0, 0, z]) linear_extrude(0.01) omriss(o); }
// ytre form: 45°-fas c oppe og nede
module kropp() { hull() { skive(0, c); skive(c, 0); skive(H - c - 0.01, 0); skive(H - 0.01, c); } }
module kropp_over() { hull() { skive(zs, 0); skive(H - c - 0.01, 0); skive(H - 0.01, c); } }   // = kropp over skjøten
module kropp_under() { hull() { skive(0, c); skive(c, 0); skive(zs - 0.01, 0); } }             // = kropp under skjøten
// hulrom: vegg t langs sidene og vinkelrett på fasene, gulv tB og topp tT
z1 = H - c - 0.414*t;  z0 = c + 0.414*t;
module hulrom() {
  hull() {
    skive(tB, t + (z0 - tB)); skive(z0, t); skive(z1, t); skive(H - tT - 0.01, t + (H - tT - z1));
  }
}
function P(x, n) = [x, L - n];

// 2D-form for en hette (o = forstørrelse)
module hform(f, b, h, o = 0) {
  if (f == "rund" || f == "ok") circle(d = b + 2*o, $fn = 40);
  else if (f == "ring") circle(d = b + 2*o, $fn = 96);
  else { r = min(b, h)/2 + o; hull() for (s = [-1, 1]) if (b >= h) translate([s*(b/2 - min(b, h)/2), 0]) circle(r, $fn = 32);
         else translate([0, s*(h/2 - min(b, h)/2)]) circle(r, $fn = 32); }
}

// ---------- symboler (2D, sentrert, ca. 4 mm store; streker ≥ 0,8 mm) ----------
module strek(a, b, w = 0.85) { hull() { translate(a) circle(d = w, $fn = 12); translate(b) circle(d = w, $fn = 12); } }
module trekant(s = 2.6) { polygon([[-s*0.45, -s/2], [-s*0.45, s/2], [s*0.55, 0]]); }
module tekst(s, z = 3.0) { text(s, size = z, font = "Liberation Sans", halign = "center", valign = "center"); }
// ---------- strektegnede symboler: jevn strek sw, ca. 38 % av tastens diameter (s = symbolets størrelse) ----------
sw = 0.65;                      // strekbredde (mm) for alle hovedsymbolene
module bue(r, a0, a1, w = sw) { for (a = [a0:(a1 - a0)/16:a1 - 0.001]) hull() { rotate(a) translate([r, 0]) circle(d = w, $fn = 12); rotate(a + (a1 - a0)/16) translate([r, 0]) circle(d = w, $fn = 12); } }
module strekomriss(pts, w = sw) { difference() { offset(delta = w/2) polygon(pts); offset(delta = -w/2) polygon(pts); } }
module ikonL(i, s) {
  if (i == "av") { bue(0.42*s, 125, 415); strek([0, 0.02*s], [0, 0.55*s], sw); }
  else if (i == "skjold") strekomriss([for (p = [[-1.9, 1.9], [1.9, 1.9], [1.9, 0.2], [0, -2.3], [-1.9, 0.2]]) p*s/4.4]);
  else if (i == "meny") for (y = [-0.3, 0, 0.3]) strek([-0.42*s, y*s], [0.42*s, y*s], sw);
  else if (i == "tilbake") { strek([0.12*s, 0.4*s], [-0.28*s, 0], sw); strek([-0.28*s, 0], [0.12*s, -0.4*s], sw); }
  else if (i == "avslutt") { strek([-0.32*s, -0.32*s], [0.32*s, 0.32*s], sw); strek([-0.32*s, 0.32*s], [0.32*s, -0.32*s], sw); }
  else if (i == "spill_pause") { strekomriss([for (p = [[-0.5, -0.36], [-0.5, 0.36], [0.06, 0]]) p*s]);
                                 strek([0.28*s, -0.36*s], [0.28*s, 0.36*s], sw); strek([0.5*s, -0.36*s], [0.5*s, 0.36*s], sw); }
  else if (i == "demp") { strekomriss([for (p = [[-0.5, -0.17], [-0.24, -0.17], [0.04, -0.42], [0.04, 0.42], [-0.24, 0.17], [-0.5, 0.17]]) p*s]);
                         strek([-0.5*s, -0.5*s], [0.5*s, 0.5*s], sw); }
  else if (i == "OK") tekst("OK", 3.6);
  else if (i == "pluss") { strek([-0.4*s, 0], [0.4*s, 0], sw); strek([0, -0.4*s], [0, 0.4*s], sw); }
  else if (i == "minus") strek([-0.4*s, 0], [0.4*s, 0], sw);
}
module ikon(i) {
  if (i == "av") { difference() { circle(d = 4.2, $fn = 32); circle(d = 2.5, $fn = 32); translate([-0.9, 0]) square([1.8, 3]); } translate([-0.42, 0]) square([0.84, 2.4]); }
  else if (i == "skjold") difference() {   // skjold-omriss
    offset(0.3) polygon([[-1.9, 1.9], [1.9, 1.9], [1.9, 0.2], [0, -2.3], [-1.9, 0.2]]);
    offset(-0.55) polygon([[-1.9, 1.9], [1.9, 1.9], [1.9, 0.2], [0, -2.3], [-1.9, 0.2]]);
  }
  else if (i == "meny") for (y = [-1.3, 0, 1.3]) strek([-1.6, y], [1.6, y]);
  else if (i == "tilbake") { strek([1.4, -1.2], [1.4, 0.6]); strek([1.4, 0.6], [-1.0, 0.6]); polygon([[-1.9, 0.6], [-0.7, 1.7], [-0.7, -0.5]]); }
  else if (i == "info") { translate([0, 1.5]) circle(d = 1.0, $fn = 16); strek([0, -1.6], [0, 0.4], 0.95); }
  else if (i == "guide") for (x = [-0.9, 0.9], y = [-0.9, 0.9]) translate([x, y]) square(1.25, center = true);
  else if (i == "avslutt") { strek([-1.3, -1.3], [1.3, 1.3]); strek([-1.3, 1.3], [1.3, -1.3]); }
  else if (i == "OK") tekst("OK", 3.2);
  else if (i == "demp") { polygon([[-2.6, -0.7], [-1.6, -0.7], [-0.3, -1.8], [-0.3, 1.8], [-1.6, 0.7], [-2.6, 0.7]]);
                         strek([0.7, -1.0], [2.5, 1.0], 0.8); strek([0.7, 1.0], [2.5, -1.0], 0.8); }
  else if (i == "siste") { difference() { circle(d = 3.8, $fn = 32); circle(d = 2.2, $fn = 32); translate([0, 0]) square(3); }
                           translate([1.5, 0.3]) polygon([[-0.9, 0], [0.9, 0], [0, 1.2]]); }
  else if (i == "spol_tilbake") { translate([0.6, 0]) mirror([1, 0]) trekant(2.4); translate([-1.0, 0]) mirror([1, 0]) trekant(2.4); }
  else if (i == "spol_frem") { translate([-0.6, 0]) trekant(2.4); translate([1.0, 0]) trekant(2.4); }
  else if (i == "spill_pause") { translate([-1.5, 0]) trekant(2.6); translate([0.6, -1.3]) square([0.8, 2.6]); translate([1.8, -1.3]) square([0.8, 2.6]); }
  else if (i == "opptak") circle(d = 2.8, $fn = 32);
  else if (i == "stopp") square(2.4, center = true);
  else if (i == "dvr") { difference() { square([4.0, 2.8], center = true); square([2.4, 1.2], center = true); } }
  else if (i == "strek") strek([-1.3, 0], [1.3, 0], 0.9);
  else if (i == "enter") { strek([1.5, 1.2], [1.5, -0.4]); strek([1.5, -0.4], [-0.8, -0.4]); polygon([[-1.8, -0.4], [-0.6, 0.6], [-0.6, -1.4]]); }
  else if (i == "lys") { circle(d = 2.6, $fn = 24); translate([-0.7, -2.3]) square([1.4, 1.2]); }
  else if (i == "stikk") { difference() { offset(0.6) square([2.0, 1.6], center = true); } translate([-0.7, 1.2]) square([0.5, 1.0]); translate([0.2, 1.2]) square([0.5, 1.0]); }
  else if (i == "minus") strek([-1.3, 0], [1.3, 0], 0.9);
  else if (i == "pluss") { strek([-1.3, 0], [1.3, 0], 0.9); strek([0, -1.3], [0, 1.3], 0.9); }
  else if (len(i) == 1) tekst(i, 3.4);
}
// symbolene på vippene: + / − (volum) og ∧ / ∨ (kanal), og en liten prikk i midten
module vippe_ikon(i, b = 0, h = 1) {   // + mot nesen (loddrett pille) eller mot høyre (vannrett pille), − motsatt
  d = b > 0 ? abs(h - b)/2 : VIPPE_D;
  rotate(b > h ? -90 : 0) {
    translate([0, d]) if (i == "vol") { strek([-1.8, 0], [1.8, 0], sw); strek([0, -1.8], [0, 1.8], sw); } else { strek([-1.2, -0.6], [0, 0.6]); strek([0, 0.6], [1.2, -0.6]); }
    translate([0, -d]) if (i == "vol") strek([-1.8, 0], [1.8, 0], sw); else { strek([-1.2, 0.6], [0, -0.6]); strek([0, -0.6], [1.2, 0.6]); }
  }
}
module symbol2d(h) {   // symbolet for hette h, i hettens lokale ramme (y peker mot nesen)
  if (h[1] == "vippe") vippe_ikon(h[6], h[4], h[5]);
  else if (h[1] == "ring") for (a = [0:90:270]) rotate(a) { strek([-2.4, 13.0], [0, 14.9], sw); strek([0, 14.9], [2.4, 13.0], sw); }   // tynne vinkler 4,8 × 1,9 mm
  else if (h[1] == "ok") ikonL("OK", 0);
  else if (h[1] == "rund" && h[4] >= 8) ikonL(h[6], 0.38*max(h[4], 10));   // runde taster: strektegnet, 38 % av diameteren
  else ikon(h[6]);
}

// ---------- hettene ----------
// Flat underside på zHb, flens fl rundt, kroppen gjennom hullet og opp til toppen + opp. Symbolet er felt inn ink mm.
function topp_av(h) = h[1] == "ring" ? H + ringOpp : h[1] == "ok" ? H + okOpp : H + opp;
module hette_kropp(h) {
  f = h[1]; b = h[4]; hh = h[5]; zt = topp_av(h);
  if (f == "ring") {
    ri = hh/2;                   // indre radius (8,5)
    difference() {
      union() {
        translate([0, 0, zHb]) cylinder(r = b/2 + fl, h = flT, $fn = 96);
        translate([0, 0, zHb]) hull() { cylinder(r = b/2, h = zt - zHb - kr, $fn = 96); for (a = [22.5:22.5:90]) cylinder(r = b/2 - kr*(1 - cos(a)), h = zt - zHb - kr + kr*sin(a), $fn = 96); }
      }
      translate([0, 0, zHb - 1]) cylinder(r = ri, h = H - 0.9 - zHb + 1, $fn = 64);         // OK-ens flens går inn her
      translate([0, 0, H - 0.9 - 0.001]) cylinder(r1 = ri, r2 = ri - 0.7, h = 0.7, $fn = 64);   // 45° krage holder OK-en
      translate([0, 0, H - 0.2 - 0.01]) cylinder(r = ri - 0.7, h = 5, $fn = 64);
    }
  } else if (f == "ok") {
    ri = [for (q = HETTER) if (q[1] == "ring") q[5]][0]/2 - 0.3;   // OK: 0,3 mm klaring inni ringen (nedre del Ø16,4, øvre Ø15)
    union() {
      translate([0, 0, zHb]) cylinder(r = ri, h = H - 1.2 - zHb, $fn = 64);
      translate([0, 0, H - 1.2 - 0.001]) cylinder(r1 = ri, r2 = ri - 0.7, h = 0.7, $fn = 64);
      translate([0, 0, H - 1.2]) hull() { cylinder(r = b/2, h = zt - (H - 1.2) - kr, $fn = 64); for (a = [22.5:22.5:90]) cylinder(r = b/2 - kr*(1 - cos(a)), h = zt - (H - 1.2) - kr + kr*sin(a), $fn = 64); }
    }
  } else {
    translate([0, 0, zHb]) linear_extrude(flT) hform(f, b, hh, fl);
    hull() {
      translate([0, 0, zHb]) linear_extrude(zt - zHb - kr) hform(f, b, hh);
      for (a = [22.5:22.5:90]) translate([0, 0, zt - kr + kr*sin(a) - 0.01]) linear_extrude(0.01) hform(f, b, hh, -kr*(1 - cos(a)));
    }
  }
}
module hette(h) { difference() { hette_kropp(h); translate([0, 0, topp_av(h) - ink]) linear_extrude(1) symbol2d(h); } }
module symbol(h) { intersection() { hette_kropp(h); translate([0, 0, topp_av(h) - ink]) linear_extrude(ink) symbol2d(h); } }
// i bildene (forhåndsvisning) uten intersection – OpenCSG blander fargene ellers
module symbol_vis(h) { translate([0, 0, topp_av(h) - ink]) linear_extrude(ink - 0.02) symbol2d(h); }
module ved(h) { translate([h[2], L - h[3], 0]) children(); }
// grupper: «mork» = mørke hetter (med OK), «lys» = smarthus-raden, «gull» = ring og Skjold-tasten, ellers fargetastene
function gruppe(h) = h[7];
// oppsettets hetter (over rutenettet): hetta står 0,7 mm over alle bryterne, og har én aktuator (Ø2,6 × 0,6 mm) rett
// over sin egen bryter (to for volumpillene). Flensen er løftet tilsvarende og ligger i en 0,6 mm forsenkning under toppen.
// Ingen støtteknotter: hetta styres av hullet. Flensens overside er 45° skrå, så hetta printes med forsiden ned.
akt_d = 2.6; akt_h = 0.6;       // aktuatoren: Ø2,6 mm, 0,6 mm under hetta
function er_maal(h, p) = len([for (m = h[8]) if (abs(m[0] - p[0]) < 0.01 && abs(m[1] - p[1]) < 0.01) 1]) > 0;
module aktuatorer(h, ekstra = 0) {
  for (m = h[8]) translate([m[0] - h[2], h[3] - m[1], zHb]) cylinder(d = akt_d + ekstra, h = akt_h + 0.01, $fn = 24);
}
module hette_front(h) {
  f = h[1]; b = h[4]; hh = h[5]; zt = topp_av(h); zb = zHb + akt_h;
  difference() {
    union() {
      // flens: 0,2 mm loddrett kant og 45° opp til kroppen (printes som 45°-overheng med forsiden ned)
      hull() {
        translate([0, 0, zb]) linear_extrude(0.2) hform(f, b, hh, fl);
        translate([0, 0, zb + flT - 0.01]) linear_extrude(0.01) hform(f, b, hh, 0.1);
      }
      hull() {
        translate([0, 0, zb]) linear_extrude(zt - zb - kr) hform(f, b, hh);
        for (a = [22.5:22.5:90]) translate([0, 0, zt - kr + kr*sin(a) - 0.01]) linear_extrude(0.01) hform(f, b, hh, -kr*(1 - cos(a)));
      }
      aktuatorer(h);
    }
    translate([0, 0, zt - ink]) linear_extrude(1) symbol2d(h);
  }
}
module en_hette(h) { if (len(h) > 8) hette_front(h); else hette(h); }
module hetter(g, liste = ALLE) { for (h = liste) if (gruppe(h) == g) ved(h) en_hette(h); }
module symboler(g, vis = false, liste = ALLE) { for (h = liste) if (gruppe(h) == g && h[6] != "") ved(h) if (vis) symbol_vis(h); else symbol(h); }


// ---------- toppen ----------
module topp() {
  difference() {
    union() {
      difference() {
        kropp_over();
        hulrom();
      }
      // pinner som holder tastekortet nede (ved sideveggene, utenfor tasteblokken)
      for (p = PINNER) translate([p[0], L - p[1], zKort + kortT]) cylinder(d = 2.2, h = H - tT - zKort - kortT + 0.01, $fn = 20);
      // skruetårn: hjørnene ned til zMot, midten ned til tastekortet
      intersection() {
        hulrom();
        for (i = [0:len(SKRUER) - 1]) translate([SKRUER[i][0], SKRUER[i][1], 0])
          if (i == MIDT) translate([0, 0, zKort + kortT]) cylinder(d = 4.0, h = H - tT - zKort - kortT + 0.01);
          else translate([0, 0, zMot]) cylinder(d = bossD, h = H - tT - zMot + 0.01);
      }
    }
    // hull for tastene
    for (h = ALLE) if (h[1] != "ok") ved(h) translate([0, 0, H - tT - 1]) linear_extrude(tT + 2) hform(h[1], h[4], h[5], spill);
    // forsenkning (0,6 mm) under toppen for flensene til oppsettets hetter
    for (h = FRONT) ved(h) translate([0, 0, H - tT - 1]) linear_extrude(1 + akt_h) hform(h[1], h[4], h[5], fl + 0.3);
    // skjermvindu og lomme for glasset
    translate([W/2, L - scrN, H - tT - 1]) linear_extrude(tT + 2) offset(1) square([scrWW - 2, scrWH - 2], center = true);
    translate([W/2, L - modC, H - tT - 1]) linear_extrude(tT - lepT + 1) offset(1) square([modW + 0.6 - 2, modH + 0.6 - 2], center = true);
    // skruehull (forbor)
    for (s = SKRUER) translate([s[0], s[1], zKort]) cylinder(d = pilot, h = H - 0.8 - zKort, $fn = 16);
    // SKJOLD felt inn nederst (gull)
    translate([0, 0, H - 0.5]) linear_extrude(1) logo2d();
    usb_forsenkning();
    if (hk) usb_aapning();   // hovedkortets USB-C sitter høyere: åpningen går over skjøten
  }
}
module logo2d() { translate([W/2, 5.2 + 1.6]) text("SKJOLD", size = 3.0, font = "Liberation Sans:style=Bold", halign = "center", valign = "center", spacing = 1.35); }
module logo() { translate([0, 0, H - 0.5]) linear_extrude(0.5) logo2d(); }   // flaten er flat her (godt innenfor fasen)

// ---------- dokk-kontakt: hunndelen av en magnetisk pogo-kontakt (2 pinner) flatt i bunnen ----------
// AliExpress «DC Magnetic Pogo Pin Connector», 1 sett (han + hun), «2Pin with ear 2.80mm». Mål din og juster her.
dokk_kontakt = false;            // true: lomme for hunndelen (bunn_dokk.stl); false: hel bunn
POGO_L = 21;                     // lengde med ører
POGO_KROPP = 15;                 // kroppens lengde (uten ører)
POGO_B = 6;                      // bredde
POGO_HH = 3.0;                   // hunndelens høyde (flate puter)
POGO_HM = 4.5;                   // handelens høyde (uten fjærpinner)
POGO_PINNE = 0.9;                // fjærpinnene stikker så langt ut over handelen (presses 0,5–1,0 mm)
POGO_ORE_T = 1.2;                // ørenes tykkelse (øverst på hunndelen, mot innsiden)
POGO_HULL = 1.8;                 // hullene i ørene
POGO_HULL_A = 18;                // avstand mellom hullene
POGO_DELING = 2.8;               // avstand mellom pinnene (2,54 eller 2,80)
POGO_ORE = true;                 // false: utgaven uten ører (limes i en trang lomme)
POGO_X = 40; POGO_Y = 43.5;      // senter i bunnen (x tvers, y fra halen); langs y, til høyre for laderen og USB-C
module pogo_2d(o = 0) {          // omrisset sett ovenfra (langs y)
  if (POGO_ORE) hull() for (s = [-1, 1]) translate([0, s * (POGO_L/2 - POGO_B/2)]) circle(d = POGO_B + 2*o, $fn = 32);
  else square([POGO_B + 2*o, POGO_KROPP + 2*o], center = true);
}
module pogo_hunn() {             // på plass i bunnen: flaten (putene) i z = 0
  translate([POGO_X, POGO_Y, 0]) {
    color([0.12, 0.12, 0.13]) difference() {
      union() {
        translate([0, 0, POGO_HH/2]) cube([POGO_B, POGO_KROPP, POGO_HH], center = true);
        if (POGO_ORE) translate([0, 0, POGO_HH - POGO_ORE_T]) linear_extrude(POGO_ORE_T) pogo_2d();
      }
      if (POGO_ORE) for (s = [-1, 1]) translate([0, s * POGO_HULL_A/2, -1]) cylinder(d = POGO_HULL, h = 10, $fn = 16);
    }
    color([0.8, 0.65, 0.3]) for (s = [-1, 1]) translate([0, s * POGO_DELING/2, -0.01]) cylinder(d = 1.6, h = 0.3, $fn = 16);
  }
}
module pogo_lomme() {            // kuttes i bunnen: kroppen gjennom gulvet, ørene over
  translate([POGO_X, POGO_Y, 0]) {
    translate([0, 0, -1]) linear_extrude(POGO_HH + 1 - (POGO_ORE ? POGO_ORE_T : 0) + 0.01) offset(0.12) square([POGO_B, POGO_KROPP], center = true);
    if (POGO_ORE) translate([0, 0, POGO_HH - POGO_ORE_T]) linear_extrude(POGO_ORE_T + 3) pogo_2d(0.2);
    if (POGO_ORE) for (s = [-1, 1]) translate([0, s * POGO_HULL_A/2, POGO_HH - POGO_ORE_T - 2.6]) cylinder(d = 1.3, h = 3, $fn = 12);   // forbor M1,6
  }
}
module pogo_ramme() {            // innvendig ramme som ørene ligger på (z = POGO_HH − ørene), med plass til skruene
  translate([POGO_X, POGO_Y, tB - 0.01]) linear_extrude(POGO_HH - (POGO_ORE ? POGO_ORE_T : 0) - tB + 0.01) offset(1.6) pogo_2d();
}

// ---------- bunnen ----------
module bunn() {
  difference() {
    union() {
      difference() {
        kropp_under();
        hulrom();
      }
      // leppe som går 1,6 mm inn i toppen
      // (ikke langs skjermmodulen, som går nesten helt ut til sideveggene)
      translate([0, 0, zs - 0.01]) linear_extrude(lipH + 0.01) difference() { omriss(t + lipG); omriss(t + lipG + lipT);
        translate([0, L - modN0 - modH - 0.6]) square([W, modH + 0.9]);
        translate([usbX - (en || hu ? 9.5 : 7), -1]) square([en || hu ? 19 : 14, t + lipT + 2]);   // ikke over USB-C-kontakten (enkel: XIAO-en er 17,5 mm bred)
        if (hk_hk) translate([2.2, L - 177 - 10.5]) square([3, 21]); }   // tynnere leppe (0,3 mm) der ESP-modulens antenne stikker ut over kortkanten
      intersection() { hulrom(); bunn_innmat(); }
      if (dokk_kontakt) pogo_ramme();
    }
    if (dokk_kontakt) pogo_lomme();
    // skruehull med forsenket hode
    for (s = SKRUER) translate([s[0], s[1], -1]) { cylinder(d = klar, h = 20, $fn = 16); cylinder(d = hodeD, h = hodeH + 1, $fn = 24); }
    // USB-C i halen
    usb_aapning();
    usb_forsenkning();
    // IR-vinduet i nesen: gjennomgående vindu og 0,6 mm krage innvendig
    translate([W/2, L + 1, irZ]) rotate([90, 0, 0]) linear_extrude(t + 2) offset(1) square([irW - 2, irH - 2], center = true);
    translate([W/2, L - t + 0.6, irZ]) rotate([90, 0, 0]) linear_extrude(1.2) offset(1) square([irW + 2 - 2, irH + 1 - 2], center = true);
    // to små hull for lysdioden på laderen (rød = lader, blå = full) ved siden av USB-C
    // rett vegg (uten innvendig fas mot gulvet) bak laderen, så kortet får 0,6 mm klaring
    translate([W/2 - 9.5, t, tB]) cube([19, 1.2, 1.0]);
    if (!hk) for (dx = [-8.5, 8.5]) translate([W/2 + dx, -1, usbZ]) rotate([-90, 0, 0]) cylinder(d = 1.2, h = t + 2, $fn = 12);
  }
}
module usb_aapning() { translate([usbX, -1, usbZ]) rotate([-90, 0, 0]) linear_extrude(t + 2) offset(1.2) square([usbW - 2.4, usbH - 2.4], center = true); }
module usb_forsenkning() { translate([usbX, -1, usbZ]) rotate([-90, 0, 0]) linear_extrude(1 + usbFD) offset(2.5) square([usbFW - 5, usbFH - 5], center = true); }
// tårn, stolper og ribber i bunnen 
module bunn_innmat() {
  union() {
          for (i = [0:len(SKRUER) - 1]) translate([SKRUER[i][0], SKRUER[i][1], 0])
            cylinder(d = bossBD, h = (i == MIDT ? zKort : zMot));
          // stolper under tastekortet
          for (p = PINNER) translate([p[0], L - p[1], 0]) cylinder(d = 3.0, h = zKort, $fn = 20);
          for (p = STOLPER) translate([p[0], L - p[1], 0]) cylinder(d = 3.0, h = zKort, $fn = 20);
          // ribber: batterilomme, ladermodul og SuperMini
          // (0,5 mm klaring rundt; batterikabelen går ut i bakkant mot ledningskanalen i midten)
          translate([W/2, L - batN - bat[1]/2, tB - 0.01]) linear_extrude(1.6) difference() { square([bat[0] + 1 + 2.4, bat[1] + 1 + 2.4], center = true); square([bat[0] + 1, bat[1] + 1], center = true); translate([4, -bat[1]/2]) square([8, 6], center = true); }
          if (!hk) translate([ladX, ladY + lad[1]/2, tB - 0.01]) linear_extrude(1.4) difference() { square([lad[0] + 1 + 2.4, lad[1] + 1 + 2.0], center = true); square([lad[0] + 1, lad[1] + 1], center = true); translate([0, -lad[1]/2]) square([lad[0] + 4, 4], center = true); translate([4, lad[1]/2]) square([6, 6], center = true); }
          if (!hk) translate([mcuX, L - mcuN - mcu[1]/2, tB - 0.01]) linear_extrude(mcuZ - tB + 1.2) difference() { square([mcu[0] + 1 + 2.4, mcu[1] + 1 + 2.4], center = true); square([mcu[0] + 1, mcu[1] + 1], center = true); translate([-mcu[0]/2, mcu[1]/2]) square([4, 6], center = true); translate([0, mcu[1]/2 + 1]) square([14, 4], center = true); }
          if (!hk) translate([mcuX, L - mcuN - mcu[1]/2, tB - 0.01]) linear_extrude(mcuZ - tB + 0.01) square([mcu[0] - 3, mcu[1] - 4], center = true);   // hylla (kortets kanter med loddepunkter ligger fritt)
          // holder for vibrasjonsbryteren (to små vugger) og en ring rundt motoren
          if (!hu) for (dn = [2, 10]) translate([vibX - 3.5, L - vibN - dn - 1, tB - 0.01]) difference() { cube([7, 2, 2.2]); translate([3.5, -1, 2.76]) rotate([-90, 0, 0]) cylinder(d = 5.4, h = 4, $fn = 24); }
          if (!hu) translate([motX, L - motN, tB - 0.01]) difference() { cylinder(d = 13.4, h = 1.4, $fn = 40); translate([0, 0, -1]) cylinder(d = 11, h = 4, $fn = 40); }
          // IR-kortet i nesen (lite hullkort 34 × 6,0 mm) står i et spor: bak ligger batteriribben (0,3 mm), foran to korte knaster (0,1 mm)
          for (x = [[W/2 - 17, 3], [W/2 + 15.5, 1.5]]) translate([x[0], L - t - 7.1, tB - 0.01]) cube([x[1], 1.0, 1.4]);
  }
}
// IR-vinduet: 1,2 mm plate (IR-gjennomslippelig) som fyller vinduet i nesen, med 0,6 mm krage innvendig
module ir_vindu() {
  translate([W/2, L, irZ]) rotate([90, 0, 0]) {
    linear_extrude(irT) offset(1) square([irW - 2 - 0.3, irH - 2 - 0.3], center = true);
    translate([0, 0, irT - 0.001]) linear_extrude(0.6) offset(1) square([irW + 2 - 2 - 0.3, irH + 1 - 2 - 0.3], center = true);
  }
}

// ---------- tastekort (1,0 mm) og bryterbrett (printet alternativ) ----------
module kort2d() {
  if (hk) difference() { polygon(D_OMRISS); for (h = D_HULL) translate([h[0], h[1]]) circle(d = h[2], $fn = 24); if (en && len(EN_VINDU)) polygon(EN_VINDU); }
  else difference() {
    translate([3.2, L - PCB_N1]) rrect(W - 6.4, PCB_N1 - PCB_N0, 4);
    for (i = [0:len(SKRUER) - 1]) translate([SKRUER[i][0], SKRUER[i][1]]) circle(d = i == MIDT ? 2.4 : bossBD + 0.6);
  }
}
module tastekort() { translate([0, 0, zKort]) linear_extrude(kortT) kort2d(); }
module brytere() { if (hu) { for (b = HU_BRYTERE) translate([b[1], b[2], zKort + kortT]) { translate([-3, -3, 0]) cube([6, 6, HU_SW_KROPP]); cylinder(d = 3.5, h = swH, $fn = 20); } }
  else if (en) { for (d = D_DELER) if (d[5] > 0) translate([(d[0] + d[2])/2, (d[1] + d[3])/2, zKort + kortT]) { translate([-2, -2, 0]) cube([4, 4, swH - 0.4]); cylinder(d = 2.4, h = swH, $fn = 16); } }
  else if (hk_hk) for (b = BRYTERE) translate([b[1], L - b[2], zKort + kortT]) { translate([-1.4, -2.1, 0]) cube([2.8, 4.2, swH - 0.5]); cylinder(d = 1.6, h = swH, $fn = 16); }
  else for (b = BRYTERE) translate([b[1], L - b[2], zKort + kortT]) { translate([-2, -2, 0]) cube([4, 4, swH - 0.4]); cylinder(d = 2.4, h = swH, $fn = 16); } }
module tca() { if (hu) hu_bein(); else if (hk) for (d = D_DELER) if (d[5] < 0) translate([d[0], d[1], zKort - d[4]]) cube([d[2] - d[0], d[3] - d[1], d[4]]);
  if (!hk) tca_hk_ikke(); }
module tca_hk_ikke() { for (c = TCA) translate([c[0] - 2.2, L - c[1] - 3.9, zKort - 1.2]) cube([4.4, 7.8, 1.2]);
  translate([fpcX - jW1/2, L - fpcN - jD/2, zKort - jH]) cube([jW1, jD, jH]);        // J1: FPC-kontakt 18 p 0,5 mm for skjermen
  translate([tpX - jW2/2, L - tpN - jD/2, zKort - jH]) cube([jW2, jD, jH]);           // J2: FPC-kontakt 6 p 0,5 mm for berøringen
  translate([W/2 - 19.5, L - fpcN - 3.2, zKort - 1.2]) cube([5.0, 6.4, 1.2]); }  // XPT2046 (bare budsjett-skjermen)
module bryterbrett() {   // printet 1,0 mm plate med to Ø1,0-hull per bryter (ledningene) – limes på bryterne (se LES_MEG)
  difference() {
    linear_extrude(kortT) kort2d();
    for (b = BRYTERE) translate([b[1], L - b[2], -1]) for (dx = [-3.2, 3.2]) translate([dx, 0, 0]) cylinder(d = 1.0, h = 3, $fn = 12);
  }
}

// ---------- innmat (illustrasjon) ----------
module skjermmodul() {
  translate([W/2 - modW/2, L - modC - modH/2, zGlass - modT]) {
    color([0.22, 0.22, 0.24]) { cube([modW, modH, modT - 0.7]); styrepinner(); }
    color(c_glass) translate([0, 0, modT - 0.7]) cube([modW, modH, 0.7]);
  }
}
module styrepinner() { for (x = [pinInn, modW - pinInn], y = [pinInn, modH - pinInn]) translate([x, y, -pinH]) cylinder(d = pinD, h = pinH + 0.01, $fn = 16); }
module skjermflate() { translate([W/2 - scrAW/2, L - scrN - scrAH/2, zGlass + 0.005]) cube([scrAW, scrAH, 0.02]); }
// samme flate delt i fire fargede kvadranter (rød = øverst til venstre på skjermbildet, grønn = øverst til høyre,
// blå = nederst til høyre, gul = nederst til venstre; «øverst» er mot nesen) – skjerm_i_render.py finner hjørnene fra dem
module skjermhjorner() {
  for (q = [[0, 1, [1, 0, 0]], [1, 1, [0, 1, 0]], [1, 0, [0, 0, 1]], [0, 0, [1, 1, 0]]])
    color(q[2]) translate([W/2 - scrAW/2 + q[0]*scrAW/2, L - scrN - scrAH/2 + q[1]*scrAH/2, zGlass + 0.005]) cube([scrAW/2, scrAH/2, 0.02]);
}
module batteri() { color([0.55, 0.57, 0.60]) translate([W/2 - bat[0]/2, L - batN - bat[1], tB + 0.05]) cube(bat);
  color([0.75, 0.2, 0.2]) translate([W/2 + 3, L - batN - bat[1] - 3, tB + 1]) cube([2, 3.01, 1]); }   // kabel ut bak
// ESP32-S3 SuperMini: 18 × 22,5 mm, PCB 1,0, USB-C (9 × 7,3 × 3,2) mot nesen, keramisk antenne mot halen
module mcu_kort() { translate([mcuX - mcu[0]/2, L - mcuN - mcu[1], mcuZ + 0.05]) {
  color([0.10, 0.10, 0.12]) cube([mcu[0], mcu[1], 1.0]);
  color([0.75, 0.75, 0.77]) translate([mcu[0]/2 - 4.5, mcu[1] - 7.3 + 0.6, 1.0]) cube([9.0, 7.3, 3.2]);   // USB-C (rager 0,6 mm ut)
  color([0.15, 0.15, 0.16]) translate([5, 7, 1.0]) cube([7, 7, 0.9]);                                  // ESP32-S3
  color([0.85, 0.85, 0.85]) translate([3, 0.5, 1.0]) cube([12, 2.5, 1.2]); } }                          // antenne
module lader() { translate([ladX - lad[0]/2, ladY, tB + 0.05]) {
  color([0.12, 0.25, 0.55]) cube([lad[0], lad[1], 1.2]);
  color([0.8, 0.8, 0.82]) translate([lad[0]/2 - 4.5, -0.25, 1.2]) cube([9.0, 7.3, 3.2]);      // USB-C mot halen
  color([0.15, 0.15, 0.16]) translate([3, 11, 1.2]) cube([5, 4, 1.5]);                       // TP4056
  color([0.15, 0.15, 0.16]) translate([10, 13, 1.2]) cube([3, 3, 1.0]); } }                  // DW01 + FS8205
module ir_kort() {
  translate([W/2 - 17, L - t - 8.2, tB + 0.05]) color([0.12, 0.42, 0.22]) cube([34, 1.0, 6.0]);
  for (x = hu ? [W/2 - 7, W/2 + 1] : [W/2 - 11, W/2 - 3, W/2 + 5]) translate([x, L - t - 7.2, irZ]) rotate([-90, 0, 0]) color([0.30, 0.30, 0.45]) { cylinder(d = 3.0, h = 4.6, $fn = 20); translate([0, 0, 4.6]) sphere(d = 3.0, $fn = 20); }
  translate([W/2 + 9, L - t - 7.2, irZ - 2.6]) color([0.08, 0.08, 0.09]) cube([6, 4.6, 5.2]);       // VS1838B
  translate([W/2 - 16.5, L - t - 7.2, irZ - 1]) color([0.1, 0.1, 0.1]) cube([3, 1.2, 1.5]);        // AO3400 foran på kortet
}
module vibbryter() { color([0.75, 0.75, 0.78]) translate([vibX, L - vibN - 12, tB + 0.25 + 2.5]) rotate([-90, 0, 0]) cylinder(d = 5, h = 12, $fn = 24); }
module motor() { color([0.7, 0.7, 0.72]) translate([motX, L - motN, tB + 0.05]) cylinder(d = 10, h = 2.7, $fn = 40); }
// skjermens flatkabel (19,16 mm, ca. 20 mm bred) ned bak glasset og inn i J1 under tastekortet, og berøringens egen flex (6 mm)
module flatkabler() {
  // skjermens hale (9,5 mm, 42,58 mm) ned bak glasset og bakover til J1; berøringens (5,2 mm, 35,2 mm) til J2
  color([0.85, 0.55, 0.15]) for (f = [[fpcX, 9.5, fpcN, "J3"], [tpX, 5.2, tpN, "J4"]]) {
    ende = hu ? [for (d = HU_GULV) if (d[6] == (f[3] == "J3" ? "A1" : "A2") && d[5] > HU_FPC_Z) d[3]][0] : hk ? [for (d = D_DELER) if (d[6] == (en ? (f[3] == "J3" ? "J2" : "J3") : f[3])) d[3]][0] : L - f[2] + jD/2;   // kontaktens front (modellens y)
    zf = hu ? HU_FPC_Z : 6.4;   // hullkort: flatkablene går ned til adapterne på gulvet
    translate([f[0] - f[1]/2, L - modN0 - modH - 0.55, zf]) cube([f[1], 0.15, zGlass - modT - zf + 0.3]);
    translate([f[0] - f[1]/2, ende, zf]) cube([f[1], (L - modN0 - modH - 0.55 + 0.15) - ende, 0.15]);
  }
}
// ledningsbunter (1,5 × 1,5 mm) i kanalene på gulvet
module ledninger() { if (hu) color([0.85, 0.2, 0.2]) for (k = HU_BUNTER) for (i = [0:len(k) - 2]) hull() for (q = [k[i], k[i + 1]]) translate([q[0], L - q[1], kanalZ + 0.75]) cube([1.5, 1.5, 1.5], center = true);
  else color([0.85, 0.2, 0.2]) for (k = [KANAL_BAT, KANAL_IR]) if (len(k)) hull() for (q = k) translate([q[0], L - q[1], kanalZ + 0.75]) cube([1.5, 0.01, 1.5], center = true); }
module innmat() { batteri(); if (!hk) { mcu_kort(); lader(); } if (hu) hu_gulv(); ir_kort(); if (!en && !hu) { vibbryter(); motor(); } ledninger(); }
// hullkort-utgaven: bryterbeina (klippet til HU_BEIN under kortet, med loddet) og delene på gulvet (XIAO, MCP-modulen, FPC-adapterne)
module hu_bein() { for (p = HU_BEINPOS) translate([p[0], p[1], zKort - HU_BEIN]) cylinder(d = 1.6, h = HU_BEIN + 0.01, $fn = 12); }
module hu_gulv() { for (d = HU_GULV) color(d[6] == "U2" ? [0.42, 0.29, 0.66] : d[6][0] == "A" ? [0.80, 0.52, 0.18] : d[6] == "USBC" ? [0.78, 0.78, 0.80] : [0.15, 0.15, 0.16])
  translate([d[0], d[1], d[4]]) cube([d[2] - d[0], d[3] - d[1], d[5] - d[4]]); }

// ---------- i dokken (bare for bildene): samme plassering som fk_plass() i dokk/skjold_dokk.scad ----------
DOKK_A = 65; DOKK_HB = 12 + 6*sin(DOKK_A) + 8*cos(DOKK_A);
module i_dokk() { translate([0, 0, DOKK_HB]) rotate([DOKK_A, 0, 0]) translate([-W/2, 0, 0]) children(); }

// ---------- montert / eksplodert ----------
module montert(e = 0) {
  color(c_bunn) bunn();
  color(c_ir) translate([0, 0.6*e, 0]) ir_vindu();
  translate([0, 0, 0.35*e]) innmat();
  translate([0, 0, 0.75*e]) flatkabler();
  translate([0, 0, 0.75*e]) { color(c_kort) tastekort(); color([0.85, 0.85, 0.85]) brytere(); color([0.1, 0.1, 0.1]) tca(); }
  translate([0, 0, 1.05*e]) skjermmodul();
  if (skjerm == "nokkel") color([1, 0, 1]) translate([0, 0, 1.05*e]) skjermflate();
  translate([0, 0, 2.0*e]) { color(c_topp) topp(); color(c_gull) translate([0, 0, -0.02]) logo(); }
  translate([0, 0, 1.45*e]) {
    color(c_knapp) hetter("mork", HETTER); color(c_sym_l) symboler("mork", true, HETTER);
    color(c_lysk) hetter("lys", HETTER); color(c_sym_m) symboler("lys", true, HETTER);
    color(c_gull) hetter("gull", HETTER); color(c_sym_m) symboler("gull", true, HETTER);
    for (f = FARGER) color(f[1]) hetter(f[0], HETTER);
  }
  translate([0, 0, 1.45*e]) { color(c_knapp) hetter("mork", FRONT); color(c_sym_l) symboler("mork", true, FRONT); }
}

// ---------- utskriftsretning ----------
module print_topp() { translate([0, L, H]) rotate([180, 0, 0]) children(); }     // forsiden ned
// hettene printes i samme mønster som de sitter, men spredt (x × 1,35, n × 1,2), flensen ned
module spredt_ned(h) { translate([(h[2] - W/2)*1.35 + W*0.675, (h[3] - 61)*1.2 - 60, topp_av(h)]) rotate([180, 0, 0]) children(); }
module spredt(h) { translate([(h[2] - W/2)*1.35 + W*0.675, -(h[3] - 61)*1.2 + 170, -zHb]) children(); }
module print_gruppe(g, sym = false) { for (h = HETTER) if (gruppe(h) == g && (!sym || h[6] != "")) spredt(h) if (sym) symbol(h); else hette(h); }

if (part == "samlet") montert(0);
else if (part == "eksplodert") montert(25);
else if (part == "planet") {   // alle utskriftsdelene slik de ligger på platene (illustrasjon)
  color(c_topp) print_topp() topp(); color(c_gull) print_topp() logo();
  color(c_bunn) translate([W + 8, 0, 0]) bunn();
  translate([2*W + 20, 0, 0]) { color(c_knapp) print_gruppe("mork"); color(c_gull) print_gruppe("gull"); color(c_lysk) print_gruppe("lys"); for (f = FARGER) color(f[1]) print_gruppe(f[0]); }
}
else if (part == "A_topp") topp();
else if (part == "A_bunn") bunn();
else if (part == "A_logo") logo();
else if (part == "A_vindu") ir_vindu();
else if (part == "front_knapper") { for (h = FRONT) spredt_ned(h) hette_front(h); }   // forsiden ned
else if (part == "front_symboler") { for (h = FRONT) if (h[6] != "") spredt_ned(h) symbol(h); }
else if (part == "aktuatorer") { for (h = FRONT) ved(h) aktuatorer(h, 0.1); }
else if (part == "A_hetter") { hetter("mork"); hetter("lys"); hetter("gull"); for (f = FARGER) hetter(f[0]); }
else if (part == "A_symboler") { symboler("mork"); symboler("lys"); symboler("gull"); }
else if (part == "A_kort") { tastekort(); brytere(); tca(); }
else if (part == "A_skjerm") translate([W/2 - modW/2, L - modC - modH/2, zGlass - modT]) { cube([modW, modH, modT]); styrepinner(); }
else if (part == "A_batteri") batteri();
else if (part == "A_mcu") mcu_kort();
else if (part == "A_hkdeler" && hu) hu_gulv();
else if (part == "A_usbc" && hu) { for (d = HU_GULV) if (d[6] == "USBC") translate([d[0], d[1], d[4]]) cube([d[2] - d[0], d[3] - d[1], d[5] - d[4]]); }
else if (part == "hu_3d") { color([0.80, 0.70, 0.45]) tastekort(); color([0.15, 0.15, 0.16]) brytere(); color([0.75, 0.75, 0.77]) hu_bein(); hu_gulv(); }
else if (part == "A_hkdeler") { for (d = D_DELER) if (d[5] < 0) translate([d[0], d[1], zKort - d[4]]) cube([d[2] - d[0], d[3] - d[1], d[4]]); }
else if (part == "A_usbc") { for (d = D_DELER) if (d[6] == (en ? "USBC" : "J1")) translate([d[0], d[1], zKort - d[4]]) cube([d[2] - d[0], d[3] - d[1], d[4]]); }
else if (part == "A_lader") lader();
else if (part == "A_ir") ir_kort();
else if (part == "A_vib") vibbryter();
else if (part == "A_motor") motor();
else if (part == "A_flex") flatkabler();
else if (part == "A_ledninger") ledninger();
else if (part == "A_pogo") pogo_hunn();
else if (part == "hk_3d") {   // hovedkortet alene, sett fra undersiden (komponentene) – bruk med elektronikk="hovedkort"
  color([0.05, 0.35, 0.18]) tastekort(); color([0.85, 0.85, 0.85]) brytere();
  for (d = D_DELER) if (d[5] < 0)
    color(d[6] == "U1" ? [0.75, 0.75, 0.78] : d[6][0] == "J" ? [0.92, 0.92, 0.88] : d[6][0] == "T" ? [0.85, 0.7, 0.3] : [0.12, 0.12, 0.13])
      translate([d[0], d[1], zKort - d[4]]) cube([d[2] - d[0], d[3] - d[1], d[4]]);
}
else if (part == "inni") {   // bunnen med alt inni; tastekortet gjennomsiktig og skjermen bare som omriss
  color(c_bunn) bunn(); innmat(); flatkabler(); color(c_ir) ir_vindu();
  color(c_kort, 0.35) tastekort(); color([0.85, 0.85, 0.85]) brytere(); color([0.1, 0.1, 0.1]) tca();
  color([0.3, 0.3, 0.35], 0.18) translate([W/2 - modW/2, L - modC - modH/2, zGlass - modT]) cube([modW, modH, modT]);
}
else if (part == "montering") montert(40);
else if (part == "i_dokk") {           // bilder: fjernkontrollen i Skjold Dokk (dokk/stl/ fra dokk/lag_dokk.sh)
  color(farge == "mork" ? [0.17, 0.17, 0.18] : c_bone) import("dokk/stl/vugge.stl");
  color(farge == "mork" ? [0.82, 0.80, 0.75] : [0.169, 0.169, 0.176]) import("dokk/stl/sokkel.stl");
  color(c_gull) import("dokk/stl/gull.stl");
  i_dokk() montert(0);
}
else if (part == "skjermflate_dokk") i_dokk() skjermhjorner();
else if (part == "skjermflate") translate([0, 0, 1.05*skjermE]) skjermhjorner();
else if (part == "topp") print_topp() topp();
else if (part == "logo") print_topp() logo();
else if (part == "bunn") bunn();
else if (part == "ir_vindu") translate([0, 0, L]) rotate([-90, 0, 0]) ir_vindu();   // forsiden ned
else if (part == "knapper") print_gruppe("mork");
else if (part == "knapper_lys") print_gruppe("lys");
else if (part == "gull") print_gruppe("gull");
else if (part == "symboler_lyse") print_gruppe("mork", true);
else if (part == "symboler_morke") { print_gruppe("lys", true); print_gruppe("gull", true); }
else if (part == "farge_rod") print_gruppe("rod");
else if (part == "farge_gronn") print_gruppe("gronn");
else if (part == "farge_gul") print_gruppe("gul");
else if (part == "farge_bla") print_gruppe("bla");
else if (part == "bryterbrett") bryterbrett();
else if (part == "kort_omriss") translate([-3.2, -(L - PCB_N1)]) kort2d();   // 2D: tastekortets omriss (DXF), origo i nedre venstre hjørne
