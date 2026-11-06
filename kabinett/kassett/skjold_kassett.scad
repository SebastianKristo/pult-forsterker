// Skjold Kassett – NFC-kassettspiller og kassett (parametrisk OpenSCAD)
// Eget design i Skjolds formspråk. Inspirert av ideen i «ESPHome Cartridge Player» av The Stock Pot
// (CC BY-NC 4.0) – ingen geometri er kopiert. Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Bruk:  openscad -D 'part="spiller_topp"' -o spiller_topp.stl skjold_kassett.scad
// part:  spiller_topp | spiller_bunn | kassett_front | kassett_bak | lysleder | samlet | med_kassett | eksplodert | kassett_samlet | kassett_bakside | snitt
// STL-ene for spiller_topp og lysleder eksporteres i utskriftsretning (toppen ned).

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
slotDepth = 38;                 // hvor dypt kassetten står i sporet (NFC-brikken havner foran PN532-antennen)
slotClr = 0.6;
ledW = 10.6; ledH = 3.4;        // WS2812-stripe 10 mm (60 LED/m) – står på høykant i en kanal rundt sporet
lidT = 2.4;                     // lokkets topptykkelse (6 × 0,4 mm linjer)
ch = 2.4;                       // 45°-fas på toppkanten (printes med toppen ned uten støtte, ingen elefantfot)
tD = 15;                        // dybden på LED-kanalen foran og på sidene (målt fra toppen)
pnW = 42.7; pnH = 40.5; pcbT = 1.6; // PN532 V3-modul (I²C), skyves inn i skinner bak sporet
espW = 18;  espL = 23.5; espT = 1.0; // Waveshare ESP32-S3 Zero, USB-C bak
bzD = 12.2; bzH = 9.5;          // passiv piezo-summer 12 mm
insD = 4.0; insL = 6.5;         // hull for M3 × 5,7 mm innpressmutter (heat-set insert)
bossD = 8;                      // skruetårn i hjørnene
footD = 10.4;                   // selvklebende gummiføtter Ø 10 mm

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
// Sporet er definert i et skrått koordinatsystem (slot_frame), men alt som må printes pent er klippet med vannrette
// plan: toppen er flat og flukter med lyslederen, sporbunnen og LED-kanalens bunn er vannrette broer (printes
// uten støtte når lokket ligger med toppen ned på platen).
slotW = kW+2*slotClr; slotT = kT+2*slotClr;
eps = 0.01;
bx = pR - ((pR-wall) - bossD/2 + 0.4)*0.7071;            // skruetårn: litt inn i hjørneveggen
bosses = [[bx,bx],[pW-bx,bx],[bx,pD-bx],[pW-bx,pD-bx]];
zf = pH - (kT/2)*sin(tilt) - slotDepth*cos(tilt);        // sporbunn (vannrett) – kassettens nedre forkant hviler her
ym = pD*0.42 + slotDepth*sin(tilt);                      // magnetens senter (rett under kassettens magnet)
usbZ = 2.4 + 1.2 + espT + 1.63;                          // midten av USB-C-kontakten på ESP32-S3 Zero
backY = slotT/2 + 1.6;                                   // bakre yttervegg av sporlomma (i sporets koordinater)

module slot_frame(){ translate([pW/2,pD*0.42,pH]) rotate([tilt,0,0]) children(); }
module S2(o){ offset(r=1.2+o) square([slotW-2.4,slotT-2.4],center=true); } // sporets omriss, forskjøvet o mm (lite hjørne, kassetten har skarpe kanter i tykkelsen)
module sring(o1,o2,z0,h){ slot_frame() translate([0,0,z0]) linear_extrude(h) difference(){ S2(o2); if(o1>-50) S2(o1); } }
module zslab(z0,z1){ translate([-50,-50,z0]) cube([pW+100,pD+100,z1-z0]); }
module back_region(){ slot_frame() translate([-80,backY-eps,-120]) cube([160,60,240]); }
module slot_cut(){ intersection(){ sring(-99,0,-slotDepth-15,80); zslab(zf,pH+30); } }

module skall(){
  difference(){
    hull(){ rbox(pW,pD,pH-ch,pR); translate([ch,ch,0]) rbox(pW-2*ch,pD-2*ch,pH,pR-ch); }
    translate([wall,wall,-1]) rbox(pW-2*wall,pD-2*wall,pH-lidT+1,pR-wall);
  }
}
module hylle(){ // skrå hylle innvendig nederst: bunnen presses mot den – gir en labyrint i skjøten (lystett) og flukter bunnen
  difference(){
    translate([wall-eps,wall-eps,2.4]) rbox(pW-2*wall+2*eps,pD-2*wall+2*eps,1.6,pR-wall);
    hull(){ translate([wall+1.6,wall+1.6,2.4-eps]) rbox(pW-2*wall-3.2,pD-2*wall-3.2,eps,pR-wall-1.6);
            translate([wall,wall,4.0]) rbox(pW-2*wall,pD-2*wall,eps,pR-wall); }
    translate([pW/2-12,pD-wall-4,2]) cube([24,4+eps,3]);   // plass til ESP-vuggen ved USB-C
  }
}
module lomme(){ // sporlomme med vannrett bunn
  intersection(){ sring(-99,1.6,-slotDepth-20,80); zslab(zf-1.6,pH); }
  // magnettårn under sporbunnen (magneten trykkes inn nedenfra, 0,6 mm hud mot kassetten)
  translate([pW/2,ym,zf-4]) cylinder(d=magD+2.4,h=4);
}
module kanal(){ // LED-kanal: dyp foran og på sidene (stripa står på høykant mot lommeveggen), grunn bak (plass til PN532)
  difference(){
    union(){
      intersection(){ sring(5.0,6.2,-40,60); zslab(pH-tD-1.2,pH); }
      intersection(){ sring(1.6-eps,6.2,-40,60); zslab(pH-tD-1.2,pH-tD); }
    }
    back_region();
  }
  intersection(){
    back_region();
    union(){
      intersection(){ sring(5.0,6.2,-40,60); zslab(pH-6.2,pH); }
      intersection(){ sring(1.6-eps,6.2,-40,60); zslab(pH-6.2,pH-5); }
    }
  }
  // avsats som lyslederen hviler på
  intersection(){ sring(4.2,5.0+eps,-40,60); zslab(pH-lidT-2.3,pH-lidT-1.5); }
}
module skinne(side){ // skinne for PN532 (kortet skyves inn nedenfra, stopper øverst); 45°-fas øverst så den printes uten støtte
  d = 0.8 + pcbT + 1.4;                                  // dybde fra lommeveggen
  slot_frame() translate([side>0 ? pnW/2-1.5 : -pnW/2-1.6, backY-eps, 0])
    difference(){
      rotate([90,0,90]) linear_extrude(3.1) polygon([[0,-56],[d,-56],[d,-6-d],[0,-6]]);
      translate([side>0 ? -1 : 1.6, 0.8-0.1, -60]) cube([2.5, pcbT+0.2, 60-11]);  // spor for kretskortet
    }
}
module spiller_topp(){
  difference(){
    union(){
      skall(); hylle(); lomme(); kanal(); skinne(1); skinne(-1);
      for(p=bosses) translate([p[0],p[1],2.4]) cylinder(d=bossD,h=pH-lidT-2.4+eps);
    }
    slot_cut();
    intersection(){ sring(1.6,5.0,-40,60); zslab(pH-lidT-1,pH+1); }                // åpning for lyslederen
    translate([pW/2,ym,zf-4-eps]) cylinder(d=magD,h=3.4+eps);                        // magnetlomme
    slot_frame() translate([slotW/2+3.3,0,-30]) cylinder(d=3.2,h=29);                // ledninger fra LED-stripa
    for(p=bosses) translate([p[0],p[1],2.4-eps]) cylinder(d=insD,h=insL);            // innpressmuttere
    translate([pW/2,pD-wall-1,usbZ]) rotate([-90,0,0]) linear_extrude(wall+2)        // USB-C (plass til pluggen)
      offset(r=2) square([12.5-4,7-4],center=true);
    translate([pW/2,0.6,pH*0.34]) rotate([90,0,0]) linear_extrude(1)                 // SKJOLD gravert foran
      text("SKJOLD",size=6,font="Liberation Sans:style=Bold",halign="center",valign="center",spacing=1.3);
  }
}
module lysleder(){ // flukter med toppen; printes med toppen ned i klar/natur PETG
  intersection(){ sring(1.6+0.15,5.0-0.15,-40,60); zslab(pH-lidT-1.5,pH); }
}
module spiller_bunn(){ // i verdenskoordinater (ligger inne i lokkets åpning, 0,15 mm klaring)
  ox = wall+0.15; bw = pW-2*ox; bd = pD-2*ox; rB = pR-wall-0.15;
  yE = pD-wall-0.3-espL;                                 // ESP-ens fremkant
  difference(){
    union(){
      hull(){ translate([ox+0.4,ox+0.4,0]) rbox(bw-0.8,bd-0.8,0.4+eps,rB-0.4); translate([ox,ox,0.4]) rbox(bw,bd,2.0,rB); }
      // vugge for ESP32-S3 Zero: to skinner under, tre vegger og små klikk-lepper
      translate([pW/2-espW/2-1.35,yE-1.2,2.4-eps]) difference(){
        cube([espW+2.7,espL+1.2,1.2+espT+0.8+eps]);
        translate([1.35,1.2,1.2]) cube([espW+0.3,espL+1,5]);
        translate([1.35+1.6,1.2,-1]) cube([espW+0.3-3.2,espL+1,5]);
      }
      for(s=[0,1]) translate([s ? pW/2+espW/2+0.15 : pW/2-espW/2-0.15,yE+espL*0.3,2.4+1.2+espT+0.05+0.55])
        rotate([-90,0,0]) linear_extrude(espL*0.4) polygon(s ? [[0.3,0],[-0.45,0.55],[0.3,0.55]] : [[-0.3,0],[0.45,0.55],[-0.3,0.55]]);
      // ring for summeren (lydhullet ned mot hullene i bunnen)
      translate([26,30,2.4-eps]) difference(){ cylinder(d=bzD+2.4,h=4); translate([0,0,-1]) cylinder(d=bzD+0.1,h=6); }
      // kabelbuer
      for(p=[[pW/2,58],[pW/2+26,50],[34,50]]) translate([p[0]-4,p[1]-2,2.4-eps]) difference(){ cube([8,4,4]); translate([1.5,-1,-1]) cube([5,6,3.5]); }
    }
    for(p=bosses) translate([p[0],p[1],-eps]) { cylinder(d=3.4,h=4); cylinder(d1=6.6,d2=3.4,h=1.6); }   // M3 senkehode
    for(x=[ox+16,pW-ox-16], y=[ox+14,pD-ox-14]) translate([x,y,-eps]) cylinder(d=footD,h=0.6);      // gummiføtter
    for(a=[0:60:300]) translate([26+3*cos(a),30+3*sin(a),-1]) cylinder(d=1.5,h=5);                   // lydhull
    translate([26,30,-1]) cylinder(d=1.5,h=5);
  }
}
// utskriftsretning: lokk og lysleder ligger med toppen ned (pen, teksturert toppflate, ingen støtte)
module topp_print(){ translate([0,pD,pH]) rotate([180,0,0]) spiller_topp(); }
module lysleder_print(){ translate([0,pD,pH]) rotate([180,0,0]) lysleder(); }

module spiller_samlet(){
  color(c_top) spiller_topp();
  color(c_bot) spiller_bunn();
  color([1,0.9,0.7,0.6]) translate([0,0,-0.05]) render() lysleder();   // -0,05 bare for å unngå flimmer i forhåndsvisning
}
module med_kassett(){
  spiller_samlet();
  slot_frame() translate([-kW/2,kT/2,-slotDepth]) rotate([90,0,0]) kassett_samlet();
}
module eksplodert(){
  color(c_top) translate([0,0,30]) spiller_topp();
  color([1,0.9,0.7,0.6]) translate([0,0,50]) render() lysleder();
  color(c_bot) translate([0,0,-20]) spiller_bunn();
  slot_frame() translate([-kW/2,kT/2,70]) rotate([90,0,0]) { color(c_k2) kassett_halv(false); color(c_k1) translate([0,0,kT+14]) mirror([0,0,1]) kassett_halv(true); }
}
module snitt(){ // vertikalt snitt gjennom sporet (for kontroll)
  intersection(){ spiller_samlet(); translate([-10,-10,-10]) cube([pW/2+10,pD+20,pH+20]); }
}

if(part=="spiller_topp") topp_print();
else if(part=="spiller_bunn") spiller_bunn();
else if(part=="lysleder") lysleder_print();
else if(part=="kassett_front") kassett_halv(true);
else if(part=="kassett_bak") kassett_halv(false);
else if(part=="kassett_samlet") kassett_samlet();
else if(part=="kassett_bakside") translate([0,kH,kT]) rotate([180,0,0]) kassett_samlet(); // baksiden med spolevinduene
else if(part=="med_kassett") med_kassett();
else if(part=="eksplodert") eksplodert();
else if(part=="snitt") snitt();
else spiller_samlet();
