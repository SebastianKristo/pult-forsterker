// Pultforsterker v2 rev B — cutouts and screw points measured from v2_body_revb.stl / v2_lid_*_revb.stl / v2_frontplate_revb*.stl
// Body coords (mm): x right, y back (front face y=-80), z up (0 = bottom, 48 = top). Wall features: front/back in (x,z), sides in (y,z), bottom in (x,y).
// Shapes: {t:'c',x,y,d} circle · {t:'r',x,y,w,h,r} rounded rect · {t:'s',x,y,w,h} stadium (long axis = w)
const c=(x,y,d)=>({t:'c',x,y,d}), r=(x,y,w,h,rad=0)=>({t:'r',x,y,w,h,r:rad}), s=(x,y,w,h)=>({t:'s',x,y,w,h});
const REVB={
  W:190, D:160, H:48, R:6, dispX:-27,   // rev C: 25 mm narrower — USB-C stacked on the back, front layout tightened
  front:[
    r(-27,24,57,30,2),                    // display window
    c(-76,24,16.4),                         // power (16 mm)
    c(22,15.5,12.4), c(38,15.5,12.4), c(22,32.5,12.4), c(38,32.5,12.4), // input buttons (12 mm)
    c(66,24,7.4),                           // volume encoder (knob Ø30)
    {...c(-76,8,6.2),hp:true}, // PJ-392 (nickel): mounted in the metal wall only; plate has Ø10.4×2.4 nut pocket at the back + Ø6.4 front hole                           // 3.5 mm headphone jack (under power)
    ...[[-83,41],[83,10],[83,41],[12,8.5],[12,39.5]].map(([x,z])=>({...c(x,z,2.6),screw:'front'})), // 2 extra in the middle stiffen the plate+panel sandwich // front plate screws (from inside)
  ],
  // sheet front panel: open behind the alu front plate (controls mount in the plate only). x,z polygon of the opening incl. bend relief x −80.5…16.5
  frontOpen:{relief:[-80.5,16.5], lip:6, pts:[[-80.5,13],[-88,13],[-88,36.5],[-79,36.5],[-79,99],[79,99],[79,6],[16.5,6]]},
  back:[
    r(70,24,19.4,13),                       // rocker switch
    r(38.5,14.5,16.8,14.5,1), c(24.75,14.5,3.4), c(52.25,14.5,3.4), // RJ45 panel extension (flange 36.5 wide, M3 pitch 27.5, body 21.5 wide) – mounted from inside, cutout = jack face, M3 × 6 from outside into the flange threads
    c(34,34,11.4),                          // DC
    c(52,40,3.4),                           // chassis ground stud M3 (star point next to DC)
    ...[[-62,37],[-42,37],[-62,17],[-42,17]].map(([x,z])=>c(x,z,9.5)), // binding posts (Ø14,5 gold, insulated) stacked: L+ L− top, R+ R− bottom; Ø8 for the plastic shoulder
    c(-26,24,6.4), c(-14,24,6.4),                                // SMA, AUX
    ...[34,24,14].flatMap(z=>[r(6,z,9.6,3.8), c(-3.5,z,2.7), c(15.5,z,2.7)]), // USB-C ×3 stacked (PC 1, PC 2, service)
  ],
  left:[-32.1,-14.6,2.9,20.4].map(y=>r(y,32.6,14.8,8)),          // 4× USB-A (Ugreen)
  right:Array.from({length:26},(_,i)=>r(+(-43.8+3.6*i).toFixed(1),26.5,2.4,24)), // vent slots
  bottom:[
    r(-75.8,-9.8,18,16),
    ...Array.from({length:23},(_,i)=>r(+(-55+5*i).toFixed(1),-14,2.4,40)), // 23 vents under the Pi 4 (no thermal block, TPA3116 has its own heatsink)
  ],
  topVents:[], // no top vents: air in through the bottom vent field, out through the right-side slots
  lidScrews:[[-85,-70],[-85,70],[85,-70],[85,70]],      // M3, lid Ø3.4 / c'bore Ø6.2
  boardPosts:[[-88.3,-44.3],[-88.3,47.7],[83.7,-44.3],[83.7,47.7]], boardZ:28, // M3, board seat height
  lidMountSlots:[[-117.5,-40],[-117.5,40],[117.5,-40],[117.5,40]].map(([x,y])=>s(x,y,10,4.6)), // pultfeste lid, W=251
  lidMountW:251,
  // printed front plate (replaces v2_frontplate_revb*.stl): 4 mm, no visible screws — M3 from inside the box into heat-set inserts
  plate:{w:178,h:46,r:3,t:4,insertD:4.0,insertDepth:3.2,
    coverT:2, cover:{oled:[72,40,2],tft:[60,40,2]}, view:{oled:[62,38,1.5],tft:[62,38,1.5]},
    // printed in: face-down, back 1.0 / cavity 2.2 / front lip 0.8 (z from the back). Pause at print-Z 3.0, insert acrylic, resume.
    layers:{back:1.0,cavity:2.2,front:0.8}, face:{oled:[69,37,2.2],tft:[56,37,2.2]}, cavClr:0.3, frame:2.0},
  dispCut:{oled:[57,39,2],tft:[57,39,2]}, // universal: OLED active 55×27,5 and TFT active 48,6×37 both fit; leaves a web for the BSO standoffs
  oledMount:null, // replaced by a printed PETG holder (see oledHolder)
  oledHolder:{mod:[72,43,1.6], glass:[62.1,38.8,2.0], pitch:[68,39], hole:2.8, cz:24.6, studs:[[-83,41],[12,8.5],[12,39.5]], studType:'FH-M3-10'}, // 2.42" SSD1309 (TZT datasheet): module 72×43×5.9, holes Ø2.8 2 mm from edge // one universal cut-out: fits the 2.42" OLED and the 2.4" TFT,
  // printable desk-mount brackets (PETG, 4 mm): clamped between lid-screw heads and the standard lid — no special lid needed.
  // right-hand outline (CCW) with corner radii; left bracket = mirror. Slots for Ø4 wood screws into the desk underside.
  bracket:{t:4, pts:[[75.5,-76,4],[95,-76,2],[95,-52,3],[114.5,-52,5],[114.5,-28,5],[95,-28,3],[95,28,3],[114.5,28,5],[114.5,52,5],[95,52,3],[95,76,2],[75.5,76,4]],
    slots:[[105,-40],[105,40]].map(([x,y])=>s(x,y,12,4.6)), screwCb:[6.6,2.2]}, // box front wall display cut-out per module
};
if(typeof window!=='undefined') window.REVB=REVB;
export { REVB };
