// KI Pultforsterker v2 – kabinett etter frontdesignet i design_handoff_pultforsterker
// Koordinater: x høyre, y bakover (front = -D/2), z opp. Boksens bunn er z=0.
// Deler: part = "body" | "frontplate" | "lid" | "both"
//
// Print: body med åpningen opp (ingen støtte), frontplate med forsiden ned mot
// glatt plate, lid flatt. PLA Matte antrasitt (PETG hvis det blir varmt).
// Lokket er det samme som i v1 (pultforsterker_lid.stl) – skruehull ±90/±50.

part = "body";

// ---------- Hovedmål ----------
W = 200; D = 120;            // ytre mål (som lokket)
H = 48;                      // boksens høyde (uten lokk)
wall = 2.7; floor_t = 2.5;
r_out = 6;
lid_t = 3; lip = 1.6; clear = 0.3;

// ---------- Front ----------
fp_w = 188; fp_h = 46; fp_t = 2; fp_r = 3;          // påsatt frontplate
fz = H/2;                                            // senterhøyde for alt på fronten (z=24)
oled_x = -30; oled_w = 57; oled_h = 30;              // vindu i veggen (aktivt område 55 x 27.5)
win_w = 70; win_h = 38; win_r = 2; win_depth = 2.2;  // forsenkning for 2 mm akryl (100x100 kuttes til 70x38)
btn_d = 12.4; btn_x = [20, 37]; btn_dz = 8.5;        // 4 x 12 mm knapper, 2x2 (AIRPLAY/BT øverst, AUX/USB nederst)
pwr_d = 16.4; pwr_x = -80;                           // 16 mm POWER
enc_d = 7.4; enc_x = 70;                             // KY-040 M7

// ---------- Bak ----------
kcd1 = [19.4, 13.0]; kcd1_x = 76;                    // KCD1 15x21 utsparing
dc_d = 11.4; dc_x = 54;                              // DC-099 M11
usbc = [9.6, 3.8]; usbc_x = 36; usbc_pitch = 17; usbc_screw = 2.7;   // USB-C flens m/ 2 skruer
aux_d = 6.4; aux_x = 20;                             // PJ392
post_d = 6.4; post_x = [-30, -45, -65, -80];         // bananterminaler M6 (R: -30/-45, L: -65/-80)

// ---------- Innvendig ----------
tower_d = 8; tower_xy = [90, 50]; insert_d = 4.0;    // M3 varmeinnsats
amp_holes = [50, 42];   amp_pos = [55, 15];          // XH-M562 (mål kortet!) – stolper, 2 brukes
pi_holes  = [58, 23];   pi_pos  = [-55, 20];         // Pi Zero 2 W

// ---------- Ventilasjon ----------
vent_n = 16; vent_w = 2.4; vent_gap = 3.6; vent_h = 24;

$fn = 64;

module rrect(w, d, r, h) { linear_extrude(h) offset(r) offset(-r) square([w, d], center = true); }
module hole_y(d, x, z, len = wall + 6) { translate([x, -D/2 - 3, z]) rotate([-90, 0, 0]) cylinder(d = d, h = len); }
module hole_y_back(d, x, z) { translate([x, D/2 - wall - 3, z]) rotate([-90, 0, 0]) cylinder(d = d, h = wall + 6); }
module slot_back(sz, x, z) { translate([x - sz[0]/2, D/2 - wall - 1, z - sz[1]/2]) cube([sz[0], wall + 2, sz[1]]); }
module rrect_y(w, h, r, x, y, z, len) { translate([x, y, z]) rotate([-90, 0, 0]) linear_extrude(len) offset(r) offset(-r) square([w, h], center = true); }

module body() {
  difference() {
    rrect(W, D, r_out, H);
    translate([0, 0, floor_t]) rrect(W - 2*wall, D - 2*wall, r_out - wall, H);

    // ---- FRONT (gjennom veggen; frontplaten har egne hull) ----
    rrect_y(oled_w, oled_h, 1.5, oled_x, -D/2 - 1, fz, wall + 2);
    for (x = btn_x) for (s = [-1, 1]) hole_y(btn_d, x, fz + s*btn_dz);
    hole_y(pwr_d, pwr_x, fz);
    hole_y(enc_d, enc_x, fz);
    // utsparing innvendig så KY-040-kortet ligger flatt
    translate([enc_x - 10, -D/2 + wall - 0.01, fz - 13]) cube([20, 1.2, 26]);
    // M3-hull for frontplaten (fire, i hjørnene av platen)
    for (sx = [-1, 1]) for (sz = [-1, 1]) hole_y(2.6, sx*(fp_w/2 - 6), fz + sz*(fp_h/2 - 6));

    // ---- BAK ----
    slot_back(kcd1, kcd1_x, fz);
    hole_y_back(dc_d, dc_x, fz);
    slot_back(usbc, usbc_x, fz);
    for (s = [-1, 1]) hole_y_back(usbc_screw, usbc_x + s*usbc_pitch/2, fz);
    hole_y_back(aux_d, aux_x, fz);
    for (x = post_x) hole_y_back(post_d, x, fz);

    // ---- VENTILASJON sider + bunn under forsterkeren ----
    for (s = [-1, 1]) for (i = [0 : vent_n - 1])
      translate([s*(W/2 - wall/2) - (wall + 2)/2, -((vent_n - 1)*vent_gap)/2 + i*vent_gap, floor_t + 12])
        cube([wall + 2, vent_w, vent_h]);
    for (i = [0 : 9]) translate([amp_pos[0] - 27 + i*6, amp_pos[1] - 25, -1]) cube([2.4, 50, floor_t + 2]);
  }
  // skruetårn til lokket med ribbe mot veggen
  for (sx = [-1, 1]) for (sy = [-1, 1])
    translate([sx*tower_xy[0], sy*tower_xy[1], 0]) difference() {
      union() {
        cylinder(d = tower_d, h = H);
        translate([-tower_d/2, 0, 0]) cube([tower_d, 1, H]); // liten ribbe
      }
      translate([0, 0, H - 6]) cylinder(d = insert_d, h = 7);
    }
  // stolper forsterker (XH-M562 har 2 diagonale hull – bruk de to som passer)
  for (x = [-1, 1]) for (y = [-1, 1])
    translate([amp_pos[0] + x*amp_holes[0]/2, amp_pos[1] + y*amp_holes[1]/2, 0])
      difference() { cylinder(d = 6, h = floor_t + 5); cylinder(d = 2.6, h = floor_t + 6); }
  // stolper Pi Zero 2 W
  for (x = [-1, 1]) for (y = [-1, 1])
    translate([pi_pos[0] + x*pi_holes[0]/2, pi_pos[1] + y*pi_holes[1]/2, 0])
      difference() { cylinder(d = 5.5, h = floor_t + 4); cylinder(d = 2.2, h = floor_t + 5); }
}

// Frontplate: 188 x 46 x 2, forsenkning for akrylvindu, samme hull som veggen
module frontplate() {
  difference() {
    linear_extrude(fp_t) offset(fp_r) offset(-fp_r) square([fp_w, fp_h], center = true);
    // vindu: gjennomgående åpning litt mindre enn glasset, forsenkning fra baksiden for akryl
    translate([oled_x, 0, -1]) linear_extrude(fp_t + 2) offset(1) offset(-1) square([oled_w + 4, oled_h + 4], center = true);
    translate([oled_x, 0, fp_t - win_depth]) linear_extrude(win_depth + 1) offset(win_r) offset(-win_r) square([win_w, win_h], center = true);
    for (x = btn_x) for (s = [-1, 1]) translate([x, s*btn_dz, -1]) cylinder(d = btn_d, h = fp_t + 2);
    translate([pwr_x, 0, -1]) cylinder(d = pwr_d, h = fp_t + 2);
    translate([enc_x, 0, -1]) cylinder(d = enc_d, h = fp_t + 2);
    for (sx = [-1, 1]) for (sz = [-1, 1]) translate([sx*(fp_w/2 - 6), sz*(fp_h/2 - 6), -1]) {
      cylinder(d = 3.4, h = fp_t + 2);
      translate([0, 0, fp_t - 1.4]) cylinder(d1 = 3.4, d2 = 6.4, h = 1.5);   // forsenket M3
    }
  }
}
// Frontplaten printes med forsiden ned: z=0 er forsiden. Akrylet (70x38x2) legges i
// forsenkningen på baksiden og limes/klemmes mot veggen når platen skrus på.

module lid() {
  ear_w = 22; ear_l = 19; ear_slot = 10; ear_screw = 4.6;
  difference() {
    union() {
      rrect(W, D, r_out, lid_t);
      translate([0, 0, -lip]) rrect(W - 2*wall - 2*clear, D - 2*wall - 2*clear, r_out - wall, lip);
      for (sx = [-1, 1]) for (sy = [-1, 1])
        translate([sx*108.5, sy*40, 0]) rrect(ear_l, ear_w, 3, lid_t);
    }
    for (sx = [-1, 1]) for (sy = [-1, 1]) {
      translate([sx*tower_xy[0], sy*tower_xy[1], -lip - 1]) {
        cylinder(d = 3.4, h = lid_t + lip + 2);
        translate([0, 0, lip + 1 + lid_t - 1.6]) cylinder(d1 = 3.4, d2 = 6.4, h = 1.7);
      }
      translate([sx*110, sy*40, -1]) hull() {
        translate([-ear_slot/2 + ear_screw/2, 0, 0]) cylinder(d = ear_screw, h = lid_t + 2);
        translate([ ear_slot/2 - ear_screw/2, 0, 0]) cylinder(d = ear_screw, h = lid_t + 2);
      }
    }
    translate([0, D/2 - 6.5, -lip - 1]) cube([30, 13, lip + 0.7 + 1], center = true); // kabelutsparing
  }
}

if (part == "body") body();
if (part == "frontplate") frontplate();
if (part == "lid") lid();
if (part == "both") { body(); translate([0, 0, H + 12]) lid(); translate([0, -D/2 - 10, fz]) rotate([90, 0, 0]) frontplate(); }
