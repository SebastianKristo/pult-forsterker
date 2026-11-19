// Skjold Nøkkel – lite kabinett for et ESP32-S3-DevKitC-1-klonekort (N16R8, YD-ESP32-S3 o.l.) som FIDO2/passkey-
// sikkerhetsnøkkel med pico-fido. Bare den innebygde USB-C-en («USB») er tilgjengelig; COM-porten er dekket.
// Brukerbekreftelse med en fjærtunge i toppen over BOOT, lysvindu over RGB-LED-en, RST bak et lite hull (binders).
// Ingen skruer: kortet ligger i holderen og klemmes av putene i toppen; bunnplata klikkes inn nedenfra.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater (montert): legg kortet med komponentene opp og USB-enden mot deg. x går fra kortkanten ved
// USB-kontaktene (x = 0) innover mot antenneenden, y sideveis fra midtlinja av kortet (+y = venstre, −y = høyre,
// der BOOT og RST sitter), z opp fra undersiden av kabinettet (0).
//
// Deler:
//   kasse – topp, sider og begge ender i ett. Fjærtunga med stempelet over BOOT, lysvinduet, RST-hullet, putene som
//           klemmer kortet, USB-hullet og øyet for nøkkelring. Printes med toppen ned (glatt topp med innfelt gull).
//   bunn  – bunnplata med støttene under kortet. Klikkes inn nedenfra (en vulst på hver langside går i et spor).
//   gull  – gullisten, Skjold-merket, SKJOLD og ringen rundt trykkpunktet (filament 2, samme utskrift som kassa).
//   vindu – lysvinduet/lyslederen over RGB-LED-en (hvit eller klar filament 3, samme utskrift som kassa).
//
// Bruk: openscad -D 'part="kasse"' -o kasse.stl skjold_nokkel.scad
// part: kasse | bunn | gull | vindu | samlet | eksplodert | inni | snitt | a_<del> (montert stilling, for sjekken)
use <../fonter/Inter-Bold.otf>

part = "samlet";
farge = "lys";        // lys | mork (bare for bildene)
oye = true;           // øye for nøkkelring i antenneenden
$fn = 48;

// =====================================================================================================
// MÅL DITT KORT – klonene varierer. Mål med skyvelære og rett tallene her før du printer (se LES_MEG.md).
// =====================================================================================================
kortL = 63.0;         // kretskortets lengde, uten modulen som stikker ut i antenneenden
kortB = 25.5;         // kretskortets bredde
kortT = 1.6;          // kretskortets tykkelse
modulUt = 2.0;        // så langt WROOM-modulen (antennen) stikker ut over kortenden
modulL = 25.5;        // modulens lengde (langs kortet); ESP32-S3-WROOM-1 er 25,5 × 18 × 3,1 mm
modulB = 18.0;        // modulens bredde
modulH = 3.2;         // modulens høyde over kortet (blikklokket)
// USB-C-kontaktene i USB-enden (x = 0). y = midten av kontakten, målt fra midtlinja av kortet (+ = venstre).
usbY = 6.6;           // «USB» – ESP32-S3 sin innebygde USB, den som brukes til FIDO (får hull)
comY = -6.6;          // «COM»/«UART» – USB-seriebrikka (dekkes)
usbKB = 8.94;         // kontaktens bredde (USB-C: 8,94 mm)
usbKH = 3.2;          // kontaktens høyde over kortet
usbKL = 7.35;         // kontaktens lengde inn på kortet
kontUt = 0.8;         // så langt kontaktene stikker ut over kortkanten
// knappene og lyset (midten av dem: x fra USB-kanten av kortet, y fra midtlinja, + = venstre, − = høyre)
bootX = 31.0; bootY = -7.5;    // BOOT (GPIO0) – trykkes av fjærtunga
rstX = 37.0;  rstY = -7.5;     // RST – nås med en binders gjennom et hull
knappH = 2.0;         // knappenes topp over kortet (med stempelet sitt)
knappB = 3.4;         // knappehusets side
rgbX = 24.0;  rgbY = -6.5;     // RGB-LED-en (WS2812, GPIO48, merket «RGB»)
rgbH = 1.0;           // LED-ens høyde over kortet
rgbB = 2.2;           // LED-ens side (2020: 2,2 mm, 5050: 5 mm)
// stiftlister og det som stikker ut under kortet
stift = false;        // true hvis det er loddet stiftlister på kortet (kabinettet blir ca. 7 mm høyere)
stiftUnder = 8.6;     // stiftlistene: plast + pinner under kortet
stiftOver = 3.0;      // pinneendene over kortet
underKomp = 1.6;      // uten stiftlister: lodding og komponenter under kortet
pinneX0 = 3.8;        // midten av første pinnehull (GND/5V-enden) fra USB-kanten; radene er 22 × 2,54 = 55,9 mm
pinneA = 22.86;       // avstanden mellom pinneradene
// USB-pluggen på kabelen din (plastkappa rundt metallet)
pluggB = 11.0; pluggH = 6.0;   // hullet blir 0,3 mm større på hver side
pluggKlar = 0.3;

// ---------- kabinettet ----------
klarK = 0.2;          // klaring kort ↔ vegger
t = 1.6;              // sidevegger
tEnde = 1.6;          // endeveggene
tb = 1.2;             // bunnplata
lokkT = 1.6;          // toppen
R = 1.5;              // fas på de stående hjørnene (fas, ikke runding: toppen ligger på plata)
fas = 0.8;            // fas på ytterkantene oppe og nede
klarB = 0.15;         // klaring bunnplate ↔ kasse

ug = stift ? stiftUnder + 0.4 : underKomp + 0.4;   // rommet under kortet
kz0 = tb + ug; kz1 = kz0 + kortT;                   // kortets under- og overside
toppKomp = max(modulH, usbKH, knappH, stift ? stiftOver : 0);
usbZ = kz1 + usbKH/2;                               // midt i USB-kontakten
hullB = pluggB + 2*pluggKlar; hullH = pluggH + 2*pluggKlar;
H = max(kz1 + toppKomp + 0.5 + lokkT, usbZ + hullH/2 + 1.2);   // høyden
zL = H - lokkT;                                     // undersiden av toppen
xi0 = -kontUt - 0.15; xi1 = kortL + modulUt + klarK;   // innsiden av endeveggene (COM-kontakten 0,15 mm fra veggen)
xo0 = xi0 - tEnde; xo1 = xi1 + tEnde;
yi = kortB/2 + klarK; yo = yi + t;
Lx = xo1 - xo0; W = 2*yo; cx = (xo0 + xo1)/2;
modX1 = kortL + modulUt; modX0 = modX1 - modulL;    // modulen (x)
kanX0 = modX0 + 0.7; kanX1 = modX1 - 6.5;           // blikklokket (resten er antennen)

// fjærtunga over BOOT: går på tvers av kortet, roten mot midten, trykkpunktet (og stempelet) over BOOT
tRet = bootY <= 0 ? 1 : -1;     // retning fra BOOT mot roten
tB = 5.6;             // tungas bredde (x)
tS = 0.6;             // spalten rundt tunga
tT = 1.0;             // tungas tykkelse (tynnere enn toppen, så den bøyer seg i roten)
tL = 11.0;            // fra roten til trykkpunktet
tSpiss = 2.4;         // tunga fortsetter så langt forbi trykkpunktet
yRot = bootY + tRet*tL; yTupp = bootY - tRet*tSpiss;
stempelD = 2.4;
luft = 0.2;           // luft mellom stempelet og BOOT-knappen (0,1–0,3 mm: ikke forspent)
knappVandring = 0.25; // knappens vandring til klikket
overTrykk = 0.3;      // tunga trykker knappen så langt forbi klikket
knappStift = 0.7;     // knappens stempel over huset (i modellen)
trykk = luft + knappVandring + overTrykk;
hengsel = 1.0;        // for sjekken: tunga dreies om en linje så langt ut fra roten (undersiden av tunga)
trykkVinkel = asin(trykk / (tL - hengsel));
// lysvinduet og RST
vinduD = 3.4;         // lysvinduet/lyslederen (Ø)
kragT = 1.0;          // kragen rundt lyslederen (skjermer lyset)
rstHull = 1.4;        // RST-hullet (en binders er ca. 0,9–1,0 mm)
// klipsene: en vulst på hver langside av bunnplata, et spor i hver sidevegg
vulstUt = 0.45; vulstZ = 0.7; vulstL = 24;
sporD = 0.45;         // sporets dybde inn i veggen fra innsiden
xm = (xi0 + xi1)/2;
// øyet for nøkkelring
oyeL = 8; oyeB = 10; oyeT = 2.6; oyeHull = 4.2;

// gull
gullT = 0.6; gullB = 1.0;
ringD = 4.6;
merkeH = 4.4; tekstS = 2.8;
blokkL = 22.4;                       // merke + SKJOLD (og gullisten under) er så lange
blokkX0 = (modX0 + xo1 - fas)/2 - blokkL/2 - 0.3;   // midt over modulen
tekstY = 2.0; listY = -4.4;

// ---------- hjelpere ----------
module crect(w, d, f) { offset(delta = f, chamfer = true) square([w - 2*f, d - 2*f], center = true); }
module rrect(w, d, r) { offset(r) offset(-r) square([w, d], center = true); }
module langs_x(x0, x1) { translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0) children(); }   // 2D (y, z) langs x

// Skjold-merket: fem avrundede staver (branding/skjold/skjold_merke.svg), sentrert
module merke2d(sc) {
  scale(sc) for (b = [[1, 22], [9, 33], [18.7, 42], [28.4, 33], [36.4, 22]])
    translate([b[0] - 21, 21 - b[1]]) hull() for (y = [2.3, b[1] - 2.3]) translate([2.3, y]) circle(2.3, $fn = 24);
}

// ytterformen: fas på de stående hjørnene og på kantene oppe og nede
module ytre() {
  hull() {
    translate([cx, 0, fas]) linear_extrude(H - 2*fas) crect(Lx, W, R);
    translate([cx, 0, 0]) linear_extrude(H) crect(Lx - 2*fas, W - 2*fas, max(R - fas*0.6, 0.1));
  }
}
module oye_form() {
  f = 0.5;
  hull() {
    translate([0, 0, H - oyeT + f]) linear_extrude(oyeT - 2*f) oye2d(0);
    translate([0, 0, H - oyeT]) linear_extrude(oyeT) oye2d(-f);
  }
}
module oye2d(o) {
  offset(delta = o) hull() {
    translate([xo1 - 2, -oyeB/2]) square([1, oyeB]);
    translate([xo1 + oyeL - 2 - 0.005, 0]) offset(delta = 2, chamfer = true) square([0.01, oyeB - 4], center = true);
  }
}

// tunga (2D-fotavtrykk og boksen som skilles ut for sjekken)
module tunge_fot(o = 0) {
  ya = min(yTupp, yRot); yb = max(yTupp, yRot);
  translate([bootX - tB/2 - o, ya - (tRet > 0 ? o : 0)]) square([tB + 2*o, yb - ya + o]);
}
module tunge_boks() {   // den bevegelige delen: fra «hengsel» mm ut fra roten til tuppen
  ya = tRet > 0 ? yTupp - 0.01 : yRot - tRet*hengsel; yb = tRet > 0 ? yRot - tRet*hengsel : yTupp + 0.01;
  translate([bootX - tB/2 - 0.01, ya, kz1 + 0.5]) cube([tB + 0.02, yb - ya, H]);
}

// ---------- gull ----------
module gull2d() {
  translate([bootX, bootY]) difference() { circle(d = ringD, $fn = 64); circle(d = ringD - 2*gullB, $fn = 64); }
  translate([blokkX0 + merkeH*0.48, tekstY]) merke2d(merkeH/42);
  translate([blokkX0 + merkeH*0.96 + 1.7, tekstY]) text("SKJOLD", size = tekstS, font = "Inter:style=Bold", halign = "left", valign = "center", spacing = 1.18);
  translate([blokkX0, listY - gullB/2]) square([blokkL, gullB]);
}
module gull(e = 0) { translate([0, 0, H - gullT]) linear_extrude(gullT + e) gull2d(); }

// ---------- vindu (lysleder) ----------
module vindu() { translate([rgbX, rgbY, kz1 + rgbH + 0.6]) cylinder(d = vinduD, h = H - (kz1 + rgbH + 0.6), $fn = 32); }

// ---------- kasse ----------
module kasse_skall() {
  difference() {
    union() {
      difference() {
        union() { ytre(); if (oye) oye_form(); }
        translate([xi0, -yi, -1]) cube([xi1 - xi0, 2*yi, zL + 1]);   // hulrommet
      }
      // puter som klemmer kortet ned: på USB-kontaktene og på blikklokket på modulen (0,1 mm luft)
      for (y = [usbY, comY]) translate([0.6, y - 2.5, kz1 + usbKH + 0.1]) cube([usbKL - 1.4, 5, zL - kz1 - usbKH - 0.1 + 0.01]);
      for (y = [-5.5, 5.5]) translate([kanX0 + 2, y - 1, kz1 + modulH + 0.1]) cube([kanX1 - kanX0 - 4, 2, zL - kz1 - modulH - 0.1 + 0.01]);
      // kragen rundt lyslederen og rundt RST-hullet
      translate([rgbX, rgbY, kz1 + rgbH + 0.6]) cylinder(d = vinduD + 2*kragT, h = zL - (kz1 + rgbH + 0.6) + 0.01, $fn = 32);
      translate([rstX, rstY, kz1 + knappH + 0.6]) cylinder(d = rstHull + 2, h = zL - (kz1 + knappH + 0.6) + 0.01, $fn = 32);
    }
    // sporene for vulstene på bunnplata (45° oppe og nede)
    for (s = [-1, 1]) langs_x(xm - vulstL/2 - 0.5, xm + vulstL/2 + 0.5)
      polygon([[s*(yi - 0.01), vulstZ - sporD - 0.12], [s*(yi + sporD), vulstZ - 0.12], [s*(yi + sporD), vulstZ + 0.12], [s*(yi - 0.01), vulstZ + sporD + 0.12]]);
    // USB-hullet: tilpasset pluggen, gjennom endeveggen og 0,3 mm inn forbi kontakten; 0,3 mm fas utover
    translate([xo0 - 1, usbY, usbZ]) rotate([0, 90, 0]) linear_extrude(-kontUt + 0.3 - xo0 + 1) rrect(hullH, hullB, 1.5);
    translate([xo0 - 0.01, usbY, usbZ]) rotate([0, 90, 0]) linear_extrude(0.31, scale = [hullH/(hullH + 0.6), hullB/(hullB + 0.6)]) rrect(hullH + 0.6, hullB + 0.6, 1.8);
    // fjærtunga: spalte rundt (gjennom toppen) og tynnere enn toppen
    difference() {
      translate([0, 0, zL - 1]) linear_extrude(lokkT + 2) tunge_fot(tS);
      translate([0, 0, zL - 2]) linear_extrude(lokkT + 4) offset(delta = 0.001) tunge_fot(0);
      translate([bootX - tB, yRot, zL - 2]) cube([2*tB, tRet*2, lokkT + 4]);   // roten står igjen
    }
    translate([0, 0, zL - 1]) linear_extrude(1 + lokkT - tT) tunge_fot(0);
    // lysvinduet (lyslederen fyller det) og RST-hullet med liten fas oppe
    translate([rgbX, rgbY, kz1]) cylinder(d = vinduD, h = H, $fn = 32);
    translate([rstX, rstY, kz1]) cylinder(d = rstHull, h = H, $fn = 24);
    translate([rstX, rstY, H - 0.4]) cylinder(d1 = rstHull, d2 = rstHull + 0.8, h = 0.41, $fn = 24);
    // øyet
    if (oye) translate([xo1 + oyeL - oyeB/2 + 0.6, 0, H - oyeT - 1]) {
      cylinder(d = oyeHull, h = oyeT + 2);
      translate([0, 0, oyeT + 1 - 0.4]) cylinder(d1 = oyeHull, d2 = oyeHull + 0.8, h = 0.41);
    }
    // gullet
    gull(0.01);
  }
}
module stempel() { translate([bootX, bootY, kz1 + knappH + luft]) cylinder(d = stempelD, h = H - tT - (kz1 + knappH + luft) + 0.01, $fn = 32); }
module kasse() { kasse_skall(); stempel(); }
module kasse_fast() { difference() { kasse_skall(); tunge_boks(); } }
module tunge() { intersection() { union() { kasse_skall(); stempel(); } tunge_boks(); } }
module tunge_trykt() {   // tunga trykket ned så stempelet går «trykk» mm under knappens topp (dreid om roten)
  yh = yRot - tRet*hengsel;
  translate([0, yh, H - tT]) rotate([tRet*trykkVinkel, 0, 0]) translate([0, -yh, -(H - tT)]) tunge();
}

// ---------- bunn ----------
module bunn() {
  bx0 = xi0 + klarB; bx1 = xi1 - klarB; by = yi - klarB;
  difference() {
    union() {
      hull() {
        translate([(bx0 + bx1)/2, 0, 0.4]) linear_extrude(tb - 0.4) square([bx1 - bx0, 2*by], center = true);
        translate([(bx0 + bx1)/2, 0, 0]) linear_extrude(tb) square([bx1 - bx0 - 0.8, 2*by - 0.8], center = true);
      }
      // vulstene (45° oppe og nede)
      for (s = [-1, 1]) langs_x(xm - vulstL/2, xm + vulstL/2)
        polygon([[s*(by - 0.5), vulstZ - vulstUt - 0.15], [s*by, vulstZ - vulstUt - 0.15], [s*(by + vulstUt), vulstZ - 0.15],
                 [s*(by + vulstUt), vulstZ + 0.15], [s*by, vulstZ + vulstUt + 0.15], [s*(by - 0.5), vulstZ + vulstUt + 0.15]]);
      // støttene under kortet: tverrlist under antenneenden, pute midt i USB-enden (mellom kontaktene), stolpe under BOOT
      translate([kortL - 3.6, -8, tb - 0.01]) cube([3.0, 16, kz0 - tb + 0.01]);
      translate([0.6, -1.5, tb - 0.01]) cube([2.0, 3.0, kz0 - tb + 0.01]);
      translate([bootX, bootY, tb - 0.01]) cylinder(d = 3.2, h = kz0 - tb + 0.01, $fn = 32);
    }
    // hakk i antenneenden for en negl eller en mynt (bunnplata lirkes ut her)
    translate([bx1 - 1.2, -4, -1]) cube([2, 8, tb + 2]);
  }
}

// ---------- kjøpte deler (bildene og sjekken) ----------
module knapp(x, y, stiften = true) {
  color("#d8d8d8") translate([x - knappB/2, y - knappB/2, kz1]) cube([knappB, knappB, knappH - knappStift]);
  if (stiften) color("#222") translate([x, y, kz1 + knappH - knappStift - 0.01]) cylinder(d = 1.6, h = knappStift + 0.01, $fn = 24);
}
module usb_kontakt(y) {
  color("silver") translate([-kontUt, y, kz1 + usbKH/2]) rotate([0, 90, 0]) linear_extrude(usbKL) rrect(usbKH, usbKB, 1.2);
}
module kortet(bootStift = true) {
  color("#16181c") translate([0, -kortB/2, kz0]) cube([kortL, kortB, kortT]);
  // pinnehullene (bare for bildene)
  color("#c9a227") for (s = [-1, 1], i = [0 : 21]) translate([pinneX0 + i*2.54, s*pinneA/2, kz1]) cylinder(d = 1.6, h = 0.05, $fn = 12);
  // WROOM-modulen: kretskort med antenne og blikklokk
  color("#1f3b2a") translate([modX0, -modulB/2, kz1]) cube([modulL, modulB, 0.8]);
  color("#c8ccd0") translate([kanX0, -modulB/2 + 0.6, kz1 + 0.79]) cube([kanX1 - kanX0, modulB - 1.2, modulH - 0.79]);
  usb_kontakt(usbY); usb_kontakt(comY);
  knapp(bootX, bootY, bootStift); knapp(rstX, rstY);
  color("#f4f4f4") translate([rgbX - rgbB/2, rgbY - rgbB/2, kz1]) cube([rgbB, rgbB, rgbH]);
  if (stift) {
    color("#111") for (s = [-1, 1]) translate([pinneX0 - 1.27, s*pinneA/2 - 1.27, kz0 - 2.5]) cube([22*2.54, 2.54, 2.5]);
    color("#c9a227") for (s = [-1, 1], i = [0 : 21]) translate([pinneX0 + i*2.54 - 0.32, s*pinneA/2 - 0.32, kz0 - stiftUnder]) cube([0.64, 0.64, stiftUnder + kortT + stiftOver]);
  }
}
module boot_stift() { translate([bootX, bootY, kz1 + knappH - knappStift - 0.01]) cylinder(d = 1.6, h = knappStift + 0.01, $fn = 24); }
module plugg(y, l = 22) {   // plastkappa på USB-C-pluggen, helt inne (kappa mot kontakten)
  color("#2a2a2a") translate([-kontUt - 0.05, y, usbZ]) rotate([0, -90, 0]) linear_extrude(l) rrect(pluggH, pluggB, 1.5);
  color("#2a2a2a") translate([-kontUt - 0.05 - l, y, usbZ]) rotate([0, -90, 0]) cylinder(d = 3.8, h = 25);
}

// ---------- utskrift og visning ----------
lys = farge == "lys";
kfarge = lys ? "#efeee9" : "#2b2b2d";
gfarge = "#d9a441";
bfarge = lys ? "#d6d3cc" : "#1f1f21";
vfarge = "#f6f8fa";
module snu() { translate([0, 0, H]) rotate([180, 0, 0]) children(); }   // toppen ned

if (part == "kasse") snu() kasse();
else if (part == "gull") snu() gull();
else if (part == "vindu") snu() vindu();
else if (part == "bunn") bunn();
else if (part == "a_kasse") kasse();
else if (part == "a_kasse_fast") kasse_fast();
else if (part == "a_tunge") tunge();
else if (part == "a_tunge_trykt") tunge_trykt();
else if (part == "a_bunn") bunn();
else if (part == "a_gull") gull();
else if (part == "a_vindu") vindu();
else if (part == "a_kort") kortet();
else if (part == "a_kort_u") kortet(false);
else if (part == "a_stift") boot_stift();
else if (part == "a_plugg") plugg(usbY);
else if (part == "a_plugg_com") plugg(comY);
else if (part == "a_lys") translate([rgbX, rgbY, kz1 + rgbH]) cylinder(d = 2.0, h = zL - kz1 - rgbH, $fn = 24);   // lyset opp til toppen
else if (part == "a_binders") translate([rstX, rstY, kz1 + knappH]) cylinder(d = 1.0, h = 20, $fn = 16);
else if (part == "samlet" || part == "eksplodert") {
  e = part == "eksplodert" ? 14 : 0;
  translate([0, 0, e]) { color(kfarge) kasse(); color(gfarge) gull(); color(vfarge, 0.9) vindu(); }
  translate([0, 0, -e]) color(bfarge) bunn();
  kortet();
  translate([-e, 0, 0]) plugg(usbY);
}
else if (part == "inni") {   // toppen fjernet: kortet i bunnplata, veggene rundt
  color(kfarge) intersection() { kasse(); translate([xo0 - 1, -W, -1]) cube([Lx + 20, 2*W, kz1 + 1.6]); }
  color(bfarge) bunn(); kortet();
}
else if (part == "snitt") {   // snitt gjennom BOOT (tunga, stempelet og knappen) og lyslederen
  intersection() {
    union() { color(kfarge) kasse(); color(gfarge) gull(); color(vfarge) vindu(); color(bfarge) bunn(); kortet(); }
    translate([bootX - 40, -W, -1]) cube([40, 2*W, H + 2]);
  }
}
