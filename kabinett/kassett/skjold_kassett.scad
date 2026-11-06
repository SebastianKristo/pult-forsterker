// Skjold Kassett – NFC-kassettspiller og kassett (parametrisk OpenSCAD)
// Eget design i Skjolds formspråk. Inspirert av ideen i «ESPHome Cartridge Player» av The Stock Pot
// (CC BY-NC 4.0) – ingen geometri er kopiert. Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Bruk:  openscad -D 'part="spiller_topp"' -o spiller_topp.stl skjold_kassett.scad
// part:  spiller_topp | spiller_bunn | kassett_front | kassett_bak | lysleder | samlet | med_kassett | eksplodert | kassett_samlet

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
module kassett_halv(front=true){
  difference(){
    rbox(kW,kH,kT/2,kR);
    // brikkelomme i bakre halvdel (innside)
    if(!front) translate([kW/2,kH*0.42,kT/2-tagT]) cylinder(d=tagD,h=tagT+0.01);
    // etikettfelt foran (utside)
    if(front) translate([(kW-lblW)/2,kH-lblH-4,-0.01]) rbox(lblW,lblH,lblT+0.01,2);
    // magnetlomme nederst (i begge, halv dybde)
    translate([kW/2,0,kT/2]) rotate([-90,0,0]) translate([0,0,-0.01]) cylinder(d=magD,h=magT+0.01);
    // grep-spor øverst
    translate([kW/2,kH+4,front?-0.01:kT/2-1.2]) scale([1,0.35,1]) cylinder(r=12,h=1.21);
    // hull til tapper (i bakre)
    if(!front) for(p=[[6,6],[kW-6,6],[6,kH-6],[kW-6,kH-6]]) translate([p[0],p[1],kT/2-pinH-0.3]) cylinder(d=pinD+0.25,h=pinH+0.31);
  }
  if(front) for(p=[[6,6],[kW-6,6],[6,kH-6],[kW-6,kH-6]]) translate([p[0],p[1],kT/2]) cylinder(d=pinD,h=pinH);
  // «SKJOLD» preget nederst foran
  if(front) color(c_txt) translate([kW/2,7,0]) mirror([0,0,1]) linear_extrude(0.4) text("SKJOLD",size=3.6,font="Liberation Sans:style=Bold",halign="center",spacing=1.25);
}
module kassett_samlet(lbl=true){
  // front-halvdel speilvendt oppå bakre, tapper inn
  color(c_k2) kassett_halv(false);
  color(c_k1) translate([0,0,kT]) mirror([0,0,1]) kassett_halv(true);
  if(lbl) color(c_lbl) translate([(kW-lblW)/2+0.4,kH-lblH-3.6,kT-0.4]) rbox(lblW-0.8,lblH-0.8,0.38,2);
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
else if(part=="med_kassett") med_kassett();
else if(part=="eksplodert") eksplodert();
else spiller_samlet();
