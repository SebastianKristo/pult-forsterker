// Skjold Dokk Flat – et lavt brett der fjernkontrollen ligger flatt med skjermen opp (for eksempel foran TV-en, der
// den stående dokka er for høy). Passer alle utgavene av fjernkontrollen (samme omriss, 55 × 202,5 mm, R11).
//   - forsenkning som følger fjernkontrollens omriss, med 45° fas øverst så den glir på plass
//   - grep på begge sider midt på, så den er lett å løfte opp
//   - spor i halen for USB-C-pluggen (rett eller vinklet), så den kan lade mens den ligger der
//   - gullstripe felt inn i toppen, gummiføtter under
//   - magnetisk lading (pogo = true): handelen av pogo-kontakten i gulvet rett under hunndelen i fjernkontrollens bunn
//     (bunn_dokk), USB-C-brikke i halen, ledningskanal under gulvet og en bunnplate som skrus fast (4 × M3 × 8)
// Printes med bunnen ned, ingen støtte. Fjernkontrollens koordinater: x tvers (0…FW), y fra halen (0…FL).
part = "brett";                  // brett | gull | bunnplate | pogo_han | samlet
pogo = true;                     // magnetisk lading (pogo-kontakt + USB-C-brikke + bunnplate)
med_fk = false;                  // vis fjernkontrollen (bare bilder)

FW = 55; FL = 202.5; FR = 11;     // fjernkontrollens omriss (R11-hjørner)
kl = 0.6;                         // klaring rundt i forsenkningen
kant = 7;                         // brettets kant rundt fjernkontrollen
gulv = pogo ? 9 : 3;              // gulvet under fjernkontrollen (pogo-kontakten trenger plass under)
dybde = 7;                        // forsenkningens dybde (fjernkontrollen stikker 6,5–9 mm over brettet)
H = gulv + dybde;                 // brettets høyde
fas = 1.6;                        // fas øverst i forsenkningen og på yttertoppen
R_ut = FR + kant;
grep_r = 16;                      // grepene: sylinder på tvers som senker kanten midt på
usb_x = 27.5; usb_z = 4.7;        // USB-C i halen (midt på; 4,7 mm over undersiden på Hullkort)
usb_b = 14; usb_h = 8.6;          // sporet: plass til pluggens støpte del
gull_inn = 3.2; gull_b = 1.2; gull_d = 0.6;
fot_d = 10; fot_h = 1.0;
// pogo-kontakten (samme som i skjold_dokk.scad og skjold_fjernkontroll.scad – mål din)
POGO_L = 21; POGO_KROPP = 15; POGO_B = 6; POGO_HM = 4.5; POGO_PINNE = 0.9; POGO_ORE_T = 1.2;
POGO_HULL_A = 18; POGO_DELING = 2.8;
POGO_X = 40; POGO_Y = 43.5;       // hunndelens senter i fjernkontrollen (x tvers, y fra halen)
// USB-C-brikke (6 pinner, 5,1 kΩ på CC) i halen til venstre, kontakten ut gjennom endeveggen
usb_kort = [12.2, 14.5, 1.6]; usb_k = [9.0, 7.4, 3.3]; usbd_x = 10;
delt_z = 2;                       // bunnplatas tykkelse (brettet deles her)
skruer = [[-3.5, 25], [FW + 3.5, 25], [-3.5, FL - 25], [FW + 3.5, FL - 25]];
$fn = 64;

module fk2d(o = 0) { translate([-o, -o]) offset(r = FR + o) offset(delta = -FR) square([FW + 2*o, FL + 2*o]); }
module brett_ytre() {
  hull() {
    translate([0, 0, 0.4]) linear_extrude(H - fas - 0.4) fk2d(kant);
    linear_extrude(0.4) fk2d(kant - 0.4);
    translate([0, 0, H - 0.01]) linear_extrude(0.01) fk2d(kant - fas);
  }
}
module brett() {
  difference() {
    brett_ytre();
    // forsenkningen med fas øverst
    translate([0, 0, gulv]) linear_extrude(dybde + 1) fk2d(kl);
    hull() {
      translate([0, 0, H - fas]) linear_extrude(0.01) fk2d(kl);
      translate([0, 0, H + 0.01]) linear_extrude(0.01) fk2d(kl + fas + 0.01);
    }
    // grep på begge sider midt på (kanten senkes ned mot gulvet)
    translate([-kant - 1, FL/2, gulv + grep_r + 0.8]) rotate([0, 90, 0]) cylinder(r = grep_r, h = FW + 2*kant + 2, $fn = 128);
    // spor for USB-C-pluggen i halen, åpent opp
    translate([usb_x - usb_b/2, -kant - 1, gulv + usb_z - usb_h/2]) cube([usb_b, kant + 2, H]);
    // gullstripa rundt toppen
    translate([0, 0, H - gull_d]) linear_extrude(1) difference() { fk2d(kant - gull_inn); fk2d(kant - gull_inn - gull_b); }
    // gummiføtter
    for (x = [-kant + 8, FW + kant - 8], y = [-kant + 14, FL + kant - 14]) translate([x, y, -0.01]) cylinder(d = fot_d + 0.4, h = fot_h);
    if (pogo) pogo_kutt();
  }
}
module pogo_2d(o = 0) { hull() for (s = [-1, 1]) translate([0, s * (POGO_L/2 - POGO_B/2)]) circle(d = POGO_B + 2*o, $fn = 32); }
module pogo_kutt() {
  // lomma: kroppen opp til flaten (i flukt med gulvet), ørene nederst (lim, eller M1,6 × 4 i forboringene), og et
  // rom under for loddingene, åpent ned mot bunnplata
  translate([POGO_X, POGO_Y, 0]) {
    translate([0, 0, gulv - POGO_HM - 0.01]) linear_extrude(POGO_HM + 1) offset(0.12) square([POGO_B, POGO_KROPP], center = true);
    translate([0, 0, gulv - POGO_HM - 0.01]) linear_extrude(POGO_ORE_T + 0.02) pogo_2d(0.2);
    for (s = [-1, 1]) translate([0, s * POGO_HULL_A/2, delt_z + 0.4]) cylinder(d = 1.3, h = gulv - POGO_HM - delt_z, $fn = 12);
    translate([0, 0, delt_z - 0.01]) linear_extrude(gulv - POGO_HM - delt_z + 0.02) offset(1) square([POGO_B, POGO_KROPP], center = true);
  }
  // ledningskanal under gulvet fra pogo-kontakten til USB-C-brikken
  hull() {
    translate([POGO_X - 2, POGO_Y - 2, delt_z - 0.01]) cube([4, 4, 3]);
    translate([usbd_x - 2, 4, delt_z - 0.01]) cube([4, 4, 3]);
  }
  // USB-C-brikken: lomme med kortet flatt, kontakten mot endeveggen (1 mm vegg) og ut
  translate([usbd_x - usb_kort[0]/2 - 0.2, -kant + 1, delt_z - 0.01]) cube([usb_kort[0] + 0.4, usb_kort[1] + 0.2, usb_kort[2] + usb_k[2] + 0.4]);
  translate([usbd_x, -kant - 1, delt_z + usb_kort[2] + usb_k[2]/2]) rotate([-90, 0, 0])
    linear_extrude(3) offset(1.2) square([usb_k[0] + 0.4 - 2.4, usb_k[2] + 0.4 - 2.4], center = true);
  translate([usbd_x, -kant - 0.01, delt_z + usb_kort[2] + usb_k[2]/2]) rotate([-90, 0, 0])
    linear_extrude(0.61) offset(2.5) square([13.6 - 5, 7.4 - 5], center = true);   // forsenkning for pluggen
}
module brett_topp() {   // brettet over delt_z (med pogo), med forboring for skruene til bunnplata
  difference() {
    brett();
    translate([-100, -100, -1]) cube([400, 400, delt_z + 1]);
    for (p = skruer) translate([p[0], p[1], delt_z - 0.01]) cylinder(d = 2.6, h = 8, $fn = 20);
  }
}
module bunnplate() {
  difference() {
    hull() { translate([0, 0, 0.4]) linear_extrude(delt_z - 0.4) fk2d(kant); linear_extrude(0.4) fk2d(kant - 0.4); }
    for (p = skruer) translate([p[0], p[1], -0.01]) {
      cylinder(d = 3.4, h = delt_z + 1, $fn = 20);
      cylinder(d1 = 6.4, d2 = 3.4, h = 1.5, $fn = 32);
    }
    for (x = [-kant + 8, FW + kant - 8], y = [-kant + 14, FL + kant - 14]) translate([x, y, -0.01]) cylinder(d = fot_d + 0.4, h = fot_h);
  }
}
module pogo_han() {     // handelen (bare for bilder og kontroll): flaten i gulvet, pinnene POGO_PINNE opp
  translate([POGO_X, POGO_Y, gulv]) {
    color([0.12, 0.12, 0.13]) { translate([0, 0, -POGO_HM/2]) cube([POGO_B, POGO_KROPP, POGO_HM], center = true);
      translate([0, 0, -POGO_HM]) linear_extrude(POGO_ORE_T) pogo_2d(); }
    color([0.85, 0.7, 0.35]) for (s = [-1, 1]) translate([0, s * POGO_DELING/2, -0.5]) cylinder(d = 1.2, h = 0.5 + POGO_PINNE, $fn = 16);
  }
}
module gull() {
  intersection() {
    translate([0, 0, H - gull_d]) linear_extrude(gull_d) difference() { fk2d(kant - gull_inn - 0.08); fk2d(kant - gull_inn - gull_b + 0.08); }
    brett_ytre();
  }
}

module gull_kuttet() {   // gullstripa der toppen er hel (ikke i grepene eller USB-sporet)
  difference() {
    gull();
    translate([-kant - 1, FL/2, gulv + grep_r + 0.8]) rotate([0, 90, 0]) cylinder(r = grep_r + 0.01, h = FW + 2*kant + 2, $fn = 128);
    translate([usb_x - usb_b/2 - 0.01, -kant - 1, gulv]) cube([usb_b + 0.02, kant + 2, H]);
  }
}
if (part == "brett") { if (pogo) brett_topp(); else brett(); }
else if (part == "bunnplate") bunnplate();
else if (part == "pogo_han") pogo_han();
else if (part == "gull") gull_kuttet();
else if (part == "samlet") {
  color([0.17, 0.17, 0.18]) if (pogo) brett_topp(); else brett();
  if (pogo) { color([0.2, 0.2, 0.21]) bunnplate(); pogo_han(); }
  color([0.85, 0.62, 0.25]) gull_kuttet();
  if (med_fk) translate([0, 0, gulv]) {
    color([0.81, 0.78, 0.71]) import("../asm_hu/topp.stl");
    color([0.17, 0.17, 0.18]) import("../asm_hu/bunn.stl");
    color([0.18, 0.18, 0.18]) import("../asm_hu/hetter.stl");
    color([0.93, 0.92, 0.89]) import("../asm_hu/symboler.stl");
    color([0.85, 0.62, 0.25]) import("../asm_hu/logo.stl");
  }
}
