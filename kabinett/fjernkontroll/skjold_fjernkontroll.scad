// Skjold Fjernkontroll – universell fjernkontroll med 2,8″ fargeberøringsskjerm, 21 taster (full variant 37), IR og Wi-Fi. Parametrisk OpenSCAD.
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

part = "samlet";
variant = "kort";               // kort (standard: 21 taster, 184 mm) | full (valgfri, med talltaster og smarthus-rad: 37 taster, 227 mm)
kortv = variant == "kort";
farge = "lys";                  // lys | mork | bone (Bone White PLA + mørk PETG) | bone_gra (Bone White PLA + grå PETG)
skjerm = "glass";               // glass | nokkel (aktivt område i magenta, så lag_render.sh kan legge inn et skjermbilde)
skjermE = 0;                    // part="skjermflate": samme eksplosjonsavstand som bildet
$fn = 48;

// ---------- ytre mål ----------
W = 55; L = kortv ? L_KORT : L_FULL;   // bredde og lengde (fra taster.py: 230 eller 187 mm)
HETTER = kortv ? HETTER_KORT : HETTER_FULL;
BRYTERE = kortv ? BRYTERE_KORT : BRYTERE_FULL;
PCB_N1 = kortv ? PCB_N1_KORT : PCB_N1_FULL;
DN = 22;                        // alt under skjermen er flyttet 22 mm mot halen for 2,8″-skjermen (taster.py: DN)
H = 13.5;                       // høyde uten taster (tastene står 1,2 mm opp, gullringen 1,5 mm: 15,0 mm totalt)
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
zKort = 8.2; kortT = 1.0;       // tastekortet (JLCPCB 1,0 mm), undersiden
swH = 1.5;                      // SMD-bryter 4 × 4 × 1,5 mm
zHb = zKort + kortT + swH + 0.1;  // hettens underside (0,1 mm over bryteren) = 10,8
opp = 1.2;                      // tastene står 1,2 mm over toppen
ringOpp = 1.5;                  // gullringen 1,5 mm
okOpp = 1.1;
ink = 0.4;                      // symbolene: 0,4 mm innfelt, fylt med annen farge (2 lag à 0,2 mm)
kf = 0.5;                       // fas på hettens toppkant

// ---------- skjerm ----------
// 2,8″ 240 × 320 naken FPC-modul med dekkglass: IPS med kapasitiv berøring (ST7789 + FT6336U, standard) eller
// «Budsjett-skjerm» TN med resistiv berøring (ST7789V + XPT2046 på tastekortet). Begge har samme omriss etter
// tegningen: 50,00 × 69,20 ± 0,2 mm, aktivt område 43,20 × 57,60 mm 2,60 mm fra overkanten (motsatt flatkabelen),
// 3,8 mm tykk med berøring. Flatkabelen (19,16 mm) går ut i nedre kant mot tastene og bøyes ned til en
// 18-pinners 0,8 mm FPC-kontakt på undersiden av tastekortet.
// Vinduet er glasset minus 1,5 mm kant på sidene og oppe, og slutter 1,1 mm under det aktive området nede.
modN0 = 8.4;                    // modulens nesekant fra nesen (R11-hjørnet bestemmer hvor nær den kan gå)
modW = 50.0; modH = 69.2; modT = 4.0;  // glass/modul (lomme under toppen, 0,3 mm klaring ≥ toleransen ± 0,2); 3,8 mm + tape
modC = modN0 + modH/2;          // modulens senter fra nesen (43,0)
aktivTopp = 2.6;                // fra glassets overkant (mot nesen) til det aktive området
scrAW = 43.2; scrAH = 57.6;     // aktivt område
scrN = modN0 + aktivTopp + scrAH/2;   // det aktive områdets og vinduets senter fra nesen (39,8)
scrWW = modW - 3; scrWH = scrAH + 2*(aktivTopp - 1.5);   // vindu i toppen: 47,0 × 59,8 mm
fpcN = modN0 + modH + 4.5;      // FPC-kontakten under tastekortet (senter, n), 18-pinners 0,8 mm, 19,6 × 5 × 2 mm
lepT = 0.8;                     // toppflaten over glasset rundt vinduet
zGlass = H - lepT;              // glassets overside (12,7)

// ---------- skruer (M2 × 10 selvgjengende, 5 stk) ----------
bossD = 5.0;  bossBD = 6.0;     // tårn i toppen og bunnen
pilot = 1.7;  klar = 2.3;  hodeD = 4.3;  hodeH = 2.5;
zMot = zs + lipH;               // hjørnetårnene møtes her (8,6)
SKRUER = [[7.5, L - 5.5], [W - 7.5, L - 5.5], [4.9, 8], [W - 4.9, 8], [8, L - 120]];   // nese ×2 (foran skjermen), hale ×2, midt (venstre for volumvippa, n = 120)
MIDT = 4;                       // skrue nr. 4 (midt) klemmer tastekortet
PINNER = [[W/2 - 7.5, 101 + DN], [W/2 + 7.5, 101 + DN]];   // pinner fra toppen og stolper fra bunnen klemmer kortet (x, n)

// ---------- innmat ----------
bat = [34, 50, 6.0];  batN = 11;    // LiPo 603450 (1200 mAh) under skjermen, fra n = 11
mcu = [18, 22.6, 4.6];              // ESP32-S3 SuperMini (antennen mot halen)
mcuN = kortv ? 125 : 150 + DN;       // kort: foran laderen, til venstre for midtskruen
mcuX = kortv ? 13.5 : W/2;
STOLPER = kortv ? [[W/2 - 15, 70 + DN], [W/2 + 15, 70 + DN], [W/2 - 15, 165], [W/2 + 15, 165]]
                : [[W/2 - 15, 70 + DN], [W/2 + 15, 70 + DN], [W/2 - 15, 172 + DN], [W/2 + 15, 172 + DN]];
TCA = kortv ? [[W/2 - 13, 157], [W/2, 157]] : [[W/2 - 13, 135 + DN], [W/2, 135 + DN], [W/2 + 13, 135 + DN]];   // TCA9555 under kortet
lad = [17, 26, 4.6];                // TP4056 USB-C-modul med beskyttelse, mot halen
usbW = 9.4; usbH = 3.6; usbZ = tB + 1.2 + 1.6;   // USB-C-åpningen (senter z ≈ 4,4)
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
module tekst(s, z = 3.0) { text(s, size = z, font = "Liberation Sans:style=Bold", halign = "center", valign = "center"); }
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
module vippe_ikon(i) {
  translate([0, VIPPE_D]) if (i == "vol") { strek([-1.2, 0], [1.2, 0]); strek([0, -1.2], [0, 1.2]); } else { strek([-1.2, -0.6], [0, 0.6]); strek([0, 0.6], [1.2, -0.6]); }
  translate([0, -VIPPE_D]) if (i == "vol") strek([-1.2, 0], [1.2, 0]); else { strek([-1.2, 0.6], [0, -0.6]); strek([0, -0.6], [1.2, 0.6]); }
  circle(d = 0.9, $fn = 12);
}
module symbol2d(h) {   // symbolet for hette h, i hettens lokale ramme (y peker mot nesen)
  if (h[1] == "vippe") vippe_ikon(h[6]);
  else if (h[1] == "ring") for (a = [0:90:270]) rotate(a) polygon([[-2.3, 10.1], [2.3, 10.1], [0, 13.4]]);   // piler 4,6 × 3,3 mm
  else ikon(h[6]);
}

// ---------- hettene ----------
// Flat underside på zHb, flens fl rundt, kroppen gjennom hullet og opp til toppen + opp. Symbolet er felt inn ink mm.
function topp_av(h) = h[1] == "ring" ? H + ringOpp : h[1] == "ok" ? H + okOpp : H + opp;
module hette_kropp(h) {
  f = h[1]; b = h[4]; hh = h[5]; zt = topp_av(h);
  if (f == "ring") {
    ri = hh/2;                   // indre radius (7,3)
    difference() {
      union() {
        translate([0, 0, zHb]) cylinder(r = b/2 + fl, h = flT, $fn = 96);
        translate([0, 0, zHb]) hull() { cylinder(r = b/2, h = zt - zHb - kf, $fn = 96); cylinder(r = b/2 - kf, h = zt - zHb, $fn = 96); }
      }
      translate([0, 0, zHb - 1]) cylinder(r = ri, h = 12.6 - zHb + 1, $fn = 64);         // OK-ens flens går inn her
      translate([0, 0, 12.6 - 0.001]) cylinder(r1 = ri, r2 = ri - 0.7, h = 0.7, $fn = 64);   // 45° krage holder OK-en
      translate([0, 0, 13.3 - 0.01]) cylinder(r = ri - 0.7, h = 5, $fn = 64);
    }
  } else if (f == "ok") {
    ri = 7.3 - 0.3;              // OK: 0,3 mm klaring inni ringen (nedre del Ø14, øvre Ø12,6)
    union() {
      translate([0, 0, zHb]) cylinder(r = ri, h = 12.3 - zHb, $fn = 64);
      translate([0, 0, 12.3 - 0.001]) cylinder(r1 = ri, r2 = ri - 0.7, h = 0.7, $fn = 64);
      translate([0, 0, 12.3]) hull() { cylinder(r = b/2, h = zt - 12.3 - kf, $fn = 64); cylinder(r = b/2 - kf, h = zt - 12.3, $fn = 64); }
    }
  } else {
    translate([0, 0, zHb]) linear_extrude(flT) hform(f, b, hh, fl);
    hull() {
      translate([0, 0, zHb]) linear_extrude(zt - zHb - kf) hform(f, b, hh);
      translate([0, 0, zt - 0.01]) linear_extrude(0.01) offset(-kf) hform(f, b, hh);
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
module hetter(g) { for (h = HETTER) if (gruppe(h) == g) ved(h) hette(h); }
module symboler(g, vis = false) { for (h = HETTER) if (gruppe(h) == g && h[6] != "") ved(h) if (vis) symbol_vis(h); else symbol(h); }

// ---------- toppen ----------
module topp() {
  difference() {
    union() {
      difference() {
        kropp_over();
        hulrom();
      }
      // skruetårn: hjørnene ned til zMot, midten ned til tastekortet
      intersection() {
        hulrom();
        for (i = [0:len(SKRUER) - 1]) translate([SKRUER[i][0], SKRUER[i][1], 0])
          if (i == MIDT) translate([0, 0, zKort + kortT]) cylinder(d = 4.0, h = H - tT - zKort - kortT + 0.01);
          else translate([0, 0, zMot]) cylinder(d = bossD, h = H - tT - zMot + 0.01);
      }
      // pinner som holder tastekortet nede
      for (p = PINNER) translate([p[0], L - p[1], zKort + kortT]) cylinder(d = 2.2, h = H - tT - zKort - kortT + 0.01, $fn = 20);
    }
    // hull for tastene
    for (h = HETTER) if (h[1] != "ok") ved(h) translate([0, 0, H - tT - 1]) linear_extrude(tT + 2) hform(h[1], h[4], h[5], spill);
    // skjermvindu og lomme for glasset
    translate([W/2, L - scrN, H - tT - 1]) linear_extrude(tT + 2) offset(1) square([scrWW - 2, scrWH - 2], center = true);
    translate([W/2, L - modC, H - tT - 1]) linear_extrude(tT - lepT + 1) offset(1) square([modW + 0.6 - 2, modH + 0.6 - 2], center = true);
    // skruehull (forbor)
    for (s = SKRUER) translate([s[0], s[1], zKort]) cylinder(d = pilot, h = H - 0.8 - zKort, $fn = 16);
    // SKJOLD felt inn nederst (gull)
    translate([0, 0, H - 0.5]) linear_extrude(1) logo2d();
  }
}
module logo2d() { translate([W/2, 5.2 + 1.6]) text("SKJOLD", size = 3.0, font = "Liberation Sans:style=Bold", halign = "center", valign = "center", spacing = 1.35); }
module logo() { translate([0, 0, H - 0.5]) linear_extrude(0.5) logo2d(); }   // flaten er flat her (godt innenfor fasen)

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
        translate([0, L - modN0 - modH - 0.6]) square([W, modH + 0.9]); }
      intersection() {
        hulrom();
        union() {
          for (i = [0:len(SKRUER) - 1]) translate([SKRUER[i][0], SKRUER[i][1], 0])
            cylinder(d = bossBD, h = (i == MIDT ? zKort : zMot));
          // stolper under tastekortet
          for (p = PINNER) translate([p[0], L - p[1], 0]) cylinder(d = 3.0, h = zKort, $fn = 20);
          for (p = STOLPER) translate([p[0], L - p[1], 0]) cylinder(d = 3.0, h = zKort, $fn = 20);
          // ribber: batterilomme, ladermodul og SuperMini
          translate([W/2, L - batN - bat[1]/2, tB - 0.01]) linear_extrude(1.6) difference() { square([bat[0] + 3.0, bat[1] + 3.0], center = true); square([bat[0] + 0.6, bat[1] + 0.6], center = true); translate([0, bat[1]/2]) square([12, 6], center = true); }
          translate([W/2, t + 0.6 + lad[1]/2, tB - 0.01]) linear_extrude(1.4) difference() { square([lad[0] + 2.6, lad[1] + 2.0], center = true); square([lad[0] + 0.4, lad[1] + 0.4], center = true); translate([0, -lad[1]/2]) square([lad[0] + 4, 4], center = true); }
          translate([mcuX, L - mcuN - mcu[1]/2, tB - 0.01]) linear_extrude(1.2) difference() { square([mcu[0] + 2.6, mcu[1] + 2.6], center = true); square([mcu[0] + 0.4, mcu[1] + 0.4], center = true); }
          // IR-kortet i nesen (lite hullkort 34 × 6,6 mm) står i et spor: bak ligger batteriribben, foran to korte knaster
          for (x = [W/2 - 17, W/2 + 14]) translate([x, L - t - 6.6, tB - 0.01]) cube([3, 1.0, 1.4]);
        }
      }
    }
    // skruehull med forsenket hode
    for (s = SKRUER) translate([s[0], s[1], -1]) { cylinder(d = klar, h = 20, $fn = 16); cylinder(d = hodeD, h = hodeH + 1, $fn = 24); }
    // USB-C i halen
    translate([W/2, -1, usbZ]) rotate([-90, 0, 0]) linear_extrude(t + 2) offset(1.2) square([usbW - 2.4, usbH - 2.4], center = true);
    // IR-vinduet i nesen: gjennomgående vindu og 0,6 mm krage innvendig
    translate([W/2, L + 1, irZ]) rotate([90, 0, 0]) linear_extrude(t + 2) offset(1) square([irW - 2, irH - 2], center = true);
    translate([W/2, L - t + 0.6, irZ]) rotate([90, 0, 0]) linear_extrude(1.2) offset(1) square([irW + 2 - 2, irH + 1 - 2], center = true);
    // to små hull for lysdioden på laderen (rød = lader, blå = full) ved siden av USB-C
    for (dx = [-8.5, 8.5]) translate([W/2 + dx, -1, usbZ]) rotate([-90, 0, 0]) cylinder(d = 1.2, h = t + 2, $fn = 12);
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
  difference() {
    translate([3.2, L - PCB_N1]) rrect(W - 6.4, PCB_N1 - PCB_N0, 4);
    for (i = [0:len(SKRUER) - 1]) translate([SKRUER[i][0], SKRUER[i][1]]) circle(d = i == MIDT ? 2.4 : bossBD + 0.6);
  }
}
module tastekort() { translate([0, 0, zKort]) linear_extrude(kortT) kort2d(); }
module brytere() { for (b = BRYTERE) translate([b[1], L - b[2], zKort + kortT]) { translate([-2, -2, 0]) cube([4, 4, swH - 0.4]); cylinder(d = 2.4, h = swH, $fn = 16); } }
module tca() { for (c = TCA) translate([c[0] - 2.2, L - c[1] - 3.9, zKort - 1.2]) cube([4.4, 7.8, 1.2]);
  translate([W/2 - 9.8, L - fpcN - 2.5, zKort - 2.0]) cube([19.6, 5.0, 2.0]);        // FPC-kontakt for skjermen
  translate([W/2 + 14 - 2.5, L - fpcN - 3.2, zKort - 1.2]) cube([5.0, 6.4, 1.2]); }  // XPT2046 (bare budsjett-skjermen)
module bryterbrett() {   // printet 1,0 mm plate med to Ø1,0-hull per bryter (ledningene) – limes på bryterne (se LES_MEG)
  difference() {
    linear_extrude(kortT) kort2d();
    for (b = BRYTERE) translate([b[1], L - b[2], -1]) for (dx = [-3.2, 3.2]) translate([dx, 0, 0]) cylinder(d = 1.0, h = 3, $fn = 12);
  }
}

// ---------- innmat (illustrasjon) ----------
module skjermmodul() {
  translate([W/2 - modW/2, L - modC - modH/2, zGlass - modT]) {
    color([0.22, 0.22, 0.24]) cube([modW, modH, modT - 0.7]);
    color(c_glass) translate([0, 0, modT - 0.7]) cube([modW, modH, 0.7]);
  }
}
module skjermflate() { translate([W/2 - scrAW/2, L - scrN - scrAH/2, zGlass + 0.005]) cube([scrAW, scrAH, 0.02]); }
// samme flate delt i fire fargede kvadranter (rød = øverst til venstre på skjermbildet, grønn = øverst til høyre,
// blå = nederst til høyre, gul = nederst til venstre; «øverst» er mot nesen) – skjerm_i_render.py finner hjørnene fra dem
module skjermhjorner() {
  for (q = [[0, 1, [1, 0, 0]], [1, 1, [0, 1, 0]], [1, 0, [0, 0, 1]], [0, 0, [1, 1, 0]]])
    color(q[2]) translate([W/2 - scrAW/2 + q[0]*scrAW/2, L - scrN - scrAH/2 + q[1]*scrAH/2, zGlass + 0.005]) cube([scrAW/2, scrAH/2, 0.02]);
}
module batteri() { color([0.55, 0.57, 0.60]) translate([W/2 - bat[0]/2, L - batN - bat[1], tB + 0.05]) cube(bat); }
module mcu_kort() { translate([mcuX - mcu[0]/2, L - mcuN - mcu[1], tB + 0.05]) { color([0.10, 0.10, 0.12]) cube([mcu[0], mcu[1], 1.0]); color([0.75, 0.75, 0.77]) translate([2, 2, 1]) cube([14, 16, 2.4]); } }
module lader() { translate([W/2 - lad[0]/2, t + 0.6, tB + 0.05]) { color([0.12, 0.25, 0.55]) cube([lad[0], lad[1], 1.2]); color([0.8, 0.8, 0.82]) translate([lad[0]/2 - 4.5, -0.25, 1.2]) cube([9.0, 7.5, 3.2]); } }
module ir_kort() {
  translate([W/2 - 17, L - t - 7.6, tB + 0.05]) color([0.12, 0.42, 0.22]) cube([34, 1.0, 6.6]);
  for (x = [W/2 - 12, W/2 - 4, W/2 + 4]) translate([x, L - t - 6.6, irZ]) rotate([-90, 0, 0]) color([0.30, 0.30, 0.45]) { cylinder(d = 3.0, h = 4.6, $fn = 20); translate([0, 0, 4.6]) sphere(d = 3.0, $fn = 20); }
  translate([W/2 + 9, L - t - 6.6, irZ - 2.6]) color([0.08, 0.08, 0.09]) cube([6, 4.6, 5.2]);
}

// ---------- montert / eksplodert ----------
module montert(e = 0) {
  color(c_bunn) bunn();
  color(c_ir) translate([0, 0.6*e, 0]) ir_vindu();
  translate([0, 0, 0.35*e]) { batteri(); mcu_kort(); lader(); ir_kort(); }
  translate([0, 0, 0.75*e]) { color(c_kort) tastekort(); color([0.85, 0.85, 0.85]) brytere(); color([0.1, 0.1, 0.1]) tca(); }
  translate([0, 0, 1.05*e]) skjermmodul();
  if (skjerm == "nokkel") color([1, 0, 1]) translate([0, 0, 1.05*e]) skjermflate();
  translate([0, 0, 2.0*e]) { color(c_topp) topp(); color(c_gull) translate([0, 0, -0.02]) logo(); }
  translate([0, 0, 1.45*e]) {
    color(c_knapp) hetter("mork"); color(c_sym_l) symboler("mork", true);
    color(c_lysk) hetter("lys"); color(c_sym_m) symboler("lys", true);
    color(c_gull) hetter("gull"); color(c_sym_m) symboler("gull", true);
    for (f = FARGER) color(f[1]) hetter(f[0]);
  }
}

// ---------- utskriftsretning ----------
module print_topp() { translate([0, L, H]) rotate([180, 0, 0]) children(); }     // forsiden ned
// hettene printes i samme mønster som de sitter, men spredt (x × 1,35, n × 1,2), flensen ned
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
else if (part == "A_hetter") { hetter("mork"); hetter("lys"); hetter("gull"); for (f = FARGER) hetter(f[0]); }
else if (part == "A_symboler") { symboler("mork"); symboler("lys"); symboler("gull"); }
else if (part == "A_kort") { tastekort(); brytere(); tca(); }
else if (part == "A_skjerm") translate([W/2 - modW/2, L - modC - modH/2, zGlass - modT]) cube([modW, modH, modT]);
else if (part == "A_batteri") translate([W/2 - bat[0]/2, L - batN - bat[1], tB + 0.05]) cube(bat);
else if (part == "A_mcu") translate([mcuX - mcu[0]/2, L - mcuN - mcu[1], tB + 0.05]) cube([mcu[0], mcu[1], 3.4]);
else if (part == "A_lader") translate([W/2 - lad[0]/2, t + 0.6, tB + 0.05]) cube([lad[0], lad[1], 4.4]);
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
