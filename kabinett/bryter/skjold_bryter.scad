// Skjold Bryter – boks under pulten med fem vippebrytere (KN3C-101 / E-TEN1021 o.l., M12-gjenge) og ESP32 D1 mini
// (eller Wemos D1 mini). Et eget feste skrus opp under bordplata; boksen skyves inn i festet forfra og klikker på plass.
// Spakene peker mot deg, og USB-kabelen går ut bak. Ingen skruer i selve boksen.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater (montert): x mot høyre (midt = 0), y innover under pulten (fronten = 0), z opp (undersiden = 0,
// toppen av boksen = H, bordplata = H + festeT).
//
// Deler:
//   kasse  – topp med to svalehalespor, front med bryterhull og sider. Åpen nedover og bakover.
//            To fjærtunger i toppen. Printes med fronten ned (glatt front med innfelt gull), ingen støtte.
//   bunn   – bunnplata og bakveggen (med USB-hullet) i ett, med holderen for ESP-kortet. Klikkes i med fire klips
//            (vinduer i sideveggene); trykk klipsene inn for å ta den ut igjen.
//   feste  – skrus under bordplata med fire treskruer. Det er mindre enn toppen av boksen og synes ikke: to
//            svalehaletunger under festet går inn i sporene i toppen. To knotter klikker i hull i fjærtungene i toppen
//            av boksen når den er skjøvet helt inn.
//            Printes med bordsiden ned, ingen støtte.
//   gull   – gullisten og SKJOLD i fronten (filament 2, samme utskrift som kassa).
//
// Bryterne: Ø12,2-hull rett gjennom fronten (fronten ligger på plata når kassa printes). Spaken vipper
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
R = 2;                // fasen på de stående hjørnene (fas, ikke runding: fronten ligger på plata)
fas = 1.2;            // fas på ytterkantene

// ESP-kortet: ligger flatt på bunnplata til høyre for bryterne, med USB-enden mot bakveggen
kortB = 0; kortL = 0;          // ditt kort, hvis det avviker (mm, 0 = standard): -D kortB=31.8 -D kortL=39.5
vB = kortB > 0 ? kortB : E32 ? 31.4 : 25.6;        // kortets bredde (x)
vL = kortL > 0 ? kortL : E32 ? 39.0 : 34.2;        // kortets lengde (y)
// Kortet holdes av klemribber: tre smale ribber på hver sidelist trykker 0,25 mm mot kortkantene (ikke oppå kortet,
// så de går klar av pinnene, loddingen og modulen). Kortet trykkes ned mellom dem og sitter fast også uten toppen.
ribbeInn = 0.25;               // så mye ribbene går inn i kortkanten
sideKlar = 0.5;                // luft mellom kortkanten og sidelistene (ribbene tar det opp)
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
// Bakveggen sitter på bunnplata; en skrå list under toppen holder overkanten av den.
// En arm reiser seg fra bunnplata langs innsiden av veggen; mothaken øverst klikker ut i et vindu i veggen.
// Den flate undersiden av mothaken hviler på vinduets nedre kant, så plata ikke faller ut. Lister langs veggene
// stopper plata oppover. Trykk mothakene inn gjennom vinduene for å ta plata ut.
klipsB = 10; armT = 1.4;          // armens bredde og tykkelse
hakeUt = 1.2;                      // mothaken stikker så langt ut i vinduet
hakeZ = 13;                        // mothakens underside (= vinduets nedre kant)
hakeFlat = 0.6;                    // rett del før skråkanten (45°)
vinduH = hakeFlat + hakeUt + klar + 0.5;
// [x, y, retning]: retning = utover (−x, +x eller +y)
klips = [[xL, yF + 14, [-1, 0]], [xL, yB - 14, [-1, 0]], [xR, yF + 14, [1, 0]], [xR, yB - 14, [1, 0]]];
stoppB = 1.2;                      // listene som stopper plata (innsiden av veggene, rett over plata)

// ---------- festet: svalehalespor i toppen, tunger og fjærtunger ----------
c = 0.3;                           // klaring i sporene
festeT = 4;                        // festets plate (mot bordplata); ligger skjult over boksen
festeInn = 3;                      // festet slutter så langt innenfor kantene av toppen
// svalehalen (x, z ned fra toppen): hals 5 mm bred og 1,5 mm høy, så 45° ut til 10 mm, så 1 mm rett
halsB = 5; halsH = 1.5; hodeB = 10; hodeH = 1;
sporDyp = halsH + (hodeB - halsB)/2 + hodeH;   // 5 mm
ribbeH = sporDyp + c + 1.2 - tTop;             // ribba under toppen der sporet går (1,2 mm bunn under sporet)
// sporene: venstre ved sideveggen (foran bryter 1), høyre over kortet
spor = [xL + 6.5, kcx];
ribbe = [[xL - 0.01, xL + 13.5], [kcx - 7.5, kcx + 7.5]];   // ribbenes x-område
sporY0 = 8;                        // sporene er lukket foran (stoppen) og åpne bak
// fjærtungene i toppen: festet ved roten foran, fri ende bak, med hull som knotten i festet klikker i
tunger = [(bx[0] + bx[1])/2, (bx[N-2] + bx[N-1])/2];   // x: mellom bryter 1 og 2, og mellom de to siste
tungeB = 7; tungeL = 22;           // bredde og lengde (hele toppens tykkelse)
tungeY1 = Dy - 12; tungeY0 = tungeY1 - tungeL;   // fri ende og rot
spalte = 1.0;                      // spalten rundt tunga
knottH = 1.2; knottD = 4.4;        // knotten i festet (kjegle 45°)
hullY = tungeY1 - 3.5; knottHull = 4.8;
knSpor = 1.4; knSporB = 5.4;       // sporet i toppen som knotten går i fram til tunga
festeHull = 4.6; festeSenk = 9.2;  // treskrue 4 × 16 med senkehode
festeSkruer = [for (x = [bx[1] + P/2, bx[2] + P/2], y = [Dy*0.27, Dy*0.73]) [x, y]];

// gull og tekst
gullB = 1.2; gullT = 0.6; gullZ = 6.0;
tekst = "SKJOLD"; tekstS = 4.2; tekstX = kcx; tekstZ = bz; merkeH = 8;   // merket til venstre for SKJOLD

// ---------- hjelpere ----------
module rrect(w, d, r) { offset(r) offset(-r) square([w, d], center = true); }
module crect(w, d, f) { offset(delta = f, chamfer = true) square([w - 2*f, d - 2*f], center = true); }

// kassens ytre form: avrundet sett ovenfra, med fas nede og oppe
module ytre() {
  hull() {
    translate([0, Dy/2, fas]) linear_extrude(H - 2*fas) crect(W, Dy, R);
    translate([0, Dy/2, 0]) linear_extrude(H) crect(W - 2*fas, Dy - 2*fas, max(R - fas*0.6, 0.1));
  }
}

// svalehaletunga under festet (x, z), sentrert i x = 0, fra toppen av boksen (z = H) og ned
module tunge2d(o = 0) {
  offset(delta = o) polygon([[-halsB/2, H + 0.01], [-halsB/2, H - halsH], [-hodeB/2, H - halsH - (hodeB - halsB)/2],
    [-hodeB/2, H - sporDyp], [hodeB/2, H - sporDyp], [hodeB/2, H - halsH - (hodeB - halsB)/2], [halsB/2, H - halsH], [halsB/2, H + 0.01]]);
}
module langs_y(y0, y1) { translate([0, y1, 0]) rotate([90, 0, 0]) linear_extrude(y1 - y0) children(); }

// bryterhull: rett gjennom fronten (står loddrett i printen)
module bryterhull() { rotate([-90, 0, 0]) cylinder(d = hullD, h = tf + 2); }

module gull2d() {
  translate([(bx[0] + bx[N-1])/2, gullZ]) square([bx[N-1] - bx[0] + 18, gullB], center = true);
  translate([tekstX + merkeH/2 + 1.2, tekstZ]) text(tekst, size = tekstS, font = "Inter:style=Bold", halign = "center", valign = "center", spacing = 1.25);
  translate([tekstX - 14.6, tekstZ]) merke2d(merkeH/42);
  translate([tekstX - 0.6, tekstZ - 7.5]) square([34, gullB], center = true);
}
// Skjold-merket: fem avrundede staver (branding/skjold/skjold_merke.svg), sentrert
module merke2d(sc) {
  scale(sc) for (b = [[1, 22], [9, 33], [18.7, 42], [28.4, 33], [36.4, 22]])
    translate([b[0] - 21, 21 - b[1]]) hull() for (y = [2.3, b[1] - 2.3]) translate([2.3, y]) circle(2.3, $fn = 24);
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
        translate([-Wi/2, yF, -1]) cube([Wi, Dy, zT + 1]);   // åpen nedover og bakover (bakveggen er en del av bunnen)
      }
      // stopplister for bunnplata (langs sidene, rett over plata)
      difference() {
        for (sx = [-1, 1]) translate([sx > 0 ? xR - stoppB : xL, yF + 4, zB]) cube([stoppB, Di - 8, 2]);
        for (k = klips) ved_klips(k) translate([-(klipsB + 2)/2, -4, zB - 1]) cube([klipsB + 2, 5, 4]);   // klipsarmene går forbi
      }
      // ribber under toppen der svalehalesporene går (slutter foran bakveggen)
      for (r = ribbe) translate([r[0], yF - 0.01, zT - ribbeH]) cube([r[1] - r[0], yB - c - 0.3 - yF, ribbeH + 0.02]);
      // to finner fra toppen som presser USB-enden av kortet ned (45° foran, så de printes uten støtte)
      for (sx = [-1, 1]) translate([kcx + sx*(vB/2 - 2) - 0.8, 0, 0]) rotate([90, 0, 90]) linear_extrude(1.6)
        polygon([[ky1 - 3, kz1], [yB - 0.4, kz1], [yB - 0.4, zT + 0.01], [ky1 - 3 - (zT - kz1), zT + 0.01]]);
      // skrå list under toppen som holder overkanten av bakveggen
      translate([-Wi/2, 0, 0]) rotate([90, 0, 90]) linear_extrude(Wi)
        polygon([[yB - c, zT + 0.01], [yB - c, zT - 3], [yB - c - 3, zT + 0.01]]);
    }
    // bryterhull
    for (x = bx) translate([x, -1, bz]) bryterhull();
    // vinduene for klipsene
    for (k = klips) ved_klips(k) translate([-(klipsB + 1)/2, -1, hakeZ]) cube([klipsB + 1, t + 2, vinduH]);
    // svalehalesporene i toppen: lukket foran, åpne bak
    for (x = spor) translate([x, 0, 0]) langs_y(sporY0, Dy + 1) tunge2d(c);
    // fjærtungene i toppen
    for (x = tunger) {
      // spalten rundt tunga (gjennom toppen), roten foran står igjen
      difference() {
        translate([x - tungeB/2 - spalte, tungeY0, zT - 1]) cube([tungeB + 2*spalte, tungeL + spalte, tTop + 2]);
        translate([x - tungeB/2, tungeY0 - 1, zT - 2]) cube([tungeB, tungeL + 1, tTop + 4]);
      }
      // hullet for knotten, og fas på den frie enden så knotten glir opp på den
      translate([x, hullY, zT - 1]) cylinder(d = knottHull, h = tTop + 2, $fn = 32);
      translate([x - tungeB/2 - 0.01, tungeY1, H]) rotate([-45, 0, 0]) translate([0, -2, -2]) cube([tungeB + 0.02, 2, 2]);
      // sporet bak tunga (knotten går i det til den når tunga)
      translate([x - knSporB/2, tungeY1 - 0.01, H - knSpor]) cube([knSporB, Dy, knSpor + 1]);
    }
    // gullisten og SKJOLD
    gull(0.01);
  }
}

// ---------- bunn ----------
module klips_arm() {   // lokalt: armen langs x, utover = +y; ytterflaten ligger i y = −klar (innsiden av veggen − klaring)
  translate([-klipsB/2, -klar - armT, zB - 0.01]) cube([klipsB, armT, hakeZ + hakeFlat + hakeUt + klar - zB]);
  translate([-klipsB/2, -klar, 0]) rotate([90, 0, 90]) linear_extrude(klipsB)
    polygon([[-armT, hakeZ], [hakeUt, hakeZ], [hakeUt, hakeZ + hakeFlat], [-armT, hakeZ + hakeFlat + hakeUt + armT]]);
}

module bunn() {
  bw = Wi - 2*klar;
  difference() {
    union() {
      translate([-bw/2, yF + klar, 0]) cube([bw, Dy - yF - klar, tLid]);
      // bakveggen
      translate([-bw/2, yB, 0]) cube([bw, tr, zT - c]);
      // kortholderen: tverrlist under fremre kortkant, puter i hjørnene ved USB-enden, sidelister med klemribber og
      // en lav stopp foran. Ingenting ligger over kortet, så pinner, lodding og modul går fri.
      translate([kcx - vB/2, ky0, zB - 0.01]) cube([vB, 2.5, bZ + 0.01]);
      for (sx = [-1, 1]) translate([kcx + sx*(vB/2 - 2.5) - 2.5, ky1 - 2.5, zB - 0.01]) cube([5, 2.5, bZ + 0.01]);
      for (sx = [-1, 1]) translate([kcx + sx*(vB/2 + sideKlar + 0.8), (ky0 + ky1)/2, zB - 0.01])
        linear_extrude(bZ + vT + 1.2) square([1.6, vL - 6], center = true);
      for (sx = [-1, 1], f = [0.18, 0.5, 0.82]) translate([kcx + sx*(vB/2 - ribbeInn + 0.6), ky0 + f*vL, zB - 0.01])
        cylinder(d = 1.2, h = bZ + vT + 0.01, $fn = 16);   // klemribbene (toppen flukter med kortets overside)
      translate([kcx - vB/2 + 2, ky0 - 0.3 - 1.6, zB - 0.01]) cube([vB - 4, 1.6, bZ + vT * 0.6]);
      // klipsene
      for (k = klips) ved_klips(k) klips_arm();
    }
    // hakk i overkanten av bakveggen der svalehaletungene går inn
    for (x = spor) translate([x - hodeB/2 - 1, yB - 1, H - sporDyp - c - 0.8]) cube([hodeB + 2, tr + 2, 20]);
    // USB-hull i bakveggen (avrundet), med fas utover
    translate([kcx, yB - 1, usbZ]) rotate([-90, 0, 0]) linear_extrude(tr + 2) rrect(usbB, usbH, 2);
    translate([kcx, Dy - 0.8, usbZ]) rotate([-90, 0, 0]) linear_extrude(1, scale = 1.15) rrect(usbB, usbH, 2);
    // to spor for buntebånd til ledningene langs bryterne
    for (x = [bx[1], bx[N-2]]) translate([x, yB - 14, -0.01]) for (dx = [-3, 3]) translate([dx - 1, 0, 0]) cube([2, 4, tLid + 1]);
    // grep for fingeren midt på plata (for å dra den ned når klipsene er trykket inn)
    translate([(bx[1] + bx[2])/2, (yF + yB)/2, -0.01]) linear_extrude(1.2) rrect(18, 8, 3);
  }
}

// ---------- feste (skrus under bordplata) ----------
module feste() {
  y1 = Dy - festeInn;
  difference() {
    union() {
      translate([0, (festeInn + y1)/2, H]) linear_extrude(festeT) crect(W - 2*festeInn, y1 - festeInn, 2);
      // svalehaletungene som går inn i sporene i toppen av boksen
      for (x = spor) translate([x, 0, 0]) langs_y(sporY0 + c, y1) tunge2d();
      // knottene som klikker i hullene i fjærtungene
      for (x = tunger) translate([x, hullY, H + 0.01]) mirror([0, 0, 1]) cylinder(d1 = knottD, d2 = knottD - 2*knottH, h = knottH + 0.01, $fn = 32);
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
module kasse_print() { rotate([90, 0, 0]) kasse(); }   // fronten ned
module gull_print() { rotate([90, 0, 0]) gull(); }
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
