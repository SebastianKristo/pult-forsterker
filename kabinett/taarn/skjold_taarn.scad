// Skjold Tårn – KONSEPT (ikke ferdig produkt). Gulvhøyttaler, bassrefleks med port bak.
// variant: "taarn" (2-veis: 1× SB17NRX2C35-8 + SB26STAC tweeter) | "pro" (2,5-veis: 2× SB17 + tweeter)
// part: samlet | par | eksplodert | snitt
variant = "taarn";
part = "samlet";
$fn = 72;

T = 18;                         // MDF
W = 200;                        // bredde
D = variant == "pro" ? 300 : 260;
H = 980;                        // kasse (sokkel kommer i tillegg)
R = 18;
WD = 172; WC = 146;             // 6,5″ bass-mellomtone: ytterdiameter / utsparing
TD = 104; TC = 75;              // 26 mm tweeter (SB26STAC): frontplate / utsparing
ztw = H - 120;                  // tweeter-senter
zw1 = ztw - 145;                // øverste bass-mellomtone
zw2 = zw1 - 190;                // andre (pro)
PORT = 50;                      // port Ø (bak)

c_side = [0.93,0.92,0.90]; c_front = [0.13,0.13,0.14]; c_gold = [0.85,0.62,0.25];
c_cone = [0.62,0.63,0.66]; c_dark = [0.08,0.08,0.09]; c_wood = [0.35,0.27,0.18];

module rcol(w,d,h,r){ hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y,0]) cylinder(r=r,h=h); }
module frontslice(z,d){ translate([W/2,-1,z]) rotate([-90,0,0]) cylinder(d=d,h=T+2); }

module kasse(){
  color(c_side) difference(){
    rcol(W,D,H,R);
    translate([T,T,T]) rcol(W-2*T,D-2*T,H-2*T,max(1,R-T));
    frontslice(ztw,TC); frontslice(zw1,WC); if (variant=="pro") frontslice(zw2,WC);
    translate([W/2,D-T-1,260]) rotate([-90,0,0]) cylinder(d=PORT,h=T+2);
    translate([W/2-35,D-T-1,120]) cube([70,T+2,70]);              // terminalpanel
  }
  // mørk front (printet/lakkert) og gullstripe
  color(c_front) translate([0,-4,0]) difference(){
    hull() for(x=[R,W-R],z=[R,H-R]) translate([x,0,z]) rotate([-90,0,0]) cylinder(r=R,h=4);
    frontslice(ztw,TC); frontslice(zw1,WC); if (variant=="pro") frontslice(zw2,WC);
  }
  color(c_gold) translate([W/2-30,-4.8,70]) cube([60,0.8,2]);
  color(c_gold) translate([W/2,-4.8,82]) rotate([90,0,0]) linear_extrude(0.8) text("SKJOLD",size=10,font="Liberation Sans:style=Bold",halign="center",spacing=1.4);
}

module konus(z,d){
  translate([W/2,-8,z]) rotate([-90,0,0]) {
    color(c_dark) difference(){ cylinder(d=d,h=4); translate([0,0,-1]) cylinder(d=d*0.82,h=6); }
    color(c_dark) translate([0,0,1.5]) rotate_extrude() translate([d*0.38,0]) circle(r=d*0.03);
    color(c_cone) translate([0,0,3]) difference(){ cylinder(d1=d*0.72,d2=d*0.3,h=d*0.15); translate([0,0,-0.01]) cylinder(d1=d*0.7,d2=d*0.28,h=d*0.15); }
    color([0.45,0.46,0.5]) translate([0,0,d*0.11]) scale([1,1,0.35]) sphere(d=d*0.3);
    color([0.25,0.25,0.27]) translate([0,0,d*0.2]) cylinder(d=d*0.55,h=d*0.25);
  }
}
module tweeter(z){
  translate([W/2,-8,z]) rotate([-90,0,0]) {
    color(c_dark) cylinder(d=TD,h=4);
    color(c_gold) translate([0,0,-0.2]) difference(){ cylinder(d=TD*0.6,h=0.6); translate([0,0,-1]) cylinder(d=TD*0.5,h=3); }
    color([0.15,0.15,0.16]) translate([0,0,1]) scale([1,1,0.5]) sphere(d=TD*0.32);
  }
}
module elementer(){ tweeter(ztw); konus(zw1,WD); if (variant=="pro") konus(zw2,WD); }

module delefilter(){ color([0.10,0.35,0.22]) translate([T+6,D/2-60,T+20]) cube([W-2*T-12,120,4]);
  color([0.75,0.45,0.2]) for(i=[0:2]) translate([T+30+i*45,D/2,T+24]) cylinder(d=30,h=18); }   // spoler
module port(){ color(c_dark) translate([W/2,D-T,260]) rotate([90,0,0]) difference(){ cylinder(d=PORT+6,h=180); translate([0,0,-1]) cylinder(d=PORT,h=182); } }
module sokkel(){
  color(c_front) translate([-15,-15,-30]) rcol(W+30,D+30,30,R+10);
  color(c_gold) for(x=[0,W],y=[0,D]) translate([x+(x?5:-5),y+(y?5:-5),-48]) cylinder(d1=2,d2=14,h=18);   // pigger
}

module en(e=0){ kasse(); translate([0,-e,0]) elementer(); translate([0,e*0.6,0]) delefilter(); port(); translate([0,0,-e*0.4]) sokkel(); }

if (part=="samlet") en();
else if (part=="par") { en(); translate([W+420,0,0]) en(); }
else if (part=="eksplodert") en(120);
else if (part=="snitt") difference(){ en(); translate([W/2,-80,-80]) cube([W,D+200,H+200]); }
