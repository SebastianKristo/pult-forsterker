// Skjold Hjul S – stativ for M5Stack Dial (rund 1,28″ skjerm i en dreiering, Ø ca. 45 mm, ca. 32 mm høy).
// To varianter: bordstativ (hellende 20° mot deg, med plass til LiPo og USB-C-kabel bak) og veggplate (magnetfeste).
// part: stativ | bunnlokk | veggplate | samlet | eksplodert
// Mål M5Dial med skyvelære før print og juster dialD/dialH. Lisens: CC BY-NC-SA 4.0
part = "samlet";
$fn = 96;

dialD = 45.2;  dialH = 32.5;   // M5Dial (v1.1): Ø 45 mm hus, ca. 32,3 mm høy inkl. ring
kl = 0.4;                      // klaring rundt
lip = 9;                       // hvor dypt M5Dial sitter i koppen
tilt = 20;                     // helling mot brukeren
baseD = 78; baseH = 22;        // bordstativets fot
wall = 2.4;
usbW = 12; usbH = 7;           // åpning for USB-C-pluggen (bak/under på M5Dial)
battW = 36; battL = 52; battT = 6.5;   // valgfri LiPo 503450 i foten
magD = 10.2; magT = 2.2;       // 10 × 2 mm magneter (veggplate)
c_lys = [0.93,0.92,0.90]; c_mork = [0.14,0.14,0.15]; c_gull = [0.85,0.62,0.25];

module kopp(){ // koppen M5Dial står i, i sitt eget koordinatsystem (z = 0 er bunnen av koppen)
  difference(){
    cylinder(d = dialD + 2*kl + 2*wall, h = lip + wall);
    translate([0, 0, wall]) cylinder(d = dialD + 2*kl, h = lip + 1);
    translate([0, 0, lip + wall - 1.2]) cylinder(d1 = dialD + 2*kl, d2 = dialD + 2*kl + 2.4, h = 1.21);  // fas
    translate([-usbW/2, -(dialD/2 + wall + 2), -1]) cube([usbW, dialD/2 + 6, usbH + wall]);             // USB-C og kabel
    translate([0, 0, -1]) cylinder(d = 14, h = wall + 2);                                                  // kabelhull i bunnen
  }
}
module koppform(){ cylinder(d = dialD + 2*kl + 2*wall, h = lip + wall); }

module plassering(){ translate([0, 6, baseH - 4]) rotate([tilt, 0, 0]) children(); }

module stativ(){
  difference(){
    union(){
      hull(){
        cylinder(d = baseD, h = 4);
        plassering() koppform();
        translate([0, 0, 4]) cylinder(d = baseD - 8, h = 6);
      }
    }
    // koppen
    plassering() translate([0, 0, wall]) cylinder(d = dialD + 2*kl, h = 60);
    plassering() translate([0, 0, lip + wall - 1.2]) cylinder(d1 = dialD + 2*kl, d2 = dialD + 2*kl + 2.4, h = 1.21);
    plassering() translate([-usbW/2, -(dialD/2 + kl + 1), -6]) cube([usbW, 14, usbH + 6 + wall]);
    // hulrom i foten for batteri og kabel (bunnlokket lukker)
    translate([-battW/2 - 1, -battL/2 - 1, -0.01]) cube([battW + 2, battL + 2, battT + 2.6]);
    // kabelkanal fra koppen ned i foten og ut bak
    plassering() translate([0, 0, -20]) cylinder(d = 12, h = 22);
    translate([-5, baseD/2 - 14, -0.01]) cube([10, 20, 6]);
    // skruehull for bunnlokket (M2 selvgjengende)
    for (a = [45, 135, 225, 315]) rotate([0, 0, a]) translate([baseD/2 - 7, 0, -0.01]) cylinder(d = 1.8, h = 8);
  }
}
module bunnlokk(){
  difference(){
    cylinder(d = baseD - 0.4, h = 1.6);
    for (a = [45, 135, 225, 315]) rotate([0, 0, a]) translate([baseD/2 - 7, 0, -1]) cylinder(d = 2.4, h = 4);
    for (a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([baseD/2 - 14, 0, 0.8]) cylinder(d = 10.4, h = 1);  // gummiføtter
  }
}
module veggplate(){  // M5Dial klikkes i koppen, platen henger på to skruer eller limes; magneter i bakkant
  difference(){
    union(){ hull(){ cylinder(d = dialD + 2*kl + 2*wall + 14, h = 3); } translate([0, 0, 3]) kopp(); }
    for (a = [90, 270]) rotate([0, 0, a]) translate([(dialD + 14)/2 + 1, 0, -1]) cylinder(d = 4.2, h = 6);
    for (a = [0, 180]) rotate([0, 0, a]) translate([(dialD + 14)/2 + 1, 0, -0.01]) cylinder(d = magD, h = magT);
  }
}
module dial(){ // M5Dial (forenklet) for bildene
  color(c_mork) cylinder(d = dialD, h = dialH - 6);
  color(c_gull) translate([0, 0, dialH - 8]) difference(){ cylinder(d = dialD, h = 8); translate([0,0,-1]) cylinder(d = 36, h = 10); }
  color([0.05,0.05,0.06]) translate([0, 0, dialH - 6]) cylinder(d = 34, h = 5.6);
  color([0.95,0.75,0.35]) translate([0, 0, dialH - 0.39]) difference(){ cylinder(d = 32, h = 0.4); cylinder(d = 28, h = 1); }
}
module samlet(ex = 0){
  color(c_lys) stativ();
  color(c_mork) translate([0, 0, -1.6 - ex]) bunnlokk();
  plassering() translate([0, 0, wall + ex * 1.5]) dial();
}

if (part == "a_stativ") stativ();
else if (part == "a_lokk") translate([0, 0, -1.6]) bunnlokk();
else if (part == "a_dial") plassering() translate([0, 0, wall]) { cylinder(d = dialD, h = dialH - 6); translate([0, 0, dialH - 6]) cylinder(d = 34, h = 5.6); }
else if (part == "a_ring") plassering() translate([0, 0, wall + dialH - 8]) difference(){ cylinder(d = dialD, h = 8); translate([0,0,-1]) cylinder(d = 36, h = 10); }
else if (part == "stativ") stativ();
else if (part == "bunnlokk") bunnlokk();
else if (part == "veggplate") veggplate();
else if (part == "eksplodert") samlet(25);
else samlet();
