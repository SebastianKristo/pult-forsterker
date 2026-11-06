// Skjold Kassett – NFC-kassettspiller og kassett (parametrisk OpenSCAD)
// Eget design i Skjolds formspråk. Inspirert av ideen i «ESPHome Cartridge Player» av The Stock Pot
// (CC BY-NC 4.0) – ingen geometri er kopiert. Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Bruk:  openscad -D 'part="spiller_topp"' -o spiller_topp.stl skjold_kassett.scad
// part:  spiller_topp | spiller_bunn | kassett_front | kassett_bak | lysleder | samlet | med_kassett | eksplodert | kassett_samlet | kassett_bakside

part = "samlet";
$fn = 64;

// ---------- kassett ----------
kW = 50;  kH = 70;  kT = 10;    // bredde, høyde, tykkelse (to halvdeler à 5 mm)
kR = 5;                         // hjørneradius
tagD = 26;  tagT = 0.8;         // NTAG215 25 mm rund brikke (+1 mm klaring)
lblW = 44;  lblH = 52; lblT = 0.4;  // etikettfelt foran (forsenket)
magD = 6.2; magT = 3.2;         // 6 × 3 mm neodym-magnet
pinD = 3;   pinH = 2.4;         // klikk-tapper mellom halvdelene

// ---------- spiller ----------
pW = 120; pD = 92; pH = 62;     // ytre mål
pR = 14;                        // myke hjørner (som Node/Touch)
wall = 2.4;
tilt = 12;                      // kassetten heller bakover mot deg
slotDepth = 34;                 // hvor dypt kassetten står i sporet
slotClr = 0.6;
ledW = 10.6; ledH = 3.4;        // WS2812-stripe 10 mm, 60 LED/m, rundt sporet
pnW = 42.7; pnH = 40.5; pnT = 5; // PN532 V3-modul (I²C)
espW = 18;  espL = 23.5;        // ESP32-S3 Zero
bzD = 12.2; bzH = 9.5;          // piezo/buzzer

c_top = [0.93,0.92,0.90];       // lokk: lys PETG
c_bot = [0.13,0.13,0.14];       // bunn: sort PETG
c_txt = [0.55,0.55,0.55];
c_k1  = [0.85,0.62,0.25];       // kassett, gull/sennep
c_k2  = [0.16,0.16,0.17];
c_lbl = [0.97,0.95,0.90];
c_led = [1.0,0.78,0.35];

module rbox(w,d,h,r){ hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y,0]) cylinder(r=r,h=h); }
module rbox_soft(w,d,h,r,t=3){ // avrundet topkant
  hull(){ for(x=[r,w-r],y=[r,d-r]) translate([x,y,0]) cylinder(r=r,h=h-t);
          for(x=[r,w-r],y=[r,d-r]) translate([x,y,h-t]) scale([1,1,t/r]) sphere(r=r); }
}

// ---------- kassett ----------
// Retro kompaktkassett i Skjold-form: to skall (1,2 mm hud, 1,6 mm vegg) med ribber i stedet for massiv plate.
// Bakre halvdel har spolevinduer og sentervindu; fremre halvdel har tannhjulsnavene som stikker gjennom vinduene,
// etikettfeltet og trapesen nederst. Begge printes med utsiden ned, uten støtte. z=0 er utsiden, z=kT/2 er skjøten.
skin = 1.2;  kWall = 1.6;  rib = 1.0;
reelX = [13, kW-13]; reelY = 50; reelD = 12.4; hubD = 7; hubTeeth = 6;
screws = [[4.6,4.6],[kW-4.6,4.6],[4.6,kH-4.6],[kW-4.6,kH-4.6]];
tagY = kH*0.42;   // brikken ligger rett bak PN532-antennen i spilleren
module hub2d(){ difference(){ circle(d=hubD); for(i=[0:hubTeeth-1]) rotate(i*360/hubTeeth) translate([hubD/2,0]) circle(d=1.6); circle(d=2.2); } }
module trapes2d(w0=40,w1=30,h=11){ polygon([[-w0/2,0],[w0/2,0],[w1/2,h],[-w1/2,h]]); }
module groove(h=0.4) translate([0,0,-0.01]) linear_extrude(h+0.01) children();

module kassett_halv(front=true){
  H = kT/2;
  difference(){
    union(){
      // skall: hud + yttervegg
      difference(){ rbox(kW,kH,H,kR); translate([kWall,kWall,skin]) rbox(kW-2*kWall,kH-2*kWall,H,kR-kWall); }
      // magnetklosse nederst (halve lomma i hver halvdel)
      translate([kW/2-5,0,0]) cube([10,magT+1.4,H]);
      // tapp-/skrueklosser i hjørnene
      for(p=screws) translate([p[0],p[1],0]) cylinder(d=pinD+3.2,h=H);
      if(front){
        // ribber: midtlinje og tverrbjelke (holder huden stiv under etiketten)
        translate([kW/2-rib/2,magT+1.4,0]) cube([rib,kH-magT-1.4-kWall,H]);
        translate([kWall,tagY-rib/2,0]) cube([kW-2*kWall,rib,H]);
        // tannhjulsnav som stikker gjennom spolevinduene i bakre halvdel
        for(x=reelX) translate([x,reelY,0]) linear_extrude(kT-0.3) hub2d();
      } else {
        // ring som holder NFC-brikken mot bakhuden
        translate([kW/2,tagY,0]) difference(){ cylinder(d=tagD+2*rib,h=skin+1.6); translate([0,0,skin]) cylinder(d=tagD,h=3); }
        // krage rundt vinduene + sentervindu
        for(x=reelX) translate([x,reelY,0]) cylinder(d=reelD+2*rib,h=H);
        translate([kW/2-5-rib,reelY-3.5-rib,0]) rbox(10+2*rib,7+2*rib,H,1.5+rib);
        // tverrbjelke under brikken
        translate([kWall,tagY-tagD/2-rib-3,0]) cube([kW-2*kWall,rib,H]);
      }
    }
    // magnetlomme (aksen langs y, sentrert i skjøten)
    translate([kW/2,-0.01,H]) rotate([-90,0,0]) cylinder(d=magD,h=magT+0.01);
    if(front){
      // tapper står på fremre; hull for etikettens plass markeres med en 0,2 mm linje (printes rett på platen)
      translate([(kW-lblW)/2+2,kH-lblH-2,0]) groove(0.2) difference(){ offset(r=2) square([lblW-4,lblH-4]); offset(r=1.4) square([lblW-4,lblH-4]); }
      // trapes nederst som på en ekte kassett, med to «styrehull» og SKJOLD
      translate([kW/2,0,0]) groove(0.4) difference(){ trapes2d(); offset(-0.8) trapes2d(); }
      for(x=[kW/2-13,kW/2+13]) translate([x,3.6,0]) groove(0.6) circle(d=2.6);
      translate([kW/2,6.2,0]) groove(0.4) text("SKJOLD",size=3.4,font="Liberation Sans:style=Bold",halign="center",spacing=1.25);
    } else {
      // spolevinduer og sentervindu tvers gjennom
      for(x=reelX) translate([x,reelY,-0.01]) cylinder(d=reelD,h=H+1);
      translate([kW/2-5,reelY-3.5,-0.01]) rbox(10,7,H+1,1.5);
      // hull til tappene (blinde – «skruene» vises som ringer på utsiden)
      for(p=screws) translate([p[0],p[1],H-pinH-0.3]) cylinder(d=pinD+0.15,h=pinH+0.31);
      for(p=screws) translate([p[0],p[1],0]) groove(0.4) difference(){ circle(d=4.2); circle(d=3); }
      translate([kW/2,10,0]) groove(0.4) difference(){ circle(d=4.2); circle(d=3); }
    }
  }
  if(front) for(p=screws) translate([p[0],p[1],H]) cylinder(d=pinD,h=pinH);
}
module kassett_samlet(lbl=true){
  // front-halvdel speilvendt oppå bakre, tapper inn
  color(c_k2) kassett_halv(false);
  color(c_k1) translate([0,0,kT]) mirror([0,0,1]) kassett_halv(true);
  if(lbl) color(c_lbl) translate([(kW-lblW)/2+0.4,kH-lblH-3.6,kT]) rbox(lblW-0.8,lblH-0.8,0.15,2);
}

// ---------- spiller ----------
slotW = kW+2*slotClr; slotT = kT+2*slotClr;
module slot_frame(){ // sporets koordinatsystem: på toppen, sentrert, hellende
  translate([pW/2,pD*0.42,pH]) rotate([tilt,0,0]) children();
}
module slot_cut(extra=0){
  slot_frame() translate([-slotW/2-extra,-slotT/2-extra,-slotDepth]) rbox(slotW+2*extra,slotT+2*extra,slotDepth+30,3+extra);
}
module spiller_topp(){
  difference(){
    rbox_soft(pW,pD,pH,pR,6);
    // hul innside
    translate([wall,wall,-0.01]) rbox(pW-2*wall,pD-2*wall,pH-wall,pR-wall);
    slot_cut();
    // LED-kanal rundt sporet (lyset slipper ut i en smal spalte)
    difference(){ slot_cut(ledH+1.2); slot_cut(1.2); }
    // USB-C bak
    translate([pW/2-5,pD-wall-1,10]) cube([10,wall+2,5]);
    // høyttalerhull for summer, venstre side
    for(i=[-1:1]) translate([-1,pD*0.6+i*4,22]) rotate([0,90,0]) cylinder(d=2,h=wall+2);
  }
  // innvendig sporlomme (vegg rundt kassetten)
  difference(){
    slot_frame() translate([-slotW/2-1.6,-slotT/2-1.6,-slotDepth-1.6]) rbox(slotW+3.2,slotT+3.2,slotDepth+1.6,4.6);
    slot_cut();
    // magnet i bunnen av sporet
    slot_frame() translate([0,0,-slotDepth-1.61]) cylinder(d=magD,h=magT);
  }
  // holder for PN532 bak sporet (antennen mot kassettens brikke) – klippet til innsiden av kassen
  intersection(){ translate([wall,wall,0]) rbox(pW-2*wall,pD-2*wall,pH-wall,pR-wall);
  slot_frame() translate([-pnW/2-1.5,slotT/2+1.6,-slotDepth+2]) difference(){
    cube([pnW+3,pnT+2.5,pnH+1]);
    translate([1.5,1,1]) cube([pnW,pnT,pnH+1]);
  } }
  // «SKJOLD» preget foran
  color(c_txt) translate([pW/2,-0.01,pH*0.32]) rotate([90,0,0]) linear_extrude(0.5) text("SKJOLD",size=6,font="Liberation Sans:style=Bold",halign="center",valign="center",spacing=1.3);
}
module lysleder(){ // gjennomskinnelig ramme som dekker LED-kanalen (print i natur/transparent PETG)
  color([1,0.9,0.7,0.6]) difference(){ slot_frame() translate([-slotW/2-ledH-1.2,-slotT/2-ledH-1.2,-1.2]) rbox(slotW+2*ledH+2.4,slotT+2*ledH+2.4,1.2,3+ledH); slot_cut(1.2); }
}
module spiller_bunn(){
  difference(){
    union(){
      rbox(pW-2*wall-0.4,pD-2*wall-0.4,2.4,pR-wall);
      // klikk-kanter
      translate([0,0,2.4]) difference(){ rbox(pW-2*wall-0.4,pD-2*wall-0.4,4,pR-wall); translate([1.6,1.6,-1]) rbox(pW-2*wall-3.6,pD-2*wall-3.6,6,pR-wall-1.6); }
    }
    for(x=[18,pW-2*wall-18]) translate([x,(pD-2*wall)/2,-0.01]) cylinder(d=8,h=1.2); // gummiføtter
  }
  // ESP32-S3 Zero-holder bak ved USB-C
  translate([(pW-2*wall)/2-espW/2-1.2,pD-2*wall-espL-4,2.4]) difference(){ cube([espW+2.4,espL+2,4]); translate([1.2,1.2,1.6]) cube([espW,espL+2,3]); }
  // summer-holder venstre
  translate([10,pD*0.6-wall,2.4]) difference(){ cylinder(d=bzD+2.4,h=6); translate([0,0,1.6]) cylinder(d=bzD,h=6); }
}
module spiller_samlet(){
  color(c_top) spiller_topp();
  color(c_bot) translate([wall+0.2,wall+0.2,-0.01]) spiller_bunn();
  lysleder();
}
module med_kassett(){
  spiller_samlet();
  slot_frame() translate([-kW/2,kT/2,-slotDepth+0.5]) rotate([90,0,0]) kassett_samlet();
}
module eksplodert(){
  color(c_top) translate([0,0,30]) spiller_topp();
  translate([0,0,40]) lysleder();
  color(c_bot) translate([wall+0.2,wall+0.2,-20]) spiller_bunn();
  slot_frame() translate([-kW/2,kT/2,60]) rotate([90,0,0]) { color(c_k2) kassett_halv(false); color(c_k1) translate([0,0,kT+14]) mirror([0,0,1]) kassett_halv(true); }
}

if(part=="spiller_topp") spiller_topp();
else if(part=="spiller_bunn") spiller_bunn();
else if(part=="lysleder") lysleder();
else if(part=="kassett_front") kassett_halv(true);
else if(part=="kassett_bak") kassett_halv(false);
else if(part=="kassett_samlet") kassett_samlet();
else if(part=="kassett_bakside") translate([0,kH,kT]) rotate([180,0,0]) kassett_samlet(); // baksiden med spolevinduene
else if(part=="med_kassett") med_kassett();
else if(part=="eksplodert") eksplodert();
else spiller_samlet();
