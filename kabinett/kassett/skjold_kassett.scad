// Skjold Kassett – NFC-kassettspiller og kassett (parametrisk OpenSCAD)
// Eget design i Skjolds formspråk. Inspirert av ideen i «ESPHome Cartridge Player» av The Stock Pot
// (CC BY-NC 4.0) – ingen geometri er kopiert. Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Bruk:  openscad -D 'part="spiller_topp"' -o spiller_topp.stl skjold_kassett.scad
// part:  spiller_topp | spiller_bunn | vindu | lysleder | trinse | motortrinse | kassett_front | kassett_bak | spole
//        samlet | med_kassett | forfra | eksplodert | kassett_samlet | kassett_bakside | snitt
// STL-ene eksporteres i utskriftsretning (lokk og lysleder med toppen ned, spole med baksiden ned).
//
// Spolene: kassetten har to frie spoler (hver med en 3 × 2 mm diametral magnet i navet) som synes gjennom vinduet i
// fronten av spilleren. Bak sporet sitter to trinser med 6 × 3 mm diametrale magneter, drevet av én N20-girmotor via
// en O-ring (alle tre trinsene i samme reim → begge spolene går samme vei, som på en ekte kassett). Magnetene drar
// spolene rundt gjennom 1,6 mm plast – ingen tannhjul som må treffe når kassetten settes inn.

part = "samlet";
$fn = 64;

// ---------- kassett ----------
kW = 50;  kH = 70;  kT = 10;    // bredde, høyde, tykkelse (to halvdeler à 5 mm)
kR = 5;                         // hjørneradius
tagD = 26;  tagT = 0.8;         // NTAG215 25 mm rund brikke (+1 mm klaring)
lblW = 44;  lblH = 52; lblT = 0.4;  // etikettfelt foran (forsenket linje) – samme mål som etikettarket
magD = 6.2; magT = 3.2;         // 6 × 3 mm neodym-magnet (holder kassetten nede i sporet)
pinD = 3;   pinH = 2.4;         // klikk-tapper mellom halvdelene

// ---------- spiller ----------
pW = 120; pD = 62; pH = 72;     // ytre mål – grunnere (var 92): ESP-en og summeren ligger ved siden av drivverket
pR = 14;                        // myke hjørner (som Node/Touch)
wall = 2.4;
tilt = 0;                       // kassetten står loddrett bak vinduet (som en kassettspiller fra 80-tallet)
slotDepth = 60;                 // kassetten står 60 mm ned – 10 mm stikker opp til å ta tak i
slotClr = 0.6;
lidT = 2.4;                     // lokkets topptykkelse (6 × 0,4 mm linjer)
ch = 2.4;                       // 45°-fas på toppkanten (printes med toppen ned uten støtte, ingen elefantfot)
pnW = 42.7; pnH = 40.5; pcbT = 1.6; // PN532 V3-modul (I²C), skyves inn i skinner bak sporet
espW = 18;  espL = 23.5; espT = 1.0; // Waveshare ESP32-S3 Zero, USB-C bak
espX = pW - 30;                 // ESP-en bak til høyre (ved siden av N20-motoren), USB-C ut bak
bzX = 30; bzY = 44;             // summeren bak til venstre
bzD = 12.2; bzH = 9.5;          // passiv piezo-summer 12 mm
insD = 4.0; insL = 6.5;         // hull for M3 × 5,7 mm innpressmutter (heat-set insert)
bossD = 8;                      // skruetårn i hjørnene
footD = 10.4;                   // selvklebende gummiføtter Ø 10 mm
// vindu og drivverk
winW = 44;  winR = 3;           // synlig vindusåpning i fronten
paneW = 49; paneT = 1.0;        // klar rute (1 mm akryl eller PETG), skyves opp i spor innenfor frontveggen
dmD = 6.2;  dmT = 3.2;          // 6 × 3 mm diametral magnet i trinsene
smD = 3.2;  smT = 2.2;          // 3 × 2 mm diametral magnet i spolenavet
pinA = 2.0;                     // Ø 2 mm stålpinne (aksel) for trinsene
oringCS = 2.0;                  // O-ring 22 × 2 mm (NBR) som reim
n20W = 12.2; n20H = 10.2; n20L = 25; // N20-girmotor (12 × 10 mm, med girkasse), 3 mm D-aksel

c_top = [0.93,0.92,0.90];       // lokk: lys PETG
c_bot = [0.13,0.13,0.14];       // bunn: sort PETG
c_txt = [0.55,0.55,0.55];
c_k1  = [0.85,0.62,0.25];       // kassett, gull/sennep
c_k2  = [0.16,0.16,0.17];
c_lbl = [0.97,0.95,0.90];
c_led = [1.0,0.78,0.35];
c_glass = [0.75,0.88,0.95,0.35];
c_reel = [0.97,0.95,0.90];

module rbox(w,d,h,r){ hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y,0]) cylinder(r=r,h=h); }
module rbox_soft(w,d,h,r,t=3){ // avrundet topkant
  hull(){ for(x=[r,w-r],y=[r,d-r]) translate([x,y,0]) cylinder(r=r,h=h-t);
          for(x=[r,w-r],y=[r,d-r]) translate([x,y,h-t]) scale([1,1,t/r]) sphere(r=r); }
}

// ---------- kassett ----------
// Retro kompaktkassett i Skjold-form: to skall (1,2 mm hud, 1,6 mm vegg) med ribber i stedet for massiv plate.
// Spolevinduene går gjennom begge halvdelene nederst, og de to spolene (egne deler) ligger fritt mellom halvdelene:
// navet stikker ut i begge vinduene, og en flens inni (større enn vinduet) holder spolen på plass – ingen aksel.
// Etikettfeltet sitter over vinduene. Begge halvdelene printes med utsiden ned, uten støtte.
// z=0 er utsiden, z=kT/2 er skjøten.
skin = 1.2;  kWall = 1.6;  rib = 1.0;
reelX = [13, kW-13]; reelY = 10.2; reelD = 12.4;          // spolevinduer (Ø 12,4)
spD = 11.6; spFl = 14.2; spFlT = 1.2;                  // spole: nav Ø 11,6, flens Ø 14,2
screws = [[4.4,4.4],[kW-4.4,4.4],[4.4,kH-4.4],[kW-4.4,kH-4.4]];
tagY = 44;        // brikken ligger rett foran PN532-antennen i spilleren (øverste del av kortet)
module trapes2d(w0=40,w1=30,h=11){ polygon([[-w0/2,0],[w0/2,0],[w1/2,h],[-w1/2,h]]); }
module groove(h=0.4) translate([0,0,-0.01]) linear_extrude(h+0.01) children();

module kassett_halv(front=true){
  H = kT/2;
  difference(){
    union(){
      // skall: hud + yttervegg
      difference(){ rbox(kW,kH,H,kR); translate([kWall,kWall,skin]) rbox(kW-2*kWall,kH-2*kWall,H,kR-kWall); }
      // magnetklosse nederst (halve lomma i hver halvdel), mellom spolene
      translate([kW/2-5,0,0]) cube([10,magT+1.4,H]);
      // tapp-/skrueklosser i hjørnene
      for(p=screws) translate([p[0],p[1],0]) cylinder(d=pinD+3.2,h=H);
      if(front){
        // ribber: midtlinje over vinduene og tverrbjelke (holder huden stiv under etiketten)
        translate([kW/2-rib/2,reelY+spFl/2+0.6,0]) cube([rib,kH-reelY-spFl/2-0.6-kWall,H]);
        translate([kWall,tagY-rib/2,0]) cube([kW-2*kWall,rib,H]);
        // krage rundt vinduene: holder spolens flens (0,6 mm klaring)
        for(x=reelX) translate([x,reelY,0]) cylinder(d=reelD+2*rib,h=skin+2.6);
      } else {
        // ring som holder NFC-brikken mot bakhuden
        translate([kW/2,tagY,0]) difference(){ cylinder(d=tagD+2*rib,h=skin+1.6); translate([0,0,skin]) cylinder(d=tagD,h=3); }
        // tverrbjelke mellom brikken og spolene
        translate([kWall,tagY-tagD/2-rib-3,0]) cube([kW-2*kWall,rib,H]);
      }
    }
    // magnetlomme (aksen langs y, sentrert i skjøten)
    translate([kW/2,-0.01,H]) rotate([-90,0,0]) cylinder(d=magD,h=magT+0.01);
    // spolevinduer tvers gjennom begge halvdelene
    for(x=reelX) translate([x,reelY,-0.01]) cylinder(d=reelD,h=H+1);
    if(front){
      // etikettfeltet markeres med en 0,2 mm linje (printes rett på platen)
      translate([(kW-lblW)/2+2,kH-lblH-2,0]) groove(0.2) difference(){ offset(r=2) square([lblW-4,lblH-4]); offset(r=1.4) square([lblW-4,lblH-4]); }
      // vinduskant rundt spolene som på en ekte kassett
      translate([kW/2,reelY,0]) groove(0.4) difference(){ offset(r=2) square([kW-2*kR-4,reelD-5.6],center=true); offset(r=1.4) square([kW-2*kR-4,reelD-5.6],center=true); }
    } else {
      // hull til tappene (blinde – «skruene» vises som ringer på utsiden)
      for(p=screws) translate([p[0],p[1],H-pinH-0.3]) cylinder(d=pinD+0.15,h=pinH+0.31);
      for(p=screws) translate([p[0],p[1],0]) groove(0.4) difference(){ circle(d=4.2); circle(d=3); }
      translate([kW/2,reelY+1.5,0]) groove(0.4) difference(){ circle(d=4.2); circle(d=3); }
      // trapes og SKJOLD bak, over spolene
      translate([kW/2,reelY+spFl/2+1,0]) groove(0.4) difference(){ trapes2d(34,26,8); offset(-0.8) trapes2d(34,26,8); }
      translate([kW/2,reelY+spFl/2+3.2,0]) mirror([1,0,0]) groove(0.4) text("SKJOLD",size=3.0,font="Liberation Sans:style=Bold",halign="center",spacing=1.2);
    }
  }
  if(front) for(p=screws) translate([p[0],p[1],H]) cylinder(d=pinD,h=pinH);
}
// Spolen ligger med baksiden (magneten) ned på platen: nav, 45°-kjegle opp til flensen, flens, nav videre opp.
// Lengde kT-0,6, så den aldri stikker ut av kassetten. Seks hakk i navet på forsiden, som en ekte kassettspole.
spL = kT - 0.6; spZ0 = 0.3;                              // spolens plass i kassetten (z fra baksiden)
spCone = (spFl-spD)/2;                                    // 45°-kjegle
spFlZ = kT/2 - 0.6 - spZ0;                                // flensens underkant (målt fra spolens bakside)
module spole(){
  difference(){
    union(){
      cylinder(d=spD,h=spL);
      translate([0,0,spFlZ-spCone]) cylinder(d1=spD,d2=spFl,h=spCone);
      translate([0,0,spFlZ]) cylinder(d=spFl,h=spFlT);
    }
    translate([0,0,-0.01]) cylinder(d=smD,h=smT+0.01);                     // magnetlomme (bak)
    for(i=[0:5]) rotate(i*60) translate([spD/2-1.6,0,spL-1.2]) cylinder(d=1.8,h=2);   // hakk foran
    translate([0,0,spL-0.8]) cylinder(d=4.2,h=1);
  }
}
module kassett_samlet(lbl=true, spoler=true){
  // front-halvdel speilvendt oppå bakre, tapper inn
  color(c_k2) kassett_halv(false);
  color(c_k1) translate([0,0,kT]) mirror([0,0,1]) kassett_halv(true);
  if(lbl) color(c_lbl) translate([(kW-lblW)/2+0.4,kH-lblH-1.6,kT]) rbox(lblW-0.8,lblH-0.8,0.15,2);
  if(spoler) for(x=reelX) color(c_reel) translate([x,reelY,spZ0]) spole();
}

// ---------- spiller ----------
// Kassetten står loddrett rett bak frontveggen. Et stort vindu i fronten (klar PETG-rute) viser spolene og etiketten,
// som på en kassettspiller fra 80-tallet. Bak sporet sitter PN532 (øverst, foran NFC-brikken) og drivverket for spolene
// (nederst, på bunnplata). Alt som må printes pent er vannrette broer eller 45°-faser (lokket printes med toppen ned).
slotW = kW+2*slotClr; slotT = kT+2*slotClr;
eps = 0.01;
slotY = wall + 1.6 + slotT/2;                            // sporets senter: lommeveggen foran er frontveggen + 1,6 mm
bx = pR - ((pR-wall) - bossD/2 + 0.4)*0.7071;            // skruetårn: litt inn i hjørneveggen
bosses = [[bx,bx],[pW-bx,bx],[bx,pD-bx],[pW-bx,pD-bx]];
zf = pH - slotDepth;                                     // sporbunn – kassetten hviler her
ym = slotY;                                              // holdemagneten (rett under kassettens magnet)
usbZ = 2.4 + 1.2 + espT + 1.63;                          // midten av USB-C-kontakten på ESP32-S3 Zero
yBack = slotY + slotT/2 + 1.6;                           // baksiden av sporlomma
// vindu
winZ0 = zf + 1.5; winZ1 = pH - 9;                        // synlig åpning
paneZ0 = 2.6; paneZ1 = pH - 6.5;                         // ruten (står på bunnplata, skyves opp i sporet)
chY0 = wall; chY1 = wall + paneT + 0.2;                  // sporet for ruten innenfor frontveggen
// PN532: antennesiden mot sporet, toppen rett under lokket
pnZ1 = pH - lidT - 0.3; pnZ0 = pnZ1 - pnH; pnY0 = yBack + 0.8;
// drivverk (trinsene står på bunnplata): senter bak spolene
dZ = zf + reelY;                                         // spolenes senter i høyden
dX = [pW/2 - (kW/2 - reelX[0]), pW/2 + (reelX[1] - kW/2)];
trY0 = yBack + 0.2;                                      // trinsenes forside (magneten) – 0,2 mm bak lommeveggen
trL = 8; trD = 10; trG = 7.6;                            // trinse: lengde, flens-Ø, spor-Ø (O-ring 2 mm)
mZ = dZ - 10;                                            // motoraksen (under trinsene)
mpD = 7; mpG = 5;                                        // motortrinse
beltY = trY0 + trL - 4.8;                                // reimplanet (midt i sporet på trinsene)
pilY0 = trY0 + trL + 0.3;                                // akselstolpene bak trinsene
// LED-list bak sporet (5 LED rett, under lyslederen i toppen)
ledL = 84; ledY0 = pnY0 + pcbT + 4.6; ledWd = 10.6;

module slot_frame(){ translate([pW/2,slotY,pH]) rotate([tilt,0,0]) children(); }
module S2(o){ offset(r=1.2+o) square([slotW-2.4,slotT-2.4],center=true); } // sporets omriss, forskjøvet o mm
module sring(o1,o2,z0,h){ slot_frame() translate([0,0,z0]) linear_extrude(h) difference(){ S2(o2); if(o1>-50) S2(o1); } }
module zslab(z0,z1){ translate([-50,-50,z0]) cube([pW+100,pD+100,z1-z0]); }
module slot_cut(){ intersection(){ sring(-99,0,-slotDepth-15,80); zslab(zf,pH+30); } }
module win2d(){ translate([pW/2,(winZ0+winZ1)/2]) offset(r=winR) square([winW-2*winR,winZ1-winZ0-2*winR],center=true); }

module skall(){
  difference(){
    hull(){ rbox(pW,pD,pH-ch,pR); translate([ch,ch,0]) rbox(pW-2*ch,pD-2*ch,pH,pR-ch); }
    translate([wall,wall,-1]) rbox(pW-2*wall,pD-2*wall,pH-lidT+1,pR-wall);
  }
}
module hylle(){ // skrå hylle innvendig nederst: bunnen presses mot den – labyrint i skjøten (lystett), bunnen flukter
  difference(){
    translate([wall-eps,wall-eps,2.4]) rbox(pW-2*wall+2*eps,pD-2*wall+2*eps,1.6,pR-wall);
    hull(){ translate([wall+1.6,wall+1.6,2.4-eps]) rbox(pW-2*wall-3.2,pD-2*wall-3.2,eps,pR-wall-1.6);
            translate([wall,wall,4.0]) rbox(pW-2*wall,pD-2*wall,eps,pR-wall); }
    translate([espX-12,pD-wall-4,2]) cube([24,4+eps,3]);   // plass til ESP-vuggen ved USB-C
  }
}
module lomme(){ // sporlomme med vannrett bunn
  intersection(){ sring(-99,1.6,-slotDepth-20,80); zslab(zf-1.6,pH); }
  translate([pW/2,ym,zf-4]) cylinder(d=magD+2.4,h=4);    // magnettårn under sporbunnen
}
module skinne(side){ // skinne for PN532: kortet skyves inn nedenfra og stopper mot lokket; 45°-fas nederst
  d = 0.8 + pcbT + 1.4; x0 = side>0 ? pW/2+pnW/2-1.5 : pW/2-pnW/2-1.6;
  translate([x0, yBack-eps, 0]) difference(){
    rotate([90,0,90]) linear_extrude(3.1) polygon([[0,pnZ0-4],[d,pnZ0-4+d],[d,pH],[0,pH]]);
    translate([side>0 ? -1 : 1.6, 0.8-0.1, pnZ0-10]) cube([2.5, pcbT+0.2, pnZ1-pnZ0+10.1]);  // spor for kretskortet
  }
}
module ledkanal(){ // kasse for LED-lista: gulv 1,2 mm (bro når lokket printes opp-ned), avsats for lyslederen
  translate([pW/2-ledL/2-1.2, ledY0-1.2, pH-9]) difference(){
    cube([ledL+2.4, ledWd+2.4, 9]);
    translate([1.2,1.2,1.2]) cube([ledL, ledWd, 9]);
  }
  for(y=[ledY0-eps, ledY0+ledWd-0.8+eps]) translate([pW/2-ledL/2, y, pH-lidT-0.8]) cube([ledL, 0.8, 0.8]);   // avsats
}
module spiller_topp(){
  difference(){
    union(){
      skall(); hylle(); lomme(); skinne(1); skinne(-1); ledkanal();
      for(p=bosses) translate([p[0],p[1],2.4]) cylinder(d=bossD,h=pH-lidT-2.4+eps);
    }
    slot_cut();
    // vindu i fronten + spor for ruten (fra undersiden og opp)
    translate([0,-1,0]) rotate([-90,0,0]) mirror([0,1,0]) linear_extrude(wall+1.6) win2d();
    translate([pW/2-paneW/2-0.25, chY0-eps, -1]) cube([paneW+0.5, chY1-chY0, paneZ1+0.2+1]);
    // åpning for lyslederen i toppen
    translate([pW/2-ledL/2, ledY0, pH-lidT-1]) cube([ledL, ledWd, lidT+2]);
    translate([pW/2+ledL/2-6, ledY0+ledWd/2, pH-12]) cylinder(d=3.2,h=4);                // ledninger ned fra LED-lista
    translate([pW/2,ym,zf-4-eps]) cylinder(d=magD,h=3.4+eps);                         // holdemagnet
    for(p=bosses) translate([p[0],p[1],2.4-eps]) cylinder(d=insD,h=insL);            // innpressmuttere
    translate([espX,pD-wall-1,usbZ]) rotate([-90,0,0]) linear_extrude(wall+2)        // USB-C (plass til pluggen)
      offset(r=2) square([12.5-4,7-4],center=true);
    translate([pW/2,0.6,(2.4+winZ0)/2+0.5]) rotate([90,0,0]) linear_extrude(1)       // SKJOLD gravert under vinduet
      text("SKJOLD",size=4.6,font="Liberation Sans:style=Bold",halign="center",valign="center",spacing=1.3);
  }
}
module vindu(){ // klar rute (PETG), 1,5 mm – printes flatt, 100 % fyll; skyves opp i sporet før bunnen skrus på
  translate([pW/2-paneW/2, chY0+0.05, paneZ0]) rotate([90,0,0]) translate([0,0,-paneT])
    linear_extrude(paneT) translate([1,1]) offset(r=1) square([paneW-2, paneZ1-paneZ0-2]);
}
module vindu_print(){ translate([1,1,0]) linear_extrude(paneT) offset(r=1) square([paneW-2, paneZ1-paneZ0-2]); }
module lysleder(){ // rett list over LED-ene, flukter med toppen; printes med toppen ned i klar/natur PETG
  translate([pW/2-ledL/2+0.15, ledY0+0.15, pH-lidT-0.8+0.05]) cube([ledL-0.3, ledWd-0.3, lidT+0.8-0.05]);
}
// trinse: 6 × 3 mm diametral magnet foran, spor for O-ringen, blindhull for Ø 2 mm aksel bak (printes med baksiden ned)
module trinse(){
  difference(){
    union(){
      cylinder(d=trD,h=3.6);
      translate([0,0,3.6]) cylinder(d=trG,h=2.4);
      translate([0,0,6.0]) cylinder(d1=trG,d2=trD,h=(trD-trG)/2);
      translate([0,0,6.0+(trD-trG)/2]) cylinder(d=trD,h=trL-6.0-(trD-trG)/2);
    }
    translate([0,0,trL-dmT]) cylinder(d=dmD,h=dmT+eps);                          // magnetlomme foran (toppen)
    translate([0,0,-eps]) cylinder(d=pinA+0.25,h=trL-dmT-0.6);                   // akselhull bak
  }
}
module motortrinse(){ // på N20-akselen (3 mm D, flat 2,5 mm)
  difference(){
    union(){ cylinder(d=mpD,h=1.2); translate([0,0,1.2]) cylinder(d=mpG,h=2.4); translate([0,0,3.6]) cylinder(d1=mpG,d2=mpD,h=1); translate([0,0,4.6]) cylinder(d=mpD,h=0.8); }
    translate([0,0,-eps]) intersection(){ cylinder(d=3.1,h=6); translate([-2,-1.6,0]) cube([4,2.65,6]); }
  }
}
// trinse i montert stilling: aksen langs +y (magneten mot kassetten)
module trinse_pos(i){ translate([dX[i], trY0+trL, dZ]) rotate([90,0,0]) children(); }
module motortrinse_pos(){ translate([pW/2, beltY+2.4, mZ]) rotate([90,0,0]) children(); }
module teardrop(d,h){ rotate([-90,0,0]) linear_extrude(h) hull(){ circle(d=d); translate([0,-d*0.7]) square([0.01,0.01],center=true); } }
module spiller_bunn(){ // i verdenskoordinater (ligger inne i lokkets åpning, 0,15 mm klaring)
  ox = wall+0.15; bw = pW-2*ox; bd = pD-2*ox; rB = pR-wall-0.15;
  yE = pD-wall-0.3-espL;                                 // ESP-ens fremkant
  difference(){
    union(){
      hull(){ translate([ox+0.4,ox+0.4,0]) rbox(bw-0.8,bd-0.8,0.4+eps,rB-0.4); translate([ox,ox,0.4]) rbox(bw,bd,2.0,rB); }
      // vugge for ESP32-S3 Zero: to skinner under, tre vegger og små klikk-lepper
      translate([espX-espW/2-1.35,yE-1.2,2.4-eps]) difference(){
        cube([espW+2.7,espL+1.2,1.2+espT+0.8+eps]);
        translate([1.35,1.2,1.2]) cube([espW+0.3,espL+1,5]);
        translate([1.35+1.6,1.2,-1]) cube([espW+0.3-3.2,espL+1,5]);
      }
      for(s=[0,1]) translate([s ? espX+espW/2+0.15 : espX-espW/2-0.15,yE+espL*0.3,2.4+1.2+espT+0.05+0.55])
        rotate([-90,0,0]) linear_extrude(espL*0.4) polygon(s ? [[0.3,0],[-0.45,0.55],[0.3,0.55]] : [[-0.3,0],[0.45,0.55],[-0.3,0.55]]);
      // ring for summeren (lydhullet ned mot hullene i bunnen)
      translate([bzX,bzY,2.4-eps]) difference(){ cylinder(d=bzD+2.4,h=4); translate([0,0,-1]) cylinder(d=bzD+0.1,h=6); }
      // kabelbuer
      for(p=[[pW/2+12,pD-10],[pW/2-12,pD-10],[bzX,30]]) translate([p[0]-4,p[1]-2,2.4-eps]) difference(){ cube([8,4,4]); translate([1.5,-1,-1]) cube([5,6,3.5]); }
      // akselstolper for trinsene (Ø 2 mm stålpinne presses inn i teardrop-hull)
      for(x=dX) translate([x-4, pilY0, 2.4-eps]) difference(){
        hull(){ cube([8,3.2,eps]); translate([0,0,dZ+3-2.4]) cube([8,3.2,eps]); translate([2,0,dZ+5-2.4]) cube([4,3.2,eps]); }
      }
      // vugge for N20-motoren (girkassen mot fronten, akselen gjennom reimplanet)
      translate([pW/2-n20W/2-1.6, pilY0, 2.4-eps]) difference(){
        cube([n20W+3.2, n20L-3, mZ+n20H/2-1.5-2.4]);
        translate([1.6, -eps, mZ-n20H/2-2.4]) cube([n20W, n20L, 20]);
      }
    }
    for(x=dX) translate([x, pilY0-eps, dZ]) teardrop(pinA-0.1, 3.2+2*eps);             // akselhull (presspasning)
    for(p=bosses) translate([p[0],p[1],-eps]) { cylinder(d=3.4,h=4); cylinder(d1=6.6,d2=3.4,h=1.6); }   // M3 senkehode
    for(x=[ox+16,pW-ox-16], y=[ox+14,pD-ox-14]) translate([x,y,-eps]) cylinder(d=footD,h=0.6);      // gummiføtter
    for(a=[0:60:300]) translate([bzX+3*cos(a),bzY+3*sin(a),-1]) cylinder(d=1.5,h=5);                 // lydhull
    translate([bzX,bzY,-1]) cylinder(d=1.5,h=5);
  }
}
// modeller av de kjøpte delene (bare for kontroll og bilder – ikke for print)
module pn532(){ color([0.75,0.1,0.1]) translate([pW/2-pnW/2, pnY0, pnZ0]) cube([pnW, pcbT, pnH]); }
module n20(){ color([0.7,0.7,0.72]) translate([pW/2-n20W/2+0.1, pilY0+0.05, mZ-n20H/2+0.1]) cube([n20W-0.2, n20L, n20H-0.2]);
              color([0.6,0.6,0.6]) translate([pW/2, pilY0+0.1, mZ]) rotate([90,0,0]) cylinder(d=3,h=pilY0-beltY+2.6); }
module oring(){ color([0.1,0.1,0.1]) translate([0,beltY,0]) rotate([90,0,0]) linear_extrude(oringCS,center=true) difference(){
  hull(){ for(x=dX) translate([x,dZ]) circle(d=trG+oringCS*2); translate([pW/2,mZ]) circle(d=mpG+oringCS*2); }
  hull(){ for(x=dX) translate([x,dZ]) circle(d=trG); translate([pW/2,mZ]) circle(d=mpG); } } }

// utskriftsretning: lokk og lysleder ligger med toppen ned (pen, teksturert toppflate, ingen støtte)
module topp_print(){ translate([0,pD,pH]) rotate([180,0,0]) spiller_topp(); }
module lysleder_print(){ translate([0,pD,pH]) rotate([180,0,0]) lysleder(); }

module drivverk(){ for(i=[0,1]) color([0.3,0.3,0.32]) trinse_pos(i) trinse(); color([0.3,0.3,0.32]) motortrinse_pos() motortrinse(); oring(); n20(); }
module spiller_samlet(rute=true){
  color(c_top) spiller_topp();
  color(c_bot) spiller_bunn();
  if(rute) color(c_glass) vindu();
  color([1,0.9,0.7,0.6]) lysleder();
}
module kassett_i_spor(ang=0){ // kassetten i sporet; ang roterer spolene (for animasjon/bilder)
  slot_frame() translate([-kW/2,kT/2,-slotDepth]) rotate([90,0,0]) kassett_samlet(spoler=false);
  slot_frame() translate([-kW/2,kT/2,-slotDepth]) rotate([90,0,0]) for(x=reelX) color(c_reel) translate([x,reelY,spZ0]) rotate(ang) spole();
}
module med_kassett(rute=true){ spiller_samlet(rute); drivverk(); pn532(); kassett_i_spor(); }
module eksplodert(){
  color(c_top) translate([0,0,40]) spiller_topp();
  color([1,0.9,0.7,0.6]) translate([0,0,60]) lysleder();
  color(c_glass) translate([0,-30,10]) vindu();
  color(c_bot) translate([0,0,-25]) spiller_bunn();
  translate([0,0,-25]) { for(i=[0,1]) color([0.3,0.3,0.32]) translate([0,-12,0]) trinse_pos(i) trinse(); }
  slot_frame() translate([-kW/2,kT/2,40]) rotate([90,0,0]) {
    color(c_k2) kassett_halv(false);
    for(x=reelX) color(c_reel) translate([x,reelY,spZ0+12]) spole();
    color(c_k1) translate([0,0,kT+26]) mirror([0,0,1]) kassett_halv(true);
  }
}
module snitt(){ // vertikalt snitt gjennom høyre spole (for kontroll)
  intersection(){ union(){ med_kassett(); } translate([dX[1],-10,-10]) cube([pW,pD+20,pH+40]); }
}

if(part=="spiller_topp") topp_print();
else if(part=="spiller_bunn") spiller_bunn();
else if(part=="lysleder") lysleder_print();
else if(part=="vindu") vindu_print();
else if(part=="trinse") trinse();
else if(part=="motortrinse") motortrinse();
else if(part=="kassett_front") kassett_halv(true);
else if(part=="kassett_bak") kassett_halv(false);
else if(part=="spole") spole();
else if(part=="kassett_samlet") kassett_samlet();
else if(part=="kassett_bakside") translate([kW,0,kT]) rotate([0,180,0]) kassett_samlet(); // baksiden (spolene ned)
else if(part=="med_kassett") med_kassett();
else if(part=="forfra") med_kassett(false);   // uten rute (OpenSCAD tegner ikke gjennom gjennomsiktige deler)
else if(part=="eksplodert") eksplodert();
else if(part=="snitt") snitt();
// delene i montert stilling (brukes av kontrollskriptet og 3D-siden)
else if(part=="A_topp") spiller_topp();
else if(part=="A_bunn") spiller_bunn();
else if(part=="A_vindu") vindu();
else if(part=="A_lysleder") lysleder();
else if(part=="A_tr0") trinse_pos(0) trinse();
else if(part=="A_tr1") trinse_pos(1) trinse();
else if(part=="A_mt") motortrinse_pos() motortrinse();
else if(part=="A_kb") slot_frame() translate([-kW/2,kT/2,-slotDepth]) rotate([90,0,0]) kassett_halv(false);
else if(part=="A_kf") slot_frame() translate([-kW/2,kT/2,-slotDepth]) rotate([90,0,0]) translate([0,0,kT]) mirror([0,0,1]) kassett_halv(true);
else if(part=="A_s0") slot_frame() translate([-kW/2,kT/2,-slotDepth]) rotate([90,0,0]) translate([reelX[0],reelY,spZ0]) spole();
else if(part=="A_s1") slot_frame() translate([-kW/2,kT/2,-slotDepth]) rotate([90,0,0]) translate([reelX[1],reelY,spZ0]) spole();
else if(part=="A_pn") pn532();
else if(part=="A_n20") n20();
else if(part=="A_oring") oring();
else spiller_samlet();
