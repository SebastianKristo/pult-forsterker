// Skjold Bryter – boks under pulten med fem vippebrytere (KN3C-101 / E-TEN1021 o.l., M12-gjenge) og ESP32 D1 mini
// (eller Wemos D1 mini). Boksen skrus opp under bordplata med fire treskruer gjennom vingene på sidene; spakene
// peker mot deg, og USB-kabelen går ut bak.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater (montert): x mot høyre (midt = 0), y innover under pulten (fronten = 0), z opp (undersiden = 0,
// bordplata = H).
//
// Deler:
//   kasse  – topp (mot bordplata) med vinger, front med bryterhull, sider og bakvegg med USB-hull. Åpen nedover.
//            Printes med toppen ned (vingene på plata), ingen støtte.
//   bunn   – plata som lukker kassa nedenfra, med holderen for ESP-kortet. Skrus i kassa med 6 × M3 × 8 (selvgjengende).
//   gull   – gullisten og SKJOLD i fronten (filament 2, samme utskrift som kassa).
//
// Bryterne: Ø12,2-hull med en kort spiss oppå (printes uten støtte; spissen ligger under mutteren). Spaken vipper
// opp/ned. Mutteren innenfor settes slik at 6–7 mm gjenge stikker ut, så passer gummihetta (21 mm) eller den ytre
// mutteren. Kroppen (13 × 29 mm, ca. 29 mm lang med skrueklemmene) får plass bak fronten.
//
// Bruk: openscad -D 'kort="esp32d1"' -D 'part="bunn"' -o bunn.stl skjold_bryter.scad
// part: kasse | bunn | gull | samlet | eksplodert | a_<del> (montert stilling, for sjekken)
use <../fonter/Inter-Bold.otf>

part = "samlet";
kort = "esp32d1";     // "esp32d1" (ESP32 D1 mini / MH-ET LIVE MiniKit, 39 × 31,4 mm, micro-USB under)
                      // | "d1mini" (Wemos D1 mini, 34,2 × 25,6 mm, USB oppå)
N = 5;                // antall brytere
farge = "lys";        // lys | mork (bare for bildene)
$fn = 64;

E32 = kort == "esp32d1";

// ---------- mål ----------
P = 25;               // avstand mellom bryterne (mutteren er ca. 19,6 mm over hjørnene, hetta Ø21)
t = 2.4;              // sidevegger
tf = 3.0;             // fronten (bryterens gjenge er ca. 9,5 mm: mutter innenfor, 6–7 mm ut)
tr = 2.4;             // bakveggen
tTop = 3.0;           // toppen (mot bordplata)
tLid = 2.4;           // bunnplata
Hi = 36;              // innvendig høyde (bryterkroppen er 29 mm i spakens retning)
Di = 50;              // innvendig dybde (bryteren er ca. 29 mm bak fronten, resten er til ledningene)
boss = 9;             // skruesøylene i hjørnene (9 × 9)
klar = 0.25;          // klaring bunnplate ↔ kasse
R = 4;                // hjørneradius sett ovenfra
fas = 1.2;            // fas på ytterkantene

// ESP-kortet: ligger flatt på bunnplata til høyre for bryterne, med USB-enden mot bakveggen
vB = E32 ? 31.4 : 25.6;        // kortets bredde (x)
vL = E32 ? 39.0 : 34.2;        // kortets lengde (y)
vT = E32 ? 1.6 : 1.0;          // tykkelse
bZ = E32 ? 5.2 : 2.6;          // kortets underside over bunnplata (micro-USB under MiniKit, CH340 under D1 mini)
lomB = 32.4;                   // plassen som er satt av til kortet (det største, ESP32 D1 mini)
kontUt = E32 ? 0.6 : 0.3;      // USB-kontakten stikker så langt ut over kortkanten
usbB = 12; usbH = 8;           // hullet for pluggen i bakveggen

Wi = boss + 3 + N*P + 4 + lomB + 2.5 + boss;
W = Wi + 2*t;
H = tLid + Hi + tTop;
Dy = tf + Di + tr;
xL = -W/2 + t; xR = W/2 - t;   // innsiden av sideveggene
yF = tf; yB = Dy - tr;         // innsiden av fronten og bakveggen
zB = tLid; zT = H - tTop;      // oversiden av bunnplata og undersiden av toppen

// bryterne
bx = [for (i = [0 : N-1]) xL + boss + 3 + P/2 + i*P];
bz = zB + Hi/2;                // midt i hullene
hullD = 12.2;
// kortet
kx1 = xR - boss - 2.5; kx0 = kx1 - lomB; kcx = (kx0 + kx1)/2;    // plassen (x)
ky1 = yB - 0.15; ky0 = ky1 - vL;                                  // kortets kanter (y): kortkanten 0,15 mm fra bakveggen, kontakten stikker inn i USB-hullet
kz0 = zB + bZ; kz1 = kz0 + vT;                                    // under- og overside
usbZ = E32 ? kz0 - 1.4 : kz1 + 1.5;                               // midt i USB-kontakten
// skruesøyler: fire hjørner + to langs bakveggen mellom bryterne
skruer = [[xL + boss/2, yF + boss/2], [xR - boss/2, yF + boss/2], [xL + boss/2, yB - boss/2], [xR - boss/2, yB - boss/2],
          [(bx[1] + bx[2])/2, yB - boss/2], [(bx[N-3] + bx[N-2])/2, yB - boss/2]];
// vingene
vinge = 16; vingeT = 4; vingeHull = 4.6; vingeSenk = 9.2;
vingeY = [Dy*0.22, Dy*0.78];
// gull og tekst
gullB = 1.2; gullT = 0.6; gullZ = 6.0;
tekst = "SKJOLD"; tekstS = 4.2; tekstX = kcx; tekstZ = bz;

// ---------- hjelpere ----------
module rrect(w, d, r) { offset(r) offset(-r) square([w, d], center = true); }

// kassens ytre form: avrundet sett ovenfra, med fas nede og oppe
module ytre() {
  hull() {
    translate([0, Dy/2, fas]) linear_extrude(H - 2*fas) rrect(W, Dy, R);
    translate([0, Dy/2, 0]) linear_extrude(H) rrect(W - 2*fas, Dy - 2*fas, R - fas);
  }
}

// bryterhull: rund med en kort spiss oppover i printretningen (kassa printes opp ned, så spissen peker mot z = 0)
module bryterhull() {
  rotate([-90, 0, 0]) linear_extrude(tf + 2) hull() {
    circle(d = hullD);
    translate([0, hullD/2 + 0.9]) square([2.2, 0.1], center = true);   // y her = −z i modellen
  }
}

module gull2d() {
  translate([(bx[0] + bx[N-1])/2, gullZ]) square([bx[N-1] - bx[0] + 18, gullB], center = true);
  translate([tekstX, tekstZ]) text(tekst, size = tekstS, font = "Inter:style=Bold", halign = "center", valign = "center", spacing = 1.25);
  translate([tekstX, tekstZ - 6]) square([20, gullB], center = true);
}
module gull(e = 0) { translate([0, -e, 0]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(gullT + e) gull2d(); }

// ---------- kasse ----------
module kasse() {
  difference() {
    union() {
      difference() {
        ytre();
        translate([0, 0, -1]) linear_extrude(zT + 1) translate([0, (yF + yB)/2]) square([Wi, Di], center = true);
      }
      // skruesøyler
      for (s = skruer) translate([s[0] - boss/2, s[1] - boss/2, zB]) cube([boss, boss, zT - zB + 0.01]);
      // vinger med avstivere
      for (side = [-1, 1]) {
        translate([side*(W/2 + vinge/2 - 1), Dy/2, H - vingeT]) linear_extrude(vingeT) rrect(vinge + 2, Dy, 3);
        for (y = [6, Dy - 6]) translate([side*W/2, y, H - vingeT])
          rotate([90, 0, 0]) linear_extrude(2.4, center = true)
            polygon(side > 0 ? [[-0.5, 0], [vinge - 3, 0], [-0.5, -(H - vingeT - 6)]] : [[0.5, 0], [-(vinge - 3), 0], [0.5, -(H - vingeT - 6)]]);
      }
      // holdere som presser kortet ned mot bunnplata (fra toppen)
      for (p = holdere()) translate([p[0], p[1], kz1]) cylinder(d = 3, h = zT - kz1 + 0.01, $fn = 24);
    }
    // bryterhull
    for (x = bx) translate([x, -1, bz]) bryterhull();
    // USB-hull i bakveggen (avrundet), med fas utover
    translate([kcx, yB - 1, usbZ]) rotate([-90, 0, 0]) linear_extrude(tr + 2) rrect(usbB, usbH, 2);
    translate([kcx, Dy - 0.8, usbZ]) rotate([-90, 0, 0]) linear_extrude(1, scale = 1.15) rrect(usbB, usbH, 2);
    // skruehull i søylene (M3 selvgjengende)
    for (s = skruer) translate([s[0], s[1], zB - 1]) cylinder(d = 2.6, h = 14, $fn = 24);
    // vingehull: Ø4,6 med senk nedenfra (treskrue 4 × 16 med senkehode)
    for (side = [-1, 1], y = vingeY) translate([side*(W/2 + vinge/2), y, H - vingeT - 0.01]) {
      cylinder(d = vingeHull, h = vingeT + 1, $fn = 32);
      cylinder(d1 = vingeSenk, d2 = vingeHull, h = (vingeSenk - vingeHull)/2, $fn = 32);
    }
    // gullisten og SKJOLD
    gull(0.01);
  }
}
function holdere() = [for (sx = [-1, 1], y = [ky0 + 2.5, ky1 - 2.5]) [kcx + sx*(vB/2 - 2), y]];

// ---------- bunn ----------
module bunn() {
  bw = Wi - 2*klar; bd = Di - 2*klar;
  difference() {
    union() {
      translate([0, (yF + yB)/2, 0]) linear_extrude(tLid) square([bw, bd], center = true);
      // kortholderen: tverrlist under fremre kortkant, puter i hjørnene ved USB-enden, sidelister og stopp foran
      translate([kcx - vB/2, ky0, zB - 0.01]) cube([vB, 2.5, bZ + 0.01]);
      for (sx = [-1, 1]) translate([kcx + sx*(vB/2 - 2.5) - 2.5, ky1 - 2.5, zB - 0.01]) cube([5, 2.5, bZ + 0.01]);
      for (sx = [-1, 1]) translate([kcx + sx*(vB/2 + 0.3 + 0.8), (ky0 + ky1)/2, zB - 0.01])
        linear_extrude(bZ + vT + 1.2) square([1.6, vL - 6], center = true);
      translate([kcx - vB/2 + 2, ky0 - 0.3 - 1.6, zB - 0.01]) cube([vB - 4, 1.6, bZ + vT + 1.2]);
    }
    // skruehull med senk nedenfra (M3)
    for (s = skruer) translate([s[0], s[1], -0.01]) {
      cylinder(d = 3.4, h = tLid + 1, $fn = 24);
      cylinder(d1 = 6.4, d2 = 3.4, h = 1.5, $fn = 24);
    }
    // gummiføtter er unødvendig; to spor for buntebånd til ledningene langs bryterne
    for (x = [bx[1], bx[N-2]]) translate([x, yB - 14, -0.01]) for (dx = [-3, 3]) translate([dx - 1, 0, 0]) cube([2, 4, tLid + 1]);
  }
}

// ---------- kjøpte deler (bildene og sjekken) ----------
module bryter() {   // KN3C-101: gjenge M12 × 9,5, kropp 13 × 29 × 22 med skrueklemmer bak
  color("silver") rotate([-90, 0, 0]) translate([0, 0, -6.5]) cylinder(d = 11.9, h = 9.5);       // gjengen (y −6,5 … 3)
  color("silver") translate([0, -6.5, 0]) rotate([90, 0, 0]) rotate([0, 0, 0]) {                // spaken (vippet opp)
    rotate([-18, 0, 0]) cylinder(d1 = 4.5, d2 = 5.5, h = 16);
  }
  color("#6b3a2a") translate([-6.5, tf + 2.5, -14.5]) cube([13, 22, 29]);                       // kroppen
  color("silver") translate([-6.5, tf + 24.5, -10]) cube([13, 4, 20]);                          // klemmene
  color("silver") translate([0, tf, 0]) rotate([-90, 0, 0]) cylinder(d = 19.6, h = 2.4, $fn = 6); // mutteren innenfor
}
module kortet() {
  color("#1d5c3a") translate([kcx - vB/2, ky0, kz0]) cube([vB, vL, vT]);
  color("silver") translate([kcx - 4, ky1 - 5, E32 ? kz0 - 2.8 : kz1]) cube([8, 5 + kontUt, 2.8]);   // USB-kontakten (stikker kontUt inn i hullet i bakveggen)
  color("#222") translate([kcx - 9, ky0 + 2, kz1]) cube([18, E32 ? 25.5 : 24, 3.2]);                  // ESP-modulen
}

// ---------- utskrift og visning ----------
lys = farge == "lys";
kfarge = lys ? "#efeee9" : "#2b2b2d";
gfarge = "#d9a441";
module kasse_print() { translate([0, 0, H]) rotate([180, 0, 0]) kasse(); }
module gull_print() { translate([0, 0, H]) rotate([180, 0, 0]) gull(); }

if (part == "kasse") kasse_print();
else if (part == "gull") gull_print();
else if (part == "bunn") bunn();
else if (part == "a_kasse") kasse();
else if (part == "a_bunn") bunn();
else if (part == "a_gull") gull();
else if (part == "a_bryter") for (x = bx) translate([x, 0, bz]) bryter();
else if (part == "a_kort") kortet();
else if (part == "a_plugg") translate([kcx, ky1 + kontUt + 0.05, usbZ]) rotate([-90, 0, 0]) linear_extrude(18) rrect(E32 ? 10.5 : 11, 6.5, 1.5);   // USB-pluggen
else if (part == "inni") {   // uten toppen: kortet, bryterne og ledningsplassen sett ovenfra
  color(kfarge) difference() { kasse(); translate([-W, -1, zT - 6]) cube([2*W, Dy + 2, 20]); }
  color(kfarge) bunn(); kortet();
  for (x = bx) translate([x, 0, bz]) bryter();
}
else if (part == "samlet" || part == "eksplodert") {
  e = part == "eksplodert" ? 30 : 0;
  color(kfarge) kasse();
  color(gfarge) gull();
  translate([0, 0, -e]) { color(kfarge) bunn(); kortet(); }
  for (x = bx) translate([x, -e/2, bz]) bryter();
}
