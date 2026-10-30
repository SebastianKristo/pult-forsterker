// CAD generator for Pultforsterker v2 rev B — run via run_script: new Function('REVB','saveFile','log', src)(...)
// Writes STEP (AP214 B-rep) + DXF. Front plate is printed, fixed from behind: M3 screws from inside the box through Ø3.4 wall holes into heat-set inserts.
return (async()=>{
function StepDoc(name,desc){
  const L=[]; let id=0; const e=s=>{L.push(`#${++id}=${s};`); return '#'+id;};
  const f=v=>{let s=(+(+v).toFixed(5)).toString(); if(s==='-0') s='0'; if(!s.includes('.')&&!s.includes('e')) s+='.'; return s;};
  const P=p=>e(`CARTESIAN_POINT('',(${p.map(f).join(',')}))`), D=d=>e(`DIRECTION('',(${d.map(f).join(',')}))`);
  const AX=(p,n,r)=>e(`AXIS2_PLACEMENT_3D('',${P(p)},${D(n)},${D(r)})`);
  const ctx=e("APPLICATION_CONTEXT('automotive design')");
  e(`APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,${ctx})`);
  const pc=e(`PRODUCT_CONTEXT('',${ctx},'mechanical')`), pdc=e(`PRODUCT_DEFINITION_CONTEXT('part definition',${ctx},'design')`);
  const lu=e('(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.))'), au=e('(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))'), su=e('(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT())');
  const unc=e(`UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-04),${lu},'distance_accuracy_value','')`);
  const gc=e(`(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((${unc}))GLOBAL_UNIT_ASSIGNED_CONTEXT((${lu},${au},${su}))REPRESENTATION_CONTEXT('',''))`);
  const prod=e(`PRODUCT('${name}','${name}','',(${pc}))`);
  const pdf=e(`PRODUCT_DEFINITION_FORMATION('','',${prod})`), pd=e(`PRODUCT_DEFINITION('design','',${pdf},${pdc})`), pds=e(`PRODUCT_DEFINITION_SHAPE('','',${pd})`);
  const solids=[]; let bad=0;
  const add=(a,b)=>a.map((x,i)=>x+b[i]), mul=(a,k)=>a.map(x=>x*k), K=p=>p.map(x=>x.toFixed(4)).join(',');
  function Solid(nm){
    const vc={}, ec={}, vec={}, use={}, faces=[];
    const VX=p=>vc[K(p)]||(vc[K(p)]=e(`VERTEX_POINT('',${P(p)})`));
    const OE=(ed,s)=>{(use[ed]=use[ed]||[]).push(s); return e(`ORIENTED_EDGE('',*,*,${ed},${s?'.T.':'.F.'})`);};
    function segEdge(F,s,w){ const A=F.m(...s.a,w), B=F.m(...s.b,w); const k=s.t+K(A)+K(B)+(s.c?K(F.m(...s.c,w)):'');
      if(ec[k]) return ec[k];
      let c; if(s.t==='L'){const d=add(B,mul(A,-1)), l=Math.hypot(...d); c=e(`LINE('',${P(A)},${e(`VECTOR('',${D(mul(d,1/l))},${f(l)})`)})`);}
      else c=e(`CIRCLE('',${AX(F.m(...s.c,w),F.W,F.U)},${f(s.r)})`);
      return ec[k]=e(`EDGE_CURVE('',${VX(A)},${VX(B)},${c},${s.t==='L'||s.ccw?'.T.':'.F.'})`);}
    function vEdge(F,uv,w0,w1){const A=F.m(...uv,w0),B=F.m(...uv,w1),k=K(A)+K(B); if(vec[k]) return vec[k];
      return vec[k]=e(`EDGE_CURVE('',${VX(A)},${VX(B)},${e(`LINE('',${P(A)},${e(`VECTOR('',${D(F.W)},${f(w1-w0)})`)})`)},.T.)`);}
    function sides(F,loop,w0,w1,extra={}){ loop.forEach((s,i)=>{
      const b0=segEdge(F,s,w0), b1=segEdge(F,s,w1), va=vEdge(F,s.a,w0,w1), vb=vEdge(F,s.b,w0,w1);
      const ob=e(`FACE_OUTER_BOUND('',${e(`EDGE_LOOP('',(${[OE(b0,1),OE(vb,1),OE(b1,0),OE(va,0)].join(',')}))`)},.T.)`);
      let surf, same='.T.';
      if(s.t==='L'){const du=s.b[0]-s.a[0], dv=s.b[1]-s.a[1], l=Math.hypot(du,dv);
        surf=e(`PLANE('',${AX(F.m(...s.a,w0),add(mul(F.U,dv/l),mul(F.V,-du/l)),add(mul(F.U,du/l),mul(F.V,dv/l)))})`);}
      else {surf=e(`CYLINDRICAL_SURFACE('',${AX(F.m(...s.c,w0),F.W,F.U)},${f(s.r)})`); same=s.ccw?'.T.':'.F.';}
      faces.push(e(`ADVANCED_FACE('',(${[ob,...(extra[i]||[])].join(',')}),${surf},${same})`)); });}
    function bound(F,loop,w,fwd,outer){const ed=loop.map(s=>segEdge(F,s,w)); const oes=fwd?ed.map(x=>OE(x,1)):[...ed].reverse().map(x=>OE(x,0));
      return e(`${outer?'FACE_OUTER_BOUND':'FACE_BOUND'}('',${e(`EDGE_LOOP('',(${oes.join(',')}))`)},.T.)`);}
    function cap(F,w,bounds,up,nm=''){faces.push(e(`ADVANCED_FACE('${nm}',(${bounds.join(',')}),${e(`PLANE('',${AX(F.m(0,0,w),F.W,F.U)})`)},${up?'.T.':'.F.'})`));}
    function done(){ for(const k in use){const u=use[k]; if(u.length!==2||u[0]===u[1]) bad++;}
      const sh=e(`CLOSED_SHELL('',(${faces.join(',')}))`); solids.push(e(`MANIFOLD_SOLID_BREP('${nm}',${sh})`)); return faces.length;}
    return {sides,bound,cap,done};
  }
  // prism: outer CCW, through holes CW; cb = counterbores from +W side; blind = blind holes from −W side {loop,depth}
  function prism(nm,F,outer,holes,w0,w1,cb=[],blind=[]){
    const S=Solid(nm); S.sides(F,outer,w0,w1); holes.forEach(h=>S.sides(F,h,w0,w1));
    cb.forEach(({big,small,depth})=>{ const wm=w1-depth; S.sides(F,big,wm,w1); S.sides(F,small,w0,wm); S.cap(F,wm,[S.bound(F,big,wm,false,true),S.bound(F,small,wm,true)],true); });
    blind.forEach(({loop,depth})=>{ S.sides(F,loop,w0,w0+depth); S.cap(F,w0+depth,[S.bound(F,loop,w0+depth,true,true)],false); });
    S.cap(F,w1,[S.bound(F,outer,w1,true,true),...holes.map(h=>S.bound(F,h,w1,true)),...cb.map(c=>S.bound(F,c.big,w1,true))],true);
    S.cap(F,w0,[S.bound(F,outer,w0,false,true),...holes.map(h=>S.bound(F,h,w0,false)),...cb.map(c=>S.bound(F,c.small,w0,false)),...blind.map(b=>S.bound(F,b.loop,w0,false))],false);
    return S.done();
  }
  // stepped through-window: loops [small(back), big(cavity), small(front)] with z-breaks w0<wa<wb<w1 — appended to a Solid
  function stepped(S,F,back,cav,front,w0,wa,wb,w1){ S.sides(F,back,w0,wa); S.sides(F,cav,wa,wb); S.sides(F,front,wb,w1);
    S.cap(F,wa,[S.bound(F,cav,wa,false,true),S.bound(F,back,wa,true)],true); S.cap(F,wb,[S.bound(F,cav,wb,true,true),S.bound(F,front,wb,false)],false); }
  function text(){ const sr=e(`ADVANCED_BREP_SHAPE_REPRESENTATION('${name}',(${AX([0,0,0],[0,0,1],[1,0,0])},${solids.join(',')}),${gc})`);
    e(`SHAPE_DEFINITION_REPRESENTATION(${pds},${sr})`);
    return `ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('${desc}'),'2;1');\nFILE_NAME('${name}.step','2026-10-30T14:00:00',(''),(''),'','','');\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n${L.join('\n')}\nENDSEC;\nEND-ISO-10303-21;\n`;}
  return {Solid,prism,stepped,text,get bad(){return bad;}};
}
const add=(a,b)=>a.map((x,i)=>x+b[i]), mul=(a,k)=>a.map(x=>x*k);
const fr=(U,V,W)=>({U,V,W,m:(u,v,w)=>add(add(mul(U,u),mul(V,v)),mul(W,w))});
const FZ=fr([1,0,0],[0,1,0],[0,0,1]), FF=fr([1,0,0],[0,0,1],[0,-1,0]), FB=fr([-1,0,0],[0,0,1],[0,1,0]), FL=fr([0,-1,0],[0,0,1],[-1,0,0]), FRt=fr([0,1,0],[0,0,1],[1,0,0]);
const FX=fr([0,1,0],[0,0,1],[1,0,0]), FY=fr([0,0,1],[1,0,0],[0,1,0]);
function fpoly(pts,rad){ const n=pts.length, cs=[];
  for(let i=0;i<n;i++){const p=pts[(i-1+n)%n], v=pts[i], q=pts[(i+1)%n], r=rad[i];
    const d1=[v[0]-p[0],v[1]-p[1]], d2=[q[0]-v[0],q[1]-v[1]], l1=Math.hypot(...d1), l2=Math.hypot(...d2);
    const a=[d1[0]/l1,d1[1]/l1], b=[d2[0]/l2,d2[1]/l2], cr=a[0]*b[1]-a[1]*b[0];
    if(!r){cs.push({in:v,out:v}); continue;}
    const th=Math.acos(Math.max(-1,Math.min(1,a[0]*b[0]+a[1]*b[1]))), t=r*Math.tan(th/2);
    const t1=[v[0]-a[0]*t,v[1]-a[1]*t], t2=[v[0]+b[0]*t,v[1]+b[1]*t], nl=cr>0?[-a[1],a[0]]:[a[1],-a[0]];
    cs.push({in:t1,out:t2,arc:{t:'A',c:[t1[0]+nl[0]*r,t1[1]+nl[1]*r],r,a:t1,b:t2,ccw:cr>0}});}
  const s=[]; for(let i=0;i<n;i++){ if(cs[i].arc) s.push(cs[i].arc); const a=cs[i].out,b=cs[(i+1)%n].in; if(Math.hypot(b[0]-a[0],b[1]-a[1])>1e-6) s.push({t:'L',a,b}); } return s;}
const rrect=(hw,hh,r,cx=0,cy=0)=>fpoly([[cx+hw,cy-hh],[cx+hw,cy+hh],[cx-hw,cy+hh],[cx-hw,cy-hh]],[r,r,r,r]);
const rev=l=>l.slice().reverse().map(s=>s.t==='L'?{...s,a:s.b,b:s.a}:{...s,a:s.b,b:s.a,ccw:!s.ccw});
const circ=(cx,cy,r)=>[{t:'A',c:[cx,cy],r,a:[cx+r,cy],b:[cx+r,cy],ccw:false}];
function hole(ft,mapU=u=>u,minR=0,override){ const x=mapU(ft.x), y=ft.y;
  if(ft.t==='c') return circ(x,y,(override??ft.d)/2);
  if(ft.t==='s') return rev(rrect(ft.w/2,ft.h/2,ft.h/2,x,y));
  return rev(rrect(ft.w/2,ft.h/2,Math.min(Math.max(ft.r||0,minR),Math.min(ft.w,ft.h)/2-0.01),x,y));}
const {W,D,H,R}=REVB, HW=W/2, HD=D/2, neg=u=>-u, id=u=>u, out={};
const FSCR=3.4; // front-plate screw clearance (M3 from inside)
const frontF=k=>REVB.front.map((f,i)=>i===0?{t:'r',x:REVB.dispX,y:24,w:REVB.dispCut[k][0],h:REVB.dispCut[k][1],r:REVB.dispCut[k][2]}:f);
for(const DK of ['oled','tft']){ const SFX=DK==='oled'?'':'_tft';
// ===== CNC body =====
{ const doc=StepDoc('pultforsterker_v2_revb_kasse_cnc'+SFX,'Pultforsterker v2 revB kasse CNC aluminium '+DK); const S=doc.Solid('kasse_cnc');
  const WT=2.7, FLR=3, PR=5, iX=HW-WT, iY=HD-WT, mr=1;
  const outer=rrect(HW,HD,R), pocket=rev(rrect(iX,iY,PR));
  const front=frontF(DK).map(ft=>hole(ft,id,mr,ft.screw?FSCR:undefined)), back=REVB.back.map(ft=>hole(ft,neg,mr)), left=REVB.left.map(ft=>hole(ft,neg,mr)), right=REVB.right.map(ft=>hole(ft,id,mr));
  const floor=[...REVB.bottom.map(ft=>hole(ft,id,mr)), ...REVB.lidScrews.map(([x,y])=>circ(x,y,1.7)), ...REVB.boardPosts.map(([x,y])=>circ(x,y,1.7))];
  S.sides(FZ,outer,0,H,{7:front.map(h=>S.bound(FF,h,HD,true)),3:back.map(h=>S.bound(FB,h,HD,true)),5:left.map(h=>S.bound(FL,h,HW,true)),1:right.map(h=>S.bound(FRt,h,HW,true))});
  S.sides(FZ,pocket,FLR,H,{0:front.map(h=>S.bound(FF,h,iY,false)),4:back.map(h=>S.bound(FB,h,iY,false)),2:left.map(h=>S.bound(FL,h,iX,false)),6:right.map(h=>S.bound(FRt,h,iX,false))});
  front.forEach(h=>S.sides(FF,h,iY,HD)); back.forEach(h=>S.sides(FB,h,iY,HD)); left.forEach(h=>S.sides(FL,h,iX,HW)); right.forEach(h=>S.sides(FRt,h,iX,HW)); floor.forEach(h=>S.sides(FZ,h,0,FLR));
  S.cap(FZ,H,[S.bound(FZ,outer,H,true,true),S.bound(FZ,pocket,H,true)],true,'topp');
  S.cap(FZ,FLR,[S.bound(FZ,pocket,FLR,false,true),...floor.map(h=>S.bound(FZ,h,FLR,true))],true,'gulv');
  S.cap(FZ,0,[S.bound(FZ,outer,0,false,true),...floor.map(h=>S.bound(FZ,h,0,false))],false,'bunn');
  S.done(); out['cnc/pultforsterker_v2_revb_kasse_cnc'+SFX+'.step']=doc.text(); log('cnc bad',doc.bad); }
}
for(const mount of [false]){ const nm=`pultforsterker_v2_revb_lokk_${mount?'pultfeste':'frittstaende'}_cnc`; const doc=StepDoc(nm,'Pultforsterker v2 revB lokk CNC 3 mm');
  doc.prism('lokk',FZ,rrect(mount?REVB.lidMountW/2:HW,HD,R),[...(mount?REVB.lidMountSlots.map(ft=>hole(ft)):[]),...REVB.topVents.map(ft=>hole(ft,id,1))],0,3,REVB.lidScrews.map(([x,y])=>({big:circ(x,y,3.2),small:circ(x,y,1.7),depth:1.7})));
  out['cnc/'+nm+'.step']=doc.text(); }
// ===== sheet metal =====
const T=1.5, RI=1.5, RO=RI+T, KF=0.44, BA=Math.PI/2*(RI+KF*T), bX=HW-RO, bY=HD-RO, sideY=HD-T-0.2;
for(const DK of ['oled','tft']){ const SFX=DK==='oled'?'':'_tft';
{ const doc=StepDoc('pultforsterker_v2_revb_kasse_platemetall'+SFX,'Pultforsterker v2 revB kasse platemetall 1.5 mm '+DK);
  const front=frontF(DK).map(ft=>hole(ft,id,0,ft.screw?FSCR:undefined)), back=REVB.back.map(ft=>hole(ft,neg)), left=REVB.left.map(ft=>hole(ft,neg)), right=REVB.right.map(ft=>hole(ft));
  const floor=[...REVB.bottom.map(ft=>hole(ft)), ...REVB.lidScrews.map(([x,y])=>circ(x,y,1.7)), ...REVB.boardPosts.map(([x,y])=>circ(x,y,2.1))];
  doc.prism('bunn',FZ,rrect(bX,bY,0),floor,0,T);
  const wall=hw=>rrect(hw,(H-RO)/2,0,0,(H+RO)/2);
  doc.prism('front',FF,wall(HW),front,HD-T,HD); doc.prism('bak',FB,wall(HW),back,HD-T,HD);
  doc.prism('venstre',FL,wall(sideY),left,HW-T,HW); doc.prism('hoyre',FRt,wall(sideY),right,HW-T,HW);
  const Pp=(c,r,a)=>[c[0]+r*Math.cos(a),c[1]+r*Math.sin(a)], d=Math.PI/180;
  const sector=(c,a0,a1)=>{const A=Pp(c,RO,a0),B=Pp(c,RO,a1),C=Pp(c,RI,a1),E=Pp(c,RI,a0); return [{t:'A',c,r:RO,a:A,b:B,ccw:true},{t:'L',a:B,b:C},{t:'A',c,r:RI,a:C,b:E,ccw:false},{t:'L',a:E,b:A}];};
  doc.prism('bend_front',FX,sector([-bY,RO],180*d,270*d),[],-bX,bX); doc.prism('bend_bak',FX,sector([bY,RO],270*d,360*d),[],-bX,bX);
  doc.prism('bend_hoyre',FY,sector([RO,bX],90*d,180*d),[],-bY,bY); doc.prism('bend_venstre',FY,sector([RO,-bX],180*d,270*d),[],-bY,bY);
  out['platemetall/pultforsterker_v2_revb_kasse_platemetall'+SFX+'.step']=doc.text(); log('sheet bad',doc.bad); }
}
for(const mount of [false]){ const nm=`pultforsterker_v2_revb_lokk_${mount?'pultfeste':'frittstaende'}_platemetall`; const doc=StepDoc(nm,'Pultforsterker v2 revB lokk platemetall 1.5 mm');
  doc.prism('lokk',FZ,rrect(mount?REVB.lidMountW/2:HW,HD,R),[...REVB.topVents.map(ft=>hole(ft)),...REVB.lidScrews.map(([x,y])=>circ(x,y,1.7)),...(mount?REVB.lidMountSlots.map(ft=>hole(ft)):[])],0,T); out['platemetall/'+nm+'.step']=doc.text(); }
function DXF(){ const E=[]; const n=v=>(+v.toFixed(4)).toString();
  const line=(a,b,ly='CUT')=>E.push(`0\nLINE\n8\n${ly}\n10\n${n(a[0])}\n20\n${n(a[1])}\n30\n0\n11\n${n(b[0])}\n21\n${n(b[1])}\n31\n0`);
  const arc=(c,r,a0,a1,ly='CUT')=>E.push(`0\nARC\n8\n${ly}\n10\n${n(c[0])}\n20\n${n(c[1])}\n30\n0\n40\n${n(r)}\n50\n${n(a0)}\n51\n${n(a1)}`);
  const circle=(c,r,ly='CUT')=>E.push(`0\nCIRCLE\n8\n${ly}\n10\n${n(c[0])}\n20\n${n(c[1])}\n30\n0\n40\n${n(r)}`);
  const loop=(segs,ly='CUT')=>segs.forEach(s=>{ if(s.t==='L') line(s.a,s.b,ly); else if(s.a[0]===s.b[0]&&s.a[1]===s.b[1]) circle(s.c,s.r,ly); else {
    const ang=p=>Math.atan2(p[1]-s.c[1],p[0]-s.c[0])*180/Math.PI; const A=ang(s.a),B=ang(s.b); s.ccw?arc(s.c,s.r,A,B,ly):arc(s.c,s.r,B,A,ly);} });
  const text=()=>`0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n2\n0\nLAYER\n2\nCUT\n70\n0\n62\n7\n6\nCONTINUOUS\n0\nLAYER\n2\nBEND\n70\n0\n62\n1\n6\nCONTINUOUS\n0\nENDTAB\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n${E.join('\n')}\n0\nENDSEC\n0\nEOF\n`;
  return {line,loop,text};}
for(const DKF of ['oled','tft']){ const d=DXF(); const yF1=-bY-BA, yF2=yF1-(H-RO), xS1=bX+BA, xS2=xS1+(H-RO);
  const pts=[[-HW,yF2],[HW,yF2],[HW,yF1],[bX,yF1],[bX,-bY],[xS1,-bY],[xS1,-sideY],[xS2,-sideY],[xS2,sideY],[xS1,sideY],[xS1,bY],[bX,bY],[bX,-yF1],[HW,-yF1],[HW,-yF2],[-HW,-yF2],[-HW,-yF1],[-bX,-yF1],[-bX,bY],[-xS1,bY],[-xS1,sideY],[-xS2,sideY],[-xS2,-sideY],[-xS1,-sideY],[-xS1,-bY],[-bX,-bY],[-bX,yF1],[-HW,yF1]];
  pts.forEach((p,i)=>d.line(p,pts[(i+1)%pts.length]));
  const map=(ft,side)=>{ const k=BA+(ft.y-RO); if(side==='front') return {...ft,y:-bY-k}; if(side==='back') return {...ft,y:bY+k}; if(side==='right') return {...ft,x:bX+k,y:ft.x}; return {...ft,x:-(bX+k),y:ft.x}; };
  const rot=ft=>ft.t==='c'?ft:{...ft,w:ft.h,h:ft.w};
  frontF(DKF).forEach(ft=>d.loop(hole(map(ft,'front'),id,0,ft.screw?FSCR:undefined))); REVB.back.forEach(ft=>d.loop(hole(map(ft,'back'))));
  REVB.right.forEach(ft=>d.loop(hole(rot(map(ft,'right'))))); REVB.left.forEach(ft=>d.loop(hole(rot(map(ft,'left')))));
  REVB.bottom.forEach(ft=>d.loop(hole(ft))); REVB.lidScrews.forEach(([x,y])=>d.loop(circ(x,y,1.7))); REVB.boardPosts.forEach(([x,y])=>d.loop(circ(x,y,2.1)));
  [-bY-BA/2, bY+BA/2].forEach(y=>d.line([-bX,y],[bX,y],'BEND')); [-bX-BA/2, bX+BA/2].forEach(x=>d.line([x,-bY],[x,bY],'BEND'));
  out['platemetall/pultforsterker_v2_revb_kasse_flatmonster'+(DKF==='oled'?'':'_tft')+'.dxf']=d.text(); }
for(const mount of [false]){ const d=DXF(); d.loop(rrect(mount?REVB.lidMountW/2:HW,HD,R)); REVB.topVents.forEach(ft=>d.loop(hole(ft))); REVB.lidScrews.forEach(([x,y])=>d.loop(circ(x,y,1.7))); if(mount) REVB.lidMountSlots.forEach(ft=>d.loop(hole(ft)));
  out[`platemetall/pultforsterker_v2_revb_lokk_${mount?'pultfeste':'frittstaende'}_platemetall.dxf`]=d.text(); }
// ===== printed front plate, 4 mm, hidden fixing (blind insert holes from the back) =====
// plate coords: x, y (= body z − 24), z 0 = back (against box), z 4 = front
for(const k of ['oled','tft']){ const P=REVB.plate, nm='pultforsterker_v2_revb_frontplate_'+k+'_skjult_feste'; const doc=StepDoc(nm,'Pultforsterker v2 revB frontplate (print) skjult feste');
  const vw=P.view[k], cv=P.cover[k]; const holes=REVB.front.filter(f=>!f.screw&&!f.hp).slice(1).map(f=>circ(f.x,f.y-24,f.d/2)); const HPf=REVB.front.find(f=>f.hp);
  const L=P.layers, fw=P.face[k], cav=[cv[0]+2*P.cavClr,cv[1]+2*P.cavClr,cv[2]+P.cavClr];
  const lb=rev(rrect(vw[0]/2,vw[1]/2,vw[2],REVB.dispX,0)), lc=rev(rrect(cav[0]/2,cav[1]/2,cav[2],REVB.dispX,0)), lf=rev(rrect(fw[0]/2,fw[1]/2,fw[2],REVB.dispX,0));
  const blind=REVB.front.filter(f=>f.screw).map(f=>({loop:circ(f.x,f.y-24,P.insertD/2),depth:P.insertDepth}));
  { const S=doc.Solid('frontplate'), outer=rrect(P.w/2,P.h/2,P.r); S.sides(FZ,outer,0,P.t); holes.forEach(h=>S.sides(FZ,h,0,P.t));
    doc.stepped(S,FZ,lb,lc,lf,0,L.back,L.back+L.cavity,P.t);
    blind.forEach(({loop,depth})=>{ S.sides(FZ,loop,0,depth); S.cap(FZ,depth,[S.bound(FZ,loop,depth,true,true)],false); });
    const hb=circ(HPf.x,HPf.y-24,5.2), hs=circ(HPf.x,HPf.y-24,3.2); S.sides(FZ,hb,0,2.4); S.sides(FZ,hs,2.4,P.t); S.cap(FZ,2.4,[S.bound(FZ,hb,2.4,true,true),S.bound(FZ,hs,2.4,false)],false);
    S.cap(FZ,P.t,[S.bound(FZ,outer,P.t,true,true),...holes.map(h=>S.bound(FZ,h,P.t,true)),S.bound(FZ,lf,P.t,true),S.bound(FZ,hs,P.t,true)],true);
    S.cap(FZ,0,[S.bound(FZ,outer,0,false,true),...holes.map(h=>S.bound(FZ,h,0,false)),S.bound(FZ,lb,0,false),...blind.map(b=>S.bound(FZ,b.loop,0,false)),S.bound(FZ,hb,0,false)],false); S.done(); }
  { const d=DXF(); d.loop(rrect(cv[0]/2-0.15,cv[1]/2-0.15,cv[2])); out['print/pultforsterker_v2_revb_akryl_skjermglass_'+k+'_2mm.dxf']=d.text(); } out['print/'+nm+'.step']=doc.text(); log(k,'plate bad',doc.bad); }
// ===== printable desk-mount brackets =====
{ const B=REVB.bracket, doc=StepDoc('pultforsterker_v2_revb_pultfeste_braketter','Pultforsterker v2 revB pultfeste-braketter PETG 4 mm');
  for(const side of [1,-1]){ let pts=B.pts.map(([x,y,r])=>[side*x,y,r]); if(side<0) pts=pts.reverse();
    const outer=fpoly(pts.map(p=>[p[0],p[1]]),pts.map(p=>p[2]));
    const slots=B.slots.map(ft=>hole({...ft,x:side*ft.x}));
    const cb=REVB.lidScrews.filter(([x])=>Math.sign(x)===side).map(([x,y])=>({big:circ(x,y,B.screwCb[0]/2),small:circ(x,y,1.7),depth:B.screwCb[1]}));
    doc.prism(side>0?'brakett_hoyre':'brakett_venstre',FZ,outer,slots,0,B.t,cb); }
  out['print/pultforsterker_v2_revb_pultfeste_braketter.step']=doc.text(); log('brackets bad',doc.bad); }
for(const [k,v] of Object.entries(out)) await saveFile(k,v);
log(Object.keys(out).length+' filer');
})();
