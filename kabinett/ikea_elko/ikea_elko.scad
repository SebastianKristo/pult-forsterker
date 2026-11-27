// IKEA BILRESA + TIMMERFLOTTE veggplate – tilpasset norsk Elko-ramme (55 × 55-systemet).
// Bygger på «IKEA BILRESA & TIMMERFLOTTE Clipsal Wall Plate Mount» av thestockpot (CC BY-NC-SA 4.0, se original/).
// Endringer: plata er gjort større (124 × 90 mm) så den dekker en Elko-ramme, og bakplata er et nytt «lokk» som tres
// over rammen i stedet for å klipses på en australsk Clipsal-bryter. Holderen for BILRESA og låseringen for
// TIMMERFLOTTE er ikke endret (original/bilresa_mount.3mf og original/timmerflotte_retainingring.3mf).
//
// part: front | bak | samlet
// Mål rammen din og endre ramme_b / ramme_h / ramme_d om de ikke stemmer (standard: Elko Plus 1-hulls, 84 × 84 mm).
part = "samlet";
$fn = 64;

ramme_b = 84.0;     // rammens bredde (mm)
ramme_h = 84.0;     // rammens høyde
ramme_d = 9.5;      // hvor langt rammen står ut fra veggen
ramme_x = 0;        // rammens midte i forhold til platas midte (+ = mot høyre, sett forfra)
klaring = 0.3;      // rundt rammen (klemribbene tar den opp)

W = 124; H = 90; R = 6;      // ny plate (originalen er 116,3 × 75,3)
skjort = 14;                 // bakplatas dybde (originalen: 14 mm skjørt + 5,9 mm plate)
plate = 5.9;                 // bakplatas front (som originalen)
vegg = 2.2;
ZF = skjort + plate;         // fronten står på bakplata her (z = 19,9 / 20)
ZT = 39.5;                   // toppen av fronten

// fra originalen (målt): sensorhullet og skruene (M3 × 10 senkehode, fra baksiden og inn i fronten)
sensor = [-13.38, 0]; sensorD = 65.8;
SKRUER = [[7.75, 28.125], [7.75, -28.125]];

module rrect(w, h, r) { offset(r) square([w - 2*r, h - 2*r], center = true); }

// originalens omriss (116,3 × 75,3, R ≈ 4,5) – fronten tegnes ut til dette
module orig2d(o = 0) { offset(4.5 + o) square([116.28 - 9, 75.25 - 9], center = true); }

// ---------- fronten: originalen + en kant rundt ----------
// Toppflaten forlenges ut til 124 × 90 og dekker originalens avrundede kant (ingen skjøt). Den nye ytterveggen får de
// samme luftespaltene som originalen har i overkanten (over TIMMERFLOTTE), og rommet mellom veggene er åpent bakover.
spalteX = [for (k = [0:10]) -41.5 + 4*k];
module front() {
  union() {
    translate([0, 0, 0]) import("original/faceplate_front.stl", convexity = 6);
    difference() {
      union() {
        translate([0, 0, ZT - 2.0]) linear_extrude(1.0 + 0.01) difference() { rrect(W, H, R); orig2d(-2.0); }   // toppflaten (den øverste mm-en er avrundingen under)
        translate([0, 0, ZF + 0.1]) linear_extrude(ZT - ZF - 0.1 - 1.0) difference() { rrect(W, H, R); rrect(W - 2*vegg, H - 2*vegg, R - vegg); }
        // avrundet ytterkant øverst (R 1,0), bare i kanten
        difference() {
          hull() {
            translate([0, 0, ZT - 1.0 - 0.01]) linear_extrude(0.01) rrect(W, H, R);
            translate([0, 0, ZT - 0.01]) linear_extrude(0.01) rrect(W - 2, H - 2, R - 1);
          }
          translate([0, 0, ZT - 2]) linear_extrude(3) orig2d(-2.0);
        }
      }
      // luftespalter i overkanten (samme som originalen), gjennom den nye ytterveggen
      for (x = spalteX) translate([x - 1.0, H/2 - vegg - 1, 24.5]) cube([2.0, vegg + 2, 10]);
    }
  }
}

// ---------- bakplata: lokk over rammen ----------
// Et skjørt rundt hele plata, med en lomme som passer rundt rammen. Klemribber på alle fire sider holder plata på
// rammen; i tillegg kan den festes med dobbeltsidig tape (3M VHB) på flatene som ligger mot rammens forside.
module bak() {
  difference() {
    union() {
      // fronten av bakplata og skjørtet
      translate([0, 0, skjort]) linear_extrude(plate) rrect(W, H, R);
      linear_extrude(skjort + 0.01) difference() { rrect(W, H, R); rrect(W - 2*vegg, H - 2*vegg, R - vegg); }
      // vegger rundt rammen (lomma), fra rammens forside og ut til skjørtet
      translate([ramme_x, 0, 0]) linear_extrude(skjort + 0.01) difference() {
        square([ramme_b + 2*klaring + 2*vegg, ramme_h + 2*klaring + 2*vegg], center = true);
        square([ramme_b + 2*klaring, ramme_h + 2*klaring], center = true);
      }
      // støtter som ligger an mot rammens forside (tape her), utenom sensorhullet
      for (p = [[-ramme_b/2 + 5, ramme_h/2 - 5], [-ramme_b/2 + 5, -ramme_h/2 + 5], [ramme_b/2 - 5, ramme_h/2 - 5], [ramme_b/2 - 5, -ramme_h/2 + 5]])
        translate([ramme_x + p[0], p[1], ramme_d]) difference() {
          cylinder(d = 8, h = skjort - ramme_d + 0.01);
          translate([sensor[0] - ramme_x - p[0], sensor[1] - p[1], -1]) cylinder(d = sensorD + 2, h = 50);
        }
    }
    // klemribbene lages ved å trekke lomma litt inn: små halvsylindre står 0,25 mm inn i lomma
    // (se ribber() under – de legges til etterpå)
    // sensorhullet og skruehullene fra originalen
    translate([sensor[0], sensor[1], -1]) cylinder(d = sensorD, h = 50, $fn = 128);
    for (s = SKRUER) translate([s[0], s[1], -1]) {
      cylinder(d = 3.2, h = 50, $fn = 24);
      translate([0, 0, 1 + skjort - 0.01]) cylinder(d1 = 6.2, d2 = 3.2, h = 1.5, $fn = 32);   // senkehodet fra baksiden
      cylinder(d = 7.5, h = 1 + skjort, $fn = 32);                                                // plass til skrutrekkeren
    }
  }
  ribber();
}
module ribber() {   // 2 per side, 0,25 mm inn i lomma (presses inn når plata tres på rammen)
  inn = klaring + 0.25;
  for (s = [-1, 1]) for (t = [-1, 1]) {
    translate([ramme_x + s*(ramme_b/2 + klaring), t*ramme_h/4, 0]) cylinder(r = inn, h = skjort * 0.7, $fn = 16);
    translate([ramme_x + t*ramme_b/4, s*(ramme_h/2 + klaring), 0]) cylinder(r = inn, h = skjort * 0.7, $fn = 16);
  }
}

if (part == "front") translate([0, 0, ZT]) rotate([180, 0, 0]) front();   // toppen ned
else if (part == "bak") translate([0, 0, ZF]) rotate([180, 0, 0]) bak();   // fronten av bakplata ned (skjørtet opp)
else if (part == "samlet") { color([0.9, 0.9, 0.88]) front(); color([0.75, 0.75, 0.72]) bak(); color([0.5, 0.5, 0.55], 0.4) translate([ramme_x, 0, ramme_d/2]) cube([ramme_b, ramme_h, ramme_d], center = true); }
