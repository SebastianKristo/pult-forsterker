// Skjold Dokk Flat – et lavt brett der fjernkontrollen ligger flatt med skjermen opp (for eksempel foran TV-en, der
// den stående dokka er for høy). Passer alle utgavene av fjernkontrollen (samme omriss, 55 × 202,5 mm, R11).
//   - forsenkning som følger fjernkontrollens omriss, med 45° fas øverst så den glir på plass
//   - grep på begge sider midt på, så den er lett å løfte opp
//   - spor i halen for USB-C-pluggen (rett eller vinklet), så den kan lade mens den ligger der
//   - gullstripe felt inn i toppen, gummiføtter under
// Printes med bunnen ned, ingen støtte. Fjernkontrollens koordinater: x tvers (0…FW), y fra halen (0…FL).
part = "brett";                  // brett | gull | samlet
med_fk = false;                  // vis fjernkontrollen (bare bilder)

FW = 55; FL = 202.5; FR = 11;     // fjernkontrollens omriss (R11-hjørner)
kl = 0.6;                         // klaring rundt i forsenkningen
kant = 7;                         // brettets kant rundt fjernkontrollen
gulv = 3;                         // gulvet under fjernkontrollen
dybde = 7;                        // forsenkningens dybde (fjernkontrollen stikker 6,5–9 mm over brettet)
H = gulv + dybde;                 // brettets høyde
fas = 1.6;                        // fas øverst i forsenkningen og på yttertoppen
R_ut = FR + kant;
grep_r = 16;                      // grepene: sylinder på tvers som senker kanten midt på
usb_x = 27.5; usb_z = 4.7;        // USB-C i halen (midt på; 4,7 mm over undersiden på Hullkort)
usb_b = 14; usb_h = 8.6;          // sporet: plass til pluggens støpte del
gull_inn = 3.2; gull_b = 1.2; gull_d = 0.6;
fot_d = 10; fot_h = 1.0;
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
if (part == "brett") brett();
else if (part == "gull") gull_kuttet();
else if (part == "samlet") {
  color([0.17, 0.17, 0.18]) brett();
  color([0.85, 0.62, 0.25]) gull_kuttet();
  if (med_fk) translate([0, 0, gulv]) {
    color([0.81, 0.78, 0.71]) import("../asm_hu/topp.stl");
    color([0.17, 0.17, 0.18]) import("../asm_hu/bunn.stl");
    color([0.18, 0.18, 0.18]) import("../asm_hu/hetter.stl");
    color([0.93, 0.92, 0.89]) import("../asm_hu/symboler.stl");
    color([0.85, 0.62, 0.25]) import("../asm_hu/logo.stl");
  }
}
