// Skjold Hjul – fjernkontroll med dreieknapp og fire favorittknapper (parametrisk OpenSCAD)
// Eget design i Skjolds formspråk: lav, rund «puck», gullknott i midten, fire knapper i en bue foran.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Bruk:  openscad -D 'part="topp"' -o topp.stl skjold_hjul.scad
// part:  topp | bunn | knott | knapp | lysleder | samlet | eksplodert | ovenfra
use <../fonter/Inter-Bold.otf>     // SKJOLD-logoen: Inter (ligger i repoet, ren J)
use <../fonter/Inter-Regular.otf>

part = "samlet";
$fn = 96;

// ---------- mål ----------
D = 92;            // ytre diameter
H = 24;            // total høyde (topp + bunn)
botH = 9;          // bunnens høyde
wall = 2.2;
topT = 2.0;        // tykkelse på toppflaten
edgeR = 4;         // avrundet toppkant

knobD = 46;  knobH = 15;   // knott (aluminiumsfarget/gull PETG), sitter på EC11-akselen
shaftD = 6.1; shaftFlat = 4.6; shaftL = 12;   // EC11 D-aksel (6 mm, flat 4.5 mm)
ec11W = 12.6; ec11H = 7.2;  ec11Bush = 7.2;  // EC11 hus og M7-gjennomføring

btnD = 11; btnClr = 0.5;   // knappehetter
btnH = 4.2;
btnR = 36.5;               // radius til knappene
btnAng = [-40, -13.3, 13.3, 40];   // vinkler rundt «fronten» (−Y)
tactW = 12.2; tactH = 3.6; // 12 × 12 mm taktbryter (stamme 3.6 mm over kortet)

ledD = 5;                  // lysleder bak knotten (WS2812 5050 under)
usbW = 9.6; usbH = 3.8;    // USB-C (TP4056-kort) bak
battW = 36; battL = 52; battT = 6.5;   // LiPo 1000 mAh (503450)
footD = 10.2; footT = 1.2; // gummiføtter
screwR = 39;               // M2-skruer topp↔bunn

c_top = [0.93,0.92,0.90];
c_bot = [0.13,0.13,0.14];
c_knob = [0.85,0.62,0.25];
c_btn = [0.20,0.20,0.21];
c_txt = [0.55,0.55,0.55];
c_led = [1.0,0.78,0.35];

module soft_disc(d,h,r){ // sylinder med avrundet toppkant
  hull(){ cylinder(d=d,h=h-r); translate([0,0,h-r]) rotate_extrude() translate([d/2-r,0]) circle(r=r); }
}

module topp(){
  difference(){
    soft_disc(D, H-botH, edgeR);
    translate([0,0,-0.01]) cylinder(d=D-2*wall, h=H-botH-topT);                      // hulrom
    translate([0,0,-1]) cylinder(d=ec11Bush+0.6, h=H);                                  // EC11-gjennomføring
    translate([0,0,H-botH-0.6]) cylinder(d=knobD+2, h=1);                               // fals rundt knotten
    for(a=btnAng) rotate([0,0,a]) translate([0,-btnR,-1]) cylinder(d=btnD+btnClr*2, h=H); // knappehull
    translate([0,knobD/2+5,-1]) cylinder(d=ledD+0.3, h=H);                              // lysleder
  }
  // EC11-holder: firkantlomme rundt huset
  translate([0,0,H-botH-topT-ec11H]) difference(){
    translate([-ec11W/2-1.6,-ec11W/2-1.6,0]) cube([ec11W+3.2,ec11W+3.2,ec11H]);
    translate([-ec11W/2,-ec11W/2,-0.1]) cube([ec11W,ec11W,ec11H+0.2]);
  }
  // førere for knappehettene
  for(a=btnAng) rotate([0,0,a]) translate([0,-btnR,H-botH-topT-3]) difference(){
    cylinder(d=btnD+btnClr*2+2.4, h=3); translate([0,0,-0.1]) cylinder(d=btnD+btnClr*2, h=3.2);
  }
  // skruestolper
  for(a=[45,135,225,315]) rotate([0,0,a]) translate([screwR-3,0,0]) difference(){
    cylinder(d=6,h=H-botH-topT); translate([0,0,-0.1]) cylinder(d=1.7,h=8);
  }
  // prikker 1–4 ved knappene (preget)
  color(c_txt) for(i=[0:3]) rotate([0,0,btnAng[i]]) translate([0,-(btnR-btnD/2-2.6),H-botH-0.01])
    for(j=[0:i]) translate([(j-i/2)*1.9,0,0]) cylinder(d=1.1,h=0.4,$fn=16);
}

module bunn(){
  difference(){
    union(){
      cylinder(d=D, h=botH);
      translate([0,0,botH-0.01]) difference(){ cylinder(d=D-2*wall-0.4, h=3); cylinder(d=D-2*wall-3.6, h=7, center=true); } // leppe inn i toppen
    }
    translate([0,0,1.6]) cylinder(d=D-2*wall, h=botH);                                   // innvendig
    for(a=[45,135,225,315]) rotate([0,0,a]) translate([screwR-3,0,-0.1]) {               // M2×16, forsenket
      cylinder(d=2.3,h=botH+4); cylinder(d=4.2,h=1.4);
    }
    for(a=[0,90,180,270]) rotate([0,0,a+22.5]) translate([D/2-14,0,-0.1]) cylinder(d=footD,h=footT); // føtter
    translate([0,D/2-wall/2,1.6+usbH/2+0.6]) cube([usbW,wall*4,usbH],center=true);      // USB-C bak
    translate([0,0,-0.1]) linear_extrude(0.5) mirror([1,0,0])
      text("SKJOLD HJUL",size=3.99,font="Inter:style=Bold",halign="center",valign="center",spacing=1.2);
  }
  for(a=[45,135,225,315]) rotate([0,0,a]) translate([screwR-3,0,0]) difference(){       // skruestolper
    cylinder(d=6,h=botH); translate([0,0,-0.1]) cylinder(d=2.3,h=botH+1); translate([0,0,-0.1]) cylinder(d=4.2,h=1.4);
  }
  // batterilomme
  translate([-battW/2-1.6,-battL/2-4,1.6]) difference(){
    cube([battW+3.2,battL+3.2,battT]); translate([1.6,1.6,0]) cube([battW,battL,battT+1]);
    translate([battW/2-4,battL,0]) cube([11.2,4,battT+1]);   // kabelutgang
  }
  // holder for TP4056-kortet ved USB-hullet
  translate([0,D/2-wall-14,1.6]) for(x=[-9.5,9.5]) translate([x,0,0]) cube([1.6,26,2.4],center=true);
}

module knott(){
  difference(){
    union(){
      soft_disc(knobD, knobH, 3);
      // riflet skjørt nederst
      for(a=[0:7.5:359]) rotate([0,0,a]) translate([knobD/2-0.6,0,0]) cylinder(d=1.6,h=knobH*0.55,$fn=12);
    }
    translate([0,0,knobH-0.8]) cylinder(d=knobD-10, h=2);                             // grunn skål på toppen
    translate([0,0,-0.01]) difference(){ cylinder(d=shaftD+0.2, h=shaftL); translate([shaftFlat-shaftD/2+0.1,-5,-1]) cube([10,10,shaftL+2]); }
    translate([0,0,-0.01]) difference(){ cylinder(d=knobD-6, h=3.6); cylinder(d=shaftD+5, h=3.6); } // letter knotten
  }
  // markør
  color(c_bot) translate([0,-(knobD/2-6),knobH-0.81]) cylinder(d=2.2,h=0.6,$fn=24);
}

module knapp(){ // knappehette: krage under, så den ikke faller ut
  cylinder(d=btnD, h=btnH);
  cylinder(d=btnD+2, h=0.9);
  translate([0,0,btnH-0.01]) scale([1,1,0.18]) sphere(d=btnD-0.6);
}

module lysleder(){ cylinder(d=ledD, h=H-botH+0.4-1.6); translate([0,0,0]) cylinder(d=ledD+1.6,h=0.8); }

module samlet(ex=0){
  color(c_bot) translate([0,0,-ex]) bunn();
  color(c_top) translate([0,0,botH+ex*0.6]) topp();
  color(c_knob) translate([0,0,H+0.4+ex*1.6]) knott();
  for(a=btnAng) rotate([0,0,a]) color(c_btn) translate([0,-btnR,H-1.6-0.9+ex*1.2]) knapp();
  color(c_led) translate([0,knobD/2+5,botH+1.6+ex*0.9]) lysleder();
}

if (part == "topp") rotate([180,0,0]) topp();
else if (part == "bunn") bunn();
else if (part == "knott") rotate([180,0,0]) translate([0,0,-knobH]) knott();
else if (part == "knapp") knapp();
else if (part == "lysleder") lysleder();
else if (part == "eksplodert") samlet(18);
else if (part == "ovenfra") samlet();
else samlet();
