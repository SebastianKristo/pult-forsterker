// Skjold IR – en liten IR-sender på Wi-Fi (parametrisk OpenSCAD). Står der fjernkontrollen ikke når fram, for eksempel
// inne i stereoskapet, og sender IR for Skjold Stav, Home Assistant og Homey. Fastvare: esphome/skjold-ir.yaml.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Formen: en lav, avrundet firkant (56 × 56 × 22 mm) i Skjolds formspråk, som sokkelen til Skjold Dokk: toppen i
// Bone White med en gullring felt inn, bunnen mørk, myke 45°-faser. Tre 5 mm IR-lysdioder peker ut fra fronten og de
// to fremre hjørnene (0° og ±45°, ca. 125° dekning med lysdiodenes egen kjegle), og en VS1838B-mottaker ser ut
// gjennom fronten (lære koder rett på senderen). Valgfritt en fjerde lysdiode rett opp (led_opp).
//
// Lysdiodene og mottakervinduet ligger i delingen mellom topp og bunn: halve hullet i hver del. Lysdiodene legges i
// bunnen og låses av toppen, kuppelen ligger 0,3 mm inne og flensen hviler mot blokka innvendig. Alt printes uten
// støtte: bunnen står på undersiden, toppen står på toppflaten (gullringen er første lag).
//
// Koordinater: x mot høyre (0 = midten), y bakover (fronten i −y), z opp (0 = bordet).
// Bruk:  openscad -D 'part="topp"' -D 'kort="c3"' -o topp.stl skjold_ir.scad
// part:  bunn | topp | gull | lysleder | samlet | eksplodert | inni | undersiden | a_<del> (montert stilling, for sjekken:
//        a_bunn a_topp a_gull a_lysleder a_kort a_led a_mott a_driver a_magnet)
use <../fonter/Inter-Bold.otf>

part  = "samlet";
kort  = "c3";            // "c3" (ESP32-C3 SuperMini) | "d1mini" (Wemos D1 mini, ESP8266)
farge = "lys";           // lys (Bone White topp, mørk bunn) | mork (mørk topp, lys bunn) – bare for bildene
led_vinkler = [-45, 0, 45];   // lysdiodene rundt fronten (0 = rett fram, positiv mot høyre)
led_opp = false;         // en fjerde lysdiode rett opp (mot taket i skapet; IR spretter godt)
mottaker = true;         // vindu og holder for VS1838B
magneter = true;         // lommer for 4 × Ø8 × 2 mm magneter i bunnen (fest på en stålhylle eller en metallplate)
$fn = 48;

// ---------- form ----------
B = 56;                  // bredde og dybde
R = 14;                  // hjørneradius sett ovenfra
H = 22;                  // høyde
zs = 10;                 // delingen topp/bunn = lysdiodenes akse
vegg = 2.4;
bunn_t = 2.4;            // gulvet
topp_t = 2.0;            // taket
fas = 2.5;               // 45°-fas rundt toppen (printes uten støtte med toppen ned)
fot_fas = 0.4;           // liten fas nederst mot elefantfot
leppe_h = 2.4;           // leppa på bunnen som toppen tres over
gull_inn = 5.6; gull_b = 1.2; gull_d = 0.6;   // gullringen i toppen

// ---------- IR-lysdioder (5 mm, 940 nm: TSAL6200 eller vanlig) ----------
ir_d = 5.1;              // hullet
ir_fas = 0.7;            // fas ytterst
ir_l = 8.6;              // lengde fra flensen til tuppen
ir_inne = 0.3;           // kuppelen ligger så langt inne
blokk_b = 8;             // blokka rundt hullet (fra gulv til tak), som flensen hviler mot
trinn = ir_inne + ir_l - 1.0;    // flensens forside, målt innover fra ytterflaten

// ---------- VS1838B ----------
mott = [7.0, 5.6, 9.0];  // b × d × h (stående, kuppelen mot fronten midt på) – mål din
mott_x = -9;             // til venstre for den midterste lysdioden
mott_vindu = 4.4;

// ---------- kort ----------
C3 = kort == "c3";
bW = C3 ? 18.0 : 25.6;   // bredde
bL = C3 ? 22.5 : 34.2;   // lengde (USB i bakkant)
bT = 1.0;                // kortets tykkelse
stolpe = C3 ? 0 : 4.0;   // D1 mini: står på fire hjørnestolper med USB-pluggen under kortet (har ditt kort USB på
                         // oversiden: sett stolpe = 0 og usb_under = false)
usb_under = !C3;
kort_z = bunn_t + stolpe;                    // undersiden av kortet
usb = C3 ? [9.0, 7.3, 3.2] : [8.0, 5.6, 2.8];    // kontakten (b × d × h); stikker 1 mm ut over kortkanten
usb_zc = usb_under ? kort_z - usb[2]/2 : kort_z + bT + usb[2]/2;
kort_y1 = B/2 - vegg - 0.2 - 1.0;            // kortets bakkant (kontakten stikker 1 mm ut og står 0,2 mm fra veggen)
kort_yc = kort_y1 - bL/2;
usb_hull = [12.6, 7.2, 2.0];                 // åpningen bak: plass til støpte plugger (b × h × hjørneradius)
// den blå lysdioden på kortet (C3: GPIO8, D1 mini: GPIO2 på ESP-12-modulen) – lyslederen står rett over
lys = C3 ? [-6.6, kort_yc + 5, kort_z + bT + 0.5] : [-6, kort_yc - 12, kort_z + bT + 3.3];
lys_d = 3.0;

// ---------- skruer, føtter og magneter ----------
skruer = [[-21, -9], [21, -9], [-21, 9], [21, 9]];   // M2 × 14 selvgjengende nedenfra
foter = [[-17, -19], [17, -19], [-17, 19], [17, 19]];  // gummiføtter Ø10 × 1
fot_d = 10.4; fot_h = 0.8;
magnet = [8.3, 2.05];                                 // Ø8 × 2 mm (lomme med 0,4 mm hud under)
magnet_pos = [[-7, -16], [7, -16], [-19, 0], [19, 0]];   // unna kortet (og antennen)
opp_pos = [0, -8];       // den valgfrie lysdioden rett opp

// ---------- farger ----------
c_bone = [0.81, 0.78, 0.71]; c_mork = [0.17, 0.17, 0.18]; c_gull = [0.85, 0.62, 0.25];
c_topp = farge == "lys" ? c_bone : c_mork;
c_bunn = farge == "lys" ? c_mork : [0.82, 0.80, 0.75];

// ---------- hjelpere ----------
module form2d(o = 0) { offset(r = R - o) square(B - 2*R, center = true); }
// avstand fra midten til ytterflaten i retning a (0 = −y)
function rs(a) = let(ux = abs(sin(a)), uy = abs(cos(a)), h = B/2, c = h - R,
                     t = min(ux > 1e-6 ? h/ux : 1e9, uy > 1e-6 ? h/uy : 1e9), p = [ux*t, uy*t])
                 (p[0] <= c + 1e-6 || p[1] <= c + 1e-6) ? t : let(b = (ux + uy)*c) b + sqrt(b*b - 2*c*c + R*R);
module retning(a) { rotate([0, 0, a]) children(); }          // lokal −y peker ut i retning a

module ytre() {          // det massive ytre: rett side, 45°-fas øverst, liten fas nederst
  hull() {
    linear_extrude(0.01) form2d(fot_fas);
    translate([0, 0, fot_fas]) linear_extrude(H - fas - fot_fas) form2d();
    translate([0, 0, H - 0.01]) linear_extrude(0.01) form2d(fas);
  }
}
module hulrom() { translate([0, 0, bunn_t]) linear_extrude(H - topp_t - bunn_t) form2d(vegg); }

// blokkene rundt lysdiodene (fra gulv til tak), mottakerens vindu og lommer
module blokker() {
  for (a = led_vinkler) retning(a) translate([-blokk_b/2, -rs(a) - 1, 0]) cube([blokk_b, trinn + 1, H]);
}
module led_hull() {
  for (a = led_vinkler) retning(a) {
    translate([0, -rs(a) + trinn, zs]) rotate([90, 0, 0]) cylinder(d = ir_d, h = trinn + 2);
    translate([0, -rs(a) + ir_fas, zs]) rotate([90, 0, 0]) cylinder(d1 = ir_d, d2 = ir_d + 2*(ir_fas + 2), h = ir_fas + 2);
  }
  if (led_opp) translate([opp_pos[0], opp_pos[1], 0]) {
    translate([0, 0, H - trinn]) cylinder(d = ir_d, h = trinn + 1);
    translate([0, 0, H - ir_fas]) cylinder(d1 = ir_d, d2 = ir_d + 2*(ir_fas + 1), h = ir_fas + 1);
  }
  if (mottaker) translate([mott_x, -B/2, zs]) rotate([-90, 0, 0]) {
    translate([0, 0, -1]) cylinder(d = mott_vindu, h = vegg + 2);
    translate([0, 0, -1.5]) cylinder(d1 = mott_vindu + 2*(1.5 + 0.6), d2 = mott_vindu, h = 1.5 + 0.6);
  }
}
module opp_blokk() { if (led_opp) translate([opp_pos[0], opp_pos[1], H - trinn]) cylinder(d = blokk_b, h = trinn); }
// leppa: bunnens indre halvdel av veggen fortsetter leppe_h opp (toppen tres over), avbrutt ved blokkene, mottakeren og USB
module leppe2d() {
  difference() {
    difference() { form2d(vegg/2 + 0.15); form2d(vegg); }
    for (a = led_vinkler) retning(a) translate([-blokk_b/2 - 0.3, -rs(a) - 1]) square([blokk_b + 0.6, trinn + 1.3]);
    if (mottaker) translate([mott_x - mott[0]/2 - 1.5, -B/2 - 1]) square([mott[0] + 3, 6]);
    translate([-usb_hull[0]/2 - 1, B/2 - 5]) square([usb_hull[0] + 2, 6]);
  }
}
module usb_aapning() {
  translate([0, B/2 + 1, usb_zc]) rotate([90, 0, 0]) linear_extrude(vegg + 2)
    offset(r = usb_hull[2]) square([usb_hull[0] - 2*usb_hull[2], usb_hull[1] - 2*usb_hull[2]], center = true);
}

// ---------- bunnen ----------
module bunn() {
  difference() {
    union() {
      intersection() {
        union() {
          difference() { ytre(); hulrom(); }
          intersection() { blokker(); ytre(); }
          for (p = skruer) translate([p[0], p[1], 0]) cylinder(d = 6.4, h = zs);
        }
        translate([-B, -B, -1]) cube([2*B, 2*B, zs + 1]);
      }
      translate([0, 0, zs - 0.01]) linear_extrude(leppe_h) leppe2d();
      kortholder();
      if (mottaker) mott_holder();
    }
    led_hull();
    usb_aapning();
    for (p = skruer) translate([p[0], p[1], -0.01]) {
      cylinder(d = 2.4, h = zs + 1, $fn = 20);
      cylinder(d = 4.2, h = 2.0, $fn = 24);                           // forsenket hode nedenfra
    }
    for (p = foter) translate([p[0], p[1], -0.01]) cylinder(d = fot_d, h = fot_h);
    if (magneter) for (p = magnet_pos) translate([p[0], p[1], bunn_t - magnet[1]]) cylinder(d = magnet[0], h = magnet[1] + 0.01);
    translate([0, 3, -0.01]) linear_extrude(0.5) mirror([1, 0, 0])   // navnet speilvendt i undersiden
      text("SKJOLD IR", size = 3.6, font = "Inter:style=Bold", halign = "center", valign = "center", spacing = 1.2);
  }
}
module kortholder() {    // fire L-hjørner rundt kortet (og stolper under D1 mini), åpent bak mot USB-veggen
  translate([0, kort_yc, bunn_t - 0.01]) {
    linear_extrude(stolpe + bT + 1.2) difference() {
      square([bW + 0.4 + 2.4, bL + 0.4 + 2.4], center = true);
      square([bW + 0.4, bL + 0.4], center = true);
      square([bW - 8, 100], center = true);
      square([100, bL - 8], center = true);
      translate([-50, bL/2 - 3]) square([100, 10]);                   // ikke bak (veggen holder kortet der)
    }
    if (stolpe > 0) for (sx = [-1, 1], sy = [-1, 1])
      translate([sx * (bW/2 - 1.4), sy * (bL/2 - 1.4), stolpe/2]) cube([2.8, 2.8, stolpe + 0.01], center = true);
  }
}
module mott_holder() {   // to ribber som holder mottakeren mot fronten
  for (s = [-1, 1]) translate([mott_x + s * (mott[0]/2 + 0.2 + 0.6), -B/2 + vegg + mott[1]/2 + 0.5, bunn_t - 0.01 + (zs - bunn_t)/2])
    cube([1.2, mott[1] + 1, zs - bunn_t], center = true);
}

// ---------- toppen ----------
module topp() {
  difference() {
    union() {
      intersection() {
        union() {
          difference() { ytre(); hulrom(); }
          intersection() { blokker(); ytre(); }
          opp_blokk();
          for (p = skruer) translate([p[0], p[1], zs]) cylinder(d = 6.4, h = H - zs);
          translate([lys[0], lys[1], H - topp_t - 2]) cylinder(d = lys_d + 2.4, h = 2.01);   // krage for lyslederen
        }
        translate([-B, -B, zs]) cube([2*B, 2*B, H]);
      }
    }
    translate([0, 0, zs - 0.01]) linear_extrude(leppe_h + 0.2) offset(r = 0.15) leppe2d();
    led_hull();
    for (p = skruer) translate([p[0], p[1], zs - 0.01]) cylinder(d = 1.7, h = 7, $fn = 16);   // forboring M2
    translate([lys[0], lys[1], 0]) cylinder(d = lys_d, h = H + 1, $fn = 20);
    translate([0, 0, H - gull_d]) linear_extrude(1) difference() { form2d(gull_inn); form2d(gull_inn + gull_b); }
  }
}
module gull() { translate([0, 0, H - gull_d]) linear_extrude(gull_d) difference() { form2d(gull_inn + 0.08); form2d(gull_inn + gull_b - 0.08); } }
// lysleder (klar PETG): fra like over lysdioden til toppflaten, med en kjegleformet krage under taket
module lysleder() {
  z0 = lys[2] + 0.5;
  translate([lys[0], lys[1], 0]) {
    translate([0, 0, z0]) cylinder(d = lys_d - 0.25, h = H - z0, $fn = 20);
    translate([0, 0, H - topp_t - 2 - 0.9]) cylinder(d1 = lys_d - 0.25, d2 = lys_d + 1.4, h = 0.9, $fn = 20);
    translate([0, 0, H - topp_t - 2 - 0.01]) cylinder(d = lys_d + 1.4, h = 0.01, $fn = 20);
  }
}

// ---------- kjøpte deler (bilder og kollisjonssjekk) ----------
module led(a, opp = false) {
  module en() {          // lokal: origo i ytterflaten, tuppen ir_inne inne, kroppen innover (+y)
    color([0.32, 0.36, 0.52]) {
      translate([0, ir_inne + 2.47, 0]) sphere(d = 4.95);
      translate([0, ir_inne + 2.47, 0]) rotate([-90, 0, 0]) cylinder(d = 4.95, h = ir_l - 1 - 2.47);
      translate([0, trinn, 0]) rotate([-90, 0, 0]) cylinder(d = 5.8, h = 1.0);
    }
    color([0.75, 0.75, 0.78]) for (x = [-1.27, 1.27]) translate([x, ir_inne + ir_l, 0]) rotate([-90, 0, 0]) cylinder(d = 0.5, h = 3, $fn = 8);
  }
  if (opp) translate([opp_pos[0], opp_pos[1], H]) rotate([-90, 0, 0]) en();
  else retning(a) translate([0, -rs(a), zs]) en();
}
module leder() { for (a = led_vinkler) led(a); if (led_opp) led(0, true); }
module mott_del() {
  translate([mott_x, -B/2 + vegg + 0.05, zs]) color([0.08, 0.08, 0.09]) {
    translate([-mott[0]/2, 0.0, -mott[2]/2]) cube([mott[0], mott[1], mott[2]]);
    rotate([90, 0, 0]) cylinder(d = 3.6, h = 0.01);
  }
}
module kort_del() {
  translate([0, kort_yc, kort_z]) {
    color(C3 ? [0.12, 0.18, 0.40] : [0.15, 0.35, 0.55]) translate([-bW/2, -bL/2, 0]) cube([bW, bL, bT]);
    color([0.75, 0.75, 0.78]) translate([-usb[0]/2, bL/2 - usb[1] + 1, usb_under ? -usb[2] : bT]) cube(usb);
    if (C3) {
      color([0.15, 0.15, 0.16]) translate([-2.5, -1, bT]) cube([5, 5, 0.9]);
      color([0.85, 0.85, 0.82]) translate([-5, -bL/2 + 0.5, bT]) cube([10, 2.5, 1]);
    } else
      color([0.7, 0.7, 0.72]) translate([-8, -bL/2 + 1, bT]) cube([16, 24, 3.2]);   // ESP-12-modulen
  }
  color([0.3, 0.5, 1.0]) translate([lys[0] - 0.5, lys[1] - 0.4, lys[2] - 0.5]) cube([1, 0.8, 0.5]);
}
module driver_del() {    // AO3400 og motstandene på et lite hullkort, flatt på gulvet foran kortet (til høyre)
  color([0.15, 0.35, 0.2]) translate([3, -20, bunn_t + 0.05]) cube([12, 7.5, 1.6]);
  color([0.1, 0.1, 0.1]) translate([7, -17.5, bunn_t + 1.65]) cube([3, 2.9, 1.1]);
}
module magnet_del() { if (magneter) color([0.6, 0.6, 0.62]) for (p = magnet_pos) translate([p[0], p[1], bunn_t - 2.0]) cylinder(d = 8, h = 2); }

module samlet(ex = 0) {
  color(c_bunn) translate([0, 0, -ex]) render() bunn();          // render(): forhåndsvisningen viser ellers delene feil
  color(c_topp) translate([0, 0, ex * 1.4]) render() topp();
  color(c_gull) translate([0, 0, ex * 1.6]) gull();
  color([0.85, 0.88, 0.95]) translate([0, 0, ex * 0.9]) lysleder();
  translate([0, 0, ex * 0.35]) { kort_del(); driver_del(); }
  translate([0, 0, ex * 0.5]) { leder(); if (mottaker) mott_del(); }
  translate([0, 0, -ex * 1.3]) magnet_del();
}

if (part == "bunn") bunn();
else if (part == "topp") translate([0, 0, H]) rotate([180, 0, 0]) topp();          // toppflaten ned
else if (part == "gull") translate([0, 0, H]) rotate([180, 0, 0]) gull();          // samme stilling som toppen
else if (part == "lysleder") translate([0, 0, H]) rotate([180, 0, 0]) lysleder();  // toppenden ned
else if (part == "eksplodert") samlet(16);
else if (part == "inni") { color(c_bunn) render() bunn(); kort_del(); driver_del(); leder(); if (mottaker) mott_del();
                           color([0.85, 0.88, 0.95]) lysleder(); magnet_del(); }
else if (part == "undersiden") color(c_bunn) render() bunn();
else if (part == "a_bunn") bunn();
else if (part == "a_topp") topp();
else if (part == "a_gull") gull();
else if (part == "a_lysleder") lysleder();
else if (part == "a_kort") kort_del();
else if (part == "a_led") leder();
else if (part == "a_mott") { if (mottaker) mott_del(); }
else if (part == "a_driver") driver_del();
else if (part == "a_magnet") magnet_del();
else samlet();
