// Skjold Bryter – boks under pulten med fem vippebrytere (KN3C-101 / E-TEN1021 o.l., M12-gjenge) og ESP32 D1 mini
// (eller Wemos D1 mini). Et eget feste skrus opp under bordplata; boksen skyves inn i festet forfra og klikker på plass.
// Spakene peker mot deg, og USB-kabelen går ut bak. Ingen skruer i selve boksen.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater (montert): x mot høyre (midt = 0), y innover under pulten (fronten = 0), z opp (undersiden = 0,
// toppen av boksen = H, bordplata = H + festeT).
//
// Deler:
//   kasse  – topp med en vinge på hver side, front med bryterhull, sider og bakvegg med USB-hull. Åpen nedover.
//            Printes med toppen ned (vingene på plata), ingen støtte.
//   bunn   – plata som lukker kassa nedenfra, med holderen for ESP-kortet. Klikkes i med seks klips (vinduer i
//            sideveggene og bakveggen); trykk klipsene inn for å ta den ut igjen.
//   feste  – skrus under bordplata med fire treskruer. To skinner med 45° svalehale tar imot vingene; en knott i
//            festet klikker i et hull i en fjærende tunge i hver vinge når boksen er skjøvet helt inn.
//            Printes med bordsiden ned, ingen støtte.
//   gull   – gullisten og SKJOLD i fronten (filament 2, samme utskrift som kassa).
//
// Bryterne: Ø12,2-hull med en kort spiss oppå (printes uten støtte; spissen ligger under mutteren). Spaken vipper
// opp/ned. Mutteren innenfor settes slik at 6–7 mm gjenge stikker ut, så passer gummihetta (21 mm) eller den ytre
// mutteren. Kroppen (13 × 29 mm, ca. 29 mm lang med skrueklemmene) får plass bak fronten.
//
// Bruk: openscad -D 'kort="esp32d1"' -D 'part="bunn"' -o bunn.stl skjold_bryter.scad
// part: kasse | bunn | feste | gull | samlet | eksplodert | inni | a_<del> (montert stilling, for sjekken)
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
tTop = 3.0;           // toppen
tLid = 2.4;           // bunnplata
Hi = 36;              // innvendig høyde (bryterkroppen er 29 mm i spakens retning)
Di = 50;              // innvendig dybde (bryteren er ca. 29 mm bak fronten, resten er til ledningene)
kant = 5;             // fri plass innenfor sideveggene (klipsene)
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

Wi = kant + 3 + N*P + 4 + lomB + 2.5 + kant;
W = Wi + 2*t;
H = tLid + Hi + tTop;
Dy = tf + Di + tr;
xL = -W/2 + t; xR = W/2 - t;   // innsiden av sideveggene
yF = tf; yB = Dy - tr;         // innsiden av fronten og bakveggen
zB = tLid; zT = H - tTop;      // oversiden av bunnplata og undersiden av toppen

// bryterne
bx = [for (i = [0 : N-1]) xL + kant + 3 + P/2 + i*P];
bz = zB + Hi/2;                // midt i hullene
hullD = 12.2;
// kortet
kx1 = xR - kant - 2.5; kx0 = kx1 - lomB; kcx = (kx0 + kx1)/2;    // plassen (x)
ky1 = yB - 0.15; ky0 = ky1 - vL;                                  // kortkanten 0,15 mm fra bakveggen; kontakten stikker inn i USB-hullet
kz0 = zB + bZ; kz1 = kz0 + vT;                                    // under- og overside
usbZ = E32 ? kz0 - 1.4 : kz1 + 1.5;                               // midt i USB-kontakten

// ---------- klipsene (bunnplata) ----------
// En arm reiser seg fra bunnplata langs innsiden av veggen; mothaken øverst klikker ut i et vindu i veggen.
// Den flate undersiden av mothaken hviler på vinduets nedre kant, så plata ikke faller ut. Lister langs veggene
// stopper plata oppover. Trykk mothakene inn gjennom vinduene for å ta plata ut.
klipsB = 10; armT = 1.4;          // armens bredde og tykkelse
hakeUt = 1.2;                      // mothaken stikker så langt ut i vinduet
hakeZ = 13;                        // mothakens underside (= vinduets nedre kant)
hakeFlat = 0.6;                    // rett del før skråkanten (45°)
vinduH = hakeFlat + hakeUt + klar + 0.5;
// [x, y, retning]: retning = utover (−x, +x eller +y)
klips = [[xL, yF + 14, [-1, 0]], [xL, yB - 14, [-1, 0]], [xR, yF + 14, [1, 0]], [xR, yB - 14, [1, 0]],
         [bx[1], yB, [0, 1]], [bx[N-2], yB, [0, 1]]];
stoppB = 1.2;                      // listene som stopper plata (innsiden av veggene, rett over plata)

// ---------- vingene og festet ----------
vinge = 16; vingeT = 4;            // vingene: bredde ut fra sideveggen og tykkelse
svale = 3;                         // 45°-fasen under ytterkanten av vingen (svalehalen)
c = 0.3;                           // klaring i skinnene
festeT = 4;                        // festets plate (mot bordplata)
skinneV = 3;                       // skinnenes yttervegg
skinneU = 2;                       // skinnene går så langt under vingen
xo = W/2 + vinge;                  // vingens ytterkant
FW = 2*(xo + c + skinneV);         // festets bredde
stopp = 6;                         // festet er så mye lengre enn boksen; halvparten er stoppen bak i skinnene
// fjærtungen i vingen: festet ved roten foran, fri ende bak, med hull som knotten i festet klikker i
tungeX = W/2 + 7;                  // midt på tunga (x)
tungeB = 7; tungeL = 22; tungeT = 2.5;  // bredde, lengde og tykkelse (vingen er tynnet nedenfra)
tungeY1 = Dy - 12; tungeY0 = tungeY1 - tungeL;   // fri ende og rot
spalte = 1.0;                      // spalten rundt tunga
knottH = 1.2; knottD = 4.4;        // knotten i festet (kjegle 45°)
hullY = tungeY1 - 3.5; knottHull = 4.8;
spor = 1.4; sporB = 5.4;           // sporet i vingen som knotten går i fram til tunga
festeHull = 4.6; festeSenk = 9.2;  // treskrue 4 × 16 med senkehode
festeSkruer = [for (sx = [-1, 1], y = [Dy*0.28, Dy*0.72]) [sx*(W/2 - 22), y]];

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

// vingens tverrsnitt (x, z) for høyre side: flat topp mot festet, 45° fas under ytterkanten
module vinge2d() {
  polygon([[W/2 - 1, H - vingeT], [xo - svale, H - vingeT], [xo, H - vingeT + svale], [xo, H], [W/2 - 1, H]]);
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

// plassér noe ved et klips: lokal x = langs veggen, lokal y = utover, z = høyde
module ved_klips(k) {
  translate([k[0], k[1], 0]) rotate([0, 0, k[2][0] < 0 ? 90 : k[2][0] > 0 ? -90 : 0]) children();
}

// ---------- kasse ----------
module kasse() {
  difference() {
    union() {
      difference() {
        ytre();
        translate([0, 0, -1]) linear_extrude(zT + 1) translate([0, (yF + yB)/2]) square([Wi, Di], center = true);
      }
      // stopplister for bunnplata (langs sidene og bakveggen, rett over plata)
      difference() {
        union() {
          for (sx = [-1, 1]) translate([sx > 0 ? xR - stoppB : xL, yF + 4, zB]) cube([stoppB, Di - 8, 2]);
          translate([xL + 4, yB - stoppB, zB]) cube([kx0 - xL - 8, stoppB, 2]);
        }
        for (k = klips) ved_klips(k) translate([-(klipsB + 2)/2, -4, zB - 1]) cube([klipsB + 2, 5, 4]);   // klipsarmene går forbi
      }
      // vinger med avstivere (avstiverne går klar av skinnene i festet og av fjærtunga)
      for (sx = [-1, 1]) mirror([sx < 0 ? 1 : 0, 0, 0]) {
        rotate([90, 0, 0]) translate([0, 0, -Dy]) linear_extrude(Dy) vinge2d();
        for (y = [5, Dy - 5]) translate([W/2, y, H - vingeT])
          rotate([90, 0, 0]) linear_extrude(2.4, center = true)
            polygon([[-0.5, 0.01], [vinge - svale - 3, 0.01], [-0.5, -(H - vingeT - 8)]]);
      }
      // holdere som presser kortet ned mot bunnplata (fra toppen)
      for (p = holdere()) translate([p[0], p[1], kz1]) cylinder(d = 3, h = zT - kz1 + 0.01, $fn = 24);
    }
    // bryterhull
    for (x = bx) translate([x, -1, bz]) bryterhull();
    // USB-hull i bakveggen (avrundet), med fas utover
    translate([kcx, yB - 1, usbZ]) rotate([-90, 0, 0]) linear_extrude(tr + 2) rrect(usbB, usbH, 2);
    translate([kcx, Dy - 0.8, usbZ]) rotate([-90, 0, 0]) linear_extrude(1, scale = 1.15) rrect(usbB, usbH, 2);
    // vinduene for klipsene
    for (k = klips) ved_klips(k) translate([-(klipsB + 1)/2, -1, hakeZ]) cube([klipsB + 1, t + 2, vinduH]);
    // fjærtunga og sporet i vingene
    for (sx = [-1, 1]) mirror([sx < 0 ? 1 : 0, 0, 0]) {
      // spalten rundt tunga (gjennom), roten foran står igjen
      difference() {
        translate([tungeX - tungeB/2 - spalte, tungeY0, H - vingeT - 1]) cube([tungeB + 2*spalte, tungeL + spalte, vingeT + 2]);
        translate([tungeX - tungeB/2, tungeY0 - 1, H - vingeT - 2]) cube([tungeB, tungeL + 1, vingeT + 4]);
      }
      // tunga tynnes nedenfra, hullet for knotten, og fas på den frie enden så knotten glir opp på den
      translate([tungeX - tungeB/2 - 0.01, tungeY0 + 3, H - vingeT - 1]) cube([tungeB + 0.02, tungeL, vingeT - tungeT + 1]);
      translate([tungeX, hullY, H - vingeT - 1]) cylinder(d = knottHull, h = vingeT + 2, $fn = 32);
      translate([tungeX - tungeB/2 - 0.01, tungeY1, H]) rotate([-45, 0, 0]) translate([0, -2, -2]) cube([tungeB + 0.02, 2, 2]);
      // sporet bak tunga (knotten går i det til den når tunga)
      translate([tungeX - sporB/2, tungeY1 - 0.01, H - spor]) cube([sporB, Dy, spor + 1]);
    }
    // gullisten og SKJOLD
    gull(0.01);
  }
}
function holdere() = [for (sx = [-1, 1], y = [ky0 + 2.5, ky1 - 2.5]) [kcx + sx*(vB/2 - 2), y]];

// ---------- bunn ----------
module klips_arm() {   // lokalt: armen langs x, utover = +y; ytterflaten ligger i y = −klar (innsiden av veggen − klaring)
  translate([-klipsB/2, -klar - armT, zB - 0.01]) cube([klipsB, armT, hakeZ + hakeFlat + hakeUt + klar - zB]);
  translate([-klipsB/2, -klar, 0]) rotate([90, 0, 90]) linear_extrude(klipsB)
    polygon([[-armT, hakeZ], [hakeUt, hakeZ], [hakeUt, hakeZ + hakeFlat], [-armT, hakeZ + hakeFlat + hakeUt + armT]]);
}

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
      // klipsene
      for (k = klips) ved_klips(k) klips_arm();
    }
    // to spor for buntebånd til ledningene langs bryterne
    for (x = [bx[1], bx[N-2]]) translate([x, yB - 14, -0.01]) for (dx = [-3, 3]) translate([dx - 1, 0, 0]) cube([2, 4, tLid + 1]);
    // grep for fingeren midt på plata (for å dra den ned når klipsene er trykket inn)
    translate([(bx[1] + bx[2])/2, (yF + yB)/2, -0.01]) linear_extrude(1.2) rrect(18, 8, 3);
  }
}

// ---------- feste (skrus under bordplata) ----------
module feste() {
  difference() {
    union() {
      translate([0, Dy/2, H]) linear_extrude(festeT) rrect(FW, Dy + stopp, 3);
      // skinnene: yttervegg og 45°-kile under vingen, stopp bak
      for (sx = [-1, 1]) mirror([sx < 0 ? 1 : 0, 0, 0]) difference() {
        translate([xo - svale - skinneU, -0.0, H - vingeT - skinneU - c]) cube([svale + skinneU + c + skinneV, Dy + stopp/2, vingeT + skinneU + c + 0.01]);
        translate([0, -1, 0]) rotate([90, 0, 0]) translate([0, 0, -Dy - c - 1]) linear_extrude(Dy + c + 1) offset(delta = c) vinge2d();
      }
      // knotten som klikker i hullet i tunga
      for (sx = [-1, 1]) translate([sx*tungeX, hullY, H + 0.01]) mirror([0, 0, 1]) cylinder(d1 = knottD, d2 = knottD - 2*knottH, h = knottH + 0.01, $fn = 32);
    }
    // treskruer: senkehodet ligger i flukt med undersiden (boksen glir under dem)
    for (s = festeSkruer) translate([s[0], s[1], H - 0.01]) {
      cylinder(d = festeHull, h = festeT + 1, $fn = 32);
      cylinder(d1 = festeSenk, d2 = festeHull, h = (festeSenk - festeHull)/2, $fn = 32);
    }
  }
}

// ---------- kjøpte deler (bildene og sjekken) ----------
module bryter() {   // KN3C-101: gjenge M12 × 9,5, kropp 13 × 29 × 22 med skrueklemmer bak
  color("silver") rotate([-90, 0, 0]) translate([0, 0, -6.5]) cylinder(d = 11.9, h = 9.5);       // gjengen (y −6,5 … 3)
  color("silver") translate([0, -6.5, 0]) rotate([90, 0, 0]) rotate([-18, 0, 0]) cylinder(d1 = 4.5, d2 = 5.5, h = 16);   // spaken
  color("#6b3a2a") translate([-6.5, tf + 2.5, -14.5]) cube([13, 22, 29]);                       // kroppen
  color("silver") translate([-6.5, tf + 24.5, -10]) cube([13, 4, 20]);                          // klemmene
  color("silver") translate([0, tf, 0]) rotate([-90, 0, 0]) cylinder(d = 19.6, h = 2.4, $fn = 6); // mutteren innenfor
}
module kortet() {
  color("#1d5c3a") translate([kcx - vB/2, ky0, kz0]) cube([vB, vL, vT]);
  color("silver") translate([kcx - 4, ky1 - 5, E32 ? kz0 - 2.8 : kz1]) cube([8, 5 + kontUt, 2.8]);   // USB-kontakten (stikker inn i hullet)
  color("#222") translate([kcx - 9, ky0 + 2, kz1]) cube([18, E32 ? 25.5 : 24, 3.2]);                  // ESP-modulen
}

// ---------- utskrift og visning ----------
lys = farge == "lys";
kfarge = lys ? "#efeee9" : "#2b2b2d";
gfarge = "#d9a441";
ffarge = lys ? "#d6d3cc" : "#1f1f21";
module kasse_print() { translate([0, 0, H]) rotate([180, 0, 0]) kasse(); }
module gull_print() { translate([0, 0, H]) rotate([180, 0, 0]) gull(); }
module feste_print() { translate([0, 0, H + festeT]) rotate([180, 0, 0]) feste(); }
module bord(e) { color(lys ? "#b89a74" : "#5a4632") translate([0, Dy/2 - 60, H + festeT + e]) linear_extrude(18) square([340, 200], center = true); }

if (part == "kasse") kasse_print();
else if (part == "gull") gull_print();
else if (part == "bunn") bunn();
else if (part == "feste") feste_print();
else if (part == "a_kasse") kasse();
else if (part == "a_bunn") bunn();
else if (part == "a_gull") gull();
else if (part == "a_feste") feste();
else if (part == "a_bryter") for (x = bx) translate([x, 0, bz]) bryter();
else if (part == "a_kort") kortet();
else if (part == "a_plugg") translate([kcx, ky1 + kontUt + 0.05, usbZ]) rotate([-90, 0, 0]) linear_extrude(18) rrect(E32 ? 10.5 : 11, 6.5, 1.5);   // USB-pluggen
else if (part == "inni") {   // uten toppen: kortet, bryterne og ledningsplassen sett ovenfra
  color(kfarge) difference() { kasse(); translate([-W, -1, zT - 6]) cube([2*W, Dy + 2, 20]); }
  color(kfarge) bunn(); kortet();
  for (x = bx) translate([x, 0, bz]) bryter();
}
else if (part == "samlet" || part == "eksplodert" || part == "uttrukket") {
  e = part == "eksplodert" ? 30 : 0;
  ut = part == "uttrukket" ? -45 : 0;   // boksen dratt halvveis ut av festet
  color(ffarge) translate([0, 0, e]) feste();
  translate([0, ut, 0]) {
    color(kfarge) kasse();
    color(gfarge) gull();
    translate([0, 0, -e]) { color(kfarge) bunn(); kortet(); }
    for (x = bx) translate([x, -e/2, bz]) bryter();
  }
}
