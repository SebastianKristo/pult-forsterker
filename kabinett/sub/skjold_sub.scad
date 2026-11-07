// Skjold Sub – KONSEPT (ikke ferdig produkt). Lukket kasse, element ned-/framovervendt, elektronikk bak.
// variant: "sub8" (Dayton RSS210HF-4, ~20 l netto) | "sub10" (Dayton RSS265HF-4, ~35 l netto)
// part: samlet | eksplodert | snitt
variant = "sub8";
part = "samlet";
$fn = 72;

T  = 18;                                  // MDF-tykkelse
W  = variant == "sub10" ? 380 : 320;      // ytre bredde = dybde
H  = variant == "sub10" ? 420 : 360;      // ytre høyde (uten føtter)
DD = variant == "sub10" ? 262 : 210;      // elementets ytterdiameter
DC = variant == "sub10" ? 232 : 186;      // utsparing
R  = 22;                                  // hjørneradius (rundet MDF / printede hjørnelister)

c_side = [0.93,0.92,0.90];  c_front = [0.13,0.13,0.14];  c_gold = [0.85,0.62,0.25];
c_cone = [0.62,0.63,0.66];  c_pcb = [0.10,0.35,0.22];    c_dark = [0.08,0.08,0.09];

module rbox(w,d,h,r){ hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y,0]) cylinder(r=r,h=h); }

module kasse(){
  color(c_side) difference(){
    rbox(W,W,H,R);
    translate([T,T,T]) rbox(W-2*T,W-2*T,H-2*T,max(1,R-T));
    translate([W/2,-1,H/2]) rotate([-90,0,0]) cylinder(d=DC,h=T+2);   // element foran
    translate([W/2-70,W-T-1,40]) cube([140,T+2,110]);                 // åpning for elektronikkpanel bak
  }
  // mørk front med gullkant
  color(c_front) translate([0,-4,0]) difference(){
    hull() for(x=[R,W-R],z=[R,H-R]) translate([x,0,z]) rotate([-90,0,0]) cylinder(r=R,h=4);
    translate([W/2,-1,H/2]) rotate([-90,0,0]) cylinder(d=DC,h=6);
  }
  color(c_gold) translate([W/2,-4.6,H/2]) rotate([-90,0,0]) difference(){ cylinder(d=DD+16,h=0.8); translate([0,0,-1]) cylinder(d=DD+8,h=3); }
  // SKJOLD-logo
  color(c_gold) translate([W/2,-4.8,28]) rotate([90,0,0]) linear_extrude(0.8) text("SKJOLD",size=11,font="Liberation Sans:style=Bold",halign="center",spacing=1.4);
}

module element(){
  translate([W/2,-8,H/2]) rotate([-90,0,0]) {
    color(c_dark) difference(){ cylinder(d=DD,h=4); translate([0,0,-1]) cylinder(d=DD*0.84,h=6); }   // ramme
    color(c_dark) translate([0,0,1.5]) rotate_extrude() translate([DD*0.385,0]) circle(r=DD*0.03);    // gummioppheng
    color(c_cone) translate([0,0,3]) difference(){ cylinder(d1=DD*0.74,d2=DD*0.3,h=DD*0.16); translate([0,0,-0.01]) cylinder(d1=DD*0.72,d2=DD*0.28,h=DD*0.16); } // aluminiumskon
    color(c_cone) translate([0,0,DD*0.16]) cylinder(d=DD*0.3,h=1);                                     // bunn i kon
    color([0.45,0.46,0.5]) translate([0,0,DD*0.12]) scale([1,1,0.35]) sphere(d=DD*0.3);              // støvhette
    color([0.25,0.25,0.27]) translate([0,0,DD*0.2]) cylinder(d=DD*0.6,h=DD*0.22);                     // magnet
  }
  // mørk baffel bak åpningen så man ikke ser inn i kassen
  color(c_dark) translate([W/2,T+1,H/2]) rotate([-90,0,0]) cylinder(d=DC+2,h=0.5);
}

module elektronikk(){
  translate([W/2-70,W-T-4,40]) {
    color(c_dark) cube([140,4,110]);                                   // bakpanel (printet)
    color(c_pcb) translate([10,-28,12]) cube([90,24,60]);               // TPA3255-kort
    color([0.2,0.2,0.22]) translate([10,-48,12]) cube([90,20,8]);       // kjøleribbe-indikasjon
    color([0.0,0.45,0.25]) translate([105,-22,70]) cube([30,18,4]);     // Pi Zero 2 W
    color([0.6,0.1,0.15]) translate([105,-22,90]) cube([25,14,3]);      // DAC
    color(c_gold) for(z=[20,48]) translate([118,4,z]) rotate([-90,0,0]) cylinder(d=12,h=6); // strøm + bryter
  }
}

module fot(){ color(c_dark) for(x=[40,W-40],y=[40,W-40]) translate([x,y,-12]) cylinder(d1=34,d2=40,h=12); }

module samlet(e=0){
  kasse();
  translate([0,-e,0]) element();
  translate([0,e*1.2,0]) elektronikk();
  translate([0,0,-e*0.5]) fot();
  if (e>0) color([1,1,1,0.0]) cube(1);
}

if (part=="samlet") samlet();
else if (part=="eksplodert") samlet(140);
else if (part=="snitt") difference(){ samlet(); translate([W/2,-50,-50]) cube([W,W+100,H+100]); }
