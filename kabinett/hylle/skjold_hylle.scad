// Skjold Kassetthylle – modul med 3 plasser for Skjold-kassetter (50 × 70 × 10 mm). Moduler skrus sammen side om side.
// Ta ut en kassett = den spilles. Sett den tilbake = stopp. Én RC522-leser bak hver plass, én WS2812 under hver plass.
// Kassettene står med forsiden ut (etiketten synes), lent 8° bakover mot bakplata. NFC-brikken (Ø25, 44 mm over
// kassettens underkant, 1,2 mm fra baksiden) havner rett foran leserens antenne gjennom 1,6 mm bakplate.
// part: modul | lokk | ende_esp | ende_blind | lysleder | samlet | eksplodert
// Lisens: CC BY-NC-SA 4.0
part = "samlet";
$fn = 48;

N = 3;                      // plasser per modul
pitch = 62;                 // avstand mellom plassene
kW = 50; kH = 70; kT = 10;  // kassetten
kl = 0.6;                   // klaring rundt kassetten
tilt = 8;                   // kassettene lener seg bakover
W = N * pitch;              // modulens bredde
D = 44;                     // dybde (uten lokk)
baseH = 16;                 // sokkel (lys og ledninger)
backH = 82;                 // bakplatens høyde over sokkelen
wall = 2.4;
bp = 1.6;                   // bakplate mellom brikke og leser
rcW = 40.5; rcH = 60.5; rcT = 9;   // RC522-kort med vinklede pinner (lomme bak hver plass)
tagH = 44;                  // brikkens senter over kassettens underkant
slotD = 18;                 // hvor dypt kassetten står i sporet
ledW = 10.5;                // WS2812-kort (enkelt-LED) under hver plass
c_lys = [0.93,0.92,0.90]; c_mork = [0.14,0.14,0.15]; c_kass = [0.85,0.62,0.25]; c_klar = [1,0.9,0.7,0.55];

module rbox(w,d,h,r){ hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y,0]) cylinder(r=r,h=h); }

// koordinater: x = bredde, y = dybde (0 = front), z = høyde. Bakplata står bak, lent tilt° bakover.
module bakplan(){ translate([0, D - wall - rcT - bp, baseH]) rotate([-tilt,0,0]) children(); }

module modul(){
  difference(){
    union(){
      // sokkel med avrundet front
      rbox(W, D, baseH, 4);
      // bakplate (lent)
      bakplan() translate([0, 0, -2]) cube([W, bp + rcT + wall, backH]);
      // sidevegger (skrues mot naboen) – trekant som støtter bakplata
      for (x = [0, W - wall]) hull(){
        translate([x, D - 14, baseH - 0.1]) cube([wall, 14, 1]);
        bakplan() translate([x - 0, 0, backH - 30]) cube([wall, bp + rcT + wall, 1]);
        translate([x, D - 26, baseH - 0.1]) cube([wall, 1, 1]);
      }
    }
    for (i = [0:N-1]) {
      cx = pitch * (i + 0.5);
      // spor for kassetten (lent som bakplata), med fas foran
      bakplan() translate([cx - kW/2 - kl, -kT - 2*kl, -slotD + 2]) cube([kW + 2*kl, kT + 2*kl + 0.01, slotD + 2]);
      translate([cx - kW/2 - kl - 1.5, 4, baseH - 1.2]) cube([kW + 2*kl + 3, D - 4 - rcT - bp - wall, 2]);
      // lomme for RC522 bak hver plass (åpen bakover, lokket dekker), antennen mot brikken
      bakplan() translate([cx - rcW/2, bp, tagH - slotD + 2 - rcH/2 + 12]) cube([rcW, rcT + wall + 1, rcH]);
      // LED-lomme og lysvindu foran under plassen
      translate([cx - ledW/2, 1.0, 3]) cube([ledW, 8, 9]);
      translate([cx - 14, -1, 4]) cube([28, 2.0, 7]);     // vindu for lysleder (klar PETG trykkes inn)
      // kabelkanal i sokkelen langs hele modulen
      translate([-1, 11, 3]) cube([W + 2, 9, 9]);
    }
    // bolter mellom moduler (M3 × 12 + mutter) og kabelhull gjennom sideveggene
    for (x = [-1, W - wall - 1], p = [[D - 8, baseH + 10], [D - 16, baseH + 46]])
      translate([x, p[0], p[1]]) rotate([0,90,0]) cylinder(d = 3.4, h = wall + 2);
    // nøkkelhull for veggfeste i bakplata (2 per modul)
    for (x = [W * 0.25, W * 0.75]) bakplan() translate([x, -1, backH - 16]) rotate([-90,0,0]) {
      cylinder(d = 8, h = bp + rcT + wall + 3);
      translate([0, 5, 0]) cylinder(d = 4.2, h = bp + rcT + wall + 3);
      translate([-2.1, 0, 0]) cube([4.2, 5, bp + rcT + wall + 3]);
    }
    // gummiføtter under
    for (x = [12, W - 12], y = [8, D - 8]) translate([x, y, -0.01]) cylinder(d = 10.4, h = 1.2);
  }
}

// lokk som dekker leserne bak (skrus med M2 i bakplata)
module lokk(){ difference(){ rbox(W - 2, backH - 6, 1.6, 3); for (x = [10, W - 12], z = [8, backH - 16]) translate([x, z, -1]) cylinder(d = 2.4, h = 4); } }
module lysleder(){ for (i = [0:N-1]) translate([pitch * (i + 0.5) - 13.8, 0, 0]) cube([27.6, 1.8, 6.8]); }

// endestykker: ESP32-C3 SuperMini med USB-C ut på siden, og en blind ende
module ende(esp = true){
  difference(){
    union(){ rbox(28, D, baseH + 20, 4); }
    translate([2.4, 2.4, 2.4]) cube([28, D - 4.8, baseH + 20]);
    for (p = [[D - 8, baseH + 10]]) translate([20, p[0], p[1]]) rotate([0,90,0]) cylinder(d = 3.4, h = 20);
    translate([20, 11, 3]) cube([10, 9, 9]);                         // kabelkanal inn i modulen
    if (esp) translate([-1, D/2 - 5, 8]) cube([4, 10, 4.6]);         // USB-C ut på siden
  }
  if (esp) translate([6, D/2 - 9.5, 2.3]) difference(){ cube([20, 19, 3]); translate([1, 1.2, 1.2]) cube([18, 16.6, 3]); }   // vugge
}

module kassett(){ color(c_kass) rbox(kW, kT, kH, 4); }

module samlet(ex = 0){
  for (m = [0, 1]) translate([m * (W + ex * 0.6), 0, 0]) {
    color(c_lys) modul();
    color(c_klar) translate([0, -0.6 - ex * 0.4, 4.1]) lysleder();
    color(c_mork) bakplan() translate([1, bp + rcT + wall + 1.7 + ex * 0.8, 3]) rotate([90,0,0]) lokk();
    for (i = [0:N-1]) if (!(m == 0 && i == 1))   // én plass tom: den kassetten spilles
      bakplan() translate([pitch * (i + 0.5) - kW/2, -kT - kl, -slotD + 2.6 + ex]) rotate([0,0,0]) kassett();
  }
  color(c_mork) translate([-28 - ex * 0.6, 0, 0]) ende(true);
  color(c_mork) translate([2 * W + ex * 1.2 + 28, D, 0]) rotate([0,0,180]) ende(false);
}

module a_grupper(g){   // for 3D-siden: samlet modell delt i fargegrupper (montert stilling)
  for (m = [0, 1]) translate([m * W, 0, 0]) {
    if (g == "lys") modul();
    if (g == "klar") translate([0, -0.6, 4.1]) lysleder();
    if (g == "mork") bakplan() translate([1, bp + rcT + wall + 1.7, 3]) rotate([90,0,0]) lokk();
    if (g == "kass") for (i = [0:N-1]) if (!(m == 0 && i == 1)) bakplan() translate([pitch * (i + 0.5) - kW/2, -kT - kl, -slotD + 2.6]) rbox(kW, kT, kH, 4);
  }
  if (g == "mork") { translate([-28, 0, 0]) ende(true); translate([2 * W + 28, D, 0]) rotate([0,0,180]) ende(false); }
}
if (part == "a_lys") a_grupper("lys"); else if (part == "a_mork") a_grupper("mork");
else if (part == "a_kass") a_grupper("kass"); else if (part == "a_klar") a_grupper("klar");
else if (part == "modul") modul();
else if (part == "lokk") lokk();
else if (part == "lysleder") rotate([90,0,0]) lysleder();
else if (part == "ende_esp") ende(true);
else if (part == "ende_blind") mirror([1,0,0]) ende(false);
else if (part == "eksplodert") samlet(20);
else samlet();
