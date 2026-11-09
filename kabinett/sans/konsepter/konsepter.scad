// Skjold Sans – formkonsepter (bare utsiden, for å velge retning). Alle har plass til samme innmat:
// D1 mini (26 × 35 × 11 mm med komponenter), AM312 PIR, lyskort og et eget sensorkammer nederst med spalter.
// Koordinater: x mot høyre, z opp, forsiden mot −y, veggen/baksiden i +y.
//   fyr     – høyt, slankt tårn (44 × 44 × 128) for hylle eller vegg; PIR øverst som «lykta», ringspalter nede
//   linse   – rund skive Ø84 med hvelvet front og gullring; PIR i midten, spalter i nedre del av kanten
//   hjorne  – hjørneenhet (80 × 80 × 92) for takhjørnet; buet front ser hele rommet, spalter i bunnen
//   tavle   – liggende panel med skjerm (118 × 64 × 26): 0,96″ OLED, PIR, riflet nedre felt som er luftspalter
//   drape   – dråpe med spissen opp (70 × 102 × 28): sensorkammer i den runde bunnen, varmen ut ved spissen
// Delene: <navn>_kropp (lys), <navn>_gull (gull), <navn>_detalj (PIR-kuppel, skjerm, lysvindu).

part = "fyr_kropp";
$fn = 96;

module F() { multmatrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) children(); }   // 2D (x, z) ekstrudert langs y
module pir_kuppel(d = 12, h = 3.3) { scale([1, h / (d / 2), 1]) sphere(d = d); }
module spalte_y(x, z, l, b = 1.6, h = 10) { translate([x - b/2, -1, z]) cube([b, l, h]); }

// ---------- 1. Fyr ----------
fyrB = 44; fyrH = 128; fyrR = 10;
module fyr_2d(o = 0) { offset(r = fyrR + o) offset(delta = -fyrR) square(fyrB, center = true); }
module fyr_kropp() {
  difference() {
    union() {
      hull() { linear_extrude(0.01) fyr_2d(-1.5); translate([0, 0, 1.5]) linear_extrude(fyrH - 9) fyr_2d(0); }
      translate([0, 0, fyrH - 8]) hull() { linear_extrude(0.01) fyr_2d(0); translate([0, 0, 8 - 2]) linear_extrude(2) fyr_2d(-3); }   // toppen trappes inn
    }
    translate([0, 0, 2]) linear_extrude(fyrH - 4) fyr_2d(-2);
    for (z = [40 : 9 : 94]) translate([0, 0, z]) linear_extrude(1.2) difference() { fyr_2d(1); fyr_2d(-0.6); }   // fine riller
    for (a = [0 : 12 : 359]) rotate([0, 0, a]) translate([18, -0.8, 8]) cube([12, 1.6, 20]);              // ringspalter (kammeret)
    translate([0, -fyrB/2 - 1, 100]) rotate([-90, 0, 0]) cylinder(d = 12.4, h = 4);                                 // PIR
    translate([0, -fyrB/2 - 1, 86]) rotate([-90, 0, 0]) cylinder(d = 3.2, h = 4, $fn = 24);                         // lys
    translate([0, 0, fyrH - 18]) linear_extrude(2.5) difference() { fyr_2d(1); fyr_2d(-0.6); }                      // spor for gullbåndet
  }
}
module fyr_gull() { translate([0, 0, fyrH - 18]) linear_extrude(2.5) difference() { fyr_2d(0); fyr_2d(-0.6); } }
module fyr_detalj() {
  translate([0, -fyrB/2 + 0.6, 100]) pir_kuppel();
  translate([0, -fyrB/2 + 0.3, 86]) rotate([90, 0, 0]) cylinder(d = 3.2, h = 0.4, $fn = 24);
}

// ---------- 2. Linse ----------
liD = 84; liT = 22; liHv = 8;     // diameter, sylinderdel, hvelving foran
module linse_kropp() {
  rk = (pow((liD - 6)/2, 2) + liHv * liHv) / (2 * liHv);   // hvelvingens kuleradius
  difference() {
    union() {
      translate([0, liT, 0]) rotate([90, 0, 0]) cylinder(d = liD, h = liT);
      intersection() {   // hvelvet front
        translate([0, 0.01, 0]) rotate([90, 0, 0]) cylinder(d = liD - 6, h = liHv + 0.02);
        translate([0, rk - liHv, 0]) sphere(r = rk, $fn = 200);
      }
    }
    translate([0, liT + 1, 0]) rotate([90, 0, 0]) cylinder(d = liD - 4, h = liT - 1);
    intersection() {   // hul hvelving
      translate([0, rk - liHv, 0]) sphere(r = rk - 2, $fn = 200);
      translate([0, 2.5, 0]) rotate([90, 0, 0]) cylinder(d = liD - 10, h = liHv + 3);
    }
    for (a = [25 : 8 : 155]) rotate([0, a, 0]) translate([liD/2 - 3, 4, -0.8]) cube([6, liT - 8, 1.6]);    // spalter nede i kanten
    for (a = [45 : 10 : 135]) rotate([0, -a, 0]) translate([liD/2 - 3, 4, -0.8]) cube([6, liT - 8, 1.6]);  // oppe (varmen ut)
    translate([0, -liHv - 1, 0]) rotate([-90, 0, 0]) cylinder(d = 12.4, h = 12);
    translate([0, -liHv - 1, 18]) rotate([-90, 0, 0]) cylinder(d = 3.2, h = 12, $fn = 24);
    translate([0, 0.6, 0]) rotate([90, 0, 0]) difference() { cylinder(d = liD - 1.6, h = 1); cylinder(d = liD - 4, h = 1); }   // spor for gullringen
  }
}
module linse_gull() { translate([0, 0.6, 0]) rotate([90, 0, 0]) difference() { cylinder(d = liD - 1.6, h = 0.6); cylinder(d = liD - 4, h = 0.6); } }
module linse_detalj() {
  translate([0, -liHv + 0.6, 0]) pir_kuppel();
  translate([0, -liHv * 0.82, 18]) rotate([90, 0, 0]) cylinder(d = 3.2, h = 0.4, $fn = 24);
}

// ---------- 3. Hjørne ----------
hjL = 80; hjH = 92; hjBue = 26;   // benlengde langs veggene, høyde, hvor mye fronten buer ut fra korden
hjA = hjL / 2 + hjBue / sqrt(2);  // frontens toppunkt (x = y = hjA før rotasjon)
module hjorne_form(o = 0) {       // sett ovenfra: hjørnet i (0, 0), veggene langs +x og +y, buen ut mot (1, 1)
  cL = hjL * sqrt(2); R = (pow(cL / 2, 2) + hjBue * hjBue) / (2 * hjBue);
  offset(delta = o) offset(r = 4) offset(delta = -4) union() {
    polygon([[0, 0], [hjL, 0], [0, hjL]]);
    intersection() {
      translate([hjL / 2, hjL / 2] - (R - hjBue) * [1, 1] / sqrt(2)) circle(r = R, $fn = 300);
      polygon([[hjL, 0], [2 * hjL, hjL], [hjL, 2 * hjL], [0, hjL]]);
    }
  }
}
module hjorne_plass() { rotate([0, 0, -135]) children(); }   // fronten mot −y, hjørnet (veggene) bak
module hjorne_akse(p, z) { translate([p, p, z]) rotate([0, 0, 45]) rotate([0, 90, 0]) children(); }   // akse ut gjennom fronten
module hjorne_kropp() {
  hjorne_plass() difference() {
    hull() { linear_extrude(0.01) hjorne_form(-1.5); translate([0, 0, 1.5]) linear_extrude(hjH - 3) hjorne_form(0); translate([0, 0, hjH - 0.01]) linear_extrude(0.01) hjorne_form(-1.5); }
    translate([0, 0, 2]) linear_extrude(hjH - 4) hjorne_form(-2);
    for (i = [-6 : 6]) translate([hjL / 2 + i * 4.2 / sqrt(2), hjL / 2 - i * 4.2 / sqrt(2), -1]) rotate([0, 0, -45]) translate([-0.8, -2, 0]) cube([1.6, 30, 4]);         // spalter i bunnen
    for (i = [-5 : 5]) translate([hjL / 2 + i * 4.2 / sqrt(2), hjL / 2 - i * 4.2 / sqrt(2), hjH - 3]) rotate([0, 0, -45]) translate([-0.8, -2, 0]) cube([1.6, 30, 4]);  // og i toppen (varmen ut)
    hjorne_akse(hjA, 60) translate([0, 0, -8]) cylinder(d = 12.4, h = 12);    // PIR
    hjorne_akse(hjA, 44) translate([0, 0, -8]) cylinder(d = 3.2, h = 12, $fn = 24);
    translate([0, 0, 22]) linear_extrude(2.5) difference() { hjorne_form(1); hjorne_form(-0.6); }   // spor for gullbåndet
  }
}
module hjorne_gull() { hjorne_plass() translate([0, 0, 22]) linear_extrude(2.5) difference() { hjorne_form(0); hjorne_form(-0.6); } }
module hjorne_detalj() {
  hjorne_plass() {
    hjorne_akse(hjA - 0.6, 60) scale([1, 1, 3.3 / 6]) sphere(d = 12);
    hjorne_akse(hjA - 0.3, 44) cylinder(d = 3.2, h = 0.4, $fn = 24);
  }
}

// ---------- 4. Tavle (med skjerm) ----------
taB = 118; taH = 64; taD = 26; taR = 12;
module tavle_2d(o = 0) { offset(r = taR + o) offset(delta = -taR) square([taB, taH], center = true); }
module tavle_kropp() {
  difference() {
    hull() { F() linear_extrude(0.01) tavle_2d(-1.5); F() translate([0, 0, 1.5]) linear_extrude(taD - 1.5) tavle_2d(0); }
    F() translate([0, 0, 2]) linear_extrude(taD) tavle_2d(-2);
    // riflet nedre felt: spor tvers over fronten, hvert tredje er en gjennomgående spalte
    for (i = [0 : 7]) translate([-taB/2 + 10, -1, -taH/2 + 5 + i * 2.6]) cube([taB - 20, (i % 2 == 0) ? 3.2 : 1.6, 1.2]);
    translate([-taB/2 + 22, -1, 8]) cube([26, 3.2, 15]);                       // skjermvindu (0,96″ OLED)
    translate([30, -1, 15]) rotate([-90, 0, 0]) cylinder(d = 12.4, h = 4);     // PIR
    translate([46, -1, 15]) rotate([-90, 0, 0]) cylinder(d = 3.2, h = 4, $fn = 24);
    translate([10, -0.01, 2]) cube([1.2, 0.61, 27]);                          // spor for gullstreken
  }
}
module tavle_gull() { translate([10, -0.01, 2]) cube([1.2, 0.6, 27]); }
module tavle_detalj() {
  translate([30, 0.6, 15]) pir_kuppel();
  translate([46, 0.3, 15]) rotate([90, 0, 0]) cylinder(d = 3.2, h = 0.4, $fn = 24);
}

module tavle_skjerm() { translate([-taB/2 + 22, 0.6, 8]) cube([26, 0.4, 15]); }   // OLED-glasset

// ---------- 5. Dråpe ----------
drR = 35; drH = 102; drD = 28;
module drape_2d(o = 0) {
  offset(delta = o) offset(r = 3) offset(delta = -3) hull() { translate([0, drR]) circle(r = drR, $fn = 200); translate([0, drH]) circle(r = 0.5); }
}
module drape_kropp() {
  difference() {
    hull() { F() linear_extrude(0.01) drape_2d(-2); F() translate([0, 0, 2]) linear_extrude(drD - 2) drape_2d(0); }
    F() translate([0, 0, 2]) linear_extrude(drD) drape_2d(-2);
    for (x = [-21 : 3 : 21]) translate([x - 0.8, 4, -1]) cube([1.6, drD - 8, drR - sqrt(drR * drR - x * x) + 4]);   // spalter i bunnen, rett ned
    for (s = [-1, 1], i = [0 : 3]) let(z = 78 + i * 4) translate([s * (drR * (drH - z) / (drH - drR) * 0.92), 4, z]) cube([4, drD - 8, 1.6], center = false);
    translate([0, -1, 44]) rotate([-90, 0, 0]) cylinder(d = 12.4, h = 4);     // PIR
    translate([0, -1, 60]) rotate([-90, 0, 0]) cylinder(d = 3.2, h = 4, $fn = 24);
    F() translate([0, 0, -0.01]) linear_extrude(0.61) difference() { drape_2d(-4); drape_2d(-5); }   // spor for gullkanten
  }
}
module drape_gull() { F() translate([0, 0, -0.01]) linear_extrude(0.6) difference() { drape_2d(-4); drape_2d(-5); } }
module drape_detalj() {
  translate([0, 0.6, 44]) pir_kuppel();
  translate([0, 0.3, 60]) rotate([90, 0, 0]) cylinder(d = 3.2, h = 0.4, $fn = 24);
}

if (part == "fyr_kropp") fyr_kropp(); else if (part == "fyr_gull") fyr_gull(); else if (part == "fyr_detalj") fyr_detalj();
else if (part == "linse_kropp") linse_kropp(); else if (part == "linse_gull") linse_gull(); else if (part == "linse_detalj") linse_detalj();
else if (part == "hjorne_kropp") hjorne_kropp(); else if (part == "hjorne_gull") hjorne_gull(); else if (part == "hjorne_detalj") hjorne_detalj();
else if (part == "tavle_kropp") tavle_kropp(); else if (part == "tavle_gull") tavle_gull(); else if (part == "tavle_detalj") tavle_detalj(); else if (part == "tavle_skjerm") tavle_skjerm();
else if (part == "drape_kropp") drape_kropp(); else if (part == "drape_gull") drape_gull(); else if (part == "drape_detalj") drape_detalj();
