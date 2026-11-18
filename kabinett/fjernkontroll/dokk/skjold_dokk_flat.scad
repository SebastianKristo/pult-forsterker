// Skjold Dokk Flat – et lavt brett der fjernkontrollen ligger flatt med skjermen opp (for eksempel foran TV-en, der
// den stående dokka er for høy). Passer alle utgavene av fjernkontrollen (samme omriss, 55 × 202,5 mm, R11).
//   - forsenkning som følger fjernkontrollens omriss, med 45° fas øverst så den glir på plass
//   - grep på begge sider midt på, så den er lett å løfte opp
//   - spor i halen for USB-C-pluggen (rett eller vinklet), så den kan lade mens den ligger der
//   - gullstripe felt inn i toppen, gummiføtter under
//   - magnetisk lading (pogo = true): handelen av pogo-kontakten i gulvet rett under hunndelen i fjernkontrollens bunn
//     (bunn_dokk), USB-C-brikke i halen, ledningskanal under gulvet og en bunnplate som skrus fast (4 × M3 × 8)
// Printes med bunnen ned, ingen støtte. Fjernkontrollens koordinater: x tvers (0…FW), y fra halen (0…FL).
part = "brett";                  // brett | gull | bunnplate | pogo_han | samlet | ir_deler | ir_kanaler | ir_inni
// IR (ir = true, krever pogo = true): ESP32-C3 SuperMini, to IR-lysdioder i halen og en VS1838B på høyre side –
// se «IR» under. Alt legges inn nedenfra før bunnplata skrus på.
ir = false;
pogo = true;                     // magnetisk lading (pogo-kontakt + USB-C-brikke + bunnplate)
med_fk = false;                  // vis fjernkontrollen (bare bilder)

FW = 55; FL = 202.5; FR = 11;     // fjernkontrollens omriss (R11-hjørner)
kl = 0.6;                         // klaring rundt i forsenkningen
kant = 7;                         // brettets kant rundt fjernkontrollen
gulv = pogo ? (ir ? 11 : 9) : 3;  // gulvet under fjernkontrollen (pogo-kontakten trenger plass under; IR: 2 mm mer)
dybde = 7;                        // forsenkningens dybde (fjernkontrollen stikker 6,5–9 mm over brettet)
H = gulv + dybde;                 // brettets høyde
fas = 1.6;                        // fas øverst i forsenkningen og på yttertoppen
R_ut = FR + kant;
ut = 2 * kant;                    // fk2d(o) ligger 2·o utenfor fjernkontrollen: ytterveggen står ut = 14 mm ute
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

// ---------- IR (samme deler som i den stående dokka) ----------
// Brettet ligger under TV-en med halen (og USB-kabelen) bakover mot TV-veggen, så lysdiodene sitter i halen ved siden
// av USB-C-brikken, vippet ir_vinkel opp og ±ir_spre utover. Bak dem er et romslig kammer til driveren, en kanal går
// langs høyre side til C3-lomma, og VS1838B ser ut av høyre side (pek den gamle fjernkontrollen dit når du lærer koder).
// Lyset fra den blå lysdioden på C3 kommer opp gjennom gullstripa på høyre kant (en bit klar filament, 1,75 mm).
ir_x = [39, 47.5];                // lysdiodene i halen (x), til høyre for sporet til fjernkontrollens USB-plugg
ir_z = 7.0; ir_vinkel = 10; ir_spre = 8;
ir_d = 5.1; ir_fas = 0.7; ir_l = 8.6; ir_inne = 0.3; ir_flens = 6.4;
ir_trinn = ir_inne + ir_l - 1.0;
ir_tak = gulv - 1.5;              // taket i lommene (1,5 mm gulv over, under fjernkontrollen)
ir_kanal_b = 4.5;
ir_kam = [31, -ut + ir_trinn * cos(ir_vinkel) - 1.2, 54, 10];   // kammeret bak lysdiodene: x0, y0, x1, y1 (23 × 17,4 × 7,5 mm)
mott = [9.4, 5.8, 7.4];           // VS1838B liggende, kuppelen ut mot høyre side
mott_y = 92;                      // under grepet på høyre side
c3 = [22.5, 18.0, 3.6];           // ESP32-C3 SuperMini på tvers, USB-C-enden mot høyre
c3_x = 55; c3_y = 71;             // kortets senter (lomma går ut under høyre kant)
c3_lomme = [25, 26];
lys_x = FW + ut - 2*gull_inn - gull_b;     // lyslederen står midt i gullstripa på høyre kant …
c3_lys = [lys_x - c3_x, 6.5];     // … og den blå lysdioden (GPIO8) må stå rett under (i forhold til kortets senter)
lysleder_d = 1.9;
module ir_plass(p, yaw) { translate(p) rotate([0, 0, yaw]) rotate([90 - ir_vinkel, 0, 0]) children(); }
module draape2(d) { hull() { circle(d = d, $fn = 32); translate([0, d/2 * sqrt(2)]) circle(d = 0.05, $fn = 8); } }
module ir_hull_lokal() {
  translate([0, 0, -ir_trinn]) linear_extrude(ir_trinn + 3) draape2(ir_d);
  translate([0, 0, -ir_fas]) cylinder(h = ir_fas + 3, d1 = ir_d, d2 = ir_d + 2*(ir_fas + 3), $fn = 32);
  translate([0, 0, -ir_trinn - 10]) linear_extrude(10) draape2(ir_flens);
}
module ir_led_lokal(bein = 4) {
  z0 = -ir_inne - ir_l;
  color([0.32, 0.36, 0.52]) {
    translate([0, 0, z0]) cylinder(d = 5.8, h = 1.0, $fn = 32);
    translate([0, 0, z0 + 1]) cylinder(d = 4.95, h = ir_l - 1 - 2.47, $fn = 32);
    translate([0, 0, -ir_inne - 2.47]) sphere(d = 4.95, $fn = 32);
  }
  if (bein > 0) color([0.75, 0.75, 0.78]) for (x = [-1.27, 1.27]) translate([x, 0, z0 - bein]) cylinder(d = 0.5, h = bein, $fn = 8);
}
ir_alle = [[[ir_x[0], -ut, ir_z], -ir_spre], [[ir_x[1], -ut, ir_z], ir_spre]];
mott_z = delt_z + mott[2]/2 + 0.2;
module ir_kanal(a, b, o = 0) {
  hull() for (p = [a, b]) translate([p[0], p[1], delt_z - 0.01 + o]) cylinder(r = ir_kanal_b/2 - o, h = ir_kanal_b + 0.01 - 2*o, $fn = 24);
}
module rboks(x0, y0, x1, y1, z1, r = 1.5, o = 0) {
  translate([0, 0, delt_z - 0.01 + o]) linear_extrude(z1 - delt_z + 0.01 - 2*o)
    translate([x0 + o, y0 + o]) offset(r) offset(-r) square([x1 - x0 - 2*o, y1 - y0 - 2*o]);
}
module ir_kanaler(o = 0) {
  ir_kanal([50, ir_kam[3] - 3], [50, c3_y - c3_lomme[1]/2 + 2], o);           // kammeret → langs høyre side til C3
  ir_kanal([62, c3_y + c3_lomme[1]/2 - 2], [62, mott_y - 4], o);              // C3 → mottakeren
  ir_kanal([usbd_x + 4, -2], [ir_kam[0] + 3, -2], o);                         // USB-C-lomma → kammeret (VBUS, GND)
}
// lommene (åpne ned mot bunnplata); kanalene går mellom dem
module ir_lommer() {
  rboks(ir_kam[0], ir_kam[1], ir_kam[2], ir_kam[3], ir_tak);                   // kammeret (driver, motstander, bein)
  rboks(c3_x - c3_lomme[0]/2, c3_y - c3_lomme[1]/2, c3_x + c3_lomme[0]/2, c3_y + c3_lomme[1]/2, ir_tak, 0.8);
  rboks(FW + ut - 1.6 - mott[1] - 2.5, mott_y - mott[0]/2 - 0.3, FW + ut - 1.6, mott_y + mott[0]/2 + 0.3, mott_z + mott[2]/2 + 0.6, 0.5);
  translate([usbd_x - usb_kort[0]/2 - 0.2, -ut + 1.2, delt_z - 0.01]) cube([usb_kort[0] + 0.4, usb_kort[1] + 0.2, usb_kort[2] + usb_k[2] + 0.4]);
}
module ir_rom() {
  for (l = ir_alle) ir_plass(l[0], l[1]) ir_hull_lokal();
  ir_lommer();
  translate([lys_x, c3_y + c3_lys[1], 2]) cylinder(d = lysleder_d, h = H, $fn = 16);
  // VS1838B: vindu med fas i høyre side
  translate([FW + ut, mott_y, mott_z]) rotate([0, 90, 0]) rotate([0, 0, 180]) {
    translate([0, 0, -2]) linear_extrude(4) draape2(mott_vindu);
    translate([0, 0, -0.6]) cylinder(h = 3.6, d1 = mott_vindu, d2 = mott_vindu + 7.2, $fn = 32);
  }
  ir_kanaler();
}
mott_vindu = 4.4;
ir_tapp = [ir_kam[0] + 1.8, ir_kam[1] + 1.9];   // ved åpningen mot USB-kanalen
module ir_tapp() { if (ir) translate([ir_tapp[0], ir_tapp[1], delt_z]) cylinder(d = 3, h = ir_tak - delt_z + 0.1, $fn = 20); }
module ir_deler(bein = 4) {
  for (l = ir_alle) ir_plass(l[0], l[1]) ir_led_lokal(bein);
  translate([FW + ut - 1.6 - 0.05, mott_y, delt_z + 0.2]) color([0.08, 0.08, 0.09]) {   // VS1838B, kuppelen ut
    translate([-(mott[1] - 0.9), -mott[0]/2 + 0.1, 0]) cube([mott[1] - 0.9, mott[0] - 0.2, mott[2]]);
    translate([-0.9, 0, mott[2]/2]) rotate([0, 90, 0]) cylinder(d = 3.6, h = 0.9, $fn = 24);
  }
  translate([c3_x, c3_y, delt_z]) {                                           // C3 SuperMini, USB-C mot høyre
    color([0.12, 0.18, 0.40]) translate([-c3[0]/2, -c3[1]/2, 0]) cube([c3[0], c3[1], 1.0]);
    color([0.15, 0.15, 0.16]) translate([-2.5, -2.5, 1]) cube([5, 5, 0.9]);
    color([0.75, 0.75, 0.78]) translate([c3[0]/2 - 6.3, -4.5, 1]) cube([7.3, 9, 3.2]);
    color([0.85, 0.85, 0.82]) translate([-c3[0]/2 + 0.5, -5, 1]) cube([2.5, 10, 1]);
    color([0.3, 0.5, 1.0]) translate([c3_lys[0] - 0.5, c3_lys[1] - 0.4, 1]) cube([1, 0.8, 0.5]);
  }
  translate([usbd_x, -ut + 1.2 + usb_kort[1]/2, delt_z]) {                    // USB-C-brikken
    color([0.15, 0.35, 0.2]) translate([-usb_kort[0]/2, -usb_kort[1]/2, 0]) cube(usb_kort);
    color([0.75, 0.75, 0.78]) translate([-usb_k[0]/2, -usb_kort[1]/2 - 0.6, usb_kort[2]]) cube(usb_k);
  }
  translate([43, 2.5, delt_z]) {                                             // driverkortet, 20 × 12 mm
    color([0.15, 0.35, 0.2]) translate([-10, -6, 0]) cube([20, 12, 1.6]);
    color([0.1, 0.1, 0.1]) translate([-1.5, -1.5, 1.6]) cube([3, 2.9, 1.1]);
    color([0.8, 0.7, 0.5]) for (i = [-1, 0, 1]) translate([-8, 2 + i * 2.6 - 3, 1.6 + 1.2]) rotate([0, 90, 0]) cylinder(d = 2.4, h = 6.3, $fn = 12);
  }
}
module bunnplate_ir() {   // bunnplata med lave kanter (1 mm) rundt C3 og driverkortet
  bunnplate();
  translate([0, 0, delt_z - 0.01]) linear_extrude(1.0) {
    translate([c3_x, c3_y]) difference() { square([c3[0] + 2.2, c3[1] + 2.2], center = true); square([c3[0] + 0.6, c3[1] + 0.6], center = true);
      square([c3[0] - 6, 40], center = true); square([40, c3[1] - 6], center = true); }
    translate([43, 2.5]) difference() { square([22.4, 14.4], center = true); square([20.6, 12.6], center = true);
      square([14, 40], center = true); square([40, 6], center = true); }
  }
}
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
    translate([usb_x - usb_b/2, -ut - 1, gulv + usb_z - usb_h/2]) cube([usb_b, ut + 2, H]);
    // gullstripa rundt toppen
    translate([0, 0, H - gull_d]) linear_extrude(1) difference() { fk2d(kant - gull_inn); fk2d(kant - gull_inn - gull_b); }
    // gummiføtter
    for (x = [-kant + 8, FW + kant - 8], y = [-kant + 14, FL + kant - 14]) translate([x, y, -0.01]) cylinder(d = fot_d + 0.4, h = fot_h);
    if (pogo) pogo_kutt();
    if (ir) ir_rom();
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
    translate([usbd_x - 2, -2, delt_z - 0.01]) cube([4, 4, 3]);
  }
  // USB-C-brikken: lomme med kortet flatt, kontakten mot endeveggen (1,2 mm vegg) og ut
  translate([usbd_x - usb_kort[0]/2 - 0.2, -ut + 1.2, delt_z - 0.01]) cube([usb_kort[0] + 0.4, usb_kort[1] + 0.2, usb_kort[2] + usb_k[2] + 0.4]);
  translate([usbd_x, -ut - 1, delt_z + usb_kort[2] + usb_k[2]/2]) rotate([-90, 0, 0])
    linear_extrude(3) offset(1.2) square([usb_k[0] + 0.4 - 2.4, usb_k[2] + 0.4 - 2.4], center = true);
  translate([usbd_x, -ut - 0.01, delt_z + usb_kort[2] + usb_k[2]/2]) rotate([-90, 0, 0])
    linear_extrude(0.61) offset(2.5) square([13.6 - 5, 7.4 - 5], center = true);   // forsenkning for pluggen
}
module brett_topp() {   // brettet over delt_z (med pogo), med forboring for skruene til bunnplata
  difference() {
    brett();
    translate([-100, -100, -1]) cube([400, 400, delt_z + 1]);
    for (p = skruer) translate([p[0], p[1], delt_z - 0.01]) cylinder(d = 2.6, h = 8, $fn = 20);
  }
  ir_tapp();
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
    translate([usb_x - usb_b/2 - 0.01, -ut - 1, gulv]) cube([usb_b + 0.02, ut + 2, H]);
    if (ir) translate([lys_x, c3_y + c3_lys[1], 0]) cylinder(d = lysleder_d, h = H + 1, $fn = 16);   // lyslederen
  }
}
if (part == "brett") { if (pogo) brett_topp(); else brett(); }
else if (part == "bunnplate") { if (ir) bunnplate_ir(); else bunnplate(); }
else if (part == "ir_deler") ir_deler(0);
else if (part == "ir_kanaler") difference() { ir_kanaler(0.3); ir_lommer(); }
else if (part == "ir_inni") {   // kuttet i z = 5,5 med bunnplata og delene på plass
  color([0.82, 0.80, 0.75]) render() intersection() { brett_topp(); translate([-50, -50, 0]) cube([200, 300, 5.5]); }
  color([0.7, 0.68, 0.64]) translate([0, 0, -0.02]) render() bunnplate_ir();
  ir_deler();
}
else if (part == "pogo_han") pogo_han();
else if (part == "gull") gull_kuttet();
else if (part == "samlet") {
  color([0.17, 0.17, 0.18]) render() if (pogo) brett_topp(); else brett();   // render(): forhåndsvisningen viser ellers feil
  if (pogo) { color([0.2, 0.2, 0.21]) bunnplate(); pogo_han(); }
  if (ir) ir_deler();
  color([0.85, 0.62, 0.25]) render() gull_kuttet();
  if (med_fk) translate([0, 0, gulv]) {
    color([0.81, 0.78, 0.71]) import("../asm_hu/topp.stl");
    color([0.17, 0.17, 0.18]) import("../asm_hu/bunn.stl");
    color([0.18, 0.18, 0.18]) import("../asm_hu/hetter.stl");
    color([0.93, 0.92, 0.89]) import("../asm_hu/symboler.stl");
    color([0.85, 0.62, 0.25]) import("../asm_hu/logo.stl");
  }
}
