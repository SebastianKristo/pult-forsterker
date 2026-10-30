// Skjold S1 — rounded sheet-metal enclosure (R9 wrap): STEP assembly + DXF flat patterns. Run like cad/generate.js.
// Parts: omslag (top+sides, R9 bends, 12 mm bottom flanges) · front/back panels with 10 mm bottom flange · bottom plate · 2 internal angle rails.
// All seams and screws are on the underside. Requires the StepDoc/fpoly/... helpers from cad/generate.js (passed in as LIB).
return (async()=>{
const {StepDoc,fpoly,rrect,rev,circ,hole,fr,FZ,FF,FB,FL,FRt,FY,DXF}=LIB;
const W=REVB.W, D=REVB.D, H=REVB.H, HW=W/2, HD=D/2, T=1.5, RT=9, RB=9, K=0.44, id=u=>u, neg=u=>-u;
const xf=HW-RB-12;                     // wrap flange inner edge (x)
const PZ=1.5+3;                        // panel flat starts above its bend (flange sits on the wrap flanges, z 1.5..3)
const PW=HW-T-0.2, PTOP=H-T-0.2, PR=RT-T-0.2, FLX=HW-RB-0.5; // panel half width, top, corner radius, flange half width
const RI=1.5, RO=3, BAp=Math.PI/2*(RI+K*T);                    // panel bend
const BAw=Math.PI/2*(RB-T+K*T);                                // wrap bend (R9 outer)
const FS=[-73.5,-60,0,60,73.5].flatMap(y=>[[-(HW-RB-6),y],[HW-RB-6,y]]); // flange screws (M3 from below)
const STUD=[[-50],[50]].map(([y])=>y), RAILZ=[9.5,15.5];
// hodetelefonkontakten: åpent spor (panelClear bredt, R1) fra bunnkanten opp til senter + radius – ingen hullkant nær bøylinjen
const HPs=REVB.front.find(f=>f.hp&&f.slot), hw=HPs?HPs.panelClear/2:0, zt=HPs?HPs.y+hw:0;
const notch=(pts,rads,yb)=>{ if(!HPs) return [pts,rads]; const i=pts.findIndex(p=>p[0]===-pts[0][0]&&p[1]===yb); const out=[],ro=[];
  pts.forEach((p,k)=>{ out.push(p); ro.push(rads[k]); if(k===i){ out.push([HPs.x-hw,yb],[HPs.x-hw,zt],[HPs.x+hw,zt],[HPs.x+hw,yb]); ro.push(0,1,1,0); } }); return [out,ro]; };

const d=Math.PI/180, P=(c,r,a)=>[c[0]+r*Math.cos(a),c[1]+r*Math.sin(a)];
const out={};
// --- wrap cross-section (x,z), CCW, outer then inner
function wrapLoop(){ const s=[]; const L=(a,b)=>s.push({t:'L',a,b}), A=(c,r,a0,a1,ccw)=>s.push({t:'A',c,r,a:P(c,r,a0),b:P(c,r,a1),ccw});
  const cBR=[HW-RB,RB], cTR=[HW-RT,H-RT], cTL=[-(HW-RT),H-RT], cBL=[-(HW-RB),RB];
  L([xf,0],[HW-RB,0]); A(cBR,RB,-90*d,0,true); L([HW,RB],[HW,H-RT]); A(cTR,RT,0,90*d,true); L([HW-RT,H],[-(HW-RT),H]); A(cTL,RT,90*d,180*d,true); L([-HW,H-RT],[-HW,RB]); A(cBL,RB,180*d,270*d,true);
  L([-(HW-RB),0],[-xf,0]); L([-xf,0],[-xf,T]); L([-xf,T],[-(HW-RB),T]); A(cBL,RB-T,270*d,180*d,false); L([-(HW-T),RB],[-(HW-T),H-RT]); A(cTL,RT-T,180*d,90*d,false);
  L([-(HW-RT),H-T],[HW-RT,H-T]); A(cTR,RT-T,90*d,0,false); L([HW-T,H-RT],[HW-T,RB]); A(cBR,RB-T,0,-90*d,false); L([HW-RB,T],[xf,T]); L([xf,T],[xf,0]);
  // snap arc endpoints exactly onto neighbours
  for(let i=0;i<s.length;i++){ const n=s[(i+1)%s.length]; n.a=s[i].b; } return s; }
const sideHoles={right:REVB.right.map(f=>hole(f,id)), left:REVB.left.map(f=>hole(f,neg)), studR:STUD.map(y=>circ(y,12,1.5)), studL:STUD.map(y=>circ(-y,12,1.5))};
for(const DK of ['oled','tft']){ const SFX=DK==='oled'?'':'_tft';
  const doc=StepDoc('skjold_s1_platemetall_avrundet'+SFX,'Skjold S1 rounded sheet-metal enclosure 1.5 mm '+DK);
  // 1 wrap
  { const S=doc.Solid('omslag'), loop=wrapLoop(); const iRo=2, iLo=6, iRi=16, iLi=12; // outer right/left side lines, inner left/right side lines
    const R=[...sideHoles.right,...sideHoles.studR], Lh=[...sideHoles.left,...sideHoles.studL];
    const fl=FS.map(([x,y])=>circ(x,y,1.7)), flR=fl.filter((_,i)=>i%2), flL=fl.filter((_,i)=>!(i%2));
    S.sides(FF,loop,-HD,HD,{[iRo]:R.map(h=>S.bound(FRt,h,HW,true)),[iRi]:R.map(h=>S.bound(FRt,h,HW-T,false)),[iLo]:Lh.map(h=>S.bound(FL,h,HW,true)),[iLi]:Lh.map(h=>S.bound(FL,h,HW-T,false)),
      0:flR.map(h=>S.bound(FZ,h,0,false)),18:flR.map(h=>S.bound(FZ,h,T,true)),8:flL.map(h=>S.bound(FZ,h,0,false)),10:flL.map(h=>S.bound(FZ,h,T,true))});
    R.forEach(h=>S.sides(FRt,h,HW-T,HW)); Lh.forEach(h=>S.sides(FL,h,HW-T,HW)); fl.forEach(h=>S.sides(FZ,h,0,T));
    S.cap(FF,HD,[S.bound(FF,loop,HD,true,true)],true); S.cap(FF,-HD,[S.bound(FF,loop,-HD,false,true)],false); S.done(); }
  // 2/3 panels (front with display cut-out per module, back) + bottom flange
  const front=REVB.front.map((f,i)=>i===0?{t:'r',x:REVB.dispX,y:24,w:REVB.dispCut[DK][0],h:REVB.dispCut[DK][1],r:REVB.dispCut[DK][2]}:f);
  const pOut=HPs?fpoly(...notch([[PW,PZ],[PW,PTOP],[-PW,PTOP],[-PW,PZ]],[PR,PR,PR,PR],PZ)):fpoly([[PW,PZ],[PW,PTOP],[-PW,PTOP],[-PW,PZ]],[PR,PR,PR,PR]);
  for(const [nm,Fr,feats,map,sy] of [['front',FF,front,id,-1],['bak',FB,REVB.back,neg,1]]){
    const hs=feats.filter(f=>!(f.hp&&f.slot)).map(f=>hole(f,map,0,f.screw?3.4:undefined)); doc.prism('panel_'+nm,Fr,nm==='front'?pOut:fpoly([[PW,PZ],[PW,PTOP],[-PW,PTOP],[-PW,PZ]],[PR,PR,PR,PR]),hs,HD-T,HD);
    const c=[sy*(HD-RO),PZ], sec=sy<0?[{t:'A',c,r:RO,a:P(c,RO,180*d),b:P(c,RO,270*d),ccw:true},{t:'L',a:P(c,RO,270*d),b:P(c,RI,270*d)},{t:'A',c,r:RI,a:P(c,RI,270*d),b:P(c,RI,180*d),ccw:false},{t:'L',a:P(c,RI,180*d),b:P(c,RO,180*d)}]
      :[{t:'A',c,r:RO,a:P(c,RO,270*d),b:P(c,RO,360*d),ccw:true},{t:'L',a:P(c,RO,360*d),b:P(c,RI,360*d)},{t:'A',c,r:RI,a:P(c,RI,360*d),b:P(c,RI,270*d),ccw:false},{t:'L',a:P(c,RI,270*d),b:P(c,RO,270*d)}];
    sec.forEach((s,i)=>{ s.a=i?sec[i-1].b:s.a; }); sec[0].a=sec[3].b;
    doc.prism('panel_'+nm+'_bend',fr([0,1,0],[0,0,1],[1,0,0]),sec,[],-FLX,FLX);
    const y0=sy*(HD-RO), y1=sy*(HD-RO-7); doc.prism('panel_'+nm+'_flens',FZ,rrect(FLX,3.5,0,0,(y0+y1)/2),[-(HW-RB-6),HW-RB-6].map(x=>circ(x,sy*73.5,2.1)),1.5,3); }
  // 4 bottom plate (on the wrap flanges, between the panel flanges)
  { const bh=[...REVB.bottom.slice(1).map(f=>hole(f)),...FS.filter(([,y])=>Math.abs(y)<70).map(([x,y])=>circ(x,y,2.1))]; doc.prism('bunnplate',FZ,rrect(HW-RB,HD-RO-7-1.8,1),bh,1.5,3); }
  // 5 rails (L 6 × 11.5 mm) carrying the outer board posts; M3 PEM FH studs in the side walls
  for(const sx of [1,-1]){ const xo=sx*(HW-T), xi=sx*(HW-T-1.5), xe=sx*(HW-T-11.5);
    const pts=[[RAILZ[0],xo],[RAILZ[1],xo],[RAILZ[1],xe],[RAILZ[1]-1.5,xe],[RAILZ[1]-1.5,xi],[RAILZ[0],xi]]; const poly=sx>0?pts.slice().reverse():pts;
    const loop=poly.map((p,i)=>({t:'L',a:p,b:poly[(i+1)%poly.length]})); const fixed=sx>0?loop:loop; doc.prism('skinne_'+(sx>0?'hoyre':'venstre'),FY,fixed,[],-68,68); }
  out['platemetall/skjold_s1_avrundet/skjold_s1_platemetall_avrundet'+SFX+'.step']=doc.text(); log(DK,'round sheet bad',doc.bad);
}
// ---------- DXF flat patterns ----------
{ // wrap: s along the neutral fibre, 0 = top centre
  const s1=HW-RT, s2=s1+BAw, s3=s2+(H-RT-RB), s4=s3+BAw, s5=s4+(HW-RB-xf), d=DXF();
  [[ s5,-HD],[ s5,HD],[-s5,HD],[-s5,-HD]].forEach((p,i,a)=>d.line(p,a[(i+1)%4]));
  const sideS=z=>s2+(H-RT-z);
  REVB.right.forEach(f=>d.loop(hole({...f,t:f.t,x:sideS(f.y),y:f.x,w:f.h,h:f.w})));
  REVB.left.forEach(f=>d.loop(hole({...f,x:-sideS(f.y),y:f.x,w:f.h,h:f.w})));
  STUD.forEach(y=>{ d.loop(circ(sideS(12),y,1.5)); d.loop(circ(-sideS(12),y,1.5)); });
  FS.forEach(([x,y])=>d.loop(circ(Math.sign(x)*(s4+(HW-RB-Math.abs(x))),y,1.7)));
  [s1+BAw/2,s3+BAw/2].forEach(s=>[s,-s].forEach(x=>d.line([x,-HD],[x,HD],'BEND')));
  out['platemetall/skjold_s1_avrundet/skjold_s1_omslag_flatmonster.dxf']=d.text(); log('wrap flat',(2*s5).toFixed(2),'x',D); }
for(const [nm,feats,map,dk] of [['front_oled',null,id,'oled'],['front_tft',null,id,'tft'],['bak',REVB.back,neg,null]]){
  const d=DXF(), fl=PZ-BAp-7, fpts=[[FLX,fl],[FLX,PZ],[PW,PZ],[PW,PTOP],[-PW,PTOP],[-PW,PZ],[-FLX,PZ],[-FLX,fl]];
  if(feats||!HPs) d.loop(fpoly(fpts,[0,0,PR,PR,PR,PR,0,0])); else d.loop(fpoly(...notch(fpts,[0,0,PR,PR,PR,PR,0,0],fl)));   // front: sporet går gjennom bøy og flens
  const fs=(feats||REVB.front.map((f,i)=>i===0?{t:'r',x:REVB.dispX,y:24,w:REVB.dispCut[dk][0],h:REVB.dispCut[dk][1],r:REVB.dispCut[dk][2]}:f)).filter(f=>!(f.hp&&f.slot));
  fs.forEach(f=>d.loop(hole(f,map,0,f.screw?3.4:undefined)));
  [-(HW-RB-6),HW-RB-6].forEach(x=>d.loop(circ(x,PZ-BAp-3.5,2.1))); d.line([-FLX,PZ-BAp/2],[FLX,PZ-BAp/2],'BEND');
  out['platemetall/skjold_s1_avrundet/skjold_s1_panel_'+nm+'_flatmonster.dxf']=d.text(); }
{ const d=DXF(); d.loop(rrect(HW-RB,HD-RO-7-1.8,1)); REVB.bottom.slice(1).forEach(f=>d.loop(hole(f))); FS.filter(([,y])=>Math.abs(y)<70).forEach(([x,y])=>d.loop(circ(x,y,2.1)));
  out['platemetall/skjold_s1_avrundet/skjold_s1_bunnplate.dxf']=d.text(); }
{ const d=DXF(), w=6+11.5-BAp*0; d.loop(rrect(68,(6+11.5)/2,0,0,0)); d.line([-68,-(6+11.5)/2+6],[68,-(6+11.5)/2+6],'BEND');
  STUD.forEach(y=>d.loop(circ(y,-(6+11.5)/2+3,1.7))); [[-44.3],[47.7]].forEach(([y])=>d.loop(circ(y,(6+11.5)/2-4.8,1.7)));
  out['platemetall/skjold_s1_avrundet/skjold_s1_skinne_x2.dxf']=d.text(); }
for(const [k,v] of Object.entries(out)) await saveFile(k,v);
log(Object.keys(out).length+' filer');
})();
