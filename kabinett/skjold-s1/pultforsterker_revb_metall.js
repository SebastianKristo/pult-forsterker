import { REVB } from './revb_features.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
const stage=document.querySelector('three-d-stage');
const { THREE } = await stage.ready;
const V2=THREE.Vector2;
const { W, D, H, R } = REVB, HW=W/2, HD=D/2, DX=REVB.dispX;

const M={
  cnc:   new THREE.MeshStandardMaterial({name:'alu_anodisert_sort',color:0x232427,roughness:0.38,metalness:0.75}),
  plate: new THREE.MeshStandardMaterial({name:'pulverlakk_antrasitt',color:0x2e2f32,roughness:0.62,metalness:0.25}),
  print: new THREE.MeshStandardMaterial({name:'petg_antrasitt',color:0x2c2d30,roughness:0.55,metalness:0.12}),
  face:  new THREE.MeshStandardMaterial({name:'petg_lys_khaki',color:0xc9bd9c,roughness:0.6,metalness:0.02}),
  steel: new THREE.MeshStandardMaterial({name:'stål_forsinket',color:0xb9bab6,roughness:0.3,metalness:0.85}),
  brass: new THREE.MeshStandardMaterial({name:'messing',color:0xc2a25a,roughness:0.35,metalness:0.85}),
  black: new THREE.MeshStandardMaterial({name:'skrue_sort',color:0x141415,roughness:0.4,metalness:0.6}),
};
// ---------- 2D helpers ----------
const arcPts=(cx,cy,r,a0,a1,n=12)=>Array.from({length:n+1},(_,i)=>{const a=a0+(a1-a0)*i/n; return new V2(cx+r*Math.cos(a),cy+r*Math.sin(a));});
function rr(hw,hh,r,cx=0,cy=0){ if(r<=0.01) return [new V2(cx-hw,cy-hh),new V2(cx+hw,cy-hh),new V2(cx+hw,cy+hh),new V2(cx-hw,cy+hh)];
  const P=Math.PI; return [...arcPts(cx+hw-r,cy-hh+r,r,-P/2,0),...arcPts(cx+hw-r,cy+hh-r,r,0,P/2),...arcPts(cx-hw+r,cy+hh-r,r,P/2,P),...arcPts(cx-hw+r,cy-hh+r,r,P,1.5*P)];}
const circ=(cx,cy,r,n=40)=>Array.from({length:n},(_,i)=>new V2(cx+r*Math.cos(i/n*2*Math.PI),cy+r*Math.sin(i/n*2*Math.PI)));
function hp(ft,mapU=u=>u,minR=0,d){ const x=mapU(ft.x), y=ft.y;
  if(ft.t==='c') return circ(x,y,(d??ft.d)/2);
  if(ft.t==='s') return rr(ft.w/2,ft.h/2,ft.h/2-0.001,x,y);
  return rr(ft.w/2,ft.h/2,Math.min(Math.max(ft.r||0,minR),Math.min(ft.w,ft.h)/2-0.01),x,y);}
function shape(outer,holes=[]){const s=new THREE.Shape(outer); holes.forEach(h=>s.holes.push(new THREE.Path(h))); return s;}
const geo=(s,d)=>new THREE.ExtrudeGeometry(s,{depth:d,bevelEnabled:false,curveSegments:16});
function mesh(name,g,mat,parent){const m=new THREE.Mesh(g,mat); m.name=name; m.castShadow=m.receiveShadow=true; parent.add(m); return m;}
// placement of a (u,v) shape extruded along w in a wall frame
const basis=(U,V,Wd)=>new THREE.Matrix4().makeBasis(new THREE.Vector3(...U),new THREE.Vector3(...V),new THREE.Vector3(...Wd));
const FR={ z:[[1,0,0],[0,1,0],[0,0,1]], front:[[1,0,0],[0,0,1],[0,-1,0]], back:[[-1,0,0],[0,0,1],[0,1,0]], left:[[0,-1,0],[0,0,1],[-1,0,0]], right:[[0,1,0],[0,0,1],[1,0,0]],
  ax:[[0,1,0],[0,0,1],[1,0,0]], ay:[[0,0,1],[1,0,0],[0,1,0]] };
function panel(name,frame,s,w0,w1,mat,parent){ const m=mesh(name,geo(s,w1-w0),mat,parent); const [U,V,Wd]=FR[frame];
  m.applyMatrix4(basis(U,V,Wd)); m.position.set(Wd[0]*w0,Wd[1]*w0,Wd[2]*w0); return m;}
const neg=u=>-u;

const inner=new THREE.Group(); inner.name='pultforsterker_revb';
const bodies={print:new THREE.Group(), cnc:new THREE.Group(), plate:new THREE.Group()};
Object.entries(bodies).forEach(([k,g])=>{g.name='kasse_'+k; inner.add(g);});
const lids={}; const lidRoot=new THREE.Group(); lidRoot.name='lokk'; inner.add(lidRoot);
const frontRoot=new THREE.Group(); frontRoot.name='frontplate'; inner.add(frontRoot);

const frontWalls=[];
// ---------- CNC body ----------
{ const g=bodies.cnc, WT=2.7, FLR=3, PR=5, iX=HW-WT, iY=HD-WT, mr=1, mat=M.cnc;
  const floorH=[...REVB.bottom.map(f=>hp(f,undefined,mr)),...REVB.lidScrews.map(([x,y])=>circ(x,y,1.7)),...REVB.boardPosts.map(([x,y])=>circ(x,y,1.7))];
  panel('gulv','z',shape(rr(iX+0.01,iY+0.01,PR),floorH),0,FLR,mat,g);
  const bot=rr(HW,HD,R); // underside ring (outside pocket, below floor top) via walls below
  const sx=iX-PR, sy=iY-PR; // straight inner extents
  for(const k of ['oled','tft']){ const c=REVB.dispCut[k]; const fw=panel('front_'+k,'front',shape(rr(sx,H/2,0,0,H/2),REVB.front.map((f,i)=>i===0?rr(c[0]/2,c[1]/2,c[2],DX,24):hp(f,undefined,mr,f.screw?3.4:undefined))),iY,HD,mat,g); fw.userData.disp=k; frontWalls.push(fw); }
  panel('bak','back',shape(rr(sx,H/2,0,0,H/2),REVB.back.map(f=>hp(f,neg,mr))),iY,HD,mat,g);
  panel('venstre','left',shape(rr(sy,H/2,0,0,H/2),REVB.left.map(f=>hp(f,neg,mr))),iX,HW,mat,g);
  panel('hoyre','right',shape(rr(sy,H/2,0,0,H/2),REVB.right.map(f=>hp(f,undefined,mr))),iX,HW,mat,g);
  for(const [sxn,syn] of [[1,1],[1,-1],[-1,1],[-1,-1]]){ // corner pieces between outer R6 and pocket R5
    const oc=[sxn*(HW-R),syn*(HD-R)], ic=[sxn*sx,syn*sy], a=Math.atan2(syn,sxn), a0=a-Math.PI/4, a1=a+Math.PI/4;
    const o=arcPts(oc[0],oc[1],R,a0,a1), i=arcPts(ic[0],ic[1],PR,a1,a0);
    const E=o[o.length-1], Is=i[0], Ie=i[i.length-1], St=o[0], on=(p)=>Math.abs(Math.abs(p.y)-HD)<1e-6;
    const q1=on(E)?new V2(Is.x,E.y):new V2(E.x,Is.y), q2=on(St)?new V2(Ie.x,St.y):new V2(St.x,Ie.y);
    panel('hjorne','z',shape([...o,q1,...i,q2]),0,H,mat,g); }
  // floor underside skin under walls (outer R6 down to z=0 below walls already covered by wall panels from z=0)
}
// ---------- sheet metal body ----------
const T=1.5, RI=1.5, RO=3, bX=HW-RO, bY=HD-RO, sideY=HD-T-0.2;
{ const g=bodies.plate, mat=M.plate;
  const floorH=[...REVB.bottom.map(f=>hp(f)),...REVB.lidScrews.map(([x,y])=>circ(x,y,1.7)),...REVB.boardPosts.map(([x,y])=>circ(x,y,2.1))];
  panel('bunn','z',shape(rr(bX,bY,0),floorH),0,T,mat,g);
  const wallS=(hw,holes)=>shape(rr(hw,(H-RO)/2,0,0,(H+RO)/2),holes);
  for(const k of ['oled','tft']){ const c=REVB.dispCut[k]; const fw=panel('front_'+k,'front',wallS(HW,REVB.front.map((f,i)=>i===0?rr(c[0]/2,c[1]/2,c[2],DX,24):hp(f,undefined,0,f.screw?3.4:undefined))),HD-T,HD,mat,g); fw.userData.disp=k; frontWalls.push(fw); }
  panel('bak','back',wallS(HW,REVB.back.map(f=>hp(f,neg))),HD-T,HD,mat,g);
  panel('venstre','left',wallS(sideY,REVB.left.map(f=>hp(f,neg))),HW-T,HW,mat,g);
  panel('hoyre','right',wallS(sideY,REVB.right.map(f=>hp(f))),HW-T,HW,mat,g);
  const sector=(c,a0,a1)=>shape([...arcPts(c[0],c[1],RO,a0,a1,10),...arcPts(c[0],c[1],RI,a1,a0,10)]);
  const d=Math.PI/180;
  panel('bend_front','ax',sector([-bY,RO],180*d,270*d),-bX,bX,mat,g);
  panel('bend_bak','ax',sector([bY,RO],270*d,360*d),-bX,bX,mat,g);
  panel('bend_hoyre','ay',sector([RO,bX],90*d,180*d),-bY,bY,mat,g);
  panel('bend_venstre','ay',sector([RO,-bX],180*d,270*d),-bY,bY,mat,g);
  // PEM clinch nuts behind front-plate screw holes, SO standoffs for the board
}
// standoffs (CNC + sheet): hex M3, lid at z 48, board at z 27.5
function standoffs(g,floor){ REVB.lidScrews.forEach(([x,y])=>{const h=H-floor; const m=mesh('standoff_m3_lokk',new THREE.CylinderGeometry(3.17,3.17,h,6),M.brass,g); m.rotation.x=Math.PI/2; m.position.set(x,y,floor+h/2);});
  REVB.boardPosts.forEach(([x,y])=>{const h=REVB.boardZ-floor; const m=mesh('standoff_m3_kort',new THREE.CylinderGeometry(3.17,3.17,h,6),M.brass,g); m.rotation.x=Math.PI/2; m.position.set(x,y,floor+h/2);}); }
standoffs(bodies.cnc,3); standoffs(bodies.plate,T);
// ---------- lids ----------
function metalLid(key,mount,t,mat,cbore){ const g=new THREE.Group(); g.name='lokk_'+key; lidRoot.add(g); lids[key]=g;
  const outer=rr(mount?REVB.lidMountW/2:HW,HD,R), slots=mount?REVB.lidMountSlots.map(f=>hp(f)):[];
  if(cbore){ panel('lokk_under','z',shape(outer,[...slots,...REVB.topVents.map(f=>hp(f)),...REVB.lidScrews.map(([x,y])=>circ(x,y,1.7))]),H,H+t-1.7,mat,g);
    const b=0.6, sh=shape(rr(mount?REVB.lidMountW/2-b:HW-b,HD-b,R-b),[...slots,...REVB.topVents.map(f=>hp(f)),...REVB.lidScrews.map(([x,y])=>circ(x,y,3.2+b))]); const m=mesh('lokk_over',new THREE.ExtrudeGeometry(sh,{depth:1.7-2*b,bevelEnabled:true,bevelThickness:b,bevelSize:b,bevelSegments:4,curveSegments:24}),mat,g); m.position.z=H+t-1.7+b; }
  else { const b=0.5, sh=shape(rr(mount?REVB.lidMountW/2-b:HW-b,HD-b,R-b),[...slots,...REVB.topVents.map(f=>hp(f)),...REVB.lidScrews.map(([x,y])=>circ(x,y,1.7+b))]); const m=mesh('lokk',new THREE.ExtrudeGeometry(sh,{depth:t-2*b,bevelEnabled:true,bevelThickness:b,bevelSize:b,bevelSegments:4,curveSegments:24}),mat,g); m.position.z=H+b; }
  const z=cbore?H+t-1.7:H+t; REVB.lidScrews.forEach(([x,y])=>{const s=mesh('skrue_iso7380_m3',new THREE.SphereGeometry(2.85,24,10,0,Math.PI*2,0,Math.PI/2),M.black,g); s.scale.set(1,0.58,1); s.rotation.x=Math.PI/2; s.position.set(x,y,z);});
}
metalLid('cnc_fritt',false,3,M.cnc,true); metalLid('plate_fritt',false,T,M.plate,false);

// ---------- STL parts (print body, print lids, printed front plates) ----------
const loader=new STLLoader();
const loadSTL=(url,mat,parent,name)=>new Promise(res=>loader.load(url,g=>{g.computeVertexNormals(); res(mesh(name,g,mat,parent));},undefined,()=>res(null)));
const fronts={};
await Promise.all([
  loadSTL('uploads/v2_body_revb.stl',M.print,bodies.print,'kasse_print'),
  ...[['print_fritt','uploads/v2_lid_frittstaende_revb.stl']].map(([k,u])=>{const g=new THREE.Group(); g.name='lokk_'+k; lidRoot.add(g); lids[k]=g; return loadSTL(u,M.print,g,'lokk').then(m=>{ if(m) m.position.z=H; });}),
]);


// ================= components =================
const C={
  dark:  new THREE.MeshStandardMaterial({name:'sort_plast',color:0x141415,roughness:0.5,metalness:0.1}),
  btn:   new THREE.MeshStandardMaterial({name:'stål_sortoksidert',color:0x1b1b1d,roughness:0.32,metalness:0.7}),
  knob:  new THREE.MeshStandardMaterial({name:'alu_sort_matt',color:0x161618,roughness:0.62,metalness:0.45}),
  acryl: new THREE.MeshPhysicalMaterial({name:'akryl_royksort',color:0x050506,roughness:0.08,metalness:0,clearcoat:1,clearcoatRoughness:0.04}),
  knurl: new THREE.MeshStandardMaterial({name:'rifling',color:0x202023,roughness:0.45,metalness:0.5,flatShading:true}),
  shell: new THREE.MeshStandardMaterial({name:'nikkel',color:0xcfd0cc,roughness:0.25,metalness:0.9}),
  pcb:   new THREE.MeshStandardMaterial({name:'pcb_gronn',color:0x1d5a3a,roughness:0.6}),
  pcbB:  new THREE.MeshStandardMaterial({name:'pcb_bla',color:0x1f4a7a,roughness:0.6}),
  red:   new THREE.MeshStandardMaterial({name:'pol_rod',color:0xa3261d,roughness:0.35}),
  blk:   new THREE.MeshStandardMaterial({name:'pol_sort',color:0x1a1a1a,roughness:0.35}),
  heat:  new THREE.MeshStandardMaterial({name:'kjoleribbe',color:0x3a3b3f,roughness:0.4,metalness:0.7}),
  cap:   new THREE.MeshStandardMaterial({name:'elektrolytt',color:0x24324a,roughness:0.4}),
  coil:  new THREE.MeshStandardMaterial({name:'spole',color:0x2b2b2b,roughness:0.7}),
  glass: new THREE.MeshStandardMaterial({name:'glass',color:0x050607,roughness:0.06,metalness:0.2}),
  cable: new THREE.MeshStandardMaterial({name:'kabel',color:0xeeeeec,roughness:0.75}),
  cRed:  new THREE.MeshStandardMaterial({name:'kabel_rod',color:0x9e2a22,roughness:0.6}),
  pi:    new THREE.MeshStandardMaterial({name:'pi_gronn',color:0x2f6b3a,roughness:0.6}),
};
const parts=new THREE.Group(); parts.name='komponenter'; inner.add(parts);
const pick=[]; // clickable / hoverable
function lab(o,label,act){ o.traverse(m=>{m.userData.label=label; if(act) m.userData.act=act;}); pick.push(o); return o; }
const grp=(name,p=parts)=>{const g=new THREE.Group(); g.name=name; p.add(g); return g;};
const box=(n,w,d,h,mat,par,pos)=>{const m=mesh(n,new THREE.BoxGeometry(w,d,h),mat,par); m.position.set(...pos); return m;};
const cylY=(n,r,len,mat,par,pos,seg=32,r2=r)=>{const m=mesh(n,new THREE.CylinderGeometry(r2,r,len,seg),mat,par); m.position.set(...pos); return m;}; // axis = y
const cylZ=(n,r,len,mat,par,pos,seg=32)=>{const m=cylY(n,r,len,mat,par,pos,seg); m.rotation.x=Math.PI/2; return m;};
const cylX=(n,r,len,mat,par,pos,seg=32)=>{const m=cylY(n,r,len,mat,par,pos,seg); m.rotation.z=Math.PI/2; return m;};
const FY=-HD-REVB.plate.t; // front face of printed plate
const setLed=(m,on,k=1,off=0x8a8c90)=>{m.emissive.set(on?0xffffff:0); m.emissiveIntensity=on?1.6*k:0; m.color.set(on?0xffffff:off);};

// --- display (OLED / TFT) with live canvas
const cvs=document.createElement('canvas'); cvs.width=512; cvs.height=256;
const cvt=document.createElement('canvas'); cvt.width=640; cvt.height=480;
const texO=new THREE.CanvasTexture(cvs), texT=new THREE.CanvasTexture(cvt); [texO,texT].forEach(t=>{t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8;});
const disp={oled:grp('oled'), tft:grp('tft')};
{ const WI=-(HD-2.7); const g=disp.oled; box('oled_glass',60.5,1.3,37,C.glass,g,[DX,WI+0.66,24]);
  const sc=mesh('oled_bilde',new THREE.PlaneGeometry(55,27.5),new THREE.MeshBasicMaterial({map:texO,toneMapped:false,color:0xd8d8d8,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}),g); sc.rotation.x=Math.PI/2; sc.rotation.y=Math.PI; sc.rotation.set(Math.PI/2,0,0); sc.rotateX(Math.PI); sc.position.set(DX,-HD-REVB.plate.layers.back-REVB.plate.layers.cavity-0.04,24);
  box('oled_pcb',70,1.6,40,C.pcbB,g,[DX,WI+2.1,24]); [[-33,18],[33,18],[-33,-18],[33,-18]].forEach(([dx,dz])=>cylY('m2_skrue',1.9,1.4,M.black,g,[DX+dx,WI+3.6,24+dz],16)); box('i2c_header',10.2,2.5,8.5,C.dark,g,[DX,WI+4.2,24+15]); lab(g,'OLED 2,42″ 128×64 · SSD1309 · I2C · hvit');
  const t=disp.tft; box('tft_glass',58,1.3,44,C.glass,t,[DX,WI+0.66,24]);
  const st=mesh('tft_bilde',new THREE.PlaneGeometry(48.96,36.72),new THREE.MeshBasicMaterial({map:texT,toneMapped:false,color:0xd8d8d8,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}),t); st.rotation.set(Math.PI/2,0,0); st.rotateX(Math.PI); st.position.set(DX,-HD-REVB.plate.layers.back-REVB.plate.layers.cavity-0.04,24);
  box('tft_pcb',77,1.6,43,C.pcbB,t,[DX,WI+2.1,24]); lab(t,'TFT 2,4″ 320×240 touch (ILI9341 + XPT2046)'); }
// image planes face -y (toward viewer): PlaneGeometry faces +z; rotate so normal = -y
[disp.oled,disp.tft].forEach(g=>g.children.filter(m=>m.name.endsWith('bilde')).forEach(m=>{m.rotation.set(0,0,0); m.up.set(0,0,1); m.lookAt(m.position.x,m.position.y-1,m.position.z);}));

// --- metal push buttons with LED rings
const WL={air:{k:'AIR',t:'Midnight City',s:'M83 · iPhone'},bt:{k:'BT',t:'Teardrop',s:'Massive Attack · Sebastians iPhone'}};
const PRESETS=[['NRK P1','Distriktsprogram'],['NRK P2','Kultur og samfunn'],['NRK P3','Pop og humor'],['P4 Norge','Hits'],['Radio Norge','Pop og rock'],['NRK Klassisk','Klassisk musikk']];
const INPUTS=[{k:'AIR',n:'AirPlay · BT',t:'Midnight City',s:'M83 · iPhone'},{k:'AUX',n:'AUX',t:'Linje inn',s:'3,5 mm · analog'},{k:'RADIO',n:'Radio',t:'NRK P2',s:'Lyrion · internettradio'},{k:'USB',n:'USB-lyd',t:'PC 1',s:'48 kHz · 24 bit'}];
const BTN=[[22,32.5],[38,32.5],[22,15.5],[38,15.5]]; // AIRPLAY·BT, AUX / RADIO, USB
function metalButton(name,x,z,rHead,rCap,label,act){ const g=grp(name); g.position.set(x,FY,z);
  cylY('mutter',rHead+1.6,2,C.btn,g,[0,1+REVB.plate.t+2.7,0],6);               // nut inside wall
  cylY('hus',rHead-1,24,C.btn,g,[0,12,0]);                          // body through plate+wall
  // flat black oxidized bezel with soft front edge, thin flush LED ring, flat black plunger (12/16 mm AliExpress parts)
  const hH=rHead>8?2.4:2.0, rIn=rCap+0.9, toFront=m=>{m.applyMatrix4(basis([1,0,0],[0,0,1],[0,-1,0])); return m;};
  const bz=0.35, bez=mesh('hode',new THREE.ExtrudeGeometry(shape(circ(0,0,rHead-bz,64),[circ(0,0,rIn+bz,64)]),{depth:hH-bz,bevelEnabled:true,bevelThickness:bz,bevelSize:bz,bevelSegments:3,curveSegments:48}),C.btn,g);
  bez.geometry.translate(0,0,-bz*0); toFront(bez);
  const ledM=new THREE.MeshStandardMaterial({name:'led_ring',color:0x2a2a2a,roughness:0.35});
  toFront(mesh('led_ring',new THREE.ExtrudeGeometry(shape(circ(0,0,rIn+0.05,64),[circ(0,0,rCap+0.1,64)]),{depth:hH-0.3,bevelEnabled:false,curveSegments:48}),ledM,g));
  const cap=cylY('knapp',rCap,hH-0.45,C.btn,g,[0,-(hH-0.45)/2,0],48);
  g.userData.cap=cap; g.userData.led=ledM; lab(g,label,act); return g; }
const BLAB=['AirPlay · BT (trykk = bytt, hold = BT-paring)','AUX inn','Radio (trykk = neste av 6 favoritter)','USB-lyd'];
const inBtns=INPUTS.map((it,i)=>metalButton('knapp_'+it.k,BTN[i][0],BTN[i][1],7,5,BLAB[i]+' · 12 mm metallknapp, hvit LED-ring',()=>selectInput(i)));
inBtns[0].traverse(m=>m.userData.hold=()=>holdPair());
const pwrBtn=metalButton('power',-76,24,9.5,6.6,'Power · trykk = av/på · hold = omstart av Raspberry Pi',()=>{ if(!S.main) return; S.power=!S.power; press(pwrBtn); if(S.power) startBoot(); refresh(); });
pwrBtn.traverse(m=>m.userData.hold=()=>holdReboot());
// --- volume knob + EC11 encoder
const knob=grp('volumknapp'); knob.position.set(66,FY,24);
{ const prof=[new V2(0,0.6),new V2(14.4,0.6),new V2(15,1.2),new V2(15,16.4),new V2(14.4,17),new V2(0,17)];
  const k=mesh('knapp_kropp',new THREE.LatheGeometry(prof,96),C.knob,knob); k.rotation.x=Math.PI;
  { const ln=mesh('knapp_strek',new THREE.BoxGeometry(1.1,0.25,8),new THREE.MeshBasicMaterial({name:'knapp_strek_hvit',color:0xf2f2ee,toneMapped:false}),knob); ln.position.set(0,-17.08,9.5); ln.castShadow=false; }
  lab(knob,'Volum · alu-knapp 30 × 17 mm, 6 mm D-aksel · EC11 (trykk = mute, scroll = volum)',()=>{S.muted=!S.muted; refresh();}); }
const enc=grp('enkoder'); box('ec11',12,6.5,13,C.dark,enc,[66,-(HD-2.7)+3.25,24]); box('kontroll_pcb',26,1.6,26,C.pcbB,enc,[66,-(HD-2.7)+7.3,24]); lab(enc,'EC11 roterende enkoder + kontrollkort');
// --- main board (posts 172 × 92) at z 27.5
const mb=grp('hovedkort'); const bx0=(REVB.boardPosts[0][0]+REVB.boardPosts[2][0])/2, by0=(REVB.boardPosts[0][1]+REVB.boardPosts[1][1])/2, bz=REVB.boardZ;
box('pcb',180,100,1.6,C.pcb,mb,[bx0,by0,bz+0.8]); lab(mb,'Hovedkort 180 × 100 mm (PCBWay) · M3-hull 172 × 92');
const pi=grp('pi',mb); box('pi_zero2w',65,30,1.4,C.pi,pi,[-22,30,bz+1.6+6]); box('soc',12,12,1.2,C.dark,pi,[-30,30,bz+1.6+7.3]); box('header',51,5,8.5,C.dark,pi,[-22,42,bz+1.6+3]); lab(pi,'Raspberry Pi Zero 2 W (Lyrion / Squeezelite)');
const amp=grp('forsterker',mb); box('amp_ic',14,14,2,C.dark,amp,[30,-5,bz+2.6]);
for(let i=0;i<9;i++) box('ribbe',1.4,30,9,C.heat,amp,[18+i*3,-5,bz+1.6+4+4.5]); box('ribbe_fot',28,30,4,C.heat,amp,[30,-5,bz+1.6+2]); amp.position.x=0;
[[50,-30],[62,-30],[50,-18],[62,-18]].forEach(([x,y])=>box('spole',10,10,7,C.coil,amp,[x,y,bz+1.6+3.5]));
[[52,15],[64,15],[52,30],[64,30]].forEach(([x,y])=>cylZ('kondensator',5,13,C.cap,amp,[x,y,bz+1.6+6.5]));
{ const tb=grp('termoblokk',mb); box('alu_blokk',24,24,bz-3-1.2,new THREE.MeshStandardMaterial({name:'alu_blokk',color:0xbfc1c4,roughness:0.35,metalness:0.8}),tb,[30,-5,3+(bz-3-1.2)/2]);
  box('termopute_topp',22,22,0.6,new THREE.MeshStandardMaterial({color:0x6aa0c8,roughness:0.9}),tb,[30,-5,bz-0.3]); box('termopute_bunn',22,22,0.6,new THREE.MeshStandardMaterial({color:0x6aa0c8,roughness:0.9}),tb,[30,-5,3.3]);
  lab(tb,'Termoblokk alu 24 × 24 mm + termoputer · leder varmen fra forsterkerbrikken til bunnplaten · 2 × M3 nedenfra'); }
lab(amp,'Klasse-D forsterker 2 × 50 W (kjøleribbe, utgangsfilter, bulk-kondensatorer)');
const hub=grp('usb_hub',mb); box('hub_ic',8,8,1,C.dark,hub,[-80,-5,bz+2.1]);
REVB.left.forEach(f=>{ box('usb_a_skall',14,13.2,6.6,C.shell,hub,[-(HW-2.7)+7.2,f.x,f.y]); box('usb_a_tunge',12,10.6,1.8,C.dark,hub,[-(HW-2.7)+7.6,f.x,f.y-1.1]); });
lab(hub,'USB 2.0-hub / switch · 4 × USB-A (venstre side)');
// --- back panel
const back=grp('bakpanel'); const BY=HD;
const rk=grp('vippebryter',back); box('ramme',21,2.4,15,C.dark,rk,[70,BY+1.2,24]); const vip=box('vippe',17,3,11,C.dark,rk,[70,BY+2.6,24]); box('hus',19,20,13,C.dark,rk,[70,BY-10,24]);
lab(rk,'Hovedbryter · vippebryter 19 × 13 mm',()=>{S.main=!S.main; if(!S.main) S.power=false; else { S.power=true; startBoot(); } refresh();});
const lan=grp('lan',back); box('flens',33,2,19,C.dark,lan,[34,BY+1,13.5]); box('port',12,0.6,10,new THREE.MeshStandardMaterial({color:0x050505}),lan,[34,BY+2.05,13]); box('hus',16,22,14,C.shell,lan,[34,BY-11,13.5]);
[21,47].forEach(x=>cylY('skrue',2.4,1,C.shell,lan,[x,BY+2.5,13.5],16)); lab(lan,'RJ45 LAN · panelfeste');
const dc=grp('dc',back); cylY('mutter',7.2,2,C.shell,dc,[34,BY+1,34],6); cylY('hylse',5.4,6,C.dark,dc,[34,BY+3,34]); cylY('hull',3.1,0.4,new THREE.MeshStandardMaterial({color:0x050505}),dc,[34,BY+6.05,34]); cylY('pinne',1.05,4,C.shell,dc,[34,BY+4.2,34],12); lab(dc,'DC 19–24 V inn · 5,5/2,5 mm');
const aux=grp('aux',back); cylY('mutter',4.6,2,C.shell,aux,[-14,BY+1,24],6); cylY('hylse',3.4,3,C.dark,aux,[-14,BY+3.5,24]); cylY('hull',1.8,0.4,new THREE.MeshStandardMaterial({color:0x050505}),aux,[-14,BY+5.05,24]); lab(aux,'AUX inn · 3,5 mm jack');
{ const gs=grp('jordskrue',back); cylY('tannskive',3.4,0.5,C.shell,gs,[52,BY+0.25,40],20); cylY('skruehode',2.75,2.2,C.shell,gs,[52,BY+1.6,40],6); cylY('kabelsko',3.6,0.8,M.brass,gs,[52,BY-1.4,40],20);
  lab(gs,'Jordpunkt M3 · stjernejord ved DC-inngangen (kasse → signaljord)'); }
const POSTS=[[-84,'L+',C.red],[-70,'L−',C.blk],[-54,'R+',C.red],[-40,'R−',C.blk]];
POSTS.forEach(([x,l,m])=>{const g=grp('pol_'+l,back); cylY('base',6,2,m,g,[x,BY+1,24]); cylY('kropp',4.6,10,m,g,[x,BY+7,24],32,4.2); cylY('topp',5.2,3,m,g,[x,BY+13.5,24]); cylY('stamme',3,6,C.shell,g,[x,BY-3,24]); lab(g,'Høyttalerpol '+l+' · 4 mm banan');});
const sma=grp('bt_antenne',back); cylY('mutter',4.4,2,C.shell,sma,[-26,BY+1,24],6); cylY('sma',3.1,7,C.shell,sma,[-26,BY+4.5,24]); 
lab(sma,'SMA-kontakt for BT/Wi-Fi-antenne (antenne ikke montert)');

['PC 1','PC 2','Service'].forEach((l,i)=>{const x=6, zc=[34,24,14][i]; const g=grp('usbc_'+i,back); box('flens',18,1.6,8.5,C.dark,g,[x,BY+0.8,zc]);
  const sh=mesh('skall',new THREE.CapsuleGeometry(1.6,5.6,6,16),C.shell,g); sh.rotation.z=Math.PI/2; sh.scale.set(1,1,1); sh.position.set(x,BY+1.4,zc); box('tunge',6.6,1,0.7,C.dark,g,[x,BY+2.1,zc]); box('kabel_inn',10,16,6,C.dark,g,[x,BY-8,zc]); lab(g,'USB-C '+l+' · panelfeste');});
[34,24,14].forEach(z=>[-3.5,15.5].forEach(x=>cylY('skrue_usbc',2.2,1,C.shell,back,[x,BY+2.1,z],16)));
// --- front plate screws (countersunk M3 into body)
// --- internal wiring (ribbon to front, posts)
// ---------- details ----------
// laser-etched legends (canvas text, tinted per finish)
const legendMats=[];
function legend(text,w,h,pos,face,par=parts,bold=true,fixed){ const k=8, c=document.createElement('canvas'); c.width=Math.ceil(w*k*4); c.height=Math.ceil(h*k*4);
  const g=c.getContext('2d'); g.fillStyle='#fff'; g.textAlign='center'; g.textBaseline='middle'; g.font=(bold?'600 ':'400 ')+(c.height*0.78)+'px -apple-system,"SF Pro Text","Helvetica Neue",Arial,sans-serif';
  if('letterSpacing' in g) g.letterSpacing=(c.height*0.08)+'px'; g.fillText(text,c.width/2,c.height/2);
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8;
  const m=new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false,color:fixed??0x55575b}); if(fixed===undefined) legendMats.push(m);
  const p=mesh('etikett_'+text,new THREE.PlaneGeometry(w,h),m,par); p.castShadow=false; p.position.set(...pos);
  const n={front:[0,-1,0],back:[0,1,0],left:[-1,0,0],top:[0,0,1]}[face]; p.up.set(...(face==='top'?[0,1,0]:[0,0,1])); p.lookAt(pos[0]+n[0],pos[1]+n[1],pos[2]+n[2]); return p; }
const fy=FY-0.05;
function logo(par,pos,w=60,tag=true,fixed){ const c=document.createElement('canvas'); c.width=1200; c.height=tag?260:180; const g=c.getContext('2d'); g.fillStyle='#fff';
  const bars=[[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]], k=3.4; bars.forEach(([x,h])=>{ g.beginPath(); g.roundRect(20+x*k,30,4.6*k,h*k,2.3*k); g.fill(); });
  g.textBaseline='alphabetic'; g.font='600 120px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; if('letterSpacing' in g) g.letterSpacing='17px'; g.fillText('SKJOLD',230,135);
  if(tag){ g.font='400 40px "IBM Plex Mono",Menlo,monospace'; if('letterSpacing' in g) g.letterSpacing='12px'; g.fillText('STREAMING AMPLIFIER',232,205); }
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8; const m=new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false,color:fixed??0x55575b}); if(fixed===undefined) legendMats.push(m);
  const p=mesh('logo_skjold',new THREE.PlaneGeometry(w,w*c.height/c.width),m,par); p.castShadow=false; p.position.set(...pos); p.up.set(0,1,0); p.lookAt(pos[0],pos[1],pos[2]+1); return p; }
[['AIRPLAY · BT',22,41.6,17],['AUX',38,41.6,11],['RADIO',22,6.4,11],['USB',38,6.4,11]].forEach(([t,x,z,w])=>legend(t,w,1.9,[x,fy,z],'front',parts,true,0x161617));
legend('POWER',11,1.9,[-76,fy,37.4],'front',parts,true,0x161617);
// 3.5 mm headphone jack under the power button (nickel nut on the plate, plug toggles on click)
const hpJack=grp('hodetelefon'); { const J=[-76,8];
  cylY('mutter_riflet',4.6,2,C.shell,hpJack,[J[0],-HD-1.2,J[1]],24); cylY('gjenge',3.0,4.4,C.shell,hpJack,[J[0],-HD-2.2,J[1]],32); cylY('hylse',2.2,0.6,C.dark,hpJack,[J[0],FY+0.6,J[1]],32);
  cylY('hull',1.8,0.3,new THREE.MeshStandardMaterial({color:0x050505}),hpJack,[J[0],FY+0.28,J[1]],24); box('jack_hus',8,12,10,C.dark,hpJack,[J[0],-(HD-2.7)+6,J[1]+1]);
  const plug=grp('plugg',hpJack); cylY('plugg_hals',3.2,6,C.dark,plug,[J[0],FY-4.3,J[1]],24); cylY('plugg_kropp',4.2,14,C.dark,plug,[J[0],FY-14.3,J[1]],24,3.6); cylY('kabel',1.6,30,C.dark,plug,[J[0],FY-36,J[1]],12); hpJack.userData.plug=plug;
  lab(hpJack,'Hodetelefon · PJ-392 nikkel, festet i metallveggen · mutter skjult bak frontplaten (klikk = plugg)',()=>{S.hp=!S.hp; refresh();});
  { const c=document.createElement('canvas'); c.width=c.height=128; const g=c.getContext('2d'); g.strokeStyle='#fff'; g.lineWidth=11; g.lineCap='round';
    g.beginPath(); g.arc(64,70,40,Math.PI,0); g.stroke(); g.fillStyle='#fff'; g.beginPath(); g.roundRect(18,70,20,36,6); g.fill(); g.beginPath(); g.roundRect(90,70,20,36,6); g.fill();
    const t=new THREE.CanvasTexture(c); const m=new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false,color:0x161617}); const p=mesh('hodetelefon_ikon',new THREE.PlaneGeometry(3.6,3.6),m,parts); p.position.set(-68.6,fy,8); p.up.set(0,0,1); p.lookAt(-68.6,fy-1,8); } }
const by=HD+0.05;
[['L +',-84],['L −',-70],['R +',-54],['R −',-40],['BT',-26],['AUX',-14]].forEach(([t,x])=>legend(t,9,1.9,[x,by,33.5],'back'));
[['PC 1',34],['PC 2',24],['SERV',14]].forEach(([t,z])=>legend(t,8,1.6,[21,by,z+4.2],'back')); legend('USB-C',10,1.9,[6,by,40.2],'back');
legend('LAN',8,1.7,[34,by,24.6],'back'); legend('GND',7,1.7,[52,by,44.2],'back'); legend('DC 19–24 V',16,1.9,[34,by,42.5],'back'); legend('I / O',9,1.9,[70,by,33.5],'back');
legend('L',4,2.4,[-77,by,42.5],'back'); legend('R',4,2.4,[-47,by,42.5],'back');
REVB.left.forEach((f,i)=>legend('USB '+(i+1),11,1.9,[-HW-0.05,f.x,40.2],'left'));
const lidLegend={position:{}};
// underside product label: logo + product name + designer (laser-marked by JLC or printed)
{ const c=document.createElement('canvas'); c.width=1400; c.height=560; const g=c.getContext('2d'); g.fillStyle='#fff';
  [[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]].forEach(([x,h])=>{ g.beginPath(); g.roundRect(330+x*3,40,13.8,h*3,6.9); g.fill(); });
  g.font='600 104px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; if('letterSpacing' in g) g.letterSpacing='15px'; g.fillText('SKJOLD',500,140);
  g.font='400 34px "IBM Plex Mono",Menlo,monospace'; if('letterSpacing' in g) g.letterSpacing='10px'; g.fillText('STREAMING AMPLIFIER',502,200);
  g.textAlign='center'; if('letterSpacing' in g) g.letterSpacing='2px';
  g.font='500 46px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; g.fillText('Skjold S1',700,320);
  g.font='400 32px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; g.fillText('Designet av Sebastian Kristo Jemtland i Norge',700,385);
  g.font='400 28px "IBM Plex Mono",Menlo,monospace'; g.fillText('19–24 V ⎓ 3 A  ·  Modell S1  ·  Serienr. SKJ-S1-0001',700,445);
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8; const m=new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false,color:0x55575b,side:THREE.DoubleSide}); legendMats.push(m);
  const p=mesh('produktetikett_under',new THREE.PlaneGeometry(75,30),m,parts); p.castShadow=false; p.position.set(0,47,-0.06); p.up.set(0,-1,0); p.lookAt(0,47,-1.06);
  lab(p,'Produktmerking under kassen · lasermerket (JLC) eller trykt'); }
// low rubber feet: 3M Bumpon SJ5076-type, Ø12.7 × 3.5 mm, stuck on (no screws)
const padM=new THREE.MeshStandardMaterial({name:'gummi',color:0x1a1a1b,roughness:0.95});
[[-(HW-17.5),-62],[HW-17.5,-62],[-(HW-17.5),62],[HW-17.5,62]].forEach(([x,y])=>{ const g=grp('gummifot'); const p=[new V2(0,0),new V2(6.35,0),new V2(6.35,-2.2),new V2(5.4,-3.2),new V2(3.5,-3.5),new V2(0,-3.5)]; const m=mesh('fot',new THREE.LatheGeometry(p,48),padM,g); m.rotation.x=Math.PI/2; g.position.set(x,y,0); lab(g,'Gummifot Ø12,7 × 3,5 mm (selvklebende)'); });
// power toggle symbol (IEC ⏻) as lit geometry on the plunger — moves with it when pressed
{ const m=new THREE.MeshBasicMaterial({name:'power_symbol',color:0x3a3a3d,toneMapped:false}); pwrBtn.userData.sym=m; const cap=pwrBtn.userData.cap, fy0=-(2.4-0.45)/2-0.12;
  const ag=new THREE.TorusGeometry(2.35,0.32,10,48,Math.PI*2*(280/360)); ag.rotateZ((90+40)*Math.PI/180); ag.rotateX(Math.PI/2); const arc=mesh('power_ring',ag,m,cap); arc.position.y=fy0; arc.castShadow=false;
  const bar=mesh('power_strek',new THREE.BoxGeometry(0.64,0.3,3.0),m,cap); bar.position.set(0,fy0,1.45); bar.castShadow=false; }
// binding posts: gold contact rings
POSTS.forEach(([x])=>cylY('kontakt_gull',4.75,1.2,M.brass,back,[x,BY+9,24],32));
// PCB detail: SMD parts, headers, crystal, LED
{ let seed=7; const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647; const smd=new THREE.MeshStandardMaterial({color:0x1c1c1c,roughness:0.5}), res=new THREE.MeshStandardMaterial({color:0x2b2018,roughness:0.6}), tin=new THREE.MeshStandardMaterial({color:0xd0d2d4,roughness:0.3,metalness:0.9});
  const free=(x,y)=>!(x>12&&x<72&&y>-38&&y<38)&&!(x>-58&&x<14&&y>12&&y<48)&&!(x<-86);
  for(let i=0;i<140;i++){ const x=bx0-88+rnd()*176, y=by0-48+rnd()*96; if(!free(x,y)) continue; const big=rnd()<0.15;
    box('smd',big?5+rnd()*4:1.6+rnd()*1.4,big?5+rnd()*4:0.8+rnd()*0.8,big?1:0.6,big?smd:res,mb,[x,y,bz+1.6+(big?0.5:0.3)]); }
  for(let i=0;i<20;i++) box('stift',0.64,0.64,6,tin,mb,[-46+i*2.54,42,bz+1.6+5.5]);
  box('krystall',5,3.2,1.2,tin,mb,[-70,-20,bz+2.2]); box('usb_hub_ic',7,7,1,smd,mb,[-82,-30,bz+2.1]);
  box('kontakt_front',20,6,7,new THREE.MeshStandardMaterial({color:0xeeeeea,roughness:0.5}),mb,[-30,-44,bz+5.1]);
  for(let i=0;i<4;i++) box('skrueklemme',7.5,9,10,new THREE.MeshStandardMaterial({color:0x2f7a4a,roughness:0.5}),mb,[-86+i*8,46,bz+6.6]); }
// ---------- display drawing ----------
const T0=performance.now();
// boot splash: Skjold logo, bars fade in one by one, then wordmark (2.6 s)
let bootT=performance.now(), bootRAF=0; const BOOT=2600;
function startBoot(){ bootT=performance.now(); cancelAnimationFrame(bootRAF); const tick=()=>{ drawOLED(); drawTFT(); if(performance.now()-bootT<BOOT+1300) bootRAF=requestAnimationFrame(tick); }; tick(); }
function drawSplash(g,w,h,sc){ const t=(performance.now()-bootT)/BOOT, bars=[[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]];
  { g.font='600 13px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; if('letterSpacing' in g) g.letterSpacing='2px'; const unit=41*0.62+6+g.measureText('SKJOLD').width;
    sc=Math.min(w*0.78/unit, h*0.5/(42*0.62)); }
  const k=sc*0.62, mw=41*k, F='600 '+(13*sc)+'px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; g.font=F; if('letterSpacing' in g) g.letterSpacing=(2*sc)+'px';
  const tw=g.measureText('SKJOLD').width, gap=6*sc, x0=(w-(mw+gap+tw))/2, y0=h/2-21*k;
  bars.forEach(([x,bh],i)=>{ const a=Math.max(0,Math.min(1,(t*5-i*0.45))); g.globalAlpha=a; g.fillStyle='#f2f2ee'; g.beginPath(); g.roundRect(x0+x*k,y0,4.6*k,bh*k*a,2.3*k); g.fill(); });
  const ta=Math.max(0,Math.min(1,(t-0.45)*3)); g.globalAlpha=ta; g.fillStyle='#f2f2ee'; g.textBaseline='middle'; g.fillText('SKJOLD',x0+mw+gap,h/2-2*sc);
  g.font='400 '+(3.6*sc)+'px "IBM Plex Mono",Menlo,monospace'; if('letterSpacing' in g) g.letterSpacing=(1.1*sc)+'px'; g.fillStyle='#8b8b86'; g.fillText('STREAMING AMPLIFIER',x0+mw+gap+1,h/2+9*sc);
  g.globalAlpha=1; if('letterSpacing' in g) g.letterSpacing='0px'; g.textBaseline='alphabetic'; }
const booting=()=>performance.now()-bootT<BOOT;
const volShown=()=>{ const t=(performance.now()-bootT-BOOT)/1200; return Math.round(S.vol*Math.max(0,Math.min(1,t))); }; // soft start: output muted during boot, ramps over 1.2 s
let fxRAF=0; function animate(){ cancelAnimationFrame(fxRAF); const tick=()=>{ const busy=S.rebootT||S.pairT||performance.now()-S.menuT<2600||performance.now()-S.toastT<2200; drawOLED(); drawTFT();
  if(S.rebootT){ const on=Math.sin(performance.now()/220)>0; setLed(pwrBtn.userData.led,on,1,pwrBtn.userData.ledOff); }
  if(S.pairT) setLed(inBtns[0].userData.led,Math.floor(performance.now()/350)%2===0,1,inBtns[0].userData.ledOff); if(busy) fxRAF=requestAnimationFrame(tick); else refresh(); }; tick(); }
function overlay(g){ const now=performance.now(), F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86';
  if(S.rebootT){ const t=now-S.rebootT; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    if(t<3200){ const cx=64, cy=24, fade=Math.min(1,(3200-t)/400); g.globalAlpha=fade;
      for(let i=0;i<12;i++){ const a=i/12*Math.PI*2-Math.PI/2, k=((i-Math.floor(t/80))%12+12)%12; g.strokeStyle='rgba(242,242,238,'+(0.15+0.85*(1-k/12)).toFixed(2)+')'; g.lineWidth=1.6; g.lineCap='round';
        g.beginPath(); g.moveTo(cx+Math.cos(a)*5,cy+Math.sin(a)*5); g.lineTo(cx+Math.cos(a)*9,cy+Math.sin(a)*9); g.stroke(); }
      g.fillStyle=W; g.font='bold 8px '+F; g.textAlign='center'; g.fillText('Starter på nytt',64,46); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Raspberry Pi · Lyrion',64,55); g.textAlign='left'; g.globalAlpha=1; }
    else if(t>=3800){ S.rebootT=0; startBoot(); }
    return true; }
  if(S.pairT){ const t=(now-S.pairT)/1000; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('BLUETOOTH',4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    const cx=22, cy=34; for(let i=0;i<3;i++){ const r=((t*1.2+i/3)%1)*20; g.strokeStyle='rgba(242,242,238,'+(1-r/20).toFixed(2)+')'; g.lineWidth=1; g.beginPath(); g.arc(cx,cy,r,0,Math.PI*2); g.stroke(); }
    g.strokeStyle=W; g.lineWidth=1.6; g.lineJoin='round'; g.beginPath(); g.moveTo(cx-4,cy-4); g.lineTo(cx+4,cy+4); g.lineTo(cx,cy+8); g.lineTo(cx,cy-8); g.lineTo(cx+4,cy-4); g.lineTo(cx-4,cy+4); g.stroke();
    g.fillStyle=W; g.font='bold 9px '+F; g.fillText('Paring'+'...'.slice(0,1+Math.floor(t*2)%3),44,28); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Synlig som «Skjold S1»',44,38);
    g.fillText('Hold igjen = avbryt',44,47); g.fillStyle='#2a2a28'; g.fillRect(44,53,78,2.5); g.fillStyle=W; g.fillRect(44,53,78*Math.min(1,t/6),2.5); return true; }
  if(now-S.toastT<2200){ g.fillStyle='#000'; g.fillRect(0,0,128,64); g.fillStyle=W; g.font='bold 10px '+F; g.textAlign='center'; g.fillText('Tilkoblet',64,28); g.fillStyle=Dm; g.font='7px '+F; g.fillText('Sebastians iPhone',64,40); g.textAlign='left'; return true; }
  if(S.input===2&&now-S.menuT<2600){ g.fillStyle='#000'; g.fillRect(0,0,128,64); g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('RADIO · FAVORITTER',4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    g.textAlign='right'; g.fillText((S.preset+1)+'/6',124,8); g.textAlign='left';
    for(let i=-1;i<=1;i++){ const p=(S.preset+i+6)%6, y=24+(i+1)*14; if(i===0){ g.fillStyle=W; g.fillRect(2,y-10,124,13); g.fillStyle='#000'; } else g.fillStyle=Dm;
      g.font=(i===0?'bold 9px ':'8px ')+F; g.fillText((p+1)+'   '+PRESETS[p][0],6,y); }
    return true; }
  return false; }
function holdReboot(){ if(!S.main) return; S.power=true; S.pairT=0; S.rebootT=performance.now(); press(pwrBtn); animate(); }
function holdPair(){ if(!S.power) return; S.input=0; S.wl='bt'; S.pairT=performance.now(); clearTimeout(S.pairTO); S.pairTO=setTimeout(()=>{ if(!S.pairT) return; S.pairT=0; S.btPaired=true; S.toastT=performance.now(); syncInputs(); animate(); },6000); syncInputs(); press(inBtns[0]); animate(); }
function syncInputs(){ Object.assign(INPUTS[0],WL[S.wl]); INPUTS[2].t=PRESETS[S.preset][0]; INPUTS[2].s=PRESETS[S.preset][1]+' · Lyrion'; }
function drawOLED(){ const g=cvs.getContext('2d'); g.setTransform(4,0,0,4,0,0); g.fillStyle='#000'; g.fillRect(0,0,128,64);
  if(!S.power){ texO.needsUpdate=true; return; }
  if(booting()){ drawSplash(g,128,64,2); texO.needsUpdate=true; return; }
  if(overlay(g)){ texO.needsUpdate=true; return; }
  const it=INPUTS[S.input], F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86';
  g.fillStyle=W; g.font='bold 7px '+F; let x=2; INPUTS.forEach((t,i)=>{const w=g.measureText(t.k).width+6; if(i===S.input){g.fillRect(x,1,w,9); g.fillStyle='#000';} else g.fillStyle=Dm; g.fillText(t.k,x+3,8); g.fillStyle=W; x+=w+3;});
  if(S.hp){g.fillStyle=W; g.font='bold 6px '+F; g.textAlign='right'; g.fillText('HP',126,8); g.textAlign='left';}
  g.fillStyle=W; g.font='bold 12px '+F; g.fillText(S.input===3?'USB · '+it.t:it.t,2,27); g.fillStyle=Dm; g.font='7px '+F; g.fillText(it.s,2,37);
  g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(S.muted?'MUTE':'VOL',2,58); const on=S.muted?0:Math.round(volShown()/100*24);
  for(let i=0;i<24;i++){g.fillStyle=i<on?W:'#2a2a28'; g.fillRect(20+i*3.6,52,2.6,7);} g.fillStyle=W; g.font='bold 8px '+F; g.textAlign='right'; g.fillText(S.muted?'—':String(volShown()),126,59); g.textAlign='left';
  texO.needsUpdate=true; }
function drawTFT(){ const g=cvt.getContext('2d'); g.setTransform(2,0,0,2,0,0); g.fillStyle='#000'; g.fillRect(0,0,320,240);
  if(!S.power){ texT.needsUpdate=true; return; }
  if(booting()){ drawSplash(g,320,240,4.4); texT.needsUpdate=true; return; }
  { g.save(); g.translate(0,40); g.scale(2.5,2.5); const o=overlay(g); g.restore(); if(o){ texT.needsUpdate=true; return; } }
  const it=INPUTS[S.input], F='"Helvetica Neue",Arial,sans-serif', W='#f4f1ea', Dm='#9a968c', A='#d9a441', now=(performance.now()-T0)/1000;
  g.font='bold 11px '+F; g.textBaseline='middle'; let x=12; INPUTS.forEach((t,i)=>{const w=g.measureText(t.k).width+16; g.beginPath(); g.roundRect(x,8,w,18,9); if(i===S.input){g.fillStyle=W; g.fill(); g.fillStyle='#000';} else {g.strokeStyle='#55524c'; g.stroke(); g.fillStyle=Dm;} g.fillText(t.k,x+8,17.5); x+=w+6;});
  const hu=[[18,52],[205,260],[150,95],[280,330]][S.input]; const gr=g.createLinearGradient(12,36,140,164); gr.addColorStop(0,'hsl('+hu[0]+' 70% 55%)'); gr.addColorStop(1,'hsl('+hu[1]+' 60% 20%)');
  g.save(); g.beginPath(); g.roundRect(12,36,128,128,6); g.clip(); g.fillStyle=gr; g.fillRect(12,36,128,128); g.restore();
  g.fillStyle=W; g.font='bold 18px '+F; g.fillText(it.t,154,54); g.fillStyle=Dm; g.font='13px '+F; g.fillText(it.s,154,76); g.fillStyle=A; g.font='bold 10px '+F; g.fillText(('LYRION · '+it.n).toUpperCase(),154,98);
  for(let i=0;i<26;i++){const v=0.35+0.65*Math.abs(Math.sin(now*3.1+i*0.7)*Math.sin(now*1.7+i*0.31)), h=S.muted?2:4+v*44; g.fillStyle=A; g.fillRect(154+i*6,164-h,4,h);}
  g.fillStyle=Dm; g.font='bold 10px '+F; g.fillText(S.muted?'MUTE':'VOL',12,222); const on=S.muted?0:Math.round(volShown()/100*32);
  for(let i=0;i<32;i++){g.fillStyle=i<on?W:'#2c2b29'; g.fillRect(44+i*6.875,216,5.4,12);} g.fillStyle=W; g.font='bold 16px '+F; g.textAlign='right'; g.fillText(S.muted?'—':String(volShown()),308,222); g.textAlign='left';
  texT.needsUpdate=true; }
// printable desk-mount brackets: clamped under the lid screws (same lid for both versions)
function filletPts(pts){ const n=pts.length, out=[]; for(let i=0;i<n;i++){ const p=pts[(i-1+n)%n], v=pts[i], q=pts[(i+1)%n], r=v[2];
  const a=new V2(v[0]-p[0],v[1]-p[1]).normalize(), b=new V2(q[0]-v[0],q[1]-v[1]).normalize(); if(!r){out.push(new V2(v[0],v[1])); continue;}
  const th=Math.acos(Math.max(-1,Math.min(1,a.dot(b)))), t=r*Math.tan(th/2), cr=a.x*b.y-a.y*b.x, t1=new V2(v[0]-a.x*t,v[1]-a.y*t), nl=cr>0?new V2(-a.y,a.x):new V2(a.y,-a.x), c=t1.clone().addScaledVector(nl,r);
  const a0=Math.atan2(t1.y-c.y,t1.x-c.x), sweep=(cr>0?1:-1)*th; for(let k=0;k<=8;k++){const an=a0+sweep*k/8; out.push(new V2(c.x+r*Math.cos(an),c.y+r*Math.sin(an)));} } return out; }
const PET=new THREE.MeshStandardMaterial({name:'petg_sort',color:0x2a2b2e,roughness:0.7,metalness:0.02});
const brackets=new THREE.Group(); brackets.name='pultfeste_braketter'; lidRoot.add(brackets);
{ const B=REVB.bracket; for(const side of [1,-1]){ let pts=B.pts.map(([x,y,r])=>[side*x,y,r]); if(side<0) pts=pts.reverse();
    const holes=[...B.slots.map(ft=>hp({...ft,x:side*ft.x})),...REVB.lidScrews.filter(([x])=>Math.sign(x)===side).map(([x,y])=>circ(x,y,1.7))];
    const m=mesh('brakett',geo(shape(filletPts(pts),holes),B.t),PET,brackets);
    REVB.lidScrews.filter(([x])=>Math.sign(x)===side).forEach(([x,y])=>{ const h=mesh('skrue_iso7380_m3x10',new THREE.SphereGeometry(2.85,24,10,0,Math.PI*2,0,Math.PI/2),M.black,brackets); h.scale.set(1,0.58,1); h.rotation.x=Math.PI/2; h.position.set(x,y,B.t-B.screwCb[1]); });
    lab(m,'Pultfeste-brakett · PETG 4 mm · klemmes under lokkskruene (M3 × 10) · spor for Ø4 treskrue'); } }
lids.cnc_pult=lids.cnc_fritt; lids.plate_pult=lids.plate_fritt;

// ================= rounded form (Fosi-style): top + sides as one shell with R9 edges, removable bottom plate =================
const RT=9; // top-edge radius (sides stay straight up to z 39 → all side cut-outs unchanged)
const roundB={}, frontsR={};
function profPts(hw,z0,z1,rt,rb,cx=0,cz=0){ const P=Math.PI; const pts=[];
  const add=(c,r,a0,a1)=>{ if(r<=0.05){ pts.push(new V2(c[0],c[1])); return; } arcPts(c[0],c[1],r,a0,a1,10).forEach(p=>pts.push(p)); };
  add([cx+hw-rb,cz+z0+rb],rb,-P/2,0); add([cx+hw-rt,cz+z1-rt],rt,0,P/2); add([cx-hw+rt,cz+z1-rt],rt,P/2,P); add([cx-hw+rb,cz+z0+rb],rb,P,1.5*P); return pts; }
function roundBody(key,t,tb,mat){ const g=new THREE.Group(); g.name='kasse_'+key+'_avrundet'; inner.add(g); roundB[key]=g; g.visible=false;
  const RB=RT, iy=HD-t, mr=key==='cnc'?1:0;
  panel('topp','z',shape(rr(HW-RT,iy,0),REVB.topVents.map(f=>hp(f))),H-t,H,mat,g);
  const d=Math.PI/180, sector=(c,r0,r1,a0,a1)=>shape([...arcPts(c[0],c[1],r1,a0,a1,16),...arcPts(c[0],c[1],r0,a1,a0,16)]);
  panel('kant_topp_h','ay',sector([H-RT,HW-RT],RT-t,RT,0,90*d),-iy,iy,mat,g);
  panel('kant_topp_v','ay',sector([H-RT,-(HW-RT)],RT-t,RT,-90*d,0),-iy,iy,mat,g);
  panel('kant_bunn_h','ay',sector([RB,HW-RB],RB-t,RB,90*d,180*d),-iy,iy,mat,g);
  panel('kant_bunn_v','ay',sector([RB,-(HW-RB)],RB-t,RB,180*d,270*d),-iy,iy,mat,g);
  const sideS=(holes)=>shape(rr(iy,(H-RT-RB)/2,0,0,(H-RT+RB)/2),holes);
  panel('venstre','left',sideS(REVB.left.map(f=>hp(f,neg,mr))),HW-t,HW,mat,g);
  panel('hoyre','right',sideS(REVB.right.map(f=>hp(f,undefined,mr))),HW-t,HW,mat,g);
  const prof=profPts(HW,0,H,RT,RB);
  for(const k of ['oled','tft']){ const c=REVB.dispCut[k]; const fw=panel('front_'+k,'front',shape(prof,REVB.front.map((f,i)=>i===0?rr(c[0]/2,c[1]/2,c[2],DX,24):hp(f,undefined,mr,f.screw?3.4:undefined))),HD-t,HD,mat,g); fw.userData.disp=k; frontWalls.push(fw); }
  panel('bak','back',shape(prof,REVB.back.map(f=>hp(f,neg,mr))),HD-t,HD,mat,g);
  // removable bottom plate, screwed from below into internal side rails at the old lid-screw points
  const bp=new THREE.Group(); bp.name='bunnplate'; g.add(bp); g.userData.bottom=bp;
  const sheet=key==='plate', FLW=20, fx=HW-RB-FLW/2, BS=sheet?[[-fx,-62],[-fx,0],[-fx,62],[fx,-62],[fx,0],[fx,62],[-40,-(iy-5)],[40,-(iy-5)],[-40,iy-5],[40,iy-5]]:REVB.lidScrews;
  panel('bunnplate','z',shape(rr(HW-RB,iy,0.5),[...REVB.bottom.map(f=>hp(f,undefined,mr)),...BS.map(([x,y])=>circ(x,y,1.7)),...REVB.boardPosts.filter(([x])=>Math.abs(x)<HW-12.5).map(([x,y])=>circ(x,y,key==='cnc'?1.7:2.1))]),0,tb,mat,bp);
  BS.forEach(([x,y])=>{ const h=cylZ('senkskrue_m3',2.9,0.4,M.black,bp,[x,y,-0.15],24); lab(h,sheet?'M3 senkskrue i PEM-mutter (skjøt på undersiden)':'M3 senkskrue nedenfra (skjult under kassen)'); });
  if(sheet){ // one wrap (top + sides + R9 edges) ending in 20 mm flanges under the box; front/back panels with bottom flanges — every seam and screw sits underneath
    const seamM=new THREE.MeshStandardMaterial({name:'skjot',color:0x0c0c0d,roughness:0.9});
    [1,-1].forEach(sx=>{ const fl=box('omslag_flens',FLW,2*iy,t,mat,g,[sx*fx,0,tb+t/2]); lab(fl,'Omslag-flens 20 mm (bøyd inn under) · PEM CLS-M3 ×3');
      box('skjot_bunn',0.35,2*iy,0.2,seamM,g,[sx*(HW-RB),0,-0.05]); });
    [1,-1].forEach(sy=>{ const fl=box('panel_flens',2*(HW-RB-FLW)-1,10,t,mat,g,[0,sy*(iy-5),tb+t/2]); lab(fl,(sy<0?'Front':'Bak')+'panel · 10 mm flens bøyd inn, skrus nedenfra'); box('skjot_panel',2*(HW-RB),0.35,0.2,seamM,g,[0,sy*(iy+0.2),-0.05]); });
    lab(g.children.find(c=>c.name==='topp'),'Omslag: topp + sider i ett stykke, R9 bøy (Ri 7,5) · 1,5 mm alu'); }
  const RZ=16, ri=RB-t, xa=Math.sqrt(Math.max(0,ri*ri-(RB-tb)*(RB-tb)));
  [1,-1].forEach(sx=>{ const pts=[[HW-13.5,tb],[HW-RB+xa,tb]]; const a0=Math.atan2(tb-RB,xa); for(let i=1;i<=12;i++){const an=a0+(0-a0)*i/12; pts.push([HW-RB+ri*Math.cos(an),RB+ri*Math.sin(an)]);} pts.push([HW-t,RZ],[HW-13.5,RZ]);
    const sh=shape(pts.map(([x,z])=>new V2(z,sx*x))); const r=panel('skinne','ay',sh,-(iy-9),iy-9,mat,g);
    lab(r,key==='cnc'?'Innvendig skinne (frest i hjørnet) · M3 gjenget for bunnplate og kort':'Innvendig skinne (alu-profil) · M3 for bunnplate og kort'); });
  REVB.boardPosts.forEach(([x,y])=>{ const z0=Math.abs(x)>=HW-12.5?RZ:tb, h=REVB.boardZ-z0; const m=mesh('standoff_m3_kort',new THREE.CylinderGeometry(3.17,3.17,h,6),M.brass,Math.abs(x)>=HW-12.5?g:bp); m.rotation.x=Math.PI/2; m.position.set(x,y,z0+h/2); });
  REVB.front.filter(f=>f.screw).forEach(f=>{ const s1=mesh('skrue_m3_innvendig',new THREE.CylinderGeometry(2.75,2.75,3,24),M.black,g); s1.position.set(f.x,-(HD-t)+1.5,f.y); });
}
roundBody('cnc',2.7,3,M.cnc); roundBody('plate',1.5,1.5,M.plate);
// printed front plate (face-down on the K2 bed, CFS/AMS): back 1.0 · acrylic cavity 2.2 · front lip 0.8 mm.
// Print pauses at Z 3.0 → drop the 2 mm acrylic in → printer closes the back over it (no glue). First 0.4 mm: black inlay (legends + window frame).
const INK=new THREE.MeshStandardMaterial({name:'petg_sort_innlegg',color:0x161617,roughness:0.85});
function buildPlate(g,k,outline){ const P=REVB.plate, L=P.layers, fw=P.face[k], cv=P.cover[k], vw=P.view[k], cav=[cv[0]+P.cavClr*2,cv[1]+P.cavClr*2,cv[2]+P.cavClr];
  const holeC=off=>REVB.front.filter(f=>!f.screw).slice(1).map(f=>circ(f.x,f.y-24,f.d/2+off,48)), toF=m=>{m.applyMatrix4(basis([1,0,0],[0,0,1],[0,-1,0])); return m;};
  const l1=toF(mesh('frontplate_bak',geo(shape(outline(0),[rr(vw[0]/2,vw[1]/2,vw[2],DX,0),...holeC(0)]),L.back),M.face,g)); l1.position.set(0,-HD,H/2);
  const l2=toF(mesh('frontplate_hulrom',geo(shape(outline(0),[rr(cav[0]/2,cav[1]/2,cav[2],DX,0),...holeC(0)]),L.cavity),M.face,g)); l2.position.set(0,-HD-L.back,H/2);
  const bb=0.35, l3=toF(mesh('frontplate',new THREE.ExtrudeGeometry(shape(outline(bb),[rr(fw[0]/2+bb,fw[1]/2+bb,fw[2]+bb,DX,0),...holeC(bb)]),{depth:L.front-2*bb,bevelEnabled:true,bevelThickness:bb,bevelSize:bb,bevelSegments:4,curveSegments:32}),M.face,g));
  l3.geometry.translate(0,0,bb); l3.position.set(0,-HD-L.back-L.cavity,H/2);
  const ink=toF(mesh('innlegg_ramme',geo(shape(rr(fw[0]/2+P.frame,fw[1]/2+P.frame,fw[2]+P.frame,DX,0),[rr(fw[0]/2,fw[1]/2,fw[2],DX,0)]),0.42),INK,g)); ink.position.set(0,FY+0.4,H/2);
  lab(ink,'Sort innlegg 0,4 mm (første lag, CFS) · ramme rundt skjermvinduet');
  const ac=toF(mesh('akryl_skjermglass',geo(shape(rr(cv[0]/2,cv[1]/2,cv[2])),2),C.acryl,g)); ac.position.set(DX,-HD-L.back-L.cavity+2,24); ac.castShadow=false;
  lab(ac,'Røyksort akryl 2 mm, '+cv[0]+' × '+cv[1]+' mm · legges inn under printpause (Z 3,0) · printet inn, ingen lim');
  REVB.front.filter(f=>f.screw).forEach(f=>{ const ins=mesh('innsats_m3',new THREE.CylinderGeometry(P.insertD/2,P.insertD/2,P.insertDepth,20),M.brass,g); ins.position.set(f.x,-HD-P.insertDepth/2,f.y); }); }
{ const P=REVB.plate;
  for(const k of ['oled','tft']){
    const gR=new THREE.Group(); gR.name='frontplate_avrundet_'+k; frontRoot.add(gR); frontsR[k]=gR; gR.visible=false;
    buildPlate(gR,k,o=>profPts(HW-2-o,-22+o,22-o,RT-2-o,RT-2-o));
    const gS=new THREE.Group(); gS.name='frontplate_'+k; frontRoot.add(gS); fronts[k]=gS;
    buildPlate(gS,k,o=>rr(P.w/2-o,P.h/2-o,P.r-o)); }
  // M3 screws from inside the box, through the wall into the inserts
  REVB.front.filter(f=>f.screw).forEach(f=>{ const s1=mesh('skrue_m3_innvendig',new THREE.CylinderGeometry(2.75,2.75,3,24),M.black,bodies.cnc); s1.position.set(f.x,-(HD-2.7)+1.5,f.y);
    const s2=s1.clone(); s2.position.y=-(HD-1.5)+1.5; bodies.plate.add(s2); });
}
const root=new THREE.Group(); root.name='Pultforsterker_revB'; root.add(inner); inner.rotation.x=-Math.PI/2; inner.scale.setScalar(0.001);
inner.position.set(0,-H/2*0.001,0);
stage.setObject(root);


// ---------- finishes (Apple-like) ----------
const FIN={
  solv:{n:'Sølv',body:[0xd9dadc,0.42,0.62],face:[0xcbbd9e,0.88,0.0],btn:[0xcfd1d4,0.3,0.75],knob:[0xd2d4d7,0.32,0.75],led:0x8a8c90},
  stellar:{n:'Stellargrå',body:[0x5e6064,0.42,0.6],face:[0xcbbd9e,0.88,0.0],btn:[0x8d8f93,0.3,0.72],knob:[0x76787c,0.32,0.72],led:0x6a6c70},
  starlight:{n:'Starlight',body:[0xe6ddd0,0.45,0.5],face:[0xcbbd9e,0.88,0.0],btn:[0xdcd3c6,0.3,0.65],knob:[0xd9cfc1,0.32,0.65],led:0x8f877b},
  sort:{n:'Sort',body:[0x3a3b3f,0.34,0.45],face:[0xcbbd9e,0.88,0.0],btn:[0x6a6c71,0.25,0.6],knob:[0x4a4c51,0.28,0.55],led:0x5a5c60},
  midnatt:{n:'Midnatt',body:[0x2b2f38,0.45,0.55],face:[0xcbbd9e,0.88,0.0],btn:[0x3a3e47,0.3,0.6],knob:[0x30343c,0.32,0.6],led:0x4a4e56},
};
const setM=(m,[c,r,me])=>{m.color.set(c); m.roughness=r; m.metalness=me;};
// JLC surface options + common colours (as in the JLC order dialog)
const SURF={milled:{n:'Standard (frest)',r:0.32,m:0.9,map:'mill'},anod:{n:'Anodisert',r:0.26,m:0.75},brush:{n:'Børstet',r:0.3,m:0.85,map:'brush'},bead:{n:'Glassperleblåst',r:0.55,m:0.65},beadanod:{n:'Perleblåst + eloksert',r:0.5,m:0.7},spray:{n:'Sprøytelakk',r:0.45,m:0.05},powder:{n:'Pulverlakk',r:0.72,m:0.08}};
const COLS={natural:['Natur',0xd6d7d9],black:['Sort',0x1a1a1c],grey:['Grå',0x8c8e92],gold:['Gull',0xd9b23a],salmon:['Lakserosa',0xe99a7c],red:['Rød',0xc94a55],blue:['Blå',0x2c82c4],champagne:['Champagne',0xe9c9a2],wine:['Vinrød',0x7a2a2a],purple:['Lilla',0x9d57b8],teal:['Turkis',0x39a585],orange:['Oransje',0xe5713a]};
function stripeTex(kind){ const c=document.createElement('canvas'); c.width=c.height=512; const g=c.getContext('2d'); g.fillStyle='#808080'; g.fillRect(0,0,512,512);
  if(kind==='brush'){ for(let i=0;i<2600;i++){ const y=Math.random()*512, v=110+Math.random()*60|0; g.strokeStyle='rgb('+v+','+v+','+v+')'; g.lineWidth=0.6+Math.random(); g.beginPath(); g.moveTo(0,y); g.lineTo(512,y+Math.random()*2-1); g.stroke(); } }
  else { for(let r=8;r<760;r+=6){ const v=100+(r/6%2)*50; g.strokeStyle='rgb('+v+','+v+','+v+')'; g.lineWidth=2; g.beginPath(); g.arc(256,256,r,0,Math.PI*2); g.stroke(); } }
  const t=new THREE.CanvasTexture(c); t.wrapS=t.wrapT=THREE.RepeatWrapping; t.repeat.set(1/60,1/60); return t; }
const TEX={brush:stripeTex('brush'),mill:stripeTex('mill')};
function applyFinish(){ const sf=SURF[S.surf], col=COLS[S.col][1], dark=['black','wine','purple','blue','grey','teal','red'].includes(S.col);
  [M.cnc,M.plate].forEach(m=>{ m.color.set(col); m.roughness=sf.r; m.metalness=S.surf==='spray'||S.surf==='powder'?sf.m:(S.col==='natural'?sf.m:sf.m*0.85); m.bumpMap=sf.map?TEX[sf.map]:null; m.bumpScale=sf.map?0.6:0; m.roughnessMap=sf.map?TEX[sf.map]:null; m.needsUpdate=true; });
  M.print.color.set(0x2c2d30); legendMats.forEach(m=>m.color.set(dark?0xd2d4d7:0x3a3b3e));
  inBtns.concat([pwrBtn]).forEach(b=>b.userData.ledOff=0x3a3a3d);
  document.querySelectorAll('[data-surf]').forEach(b=>b.classList.toggle('on',b.dataset.surf===S.surf)); document.querySelectorAll('[data-col]').forEach(b=>b.classList.toggle('on',b.dataset.col===S.col));
  $('surfInfo').textContent=sf.n+' · '+COLS[S.col][0]; }
// ---------- UI ----------
const S={rebootT:0,wl:'air',btPaired:true,pairT:0,pairTO:0,preset:1,menuT:-1e9,toastT:-1e9,hp:false,flip:false,ac:'royk',form:'rund',surf:'beadanod',col:'black',v:'cnc',l:'fritt',f:'oled',open:false,ex:false,xray:false,main:true,power:true,input:0,vol:42,muted:false};
const SPEC={
  print:{t:'Print rev B (gammel, 215 mm) · PETG/ASA',li:['Opplastet v2_body_revb.stl, 215 × 160 × 48 mm','Vegg 2,7 mm, bunn 2,5 mm','Lokket skrus i støpte søyler med gjengeinnsatser'],files:[]},
  cnc:{t:'CNC · aluminium 6082, sort eloksert',li:['Frest ut av én blokk, 190 × 160 × 48 mm, R6','Vegg 2,7 mm, bunn 3 mm, lomme R5 (Ø10-fres)','Firkantede hull R1 (Ø2-fres)','Frontplate: skjult feste, 4 × M3 innenfra (Ø3,4)','Lokk 3 mm, Ø6,4 × 1,7 senkning, M3 ISO 7380','Lokk på 4 × M3 × 45 avstandsstykker','Hovedkort på 4 × M3 × 24,5 (topp z 27,5)'],
    files:[['Kasse STEP (OLED)','cnc/pultforsterker_v2_revb_kasse_cnc.step'],['Kasse STEP (TFT)','cnc/pultforsterker_v2_revb_kasse_cnc_tft.step'],['Lokk STEP','cnc/pultforsterker_v2_revb_lokk_frittstaende_cnc.step']]},
  plate:{t:'Platemetall · aluminium 5052, 1,5 mm',li:['Avrundet: ett omslag (topp + sider, R9) + front/bak-paneler med flens','Alle skjøter og skruer på undersiden','Rette kanter: brettet kar, bunn + 4 vegger, Ri 1,5, K 0,44','Flatmønster 280,8 × 250,8 mm (DXF, CUT/BEND)','Åpne hjørner, kan sveises','Frontplate: skjult feste, 4 × M3 innenfra (Ø3,4)','Hovedkort: 4 × PEM SO-M3-25 (Ø4,2), 1 mm lavere','Lokk 1,5 mm: M3 × 45 + 1,5 mm skive'],
    files:[['Kasse OLED STEP / DXF','platemetall/pultforsterker_v2_revb_kasse_platemetall.step','platemetall/pultforsterker_v2_revb_kasse_flatmonster.dxf'],['Kasse TFT STEP / DXF','platemetall/pultforsterker_v2_revb_kasse_platemetall_tft.step','platemetall/pultforsterker_v2_revb_kasse_flatmonster_tft.dxf'],['Lokk STEP / DXF','platemetall/pultforsterker_v2_revb_lokk_frittstaende_platemetall.step','platemetall/pultforsterker_v2_revb_lokk_frittstaende_platemetall.dxf']]},
};
const common=[['Pultfeste-braketter STEP (print, PETG)','print/pultforsterker_v2_revb_pultfeste_braketter.step'],['Frontplate OLED STEP (print)','print/pultforsterker_v2_revb_frontplate_oled_skjult_feste.step'],['Frontplate TFT STEP (print)','print/pultforsterker_v2_revb_frontplate_tft_skjult_feste.step'],['Akrylglass OLED DXF (laser, 2 mm)','print/pultforsterker_v2_revb_akryl_skjermglass_oled_2mm.dxf'],['Akrylglass TFT DXF (laser, 2 mm)','print/pultforsterker_v2_revb_akryl_skjermglass_tft_2mm.dxf']];
const $=id=>document.getElementById(id);
function press(g){ const c=g.userData.cap; if(!c) return; c.position.y+=0.8; setTimeout(()=>{c.position.y-=0.8;},140); }
function selectInput(i){ if(!S.power) return;
  if(i===0&&S.pairT){ S.pairT=0; clearTimeout(S.pairTO); }
  else if(i===0&&S.input===0){ S.wl=S.wl==='air'&&S.btPaired?'bt':'air'; }
  if(i===2){ if(S.input===2) S.preset=(S.preset+1)%6; S.menuT=performance.now(); }
  S.input=i; syncInputs(); press(inBtns[i]); refresh(); animate(); }
function refresh(){
  inBtns.forEach((b,i)=>setLed(b.userData.led,S.power&&i===S.input,1,b.userData.ledOff)); setLed(pwrBtn.userData.led,S.main,S.power?1:0.25,pwrBtn.userData.ledOff); if(pwrBtn.userData.sym) pwrBtn.userData.sym.color.set(S.power?0xffffff:(S.main?0x9a9a9a:0x6a6a6c));
  vip.rotation.x=S.main?0.18:-0.18; knob.rotation.y=-(S.vol/100)*Math.PI*1.5;
  hpJack.userData.plug.visible=S.hp; drawOLED(); drawTFT();
  document.querySelectorAll('[data-i]').forEach(b=>b.classList.toggle('on',+b.dataset.i===S.input));
  $('pwr').classList.toggle('on',S.power); $('pwr').textContent=S.power?'⏻ På':'⏻ Standby'; $('main').classList.toggle('on',S.main); $('main').textContent=S.main?'Hovedbryter på':'Hovedbryter av';
  $('mute').classList.toggle('on',S.muted); $('vol').value=S.vol; $('volv').textContent=S.muted?'mute':S.vol;
}
const bodyMats=[M.cnc,M.plate,M.print,M.face];
function sync(){
  const rund=S.form==='rund'&&S.v!=='print';
  Object.entries(bodies).forEach(([k,g])=>g.visible=k===S.v&&!rund); Object.entries(roundB).forEach(([k,g])=>{g.visible=rund&&k===S.v; g.userData.bottom.position.z=S.open?-45:(S.ex?-25:0);});
  document.querySelectorAll('[data-form]').forEach(b=>b.classList.toggle('on',b.dataset.form===S.form)); $('open').textContent=rund?'Åpne bunn':'Åpne lokk';
  const lidT=S.v==='plate'?T:3; Object.entries(lids).forEach(([k,g])=>{g.visible=k===S.v+'_fritt';}); brackets.visible=S.l==='pult'; brackets.position.z=H+lidT;
  Object.values(lids).forEach(g=>g.children.forEach(c=>{ if(c.name==='skrue_iso7380_m3') c.visible=S.l!=='pult'; })); lidRoot.position.z=S.open?70:(S.ex?30:0);
  lidLegend.position.z=H+(S.v==='cnc'?3:S.v==='plate'?1.5:3)+0.05;
  Object.entries(fronts).forEach(([k,g])=>{g.visible=k===S.f&&!rund; g.position.y=S.ex?-35:0;}); Object.entries(frontsR).forEach(([k,g])=>{g.visible=k===S.f&&rund; g.position.y=S.ex?-35:0;});
  lidRoot.visible=!rund;
  Object.entries(disp).forEach(([k,g])=>{g.visible=k===S.f; const sh=(S.v==='plate'?-1.2:0); g.children.forEach(c=>{ if(c.userData.by===undefined) c.userData.by=c.position.y;
    if(c.name.endsWith('bilde')){ const royk=S.ac==='royk'; c.position.y=royk?c.userData.by+(S.ex?-35:0):-(HD-2.7)-0.02+sh; c.material.blending=royk?THREE.AdditiveBlending:THREE.NormalBlending; c.material.transparent=royk; c.material.color.set(royk?0xd8d8d8:0xffffff); c.material.needsUpdate=true; }
    else c.position.y=c.userData.by+sh; });}); frontWalls.forEach(w=>w.visible=w.userData.disp===S.f);
  [...inBtns,pwrBtn,knob].forEach(g=>{ if(g.userData.baseY===undefined) g.userData.baseY=g.position.y; g.position.y=g.userData.baseY+(S.ex?-35:0); });
  applyFinish(); root.rotation.z=S.flip?Math.PI:0; $('flip').classList.toggle('on',S.flip);
  { const m=C.acryl, royk=S.ac==='royk'; m.color.set(royk?0x050506:0xffffff); m.transparent=!royk; m.opacity=royk?1:0.12; m.roughness=royk?0.08:0.02; m.depthWrite=royk; m.needsUpdate=true;
    document.querySelectorAll('[data-ac]').forEach(b=>b.classList.toggle('on',b.dataset.ac===S.ac)); }
  bodyMats.forEach(m=>{m.transparent=S.xray; m.opacity=S.xray?0.22:1; m.depthWrite=!S.xray; m.needsUpdate=true;});
  document.querySelectorAll('[data-v]').forEach(b=>b.classList.toggle('on',b.dataset.v===S.v));
  document.querySelectorAll('[data-l]').forEach(b=>b.classList.toggle('on',b.dataset.l===S.l));
  document.querySelectorAll('[data-f]').forEach(b=>b.classList.toggle('on',b.dataset.f===S.f));
  $('open').classList.toggle('on',S.open); $('explode').classList.toggle('on',S.ex); $('xray').classList.toggle('on',S.xray);
  const sp=SPEC[S.v]; $('specT').textContent=sp.t; $('spec').innerHTML=sp.li.map(t=>'<li>'+t+'</li>').join('');
  $('files').innerHTML=[...sp.files,...common].map(([t,...u])=>u.length>1?'<span style="font-size:11px">'+t.split(' STEP')[0]+': <a href="'+u[0]+'" download>STEP</a> · <a href="'+u[1]+'" download>DXF</a></span>':'<a href="'+u[0]+'" download>'+t+'</a>').join('');
  refresh();
}
document.querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{S.v=b.dataset.v; sync();});
document.querySelectorAll('[data-l]').forEach(b=>b.onclick=()=>{S.l=b.dataset.l; sync();});
document.querySelectorAll('[data-f]').forEach(b=>b.onclick=()=>{S.f=b.dataset.f; sync();});
$('open').onclick=()=>{S.open=!S.open; sync();}; $('flip').onclick=()=>{S.flip=!S.flip; sync();}; $('explode').onclick=()=>{S.ex=!S.ex; sync();};
document.querySelectorAll('[data-ac]').forEach(b=>b.onclick=()=>{S.ac=b.dataset.ac; sync();});
document.querySelectorAll('[data-form]').forEach(b=>b.onclick=()=>{S.form=b.dataset.form; sync();});
$('surfs').innerHTML=Object.entries(SURF).map(([k,v])=>'<button data-surf="'+k+'">'+v.n+'</button>').join('');
$('cols').innerHTML=Object.entries(COLS).map(([k,v])=>'<button data-col="'+k+'" title="'+v[0]+'" style="flex:0 0 26px;height:26px;padding:0;border-radius:50%!important;background:#'+v[1].toString(16).padStart(6,'0')+'"></button>').join('');
document.querySelectorAll('[data-surf]').forEach(b=>b.onclick=()=>{S.surf=b.dataset.surf; sync();}); document.querySelectorAll('[data-col]').forEach(b=>b.onclick=()=>{S.col=b.dataset.col; sync();});
$('xray').onclick=()=>{S.xray=!S.xray; sync();};
$('inputs').innerHTML=INPUTS.map((it,i)=>'<button data-i="'+i+'">'+it.n+'</button>').join('')+'<button id="pairBtn">Hold: BT-paring</button><button id="rebootBtn">Hold power: omstart</button>';
document.querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>selectInput(+b.dataset.i)); $('pairBtn').onclick=()=>holdPair(); $('rebootBtn').onclick=()=>holdReboot();
syncInputs();
$('pwr').onclick=()=>pwrBtn.userData.act(); $('main').onclick=()=>rk.userData.act?rk.userData.act():rk.children[0].userData.act();
$('mute').onclick=()=>{S.muted=!S.muted; refresh();}; $('vol').oninput=e=>{S.vol=+e.target.value; S.muted=false; refresh();};
// ---------- 3D picking: hover label, click to operate, scroll on knob = volume ----------
const cv=stage._renderer.domElement, cam=stage._camera, ray=new THREE.Raycaster(), ptr=new THREE.Vector2(), tip=$('tip');
const hit=e=>{ const r=cv.getBoundingClientRect(); ptr.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1); ray.setFromCamera(ptr,cam);
  const hs=ray.intersectObjects(root.children,true).filter(h=>{for(let o=h.object;o;o=o.parent) if(!o.visible) return false; const m=h.object.material; return !(m&&m.transparent&&m.opacity<0.5);});
  return hs.length&&hs[0].object.userData.label?hs[0].object:null; };
let down=null;
cv.addEventListener('pointermove',e=>{ const o=hit(e); cv.style.cursor=o&&o.userData.act?'pointer':''; if(o){tip.style.display='block'; tip.textContent=o.userData.label; tip.style.left=(e.clientX+14)+'px'; tip.style.top=(e.clientY+12)+'px';} else tip.style.display='none'; });
cv.addEventListener('pointerleave',()=>tip.style.display='none');
let holdTO=0, held=false; cv.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY]; held=false; clearTimeout(holdTO); const o=hit(e); if(o&&o.userData.hold){ holdTO=setTimeout(()=>{ held=true; o.userData.hold(); },1200); }});
cv.addEventListener('pointerup',e=>{ clearTimeout(holdTO); if(held){ held=false; return; } if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4) return; const o=hit(e); if(o&&o.userData.act) o.userData.act(); });
cv.addEventListener('wheel',e=>{ const o=hit(e); if(!o||o.userData.label.indexOf('Volum')!==0) return; e.preventDefault(); e.stopImmediatePropagation(); S.vol=Math.max(0,Math.min(100,S.vol+(e.deltaY<0?2:-2))); S.muted=false; refresh(); },{capture:true,passive:false});
setInterval(()=>{ if(S.f==='tft'&&S.power) drawTFT(); },80);
sync();
startBoot();
window.__S=S; window.__sync=sync;
