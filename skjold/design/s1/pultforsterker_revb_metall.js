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
let LEDK=1; const setLed=(m,on,k=1,off=0x8a8c90)=>{ k*=LEDK; on=on&&k>0; m.emissive.set(on?0xffffff:0); m.emissiveIntensity=on?1.6*k:0; m.color.set(on?0xffffff:off);};

// --- display (OLED / TFT) with live canvas
const cvs=document.createElement('canvas'); cvs.width=512; cvs.height=256;
const cvt=document.createElement('canvas'); cvt.width=640; cvt.height=480;
const texO=new THREE.CanvasTexture(cvs), texT=new THREE.CanvasTexture(cvt); [texO,texT].forEach(t=>{t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8;});
const disp={oled:grp('oled'), tft:grp('tft')};
{ const WI=-(HD-2.7); const g=disp.oled; box('oled_glass',60.5,1.3,37,C.glass,g,[DX,WI+0.66,24]);
  const sc=mesh('oled_bilde',new THREE.PlaneGeometry(55,27.5),new THREE.MeshBasicMaterial({map:texO,toneMapped:false,color:0xd8d8d8,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}),g); sc.rotation.x=Math.PI/2; sc.rotation.y=Math.PI; sc.rotation.set(Math.PI/2,0,0); sc.rotateX(Math.PI); sc.position.set(DX,-HD-REVB.plate.layers.back-REVB.plate.layers.cavity-0.04,24);
  box('oled_pcb',70,1.6,40,C.pcbB,g,[DX,WI+2.1,24]); [[-33,18],[33,18],[-33,-18],[33,-18]].forEach(([dx,dz])=>cylY('m2_skrue',1.9,1.4,M.black,g,[DX+dx,WI+3.6,24+dz],16)); box('i2c_header',10.2,2.5,8.5,C.dark,g,[DX,WI+4.2,24+15]); { const O=REVB.oledHolder, PET2=new THREE.MeshStandardMaterial({name:'petg_sort_holder',color:0x1c1c1e,roughness:0.75}); const hg=new THREE.Group(); hg.name='oled_holder'; g.add(hg);
  const fr=shape(rr(O.mod[0]/2+3,O.mod[1]/2-0.3,2,DX,O.cz),[rr(26,13,2,DX+2,O.cz-1)]); const back=mesh('holder_bak',geo(fr,2),PET2,hg); back.applyMatrix4(basis([1,0,0],[0,0,1],[0,1,0])); back.position.set(0,WI+3.8,0);
  const ring=mesh('holder_ramme',geo(shape(rr(O.mod[0]/2+3,O.mod[1]/2-0.3,2,DX,O.cz),[rr(O.mod[0]/2+0.2,O.mod[1]/2-0.31,0.5,DX,O.cz)]),3.8),PET2,hg); ring.applyMatrix4(basis([1,0,0],[0,0,1],[0,1,0])); ring.position.set(0,WI,0);
  O.studs.forEach(([x,z])=>{ const e=cylY('holder_ore',4,2,PET2,hg,[x,WI+1,z],24); cylY('m3_mutter_stud',3.2,2.4,C.shell,hg,[x,WI+3.2,z],6); });
  for(const dx of [-1,1]) for(const dz of [-1,1]) cylY('m25_skrue',2.2,1.4,M.black,g,[DX+dx*O.pitch[0]/2,WI+1.0,O.cz+dz*O.pitch[1]/2],16);
  lab(hg,'OLED-holder · PETG · modulen skrus inn forfra med 4 × M2,5 × 6 (selvgjengende) · festes på frontplatens 4 pigger (FH-M3-10) med mutter'); } lab(g,'OLED 2,42″ 128×64 · SSD1309 · I2C · hvit');
  const t=disp.tft; box('tft_glass',58,1.3,44,C.glass,t,[DX,WI+0.66,24]);
  const st=mesh('tft_bilde',new THREE.PlaneGeometry(48.96,36.72),new THREE.MeshBasicMaterial({map:texT,toneMapped:false,color:0xd8d8d8,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}),t); st.rotation.set(Math.PI/2,0,0); st.rotateX(Math.PI); st.position.set(DX,-HD-REVB.plate.layers.back-REVB.plate.layers.cavity-0.04,24);
  box('tft_pcb',77,1.6,43,C.pcbB,t,[DX,WI+2.1,24]); lab(t,'TFT 2,4″ 320×240 touch (ILI9341 + XPT2046)'); }
// image planes face -y (toward viewer): PlaneGeometry faces +z; rotate so normal = -y
[disp.oled,disp.tft].forEach(g=>g.children.filter(m=>m.name.endsWith('bilde')).forEach(m=>{m.rotation.set(0,0,0); m.up.set(0,0,1); m.lookAt(m.position.x,m.position.y-1,m.position.z);}));

// --- metal push buttons with LED rings
const WL={air:{k:'AIR',st:'AirPlay · iPhone',t:'Midnight City',s:'M83'},bt:{k:'BT',st:'Blåtann · Sebastians iPhone',t:'Teardrop',s:'Massive Attack'}};
const TRACKS={air:[['Midnight City','M83',243],['Intro','The xx',128],['Breathe','Télépopmusik',279]],bt:[['Teardrop','Massive Attack',331],['Angel','Massive Attack',379],['Unfinished Sympathy','Massive Attack',308]]};
const NOWP=[['Nyheter','NRK Dagsnytt'],['Ekko','Et aktuelt samfunnsprogram'],['Dance The Way I Feel','Ofenbach'],['Flowers','Miley Cyrus'],['Mr. Brightside','The Killers'],['Clair de lune','Claude Debussy']];
const AUXSRC=[['AUX 1','3,5 mm · analog'],['AUX 2','3,5 mm · analog']];
const USBSRC=[['PC','USB-C «PC 1» · 48 kHz · 24 bit'],['Switch','USB-C «PC 2» · 48 kHz · 16 bit']];
const PRESETS=[['NRK P1','Distriktsprogram'],['NRK P2','Kultur og samfunn'],['NRK P3','Pop og humor'],['P4 Norge','Hits'],['Radio Norge','Pop og rock'],['NRK Klassisk','Klassisk musikk']];
const INPUTS=[{k:'AIR',n:'AirPlay · BT',t:'Midnight City',s:'M83 · iPhone'},{k:'AUX',n:'AUX',t:'Linje inn',s:'3,5 mm · analog'},{k:'RADIO',n:'Radio',t:'NRK P2',s:'Lyrion · internettradio'},{k:'USB',n:'USB-lyd',t:'PC 1',s:'48 kHz · 24 bit'}];
const BTN=[[22,32.5],[22,15.5],[38,32.5],[38,15.5]]; // BT · AUX (under) · RADIO · USB (under) — per SPESIFIKASJON_KABINETT // AIRPLAY·BT, AUX / RADIO, USB
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
const BLAB=['AirPlay · Blåtann (trykk = bytt, hold = paring)','AUX inn (trykk = bytt mellom AUX 1 og AUX 2)','Radio (trykk = neste favoritt · hold = fast Lyrion-favoritt, velges i innstillinger)','USB-lyd (trykk = bytt mellom PC og Switch)'];
const inBtns=INPUTS.map((it,i)=>metalButton('knapp_'+it.k,BTN[i][0],BTN[i][1],7,5,BLAB[i]+' · 12 mm metallknapp, hvit LED-ring',()=>selectInput(i)));
inBtns[0].traverse(m=>m.userData.hold=()=>holdPair());
inBtns[2].traverse(m=>{ m.userData.hold=()=>saveRadio(); m.userData.holdMs=3000; m.userData.holdKind='radio'; m.userData.hold2=()=>holdRadio(); });
const pwrBtn=metalButton('power',-76,24,10.75,7.2,'Power · 16 mm metallbryter (M16), hode Ø21,5, lengde 36,4, LED-ring, fjærende (self-reset) · trykk = av/på · hold = omstart av Raspberry Pi',()=>{ if(!S.main) return; S.power=!S.power; press(pwrBtn); if(S.power) startBoot(); refresh(); });
pwrBtn.traverse(m=>m.userData.hold=()=>holdReboot());
// --- volume knob + EC11 encoder
let knobClickTO=0; const knob=grp('volumknapp'); knob.position.set(66,FY,24);
{ const prof=[new V2(0,0.6),new V2(14.4,0.6),new V2(15,1.2),new V2(15,16.4),new V2(14.4,17),new V2(0,17)];
  const k=mesh('knapp_kropp',new THREE.LatheGeometry(prof,96),C.knob,knob); k.rotation.x=Math.PI;
  { const ln=mesh('knapp_strek',new THREE.BoxGeometry(1.1,0.25,8),new THREE.MeshBasicMaterial({name:'knapp_strek_hvit',color:0xf2f2ee,toneMapped:false}),knob); ln.position.set(0,-17.08,9.5); ln.castShadow=false; }
  lab(knob,'Volum · alu-knapp 30 × 17 mm, 6 mm D-aksel · EC11 (trykk = mute / velg i meny, scroll = volum / bla i meny)',()=>{ if(S.set.open){ setAct(); return; } if(menuOpen()){ S.menuT=-1e9; refresh(); return; } if(knobClickTO){ clearTimeout(knobClickTO); knobClickTO=0; nextTrack(); return; } knobClickTO=setTimeout(()=>{ knobClickTO=0; S.muted=!S.muted; S.volT=S.muteT=performance.now(); refresh(); animate(); },260); }); }
knob.traverse(m=>{ m.userData.hold=()=>toggleSettings(); m.userData.holdMs=3000; m.userData.hold2=()=>togglePause(); });
const enc=grp('enkoder'); box('ec11',12,6.5,13,C.dark,enc,[66,-(HD-2.7)+3.25,24]); box('kontroll_pcb',26,1.6,26,C.pcbB,enc,[66,-(HD-2.7)+7.3,24]); lab(enc,'EC11 roterende enkoder + kontrollkort');
// --- main board (posts 172 × 92) at z 27.5
const mb=grp('hovedkort'); const bx0=(REVB.boardPosts[0][0]+REVB.boardPosts[2][0])/2, by0=(REVB.boardPosts[0][1]+REVB.boardPosts[1][1])/2, bz=REVB.boardZ;
box('pcb',180,100,1.6,C.pcb,mb,[bx0,by0,bz+0.8]); lab(mb,'Hovedkort 180 × 100 mm (PCBWay) · M3-hull 172 × 92');
const top=bz+1.6, cz=(h)=>top+h/2;
// Raspberry Pi 4 under the board (M2.5 × 20 standoffs), ports towards +x
const pi=grp('pi4',mb); box('pi4_pcb',85,56,1.6,C.pi,pi,[-32.3,13.2,6.7]); box('pi4_usb',17,13,16,C.shell,pi,[2.2,25,7.5+8]); box('pi4_usb2',17,13,16,C.shell,pi,[2.2,7,7.5+8]); box('pi4_rj45',21,16,13.5,C.shell,pi,[0.2,-8,7.5+6.75]);
box('pi4_soc',15,15,1.2,C.shell,pi,[-32,10,8.1]); box('pi4_header',51,5,8.5,C.dark,pi,[-46.5,38.5,7.5+4.25]);
[[-71.3,37.7],[-13.3,37.7],[-71.3,-11.3],[-13.3,-11.3]].forEach(([x,y])=>{ const m=mesh('m25_standoff_20',new THREE.CylinderGeometry(2.5,2.5,20,6),M.brass,pi); m.rotation.x=Math.PI/2; m.position.set(x,y,7.5+10); });
lab(pi,'Raspberry Pi 4 · under hovedkortet på 4 × M2,5 × 20 · SD-kort byttes ved å ta av bunnplaten'); pi.position.z+=REVB.boardZ-27.5;
const amp=grp('forsterker',mb); box('U6_tpa3116',12,12,1.2,C.dark,amp,[31.7,17.7,cz(1.2)]);
for(let i=0;i<7;i++) box('ribbe',1.6,20,8.5,C.heat,amp,[31.7-9+i*3,17.7,top+1.2+1.5+1.5+4.25]); box('ribbe_fot',20,20,1.5,C.heat,amp,[31.7,17.7,top+1.2+1.5+0.75]);
[[65.7,22.2],[79.7,22.2],[65.7,8.7],[79.7,8.7]].forEach(([x,y])=>box('L2_5_spole',12,12,8,C.coil,amp,[x,y,cz(8)])); box('L1_SRP1245A',12,12,4.5,C.coil,amp,[-8.3,21.7,cz(4.5)]);
[[33.7,31.7],[47.7,31.7],[-58.3,35.7]].forEach(([x,y])=>cylZ('C40_41_72_220uF',5,10.5,C.cap,amp,[x,y,cz(10.5)]));
cylZ('C1_2200uF_lavprofil',8,15,C.cap,amp,[41.7,44.7,cz(15)]);
box('K1_rele',19,15.5,15.7,new THREE.MeshStandardMaterial({color:0x2d5fa8,roughness:0.5}),amp,[7.7,31.7,cz(15.7)]);
box('F1_sikringsholder',23.6,7.3,9.5,C.dark,amp,[-1.85,44.7,cz(9.5)]);
const term=new THREE.MeshStandardMaterial({color:0x2f7a4a,roughness:0.5}); [[-38.3,45.7],[55.7,45.7],[71.7,45.7],[0.7,-42.3]].forEach(([x,y])=>box('skruterminal',10.5,8,10.3,term,amp,[x,y,cz(10.3)]));
box('J5_2x20_header',5,51,8.5,C.dark,amp,[-45.3,-13.4,cz(8.5)]);
const jst=new THREE.MeshStandardMaterial({color:0xeeeeea,roughness:0.5}); [-70,-58,-46,-20,-8,4].forEach(x=>box('JST_XH',8,6,7,jst,amp,[x,-42.3,cz(7)])); [-6.3,-18.3,-32.3].forEach(y=>box('JST_XH_hoyre',6,8,7,jst,amp,[83.7,y,cz(7)]));
box('J13_1x14',35,2.5,8.5,C.dark,amp,[44.1,-42.3,cz(8.5)]);
lab(amp,'Hovedkort rev B · TPA3116 med ribbe 20 × 20 × 10 · C1 2200 µF lavprofil ≤ 15 mm · fri høyde over kortet 17,4 mm');
const hub=grp('usb_hub',mb); box('hub_ic',8,8,1,C.dark,hub,[-80,-5,bz+2.1]);
REVB.left.forEach(f=>{ box('usb_a_skall',14,13.2,6.6,C.shell,hub,[-(HW-2.7)+7.2,f.x,f.y]); box('usb_a_tunge',12,10.6,1.8,C.dark,hub,[-(HW-2.7)+7.6,f.x,f.y-1.1]); });
lab(hub,'USB 2.0-hub / switch · 4 × USB-A (venstre side)');
// --- back panel
const back=grp('bakpanel'); const BY=HD;
const rk=grp('vippebryter',back); box('ramme',21,1.6,15,C.dark,rk,[70,BY+0.8,24]); box('ramme_kant',19.6,0.8,13.6,new THREE.MeshStandardMaterial({color:0x0c0c0d,roughness:0.6}),rk,[70,BY+1.7,24]);
const vip=box('vippe',17,2.6,11,new THREE.MeshStandardMaterial({color:0x151516,roughness:0.45}),rk,[70,BY+2.6,24]);
{ const wm=new THREE.MeshBasicMaterial({color:0xe8e8e4}); const I=box('merke_I',0.7,0.2,4,wm,vip,[4.2,1.35,0]); I.position.set(4.2,1.35,0); const O=mesh('merke_O',new THREE.TorusGeometry(1.7,0.32,8,32),wm,vip); O.rotation.x=Math.PI/2; O.position.set(-4.2,1.35,0); } box('hus',19,20,13,C.dark,rk,[70,BY-10,24]);
lab(rk,'Hovedbryter · vippebryter 19 × 13 mm',()=>{S.main=!S.main; if(!S.main) S.power=false; else { S.power=true; startBoot(); } refresh();});
const lan=grp('lan',back); box('flens',36.5,2.4,19,C.dark,lan,[38.5,BY-1.5-1.2,14.5]); box('skjerm',16,1.5,13.5,C.shell,lan,[38.5,BY-0.75,14.5]); box('port',12,0.6,10,new THREE.MeshStandardMaterial({color:0x050505}),lan,[38.5,BY+0.05,14]); box('hus',21.5,26,17,C.dark,lan,[38.5,BY-1.5-2.4-13,14.5]);
[24.75,52.25].forEach(x=>cylY('skrue',2.6,1,M.black,lan,[x,BY+0.5,14.5],16)); lab(lan,'RJ45 LAN · panelforlenger montert innenfra · 2 × M3 × 6 utenfra i gjengene på flensen');
const dc=grp('dc',back); cylY('krage',6.6,0.8,C.shell,dc,[34,BY+0.4,34],32); cylY('mutter_inni',7.2,2,C.shell,dc,[34,BY-1.5-1.1,34],6); cylY('tannskive',7.5,0.4,C.shell,dc,[34,BY-1.5-0.2,34],20); cylY('hylse',5.4,6,C.dark,dc,[34,BY+3,34]); cylY('hull',3.1,0.4,new THREE.MeshStandardMaterial({color:0x050505}),dc,[34,BY+6.05,34]); cylY('pinne',1.05,4,C.shell,dc,[34,BY+4.2,34],12); lab(dc,'DC 24 V inn · DC-099 5,5/2,1 mm · tannskive (jord)');
const aux=grp('aux',back); cylY('krage',4.0,0.8,C.shell,aux,[-14,BY+0.4,24],32); cylY('mutter_inni',4.6,2,C.shell,aux,[-14,BY-1.5-1.1,24],6); cylY('tannskive',4.9,0.4,C.shell,aux,[-14,BY-1.5-0.2,24],20); cylY('hylse',3.4,3,C.dark,aux,[-14,BY+3.5,24]); cylY('hull',1.8,0.4,new THREE.MeshStandardMaterial({color:0x050505}),aux,[-14,BY+5.05,24]); lab(aux,'AUX 1 inn · PJ-392 3,5 mm');
{ const gs=grp('jordskrue',back); cylY('tannskive',3.4,0.5,C.shell,gs,[52,BY+0.25,40],20); cylY('skruehode',2.75,2.2,C.shell,gs,[52,BY+1.6,40],6); cylY('kabelsko',3.6,0.8,M.brass,gs,[52,BY-1.4,40],20);
  lab(gs,'Jordpunkt M3 · stjernejord ved DC-inngangen (kasse → signaljord)'); }
const POSTS=[[-62,'L+',C.red,37],[-42,'L−',C.blk,37],[-62,'R+',C.red,17],[-42,'R−',C.blk,17]];
POSTS.forEach(([x,l,m,pz])=>{const g=grp('pol_'+l,back); cylY('base',9,2,new THREE.MeshStandardMaterial({color:0xeeeee8,transparent:true,opacity:0.55,roughness:0.2}),g,[x,BY+1,pz]); cylY('kropp',4.6,10,m,g,[x,BY+7,pz],32,4.2); cylY('topp',5.2,3,m,g,[x,BY+13.5,pz]); cylY('stamme',3,6,C.shell,g,[x,BY-3,pz]); lab(g,'Høyttalerpol '+l+' · 4 mm banan · isolert (plasthus Ø14,5) i Ø8-hull');});
const sma=grp('aux2',back); cylY('krage',4.0,0.8,C.shell,sma,[-26,BY+0.4,24],32); cylY('mutter_inni',4.6,2,C.shell,sma,[-26,BY-1.5-1.1,24],6); cylY('tannskive',4.9,0.4,C.shell,sma,[-26,BY-1.5-0.2,24],20); cylY('hylse',3.4,3,C.dark,sma,[-26,BY+3.5,24]); cylY('hull',1.8,0.4,new THREE.MeshStandardMaterial({color:0x050505}),sma,[-26,BY+5.05,24]); 
lab(sma,'AUX 2 inn · PJ-392 3,5 mm');

['PC 1','PC 2','Pi'].forEach((l,i)=>{const x=6, zc=[34,24,14][i]; const g=grp('usbc_'+i,back); box('flens',24,1.6,8.5,C.dark,g,[x,BY-1.5-0.8,zc]); // flange inside, screws from outside
  const sh=mesh('skall',new THREE.CapsuleGeometry(1.6,5.6,6,16),C.shell,g); sh.rotation.z=Math.PI/2; sh.scale.set(1,1,1); sh.position.set(x,BY+1.4,zc); box('tunge',6.6,1,0.7,C.dark,g,[x,BY+2.1,zc]); box('kabel_inn',10,16,6,C.dark,g,[x,BY-8,zc]); lab(g,'USB-C '+l+' · panelfeste');});
[34,24,14].forEach(z=>[-3.5,15.5].forEach(x=>cylY('skrue_usbc',2.2,1,M.black,back,[x,BY+0.5,z],16)));
// --- front plate screws (countersunk M3 into body)
// --- internal wiring (ribbon to front, posts)
// ---------- details ----------
// laser-etched legends (canvas text, tinted per finish)
const legendMats=[];
function legend(text,w,h,pos,face,par=parts,bold=true,fixed){ const k=8, c=document.createElement('canvas'); c.width=Math.ceil(w*k*4); c.height=Math.ceil(h*k*4);
  const g=c.getContext('2d'); g.fillStyle='#fff'; g.textAlign='center'; g.textBaseline='middle'; g.font=(bold?'600 ':'400 ')+(c.height*0.78)+'px -apple-system,"SF Pro Text","Helvetica Neue",Arial,sans-serif';
  if('letterSpacing' in g) g.letterSpacing=(c.height*0.08)+'px'; g.fillText(text,c.width/2,c.height/2);
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8;
  const m=new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false,color:fixed??0x55575b}); if(fixed===undefined) legendMats.push(m); else frontInk.push(m);
  const p=mesh('etikett_'+text,new THREE.PlaneGeometry(w,h),m,par); p.castShadow=false; p.position.set(...pos);
  const n={front:[0,-1,0],back:[0,1,0],left:[-1,0,0],top:[0,0,1]}[face]; p.up.set(...(face==='top'?[0,1,0]:[0,0,1])); p.lookAt(pos[0]+n[0],pos[1]+n[1],pos[2]+n[2]); return p; }
const fy=FY-0.05; const frontInk=[];
function logo(par,pos,w=60,tag=true,fixed){ const c=document.createElement('canvas'); { const m=c.getContext('2d'); m.font='600 120px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; if('letterSpacing' in m) m.letterSpacing='17px'; c.width=Math.ceil(230+m.measureText('SKJOLD').width-17+20); } c.height=tag?260:180; const g=c.getContext('2d'); g.fillStyle='#fff';
  const bars=[[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]], k=3.4; bars.forEach(([x,h])=>{ g.beginPath(); g.roundRect(20+x*k,30,4.6*k,h*k,2.3*k); g.fill(); });
  g.textBaseline='alphabetic'; g.font='600 120px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; if('letterSpacing' in g) g.letterSpacing='17px'; g.fillText('SKJOLD',230,135);
  if(tag){ g.font='400 40px "IBM Plex Mono",Menlo,monospace'; if('letterSpacing' in g) g.letterSpacing='12px'; g.fillText('STREAMING AMPLIFIER',232,205); }
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8; const m=new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false,color:fixed??0x55575b}); if(fixed===undefined) legendMats.push(m);
  const p=mesh('logo_skjold',new THREE.PlaneGeometry(w*c.width/1200,w*c.height/1200),m,par); p.castShadow=false; p.position.set(...pos); p.up.set(0,1,0); p.lookAt(pos[0],pos[1],pos[2]+1); return p; }
[['BT',22,41.6,8],['RADIO',38,41.6,11],['AUX',22,6.4,8],['USB',38,6.4,8]].forEach(([t,x,z,w])=>legend(t,w,1.9,[x,fy,z],'front',parts,true,0x161617));
{ const p=logo(parts,[66,fy,4.9],21,false,0x161617); frontInk.push(p.material); p.up.set(0,0,1); p.lookAt(66,fy-1,4.9); lab(p,'Skjold-logo · sort innlegg under volumknappen'); }
// 3.5 mm headphone jack under the power button (nickel nut on the plate, plug toggles on click)
const hpJack=grp('hodetelefon'); { const J=[-76,8];
  cylY('mutter_riflet',4.0,1.8,C.shell,hpJack,[J[0],-HD-1-0.9,J[1]],24); cylY('gjenge',3.0,2.1,C.shell,hpJack,[J[0],-HD-1-1.05+0.3,J[1]],32); cylY('hylse',2.2,0.6,C.dark,hpJack,[J[0],FY+0.6,J[1]],32);
  cylY('hull',1.8,0.3,new THREE.MeshStandardMaterial({color:0x050505}),hpJack,[J[0],FY+0.28,J[1]],24); cylY('jack_hus',4,12,C.dark,hpJack,[J[0],-(HD-2.7)+6,J[1]],24);
  const plug=grp('plugg',hpJack); cylY('plugg_hals',3.2,6,C.dark,plug,[J[0],FY-4.3,J[1]],24); cylY('plugg_kropp',4.2,14,C.dark,plug,[J[0],FY-14.3,J[1]],24,3.6); cylY('kabel',1.6,30,C.dark,plug,[J[0],FY-36,J[1]],12); hpJack.userData.plug=plug;
  lab(hpJack,'Hodetelefon · PJ-392 nikkel, festet i metallveggen · mutter skjult bak frontplaten (klikk = plugg)',()=>{S.hp=!S.hp; if(S.set.hpOwn){ const v=S.vol; S.vol=S.hpVol; S.hpVol=v; } S.hpT=performance.now(); refresh(); animate();});
  { const c=document.createElement('canvas'); c.width=c.height=128; const g=c.getContext('2d'); g.strokeStyle='#fff'; g.lineWidth=11; g.lineCap='round';
    g.beginPath(); g.arc(64,70,40,Math.PI,0); g.stroke(); g.fillStyle='#fff'; g.beginPath(); g.roundRect(18,70,20,36,6); g.fill(); g.beginPath(); g.roundRect(90,70,20,36,6); g.fill();
    const t=new THREE.CanvasTexture(c); const m=new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false,color:0x161617}); frontInk.push(m); const p=mesh('hodetelefon_ikon',new THREE.PlaneGeometry(3.6,3.6),m,parts); p.position.set(-68.6,fy,8); p.up.set(0,0,1); p.lookAt(-68.6,fy-1,8); } }
const by=HD+0.05;
[['AUX 2',-26],['AUX 1',-14]].forEach(([t,x])=>legend(t,9,1.9,[x,by,33.5],'back')); legend('L',5,3.0,[-76,by,37],'back'); legend('R',5,3.0,[-76,by,17],'back'); legend('+',3,2.2,[-62,by,27],'back'); legend('−',3,2.2,[-42,by,27],'back');
[['PC 1',34],['PC 2',24]].forEach(([t,z])=>legend(t,8,1.6,[21,by,z+4.2],'back')); legend('Pi',5,1.6,[-14,by,14],'back'); // Pi label right of its USB-C port (seen from behind), under AUX 1 legend('USB-C',10,1.9,[6,by,40.2],'back');
legend('LAN',8,1.7,[38.5,by,25.6],'back'); legend('GND',7,1.7,[52,by,44.2],'back'); legend('DC 24 V  5,5/2,1',21,1.9,[34,by,42.5],'back'); legend('I / O',9,1.9,[70,by,33.5],'back');

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
[[-80,-65],[80,-65],[-80,65],[80,65]].forEach(([x,y])=>{ const g=grp('gummifot'); const p=[new V2(0,0),new V2(6.35,0),new V2(6.35,-2.2),new V2(5.4,-3.2),new V2(3.5,-3.5),new V2(0,-3.5)]; const m=mesh('fot',new THREE.LatheGeometry(p,48),padM,g); m.rotation.x=Math.PI/2; g.position.set(x,y,0); lab(g,'Gummifot Ø12,7 × 3,5 mm (selvklebende)'); });
// power toggle symbol (IEC ⏻) as lit geometry on the plunger — moves with it when pressed
{ const m=new THREE.MeshBasicMaterial({name:'power_symbol',color:0x3a3a3d,toneMapped:false}); pwrBtn.userData.sym=m; const cap=pwrBtn.userData.cap, fy0=-(2.4-0.45)/2-0.12;
  const ag=new THREE.TorusGeometry(2.35,0.32,10,48,Math.PI*2*(280/360)); ag.rotateZ((90+40)*Math.PI/180); ag.rotateX(Math.PI/2); const arc=mesh('power_ring',ag,m,cap); arc.position.y=fy0; arc.castShadow=false;
  const bar=mesh('power_strek',new THREE.BoxGeometry(0.64,0.3,3.0),m,cap); bar.position.set(0,fy0,1.45); bar.castShadow=false; }
// binding posts: gold contact rings
POSTS.forEach(([x,,,pz])=>cylY('kontakt_gull',4.75,1.2,M.brass,back,[x,BY+9,pz],32));
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
function startBoot(){ bootT=performance.now(); if(S.set.vstart) S.vol=VST[S.set.vstart]; S.lastAct=bootT; cancelAnimationFrame(bootRAF); const tick=()=>{ drawOLED(); drawTFT(); if(performance.now()-bootT<BOOT+1300) bootRAF=requestAnimationFrame(tick); else if(S.welcome) animate(); }; tick(); }
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
let fxRAF=0; function animate(){ cancelAnimationFrame(fxRAF); const tick=()=>{ const busy=(S.welcome&&S.power)||performance.now()-(S.clockPrevT||-1e9)<4100||S.setup.on||S.set.open||S.knobHoldT||performance.now()-S.actT<900||performance.now()-S.saveT<1700||(S.err&&performance.now()-S.errT<2700)||performance.now()-S.volT<2400||(S.power&&!booting()&&!S.muted&&S.f==='oled')||S.rebootT||S.pairT||performance.now()-S.menuT<2600||performance.now()-S.toastT<2200||performance.now()-S.hpT<1800||performance.now()-S.wlT<950||performance.now()-S.muteT<1600; drawOLED(); drawTFT();
  if(S.rebootT){ const on=Math.sin(performance.now()/220)>0; setLed(pwrBtn.userData.led,on,1,pwrBtn.userData.ledOff); }
  if(S.pairT) setLed(inBtns[0].userData.led,Math.floor(performance.now()/350)%2===0,1,inBtns[0].userData.ledOff); if(busy) fxRAF=requestAnimationFrame(tick); else refresh(); }; tick(); }
function overlay(g){ const now=performance.now(), F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86';
  if(S.rebootT){ const t=now-S.rebootT; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    if(t<380){ const u=t/380, h=Math.max(0.6,26*(1-u*u)), w=124*(u<0.7?1:1-(u-0.7)/0.3); g.fillStyle=W; g.globalAlpha=0.9; g.fillRect(64-w/2,32-h/2,w,h); g.globalAlpha=1; return true; }
    if(t<3800){ const T=t-380, fade=Math.min(1,T/250,(3420-T)/300); g.globalAlpha=Math.max(0,fade);
      g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('OMSTART',4,8); if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
      const ST=['Stopper lydtjenester','Starter Raspberry Pi','Kobler til Lyrion'], D=900, cur=Math.min(3,Math.floor(T/D));
      ST.forEach((l,i)=>{ const y=23+i*11, done=i<cur, act=i===cur;
        if(done){ g.strokeStyle=W; g.lineWidth=1.2; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(5,y-3); g.lineTo(7,y-1); g.lineTo(10.5,y-5.5); g.stroke(); }
        else if(act){ for(let k=0;k<8;k++){ const an=k/8*Math.PI*2+now/140; g.fillStyle='rgba(242,242,238,'+(0.2+0.8*((k/8+now/1120)%1)).toFixed(2)+')'; g.beginPath(); g.arc(7.7+Math.cos(an)*2.6,y-3.3+Math.sin(an)*2.6,0.55,0,Math.PI*2); g.fill(); } }
        else { g.fillStyle='#3a3a37'; g.beginPath(); g.arc(7.7,y-3.3,1,0,Math.PI*2); g.fill(); }
        g.fillStyle=done||act?W:'#55554f'; g.font=(act?'bold ':'')+'7px '+F; g.fillText(l,15,y); });
      const p=Math.min(1,T/(3*D)); g.fillStyle='#2a2a28'; g.fillRect(4,56,120,2); g.fillStyle=W; g.fillRect(4,56,120*(1-Math.pow(1-p,2)),2);
      g.globalAlpha=1; }
    else { S.rebootT=0; startBoot(); }
    return true; }
  if(now-(S.clockPrevT||-1e9)<4000&&window.SKJOLD){ g.fillStyle='#000'; g.fillRect(0,0,128,64); window.SKJOLD.drawClock(g,128,64,S.set.clockStyle||0,new Date()); return true; }
  if(S.setup.on&&S.power){ const U=S.setup; g.fillStyle='#000'; g.fillRect(0,0,128,64); const hdr=t=>{ g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(t,4,8); if('letterSpacing' in g) g.letterSpacing='0px'; };
    if(U.step<0||U.step===0){ const join=U.step<0; drawQR(g,2,4,56,join?'WIFI:T:WPA;S:'+SETUP_SSID+';P:'+SETUP_PW+';;':'http://10.42.0.1/oppsett');
      g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(join?'SETT OPP':'TELEFON KOBLET TIL',63,10); if('letterSpacing' in g) g.letterSpacing='0px';
      g.fillStyle=W; g.font='bold 8px '+F; g.fillText(join?'Skann for å':'Skann for å',63,22); g.fillText(join?'koble til':'åpne oppsett',63,31);
      g.fillStyle=Dm; g.font='5.5px '+F; if(join){ g.fillText(SETUP_SSID,63,43); g.fillText('Passord '+SETUP_PW,63,51); g.fillText('eller bruk Skjold-appen',63,59); } else { g.fillText('IP 10.42.0.1',63,43); g.fillText('10.42.0.1/oppsett',63,51); } return true; }
    if(U.step>=1&&U.step<=6){ hdr('OPPSETT'); g.textAlign='right'; g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText('STEG '+U.step+' AV 6',124,8); g.textAlign='left'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
      for(let i=0;i<6;i++){ g.fillStyle=i<U.step?W:'#2a2a28'; g.fillRect(4+i*20.4,58,18.4,2); }
      if(U.step===4&&now-U.testT<1600){ const L=U.testCh==='L'; spk(g,L?22:106,32,1.6,false,Math.min(1,(now-U.testT)/500),W); g.textAlign='center'; g.fillStyle=W; g.font='bold 11px '+F; g.fillText(L?'VENSTRE':'HØYRE',64,36); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Spiller testlyd',64,47); g.textAlign='left'; return true; }
      g.fillStyle=W; g.font='bold 12px '+F; g.fillText(STEPN[U.step-1],4,30); g.fillStyle=Dm; g.font='6px '+F;
      const sub=U.step===2?(U.connecting?'Kobler til '+U.ssid+'…':'Velg nett på telefonen'):U.step===3?'Velg navn på telefonen':U.step===4?'Trykk V og H på telefonen':U.step===5?'Velg Lyrion-server':U.step===6?(U.upd>=100?'Siste versjon installert':'Installerer 1.4.2 · ikke slå av'):'Velg språk på telefonen';
      g.fillText(sub,4,41); if(U.step===6){ g.fillStyle='#2a2a28'; g.fillRect(4,47,120,2); g.fillStyle=W; g.fillRect(4,47,120*U.upd/100,2); }
      if(U.step===2&&U.connecting){ for(let k=0;k<3;k++){ g.globalAlpha=0.3+0.7*((Math.floor(now/250)+k)%3===0?1:0); g.fillStyle=W; g.beginPath(); g.arc(112+k*5,28,1.5,0,Math.PI*2); g.fill(); } g.globalAlpha=1; } return true; }
    if(U.step>=7){ g.textAlign='center'; g.strokeStyle=W; g.lineWidth=1.4; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(56,14); g.lineTo(62,20); g.lineTo(73,8); g.stroke();
      g.fillStyle=W; g.font='bold 10px '+F; g.fillText((U.name||devName())+' er klar',64,34); g.fillStyle=Dm; g.font='6px '+F; g.fillText('IP 192.168.1.42',64,46); g.fillText('http://'+(U.name||'skjold').toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.local',64,55); g.textAlign='left'; return true; } }
  if(S.set.open&&now-S.set.t>20000) S.set.open=false;
  if(S.set.open&&S.set.page){ g.fillStyle='#000'; g.fillRect(0,0,128,64); g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px';
    if(S.set.page==='reset'){ if('letterSpacing' in g) g.letterSpacing='0px'; g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText('Tilbakestilt',64,30); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Alle innstillinger er satt til standard',64,41); g.fillText('Trykk for å gå tilbake',64,56); g.textAlign='left'; return true; }
    if(S.set.page==='bt'){ g.fillText('PAREDE ENHETER',4,8); if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
      if(!S.btDev.length){ g.textAlign='center'; g.fillStyle=Dm; g.font='7px '+F; g.fillText('Ingen parede enheter',64,32); g.font='6px '+F; g.fillText('Hold BT-knappen for å pare',64,42); g.textAlign='left'; }
      S.btDev.forEach((d,i)=>{ const y=23+i*12; icoBT(g,8,y-2.5,0.42,W); g.fillStyle=W; g.font='bold 7px '+F; g.fillText(d,15,y); g.fillStyle=Dm; g.font='6px '+F; g.textAlign='right'; g.fillText(S.wl==='bt'&&i===0&&S.input===0?'Tilkoblet':'Paret',124,y); g.textAlign='left'; });
      g.fillStyle=Dm; g.font='6px '+F; g.fillText('Trykk for å gå tilbake',4,60); return true; }
    g.fillText('OM '+devName().toUpperCase(),4,8); if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
    [['Navn',devName()],['Programvare',SWVER],['IP-adresse','192.168.1.42'],['Lyrion',S.err===1?'Frakoblet':'Tilkoblet'],['Wi-Fi',S.err===2?'Ingen':'Hjemme · −52 dBm'],['Serienr.','SKJ-S1-0001']].forEach(([k,v],i)=>{ const y=19+i*8.4; g.fillStyle=Dm; g.font='6px '+F; g.fillText(k,4,y); g.fillStyle=W; g.font='bold 6px '+F; g.textAlign='right'; g.fillText(v,124,y); g.textAlign='left'; });
    return true; }
  if(S.set.open){ g.fillStyle='#000'; g.fillRect(0,0,128,64); const L=curList(), top=S.set.cat<0;
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(top?'INNSTILLINGER':CATS[S.set.cat][1].toUpperCase(),4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    if(!top){ g.textAlign='right'; g.fillText(S.set.idx?S.set.idx+'/'+(L.length-1):'',124,8); g.textAlign='left'; } g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
    const vis=4, first=Math.max(0,Math.min(L.length-vis,S.set.idx-1));
    for(let r=0;r<vis;r++){ const i=first+r, it=L[i]; if(!it) break; const y=14+r*12.5, on=i===S.set.idx, ed=on&&S.set.edit;
      if(on&&!ed){ g.fillStyle=W; g.beginPath(); g.roundRect(2,y,118,11.5,2); g.fill(); g.fillStyle='#000'; } else if(ed){ g.strokeStyle=W; g.lineWidth=0.8; g.beginPath(); g.roundRect(2.4,y+0.4,117.2,10.7,2); g.stroke(); g.fillStyle=W; } else g.fillStyle=(it.back||it.n==='Lukk')?Dm:W;
      g.font=(on?'bold ':'')+'7px '+F; g.fillText(it.n,6,y+8.3); g.textAlign='right'; g.font=(it.cat?'':'bold ')+'7px '+F;
      const v=it.cat||it.back||it.n==='Lukk'?(it.v||''):setVal(it); g.fillText(ed?'‹ '+v+' ›':v,116,y+8.3); g.textAlign='left'; }
    if(L.length>vis){ const sh=50*vis/L.length; g.fillStyle='#2a2a28'; g.fillRect(123.5,14,1.5,50); g.fillStyle=W; g.fillRect(123.5,14+first*(50-sh)/(L.length-vis),1.5,sh); } return true; }
  if(S.knobHoldT&&now-S.knobHoldT>(S.holdWhat==='radio'?900:350)){ const p=Math.min(1,(now-S.knobHoldT-350)/2650); g.fillStyle='#000'; g.fillRect(0,0,128,64);
    const cx=64, cy=26; g.strokeStyle='#2a2a28'; g.lineWidth=2; g.beginPath(); g.arc(cx,cy,11,0,Math.PI*2); g.stroke(); g.strokeStyle=W; g.lineCap='round'; g.beginPath(); g.arc(cx,cy,11,-Math.PI/2,-Math.PI/2+p*Math.PI*2); g.stroke();
    g.save(); g.translate(cx,cy); g.rotate(p*Math.PI); g.fillStyle=W; for(let k=0;k<8;k++){ g.rotate(Math.PI/4); g.fillRect(-1.2,-6.2,2.4,2.6); } g.beginPath(); g.arc(0,0,4.6,0,Math.PI*2); g.fill(); g.fillStyle='#000'; g.beginPath(); g.arc(0,0,1.9,0,Math.PI*2); g.fill(); g.restore();
    g.textAlign='center'; g.fillStyle=W; g.font='bold 8px '+F; const R2=S.holdWhat==='radio'; g.fillText(R2?'Lagre favoritt':'Innstillinger',64,50); g.fillStyle=Dm; g.font='6px '+F; g.fillText(now-S.knobHoldT<1000?(R2?'Slipp = spill favoritt':'Slipp = pause'):(R2?'Hold for å lagre kanalen':S.set.open?'Hold for å lukke':'Hold i 3 sekunder'),64,59); g.textAlign='left'; return true; }
  if(S.pairT){ const t=(now-S.pairT)/1000; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('BLÅTANN',4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    const cx=22, cy=34; for(let i=0;i<3;i++){ const r=((t*1.2+i/3)%1)*20; g.strokeStyle='rgba(242,242,238,'+(1-r/20).toFixed(2)+')'; g.lineWidth=1; g.beginPath(); g.arc(cx,cy,r,0,Math.PI*2); g.stroke(); }
    g.strokeStyle=W; g.lineWidth=1.6; g.lineJoin='round'; g.beginPath(); g.moveTo(cx-4,cy-4); g.lineTo(cx+4,cy+4); g.lineTo(cx,cy+8); g.lineTo(cx,cy-8); g.lineTo(cx+4,cy-4); g.lineTo(cx-4,cy+4); g.stroke();
    g.fillStyle=W; g.font='bold 9px '+F; g.fillText('Paring'+'...'.slice(0,1+Math.floor(t*2)%3),44,28); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Synlig som «'+devName()+'»',44,38);
    g.fillText('Hold igjen = avbryt',44,47); g.fillStyle='#2a2a28'; g.fillRect(44,53,78,2.5); g.fillStyle=W; g.fillRect(44,53,78*Math.min(1,t/6),2.5); return true; }
  if(S.power&&now-S.hpT<1800){ const u=Math.min(1,(now-S.hpT)/220), e=1-(1-u)*(1-u)*(1-u); g.fillStyle='#000'; g.fillRect(0,0,128,64); g.save(); g.translate(64,24); g.scale(0.8+0.2*e,0.8+0.2*e); g.globalAlpha=e;
    g.strokeStyle=W; g.fillStyle=W; g.lineWidth=2.4; g.lineCap='round'; g.beginPath(); g.arc(0,2,11,Math.PI*1.02,-Math.PI*0.02); g.stroke(); g.beginPath(); g.roundRect(-13.5,1,6,10,2); g.roundRect(7.5,1,6,10,2); g.fill();
    if(!S.hp){ g.strokeStyle='#000'; g.lineWidth=4.5; g.beginPath(); g.moveTo(-15,-11); g.lineTo(15,13); g.stroke(); g.strokeStyle=W; g.lineWidth=1.6; g.beginPath(); g.moveTo(-15,-11); g.lineTo(15,13); g.stroke(); }
    g.restore(); g.globalAlpha=1; g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText(S.hp?'Hodetelefoner':'Høyttalere',64,49); g.fillStyle=Dm; g.font='6px '+F; g.fillText(S.hp?'Høyttalerutgang dempet':'Hodetelefoner frakoblet',64,58); g.textAlign='left'; return true; }
  if(S.power&&now-S.muteT<1600){ const t=now-S.muteT, u=Math.min(1,t/260), e=1-(1-u)*(1-u)*(1-u), fo=Math.min(1,(1600-t)/250); g.fillStyle='#000'; g.fillRect(0,0,128,64); g.globalAlpha=fo;
    spk(g,60,25,1.9*(0.85+0.15*e),S.muted,Math.min(1,t/420),W);
    g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText(S.muted?'Lyd av':'Lyd på',64,50); g.fillStyle=Dm; g.font='6px '+F; g.fillText(S.muted?'Trykk volumknappen for å slå på':'Volum '+S.vol,64,59); g.textAlign='left'; g.globalAlpha=1; return true; }
  if(S.power&&S.input===0&&now-S.wlT<950){ const t=now-S.wlT, u=Math.min(1,t/230), e=u<0.5?4*u*u*u:1-Math.pow(-2*u+2,3)/2, fo=Math.min(1,(950-t)/180), bt=S.wl==='bt';
    g.fillStyle='#000'; g.fillRect(0,0,128,64); g.globalAlpha=fo;
    const pos=v=>64+v*34, A=bt?-e:1-e, Bp=bt?1-e:-e;
    const dA=1-Math.min(1,Math.abs(A)), dB=1-Math.min(1,Math.abs(Bp));
    g.globalAlpha=fo*(0.25+0.75*dA); icoAir(g,pos(A),25,1+0.5*dA,dA>0.5?W:Dm);
    g.globalAlpha=fo*(0.25+0.75*dB); icoBT(g,pos(Bp),25,0.9+0.5*dB,dB>0.5?W:Dm);
    g.globalAlpha=fo*Math.min(1,Math.max(0,(t-120)/120)); g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(bt?'BLÅTANN':'AIRPLAY',64,50); if('letterSpacing' in g) g.letterSpacing='0px';
    g.fillStyle=Dm; g.font='6px '+F; g.fillText(bt?'Sebastians iPhone':'iPhone · via Wi-Fi',64,59); g.textAlign='left'; g.globalAlpha=1; return true; }
  if(S.power&&S.err&&now-S.errT<2600){ const [h,sub]=ERRS[S.err]; g.fillStyle='#000'; g.fillRect(0,0,128,64); g.strokeStyle=W; g.lineWidth=1.4; g.lineJoin='round'; g.beginPath(); g.moveTo(64,9); g.lineTo(75,28); g.lineTo(53,28); g.closePath(); g.stroke(); g.fillStyle=W; g.fillRect(63.3,15,1.4,7); g.fillRect(63.3,23.6,1.4,1.6);
    g.textAlign='center'; g.font='bold 9px '+F; g.fillText(h,64,43); g.fillStyle=Dm; g.font='6px '+F; g.fillText(sub,64,53); g.textAlign='left'; return true; }
  if(S.power&&now-S.actT<800){ const u=Math.min(1,(now-S.actT)/160), fo=Math.min(1,(800-(now-S.actT))/160); g.fillStyle='#000'; g.fillRect(0,0,128,64); g.globalAlpha=fo; g.fillStyle=W; g.save(); g.translate(64,26); g.scale(0.8+0.2*u,0.8+0.2*u);
    if(S.actK==='next'){ [[-9,0],[0,0]].forEach(([x])=>{ g.beginPath(); g.moveTo(x-1,-7); g.lineTo(x+8,0); g.lineTo(x-1,7); g.closePath(); g.fill(); }); g.fillRect(8,-7,2.4,14); } else if(S.actK==='pause'){ g.fillRect(-6,-8,4,16); g.fillRect(2,-8,4,16); } else { g.beginPath(); g.moveTo(-5,-8); g.lineTo(8,0); g.lineTo(-5,8); g.closePath(); g.fill(); }
    g.restore(); g.textAlign='center'; g.font='bold 8px '+F; g.fillText(S.actK==='next'?'Neste':S.actK==='pause'?'Pause':'Spiller',64,50); g.textAlign='left'; g.globalAlpha=1; return true; }
  if(S.power&&now-S.saveT<1600){ g.fillStyle='#000'; g.fillRect(0,0,128,64); g.strokeStyle=W; g.lineWidth=1.4; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(56,24); g.lineTo(62,30); g.lineTo(73,18); g.stroke();
    g.textAlign='center'; g.fillStyle=W; g.font='bold 8px '+F; g.fillText('Lagret på radioknappen',64,45); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Hold for å spille '+PRESETS[S.set.hold][0],64,55); g.textAlign='left'; return true; }
  if(now-S.toastT<2200){ g.fillStyle='#000'; g.fillRect(0,0,128,64); g.fillStyle=W; g.font='bold 10px '+F; g.textAlign='center'; g.fillText('Tilkoblet',64,28); g.fillStyle=Dm; g.font='7px '+F; g.fillText('Sebastians iPhone',64,40); g.textAlign='left'; return true; }
  if((S.input===3||S.input===1)&&now-S.menuT<2600){ const SRC=S.input===3?USBSRC:AUXSRC, cur=S.input===3?S.usb:S.aux; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(S.input===3?'USB-LYD':'AUX',4,8); g.textAlign='right'; g.fillText('KILDE',124,8); g.textAlign='left'; if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
    const u=Math.min(1,(now-S.menuT)/200), e=1-(1-u)*(1-u)*(1-u);
    SRC.forEach(([n,d],i)=>{ const y=14+i*18, on=i===cur; if(on){ g.globalAlpha=e; g.fillStyle=W; g.beginPath(); g.roundRect(2,y,124,16,2); g.fill(); g.globalAlpha=1; g.fillStyle='#000'; } else g.fillStyle=Dm;
      g.beginPath(); g.arc(9,y+8,2.4,0,Math.PI*2); on?g.fill():(g.lineWidth=0.8,g.strokeStyle=Dm,g.stroke());
      g.font=(on?'bold ':'')+'9px '+F; g.fillText(n,17,y+11); g.font='6px '+F; g.textAlign='right'; g.fillText(d.split(' · ')[0],122,y+11); g.textAlign='left'; });
    volBar(g,F,W,Dm); return true; }
  if(S.input===2&&now-S.menuT<2600){ g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('RADIO',4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    g.textAlign='right'; g.fillText('FAVORITT '+(S.preset+1)+' AV 6',118,8); g.textAlign='left'; g.fillStyle='#2a2a28'; g.fillRect(4,11,114,0.6);
    const u=Math.min(1,(now-S.menuT)/220), off=(1-(1-u)*(1-u)*(1-u))*0+(1-u)*(1-u)*(1-u)*14;
    g.save(); g.beginPath(); g.rect(0,12,120,52); g.clip();
    [-1,1,2].forEach(i=>{ const p=S.preset+i; if(p<0||p>5) return; const y=(i<0?22:i===1?54:68)+off; g.fillStyle=Dm; g.font='7px '+F; g.fillText(String(p+1),6,y); g.fillText(PRESETS[p][0],16,y); });
    const y0=27+off; g.fillStyle=W; g.beginPath(); g.roundRect(2,y0,116,22,2); g.fill(); g.fillStyle='#000';
    g.font='bold 7px '+F; g.fillText(String(S.preset+1),6,y0+9); g.font='bold 10px '+F; g.fillText(PRESETS[S.preset][0],16,y0+10);
    g.font='6px '+F; g.fillText(PRESETS[S.preset][1],16,y0+18);
    g.restore();
    for(let i=0;i<6;i++){ g.fillStyle=i===S.preset?W:'#3a3a37'; g.fillRect(122,15+i*8,2.4,i===S.preset?6:3); }
    return true; }
  return false; }
function holdReboot(){ if(!S.main) return; S.power=true; S.pairT=0; S.rebootT=performance.now(); press(pwrBtn); animate(); }
function holdPair(){ if(!S.power) return; S.input=0; S.wl='bt'; S.pairT=performance.now(); clearTimeout(S.pairTO); S.pairTO=setTimeout(()=>{ if(!S.pairT) return; S.pairT=0; S.btPaired=true; if(!S.btDev.includes('Sebastians iPhone')) S.btDev.unshift('Sebastians iPhone'); S.toastT=performance.now(); syncInputs(); animate(); },6000); syncInputs(); press(inBtns[0]); animate(); }
function syncInputs(){ Object.assign(INPUTS[0],WL[S.wl]); { const tr=TRACKS[S.wl][S.trk[S.wl]]; INPUTS[0].t=tr[0]; INPUTS[0].s=tr[1]; INPUTS[0].dur=tr[2]; } INPUTS[0].st=(S.wl==='air'?'AirPlay · iPhone':'Blåtann · Sebastians iPhone'); INPUTS[2].st=PRESETS[S.preset][0]+' · '+PRESETS[S.preset][1]; INPUTS[2].t=NOWP[S.preset][0]; INPUTS[2].s=NOWP[S.preset][1]; INPUTS[1].t=AUXSRC[S.aux][0]; INPUTS[1].s=AUXSRC[S.aux][1]; INPUTS[3].t=USBSRC[S.usb][0]; INPUTS[3].s=USBSRC[S.usb][1]; }
const LANGS=[['Norsk','nb-NO'],['English','en-GB'],['Svenska','sv-SE'],['Dansk','da-DK']], VV=['Lav','Middels','Høy'];
const SAY={air:['AirPlay','AirPlay','AirPlay','AirPlay'],bt:['Blåtann','Bluetooth','Blåtand','Bluetooth'],aux:['AUX','AUX','AUX','AUX'],radio:['Radio','Radio','Radio','Radio'],usb:['USB','USB','USB','USB']};
const SDEF={clockStyle:0,name:0,lvlAux:0,lvlUsb:0,led:0,voice:false,lang:0,vv:1,hold:2,bass:0,treb:0,bal:0,vstart:0,vmax:0,perIn:true,hpOwn:true,dim:1,off:1,clock:true,auto:1,wake:true};
let SWVER='1.4.2'; const NAMES=['Skjold S1','Stue','Kontor','Soverom'], ERRS=[null,['Lyrion ikke tilgjengelig','Prøver igjen om 10 s'],['Ingen Wi-Fi','Radio og AirPlay er utilgjengelig'],['Overoppheting','Volum redusert til 60']];
const devName=()=>NAMES[S.set.name];
const VMAX=[100,90,80,70], VST=[0,20,30,40], DIMMS=[0,30000,60000], OFFMS=[0,120000,300000], AUTOMS=[0,1.2e6,3.6e6];
const SETS=[{s:'LYD',n:'Bass',num:['bass',-6,6]},{s:'LYD',n:'Diskant',num:['treb',-6,6]},{s:'LYD',n:'Balanse',num:['bal',-5,5]},
 {s:'LYD',n:'Startvolum',o:['vstart',['Sist brukt','20','30','40']]},{s:'LYD',n:'Maksvolum',o:['vmax',['100','90','80','70']]},{s:'LYD',n:'Volum per inngang',b:'perIn'},{s:'LYD',n:'Eget volum hodetlf.',b:'hpOwn'},
 {s:'STEMME',n:'Talebeskjed ved bytte',b:'voice'},{s:'STEMME',n:'Språk',o:['lang',LANGS.map(l=>l[0])]},{s:'STEMME',n:'Stemmevolum',o:['vv',VV]},{s:'STEMME',n:'Test stemme',act:()=>announce(true),v:'▶'},
 {s:'SKJERM',n:'Dimme etter',o:['dim',['Av','30 s','1 min']]},{s:'SKJERM',n:'Slukk etter',o:['off',['Av','2 min','5 min']]},{s:'SKJERM',n:'Klokke i standby',b:'clock'},{s:'SKJERM',n:'Klokkestil',o:['clockStyle',['Tynn','Stor','Analog','Ord','Linje','Dato']]},
 {s:'STRØM',n:'Auto-standby',o:['auto',['Av','20 min','60 min']]},{s:'STRØM',n:'Slå på ved signal',b:'wake'},
 {s:'LYD',n:'Nivå AUX',num:['lvlAux',-6,6]},{s:'LYD',n:'Nivå USB',num:['lvlUsb',-6,6]},
 {s:'SKJERM',n:'LED-ringer',o:['led',['Høy','Middels','Lav','Av']]},
 {s:'RADIO',n:'Hold radioknapp',o:['hold',PRESETS.map(p=>p[0])]},
 {s:'TILKOBLING',n:'Enhetsnavn',o:['name',NAMES]},{s:'TILKOBLING',n:'Parede enheter',act:()=>{S.set.page='bt';},v:()=>S.btDev.length+' ›'},{s:'TILKOBLING',n:'Glem alle enheter',act:()=>{ if(S.set.confirm){ S.btDev=[]; S.btPaired=false; if(S.wl==='bt'){ S.wl='air'; syncInputs(); } S.set.confirm=0; } else S.set.confirm=1; },v:()=>S.set.confirm?'Trykk igjen':''},
 {s:'SYSTEM',n:'Demo: feilmelding',o:['__err',['Ingen','Lyrion','Wi-Fi','Overoppheting']]},
 {s:'SYSTEM',n:'Kjør oppsett på nytt',act:()=>startSetup(),v:'›'},{s:'SYSTEM',n:'Om Skjold S1',act:()=>{S.set.page='om';},v:'›'},{s:'SYSTEM',n:'Fabrikkinnstillinger',act:()=>{ if(S.set.confirm){ Object.assign(S.set,SDEF); LEDK=1; S.set.confirm=0; S.set.page=''; setTimeout(startSetup,0); } else S.set.confirm=1; },v:()=>S.set.confirm?'Trykk igjen':'›'},
 {s:'SYSTEM',n:'Lukk',act:()=>toggleSettings(),v:''}];
SETS.splice(SETS.findIndex(x=>x.n==='Lukk'),1);
const CATS=[['LYD','Lyd'],['TILKOBLING','Tilkobling'],['RADIO','Radio'],['STEMME','Stemme'],['SKJERM','Skjerm og lys'],['STRØM','Strøm'],['SYSTEM','System']];
function curList(){ if(S.set.cat<0) return [...CATS.map((c,i)=>({n:c[1],v:'›',cat:true,act:()=>{ S.set.cat=i; S.set.idx=1; }})),{n:'Lukk',v:'',act:()=>toggleSettings()}];
  return [{n:'‹ Tilbake',v:'',back:true,act:()=>{ S.set.idx=S.set.cat; S.set.cat=-1; }},...SETS.filter(x=>x.s===CATS[S.set.cat][0])]; }
const fmtNum=(k,v)=>k==='bal'?(v===0?'Midt':(v<0?'V ':'H ')+Math.abs(v)):(v>0?'+':v<0?'−':'')+Math.abs(v)+' dB';
const setVal=it=>it.o&&it.o[0]==='__err'?it.o[1][S.err]:it.num?fmtNum(it.num[0],S.set[it.num[0]]):it.o?it.o[1][S.set[it.o[0]]]:it.b?(S.set[it.b]?'På':'Av'):(typeof it.v==='function'?it.v():it.v);
const maxVol=()=>S.err===3?Math.min(60,VMAX[S.set.vmax]):VMAX[S.set.vmax];
function say(t){ if(!('speechSynthesis' in window)) return; speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(t), L=LANGS[S.set.lang][1]; u.lang=L; const v=speechSynthesis.getVoices().find(x=>x.lang&&x.lang.replace('_','-').toLowerCase().startsWith(L.slice(0,2))); if(v) u.voice=v; u.volume=[0.35,0.7,1][S.set.vv]; u.rate=1.05; speechSynthesis.speak(u); }
function announce(force){ if(!force&&!S.set.voice) return; const l=S.set.lang; let t;
  if(S.input===0) t=SAY[S.wl][l]; else if(S.input===1) t='AUX '+(S.aux+1); else if(S.input===2) t=SAY.radio[l]+', '+PRESETS[S.preset][0]; else t='USB, '+USBSRC[S.usb][0]; say(t); }
const playPos=()=>{ const d=INPUTS[0].dur||240; return ((S.paused?S.pausedAt:performance.now())-S.playT)/1000%d; };
function togglePause(){ if(!S.power) return; if(S.paused){ S.playT+=performance.now()-S.pausedAt; S.paused=false; S.actK='play'; } else { S.pausedAt=performance.now(); S.paused=true; S.actK='pause'; } S.actT=performance.now(); refresh(); animate(); }
function nextTrack(){ if(!S.power) return; if(S.input===0){ S.trk[S.wl]=(S.trk[S.wl]+1)%TRACKS[S.wl].length; S.playT=performance.now(); S.pausedAt=S.playT; } else if(S.input===2){ S.preset=Math.min(5,S.preset+1); } else return; S.actK='next'; S.actT=performance.now(); syncInputs(); refresh(); animate(); }
function saveRadio(){ if(!S.power) return; S.input=2; S.set.hold=S.preset; S.saveT=performance.now(); syncInputs(); press(inBtns[2]); refresh(); animate(); }
function holdRadio(){ if(!S.power) return; S.input=2; S.preset=S.set.hold; S.menuT=performance.now(); syncInputs(); press(inBtns[2]); announce(); refresh(); animate(); }
function toggleSettings(){ if(!S.power) return; S.set.open=!S.set.open; S.set.idx=0; S.set.cat=-1; S.set.edit=false; S.set.page=''; S.set.confirm=0; S.set.t=performance.now(); S.menuT=-1e9; refresh(); animate(); }
function setAct(){ const it=curList()[S.set.idx]; S.set.t=performance.now();
  if(S.set.page){ S.set.page=''; } else if(it.num) S.set.edit=!S.set.edit; else if(it.o&&it.o[0]==='__err'){ S.err=(S.err+1)%4; S.errT=performance.now(); if(S.err===3&&S.vol>60) S.vol=60; } else if(it.o) S.set[it.o[0]]=(S.set[it.o[0]]+1)%it.o[1].length; else if(it.b) S.set[it.b]=!S.set[it.b]; else if(it.act) it.act();
  if(it.n!=='Fabrikkinnstillinger'&&it.n!=='Glem alle enheter') S.set.confirm=0; LEDK=[1,0.55,0.22,0][S.set.led]; if(S.vol>maxVol()) S.vol=maxVol(); refresh(); animate(); }
const menuOpen=()=>S.power&&(S.input>=1&&S.input<=3)&&performance.now()-S.menuT<2600;
const volVis=()=>S.input<=1||performance.now()-S.volT<2200;
function spk(g,x,y,k,muted,p,col){ g.save(); g.translate(x,y); g.scale(k,k); g.fillStyle=col; g.strokeStyle=col; g.lineCap='round'; g.lineJoin='round';
  g.beginPath(); g.moveTo(-6,-2.5); g.lineTo(-3,-2.5); g.lineTo(1.5,-6.5); g.lineTo(1.5,6.5); g.lineTo(-3,2.5); g.lineTo(-6,2.5); g.closePath(); g.fill();
  g.lineWidth=1.3; if(muted){ const a=Math.min(1,p*2), b=Math.max(0,Math.min(1,p*2-1)); g.beginPath(); g.moveTo(4,-3); g.lineTo(4+6*a,-3+6*a); if(b>0){ g.moveTo(10,-3); g.lineTo(10-6*b,-3+6*b); } g.stroke(); }
  else [3.5,6.5,9.5].forEach((r,i)=>{ const q=Math.max(0,Math.min(1,p*3-i)); if(!q) return; g.globalAlpha=q; g.beginPath(); g.arc(1.5,0,r,-0.75*q,0.75*q); g.stroke(); }); g.restore(); }
function icoAir(g,x,y,k,col){ g.save(); g.translate(x,y); g.scale(k,k); g.strokeStyle=col; g.fillStyle=col; g.lineWidth=1.2; g.lineJoin='round'; g.lineCap='round';
  g.beginPath(); g.moveTo(-3,4); g.lineTo(-7,4); g.quadraticCurveTo(-8,4,-8,3); g.lineTo(-8,-6); g.quadraticCurveTo(-8,-7,-7,-7); g.lineTo(7,-7); g.quadraticCurveTo(8,-7,8,-6); g.lineTo(8,3); g.quadraticCurveTo(8,4,7,4); g.lineTo(3,4); g.stroke();
  g.beginPath(); g.moveTo(0,1); g.lineTo(5,8); g.lineTo(-5,8); g.closePath(); g.fill(); g.restore(); }
function icoBT(g,x,y,k,col){ g.save(); g.translate(x,y); g.scale(k,k); g.strokeStyle=col; g.lineWidth=1.3; g.lineJoin='round'; g.lineCap='round';
  g.beginPath(); g.moveTo(-4,-4); g.lineTo(4,4); g.lineTo(0,8); g.lineTo(0,-8); g.lineTo(4,-4); g.lineTo(-4,4); g.stroke(); g.restore(); }
let QRLIB=null; import('https://esm.sh/qrcode-generator@1.4.4').then(m=>{ QRLIB=m.default||m; drawOLED(); drawTFT(); }).catch(()=>{});
const qrCache={}; function drawQR(g,x,y,size,text){ g.fillStyle='#f2f2ee'; g.fillRect(x,y,size,size); if(!QRLIB){ g.fillStyle='#000'; g.font='5px sans-serif'; g.textAlign='center'; g.fillText('QR',x+size/2,y+size/2+2); g.textAlign='left'; return; }
  let q=qrCache[text]; if(!q){ q=QRLIB(0,'M'); q.addData(text); q.make(); qrCache[text]=q; } const n=q.getModuleCount(), m=size/(n+2); g.fillStyle='#000'; for(let r=0;r<n;r++) for(let c=0;c<n;c++) if(q.isDark(r,c)) g.fillRect(x+(c+1)*m,y+(r+1)*m,m+0.02,m+0.02); }
const SETUP_SSID='Skjold-Oppsett-0001', SETUP_PW='k7m2q9xd', STEPN=['Språk','Wi-Fi','Navn og rom','Høyttalertest','Lyrion','Programvare'];
function startSetup(){ S.setup={on:true,step:-1,ssid:'',name:'',upd:0,connecting:false,testCh:'',testT:-1e9}; S.set.open=false; refresh(); animate(); }
function volBar(g,F,W,Dm){ if(!volVis()) return; if(S.muted) spk(g,7,55.5,0.6,true,1,W); else { g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText('VOL',2,58); } const on=S.muted?0:Math.round(volShown()/100*24);
  for(let i=0;i<24;i++){g.fillStyle=i<on?W:'#2a2a28'; g.fillRect(20+i*3.6,52,2.6,7);} g.fillStyle=W; g.font='bold 8px '+F; g.textAlign='right'; g.fillText(S.muted?'—':String(volShown()),126,59); g.textAlign='left'; }
function screenDim(){ const idle=performance.now()-S.lastAct, o=OFFMS[S.set.off], d=DIMMS[S.set.dim]; return o&&idle>o?1:d&&idle>d?0.7:0; }
if(!window.SKJOLD_WELCOME){ const sw=document.createElement('script'); sw.src='./skjold_welcome.js'; document.head.appendChild(sw); }
if(!window.SKJOLD){ const sc=document.createElement('script'); sc.src='./skjold_settings.js'; sc.onload=()=>{ drawOLED(); drawTFT(); }; document.head.appendChild(sc); }
function drawClock(g,w,h,k){ if(window.SKJOLD&&window.SKJOLD.drawClock){ window.SKJOLD.drawClock(g,w,h,S.set.clockStyle||0,new Date()); return; } const d=new Date(), t=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'), m=d.getMinutes(); g.fillStyle='#3a3a37'; g.font='300 '+(18*k)+'px "Helvetica Neue",Arial,sans-serif'; g.textAlign='center'; g.fillText(t,w/2+((m%5)-2)*2*k,h/2+6*k+((m%3)-1)*2*k); g.textAlign='left'; }
function drawOLED(){ drawOLED0(); const g=cvs.getContext('2d'); g.setTransform(4,0,0,4,0,0); if(!S.power){ if(S.main&&S.set.clock&&!S.rebootT){ drawClock(g,128,64,1); texO.needsUpdate=true; } return; } const a=screenDim(); if(a){ g.fillStyle='rgba(0,0,0,'+a+')'; g.fillRect(0,0,128,64); texO.needsUpdate=true; } }
function drawOLED0(){ const g=cvs.getContext('2d'); g.setTransform(4,0,0,4,0,0); g.fillStyle='#000'; g.fillRect(0,0,128,64);
  if(!S.power){ texO.needsUpdate=true; return; }
  if(booting()){ drawSplash(g,128,64,2); texO.needsUpdate=true; return; }
  if(S.welcome&&S.power&&!booting()&&window.SKJOLD_WELCOME){ window.SKJOLD_WELCOME.draw(g,128,64,performance.now()-bootT-BOOT,{mono:true,hint:'Trykk en knapp'}); texO.needsUpdate=true; return; }
  if(overlay(g)){ texO.needsUpdate=true; return; }
  const it=INPUTS[S.input], F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86';
  g.fillStyle=W; g.font='bold 7px '+F; let x=2; INPUTS.forEach((t,i)=>{const w=g.measureText(t.k).width+6; if(i===S.input){g.fillRect(x,1,w,9); g.fillStyle='#000';} else g.fillStyle=Dm; g.fillText(t.k,x+3,8); g.fillStyle=W; x+=w+3;});
  if(S.err){ const ex=S.hp?(S.muted?96:106):(S.muted?110:120); g.fillStyle=W; g.beginPath(); g.moveTo(ex,1.5); g.lineTo(ex+4.5,9.5); g.lineTo(ex-4.5,9.5); g.closePath(); g.fill(); g.fillStyle='#000'; g.fillRect(ex-0.5,4,1,3); g.fillRect(ex-0.5,7.8,1,1); }
  if(S.muted) spk(g,S.hp?106:120,5.5,0.55,true,1,W);
  if(S.hp){ g.save(); g.strokeStyle=W; g.fillStyle=W; g.lineWidth=1.1; g.lineCap='round'; g.beginPath(); g.arc(121,6.2,4,Math.PI,0); g.stroke(); g.beginPath(); g.roundRect(116.2,5.6,2.4,3.6,0.8); g.roundRect(123.4,5.6,2.4,3.6,0.8); g.fill(); g.restore(); }
  const fit=(t,w)=>{ if(g.measureText(t).width<=w) return t; while(t.length>1&&g.measureText(t+'…').width>w) t=t.slice(0,-1); return t+'…'; };
  if(!volVis()&&S.input===2){ const tn=performance.now();
    g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(fit(PRESETS[S.preset][0].toUpperCase()+' · '+PRESETS[S.preset][1].toUpperCase(),100),2,20);
    g.textAlign='right'; g.fillText((S.preset+1)+'/6',126,20); g.textAlign='left';
    g.fillStyle=W; g.font='bold 13px '+F; g.fillText(fit(it.t,124),2,36); g.fillStyle=Dm; g.font='8px '+F; g.fillText(fit(it.s,124),2,47);
    g.fillStyle='#2a2a28'; g.fillRect(2,52,124,0.6); g.fillStyle=Math.floor(tn/700)%2?W:'#e05a4a'; g.beginPath(); g.arc(4.5,59,1.8,0,Math.PI*2); g.fill();
    g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(S.muted?'MUTE':'DIREKTE',9,61); g.textAlign='right'; g.fillText('LYRION · 320 KBPS',126,61); g.textAlign='left'; texO.needsUpdate=true; return; }
  if(!volVis()&&S.input===3){ const tn=performance.now()/1000;
    g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText('USB-LYD · '+(S.usb?'PC 2':'PC 1')+'-PORT',2,20);
    g.fillStyle=W; g.font='bold 16px '+F; g.fillText(it.t,2,38); g.fillStyle=Dm; g.font='7px '+F; g.textAlign='right'; g.fillText(S.usb?'48 kHz · 16 bit':'48 kHz · 24 bit',126,38); g.textAlign='left';
    ['L','R'].forEach((c,i)=>{ const y=47+i*8, v=S.muted?0:0.45+0.4*Math.abs(Math.sin(tn*2.3+i*0.9)*Math.sin(tn*0.9+i)), n=Math.round(v*30);
      g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(c,2,y+5); for(let k=0;k<30;k++){ g.fillStyle=k<n?(k>25?'#e05a4a':W):'#2a2a28'; g.fillRect(10+k*3.9,y,2.9,5); } });
    texO.needsUpdate=true; return; }
  const sigI=S.input===1?S.aux:S.input===3?2+S.usb:-1;
  if(sigI>=0&&!S.sig[sigI]){ g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText((S.input===1?'AUX':'USB-LYD')+' · '+it.t.toUpperCase(),2,19);
    g.strokeStyle=Dm; g.lineWidth=1; g.beginPath(); g.moveTo(2,31); for(let x=0;x<=22;x++) g.lineTo(2+x,31); g.stroke(); g.fillStyle=W; g.font='bold 11px '+F; g.fillText('Ingen signal',28,35); g.fillStyle=Dm; g.font='6px '+F; g.fillText(S.input===1?'Sjekk kabelen til '+it.t:'Sjekk at '+it.t+' sender lyd',2,45); volBar(g,F,W,Dm); texO.needsUpdate=true; return; }
  if(it.st){ g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(fit(it.st.toUpperCase(),116),2,19); if(S.paused){ g.fillStyle=W; g.fillRect(119,14.5,2,5.5); g.fillRect(123,14.5,2,5.5); } else for(let i=0;i<3;i++){ const h=1.5+3.5*Math.abs(Math.sin(performance.now()/260+i*1.3)); g.fillStyle=S.muted?'#3a3a37':W; g.fillRect(118+i*3,20-h,2,h); }
    g.fillStyle=W; g.font='bold 11px '+F; g.fillText(fit(it.t,124),2,31);
    if(S.input===0){ const p=playPos(), d=it.dur, tm=x=>Math.floor(x/60)+':'+String(Math.floor(x%60)).padStart(2,'0'), ts=tm(p)+' / '+tm(d); g.font='6px '+F; const tw=g.measureText(ts).width; g.fillStyle=Dm; g.font='7px '+F; g.fillText(fit(it.s,120-tw),2,41); g.font='6px '+F; g.textAlign='right'; g.fillText(ts,126,41); g.textAlign='left'; g.fillStyle='#2a2a28'; g.fillRect(2,44.5,124,1); g.fillStyle=W; g.fillRect(2,44.5,124*p/d,1); }
    else { g.fillStyle=Dm; g.font='7px '+F; g.fillText(fit(it.s,124),2,41); } }
  else { g.fillStyle=W; g.font='bold 12px '+F; g.fillText(it.t,2,27); g.fillStyle=Dm; g.font='7px '+F; g.fillText(it.s,2,37); }
  volBar(g,F,W,Dm);
  texO.needsUpdate=true; }
function drawTFT(){ drawTFT0(); const g=cvt.getContext('2d'); g.setTransform(2,0,0,2,0,0); if(!S.power){ if(S.main&&S.set.clock&&!S.rebootT){ drawClock(g,320,240,3); texT.needsUpdate=true; } return; } const a=screenDim(); if(a){ g.fillStyle='rgba(0,0,0,'+a+')'; g.fillRect(0,0,320,240); texT.needsUpdate=true; } }
function drawTFT0(){ const g=cvt.getContext('2d'); g.setTransform(2,0,0,2,0,0); g.fillStyle='#000'; g.fillRect(0,0,320,240);
  if(!S.power){ texT.needsUpdate=true; return; }
  if(booting()){ drawSplash(g,320,240,4.4); texT.needsUpdate=true; return; }
  if(S.welcome&&S.power&&!booting()&&window.SKJOLD_WELCOME){ window.SKJOLD_WELCOME.draw(g,320,240,performance.now()-bootT-BOOT); texT.needsUpdate=true; return; }
  { g.save(); g.translate(0,40); g.scale(2.5,2.5); const o=overlay(g); g.restore(); if(o){ texT.needsUpdate=true; return; } }
  const it=INPUTS[S.input], F='"Helvetica Neue",Arial,sans-serif', W='#f4f1ea', Dm='#9a968c', A='#d9a441', now=(performance.now()-T0)/1000;
  g.font='bold 11px '+F; g.textBaseline='middle'; let x=12; INPUTS.forEach((t,i)=>{const w=g.measureText(t.k).width+16; g.beginPath(); g.roundRect(x,8,w,18,9); if(i===S.input){g.fillStyle=W; g.fill(); g.fillStyle='#000';} else {g.strokeStyle='#55524c'; g.stroke(); g.fillStyle=Dm;} g.fillText(t.k,x+8,17.5); x+=w+6;});
  const hu=[[18,52],[205,260],[150,95],[280,330]][S.input]; const gr=g.createLinearGradient(12,36,140,164); gr.addColorStop(0,'hsl('+hu[0]+' 70% 55%)'); gr.addColorStop(1,'hsl('+hu[1]+' 60% 20%)');
  g.save(); g.beginPath(); g.roundRect(12,36,128,128,6); g.clip(); g.fillStyle=gr; g.fillRect(12,36,128,128); g.restore();
  g.fillStyle=W; g.font='bold 18px '+F; g.fillText(it.t,154,54); g.fillStyle=Dm; g.font='13px '+F; g.fillText(it.s,154,76); g.fillStyle=A; g.font='bold 10px '+F; g.fillText(('LYRION · '+it.n).toUpperCase(),154,98);
  for(let i=0;i<26;i++){const v=0.35+0.65*Math.abs(Math.sin(now*3.1+i*0.7)*Math.sin(now*1.7+i*0.31)), h=S.muted?2:4+v*44; g.fillStyle=A; g.fillRect(154+i*6,164-h,4,h);}
  if(volVis()){ g.fillStyle=Dm; g.font='bold 10px '+F; g.fillText(S.muted?'MUTE':'VOL',12,222); const on=S.muted?0:Math.round(volShown()/100*32);
  for(let i=0;i<32;i++){g.fillStyle=i<on?W:'#2c2b29'; g.fillRect(44+i*6.875,216,5.4,12);} g.fillStyle=W; g.font='bold 16px '+F; g.textAlign='right'; g.fillText(S.muted?'—':String(volShown()),308,222); g.textAlign='left'; }
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
  const prof=profPts(HW,0,H,RT,RB), HPx=REVB.front.find(f=>f.hp).x, slotI=prof.findIndex(p=>p.y<0.01&&p.x<HPx-4.3);
  const profF=[...prof,new V2(HPx-4.3,0),...arcPts(HPx-4.3+1,12.3-1,1,Math.PI,Math.PI/2,4),...arcPts(HPx+4.3-1,12.3-1,1,Math.PI/2,0,4),new V2(HPx+4.3,0)]; // bottom edge closes BL→BR (+x): open slot for PJ-392
  { const clip=(P,ax,v,keepLess)=>{ const o=[]; const val=p=>ax==='x'?p.x:p.y, ins=p=>keepLess?val(p)<=v+1e-9:val(p)>=v-1e-9; for(let i=0;i<P.length;i++){ const a=P[i], b=P[(i+1)%P.length]; if(ins(a)) o.push(a); if(ins(a)!==ins(b)){ const t=(v-val(a))/(val(b)-val(a)); o.push(new V2(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t)); } } return o; };
    const C=(P,...cs)=>cs.reduce((q,c)=>clip(q,...c),P), sc=REVB.front.filter(f=>f.screw), inside=(P,f)=>{ const xs=P.map(p=>p.x), zs=P.map(p=>p.y); return f.x>Math.min(...xs)+1.8&&f.x<Math.max(...xs)-1.8&&f.y>Math.min(...zs)+1.8&&f.y<Math.max(...zs)-1.8; };
    const parts=[C(prof,['x',-88,true]), C(prof,['x',-88,false],['x',-79,true],['y',36.5,false]), C(prof,['x',-88,false],['x',-81,true],['y',13,true]), C(prof,['x',-79,false],['x',79,true],['y',43.5,false]), C(prof,['x',-71,false],['x',79,true],['y',6,true]), C(prof,['x',79,false])]; // frame all round behind the plate edge, open only for the controls + PJ-392 notch // open front panel: controls mount in the alu plate only
    for(const k of ['oled','tft']) parts.forEach((P,j)=>{ const fw=panel('front_'+k+'_'+j,'front',shape(P,sc.filter(f=>inside(P,f)).map(f=>hp(f,undefined,mr,3.4))),HD-t,HD,mat,g); fw.userData.disp=k; frontWalls.push(fw); lab(fw,'Frontpanel · åpent bak frontplaten – knapper, skjerm og kontakter sitter kun i alu-platen'); }); }
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
const frontsA={}, frontsRA={};
function buildAluPlate(g,k,outline){ const T=3, toF=m=>{m.applyMatrix4(basis([1,0,0],[0,0,1],[0,-1,0])); return m;}; // spec §3: 178×46×3 R3, outside y −83
  const holes=[rr(31,19,1.5,DX,0),...REVB.front.filter(f=>!f.screw).slice(1).map(f=>circ(f.x,f.y-24,(f.hp?5.5:f.d)/2,48))];
  const bb=0.3, pl=toF(mesh('alu_frontplate',new THREE.ExtrudeGeometry(shape(outline(bb),holes.map(h=>h)),{depth:T-2*bb,bevelEnabled:true,bevelThickness:bb,bevelSize:bb,bevelSegments:3,curveSegments:32}),M.face,g));
  pl.geometry.translate(0,0,bb); pl.position.set(0,-HD,H/2);
  const ac=toF(mesh('akryl_innfelt',geo(shape(rr(30.8,18.8,1.3)),2),C.acryl,g)); ac.position.set(DX,-HD-1,24); ac.castShadow=false; // 1 mm recessed from the front (y −82)
  lab(pl,'Frontplate alu 3 mm (avrundet: 186 × 44, R7 som kassen / rett: 178 × 46, R3) · eloksert · 6 × FH-M3-8 studs bakfra · laser-merket');
  lab(ac,'Røyksort akryl 61,6 × 37,6 × 2 mm · limt inn bakfra, 1 mm innfelt');
  [[-83,17],[83,-14],[83,17],[12,-15.5],[12,15.5]].forEach(([x,y])=>{ const st=mesh('fh_m3_stud',new THREE.CylinderGeometry(1.5,1.5,8,16),C.shell,g); st.position.set(x,-HD+4-0.0+0,24+y); }); }
{ const P=REVB.plate;
  for(const k of ['oled','tft']){
    const gA=new THREE.Group(); gA.name='alu_frontplate_avrundet_'+k; frontRoot.add(gA); frontsRA[k]=gA; gA.visible=false; buildAluPlate(gA,k,o=>profPts(HW-2-o,-22+o,22-o,RT-2-o,RT-2-o));
    const gB=new THREE.Group(); gB.name='alu_frontplate_'+k; frontRoot.add(gB); frontsA[k]=gB; gB.visible=false; buildAluPlate(gB,k,o=>rr(89-o,23-o,3-o));
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
  M.print.color.set(0x2c2d30);
  if(S.fm==='alu'){ M.face.color.set(COLS[S.fcol][1]); M.face.roughness=0.45; M.face.metalness=S.fcol==='natural'?0.8:0.7; } else { M.face.color.set(0xcbbd9e); M.face.roughness=0.88; M.face.metalness=0; } M.face.needsUpdate=true;
  document.querySelectorAll('[data-fcol]').forEach(b=>b.classList.toggle('on',S.fm==='alu'&&b.dataset.fcol===S.fcol)); $('fcolRow').style.opacity=S.fm==='alu'?1:0.4; $('fcolName').textContent=S.fm==='alu'?'· '+COLS[S.fcol][0]:'';
  document.querySelectorAll('[data-fm]').forEach(b=>b.classList.toggle('on',b.dataset.fm===S.fm)); legendMats.forEach(m=>m.color.set(dark?0xd2d4d7:0x3a3b3e));
  inBtns.concat([pwrBtn]).forEach(b=>b.userData.ledOff=0x3a3a3d);
  document.querySelectorAll('[data-surf]').forEach(b=>b.classList.toggle('on',b.dataset.surf===S.surf)); document.querySelectorAll('[data-col]').forEach(b=>b.classList.toggle('on',b.dataset.col===S.col));
  $('surfInfo').textContent=sf.n+' · '+COLS[S.col][0]; }
// ---------- UI ----------
const S={rebootT:0,wl:'air',btPaired:true,pairT:0,pairTO:0,preset:1,usb:0,aux:0,menuT:-1e9,hpT:-1e9,setup:{on:false,step:-1,ssid:'',name:'',upd:0,connecting:false,testCh:'',testT:-1e9},set:{open:false,cat:-1,idx:0,t:0,edit:false,page:'',confirm:0,clockStyle:0,name:0,lvlAux:0,lvlUsb:0,led:0,voice:false,lang:0,vv:1,hold:2,bass:0,treb:0,bal:0,vstart:0,vmax:0,perIn:true,hpOwn:true,dim:1,off:1,clock:true,auto:1,wake:true},vols:[42,42,42,42],trk:{air:0,bt:0},playT:performance.now(),pausedAt:0,paused:false,actT:-1e9,actK:'',err:0,errT:-1e9,holdWhat:'',saveT:-1e9,btDev:['Sebastians iPhone','MacBook Pro'],sig:[true,false,true,true],hpVol:25,lastAct:performance.now(),knobHoldT:0,wlT:-1e9,muteT:-1e9,volT:-1e9,toastT:-1e9,hp:false,flip:false,ac:'royk',fm:'alu',fcol:'champagne',form:'rund',surf:'beadanod',col:'black',v:'plate',l:'fritt',f:'oled',open:false,ex:false,xray:false,main:true,power:true,input:0,vol:42,muted:false};
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
  else if(i===0&&S.input===0){ S.wl=S.wl==='air'&&S.btPaired?'bt':'air'; S.wlT=performance.now(); S.playT=performance.now(); S.pausedAt=S.playT; }
  if(i===2){ if(S.input===2) S.preset=(S.preset+1)%6; S.menuT=performance.now(); }
  if(i===3){ if(S.input===3) S.usb=1-S.usb; S.menuT=performance.now(); }
  if(i===1){ if(S.input===1) S.aux=1-S.aux; S.menuT=performance.now(); }
  if(S.set.perIn&&i!==S.input){ S.vols[S.input]=S.vol; S.vol=Math.min(maxVol(),S.vols[i]); S.volT=performance.now(); }
  S.input=i; syncInputs(); press(inBtns[i]); if(S.set.open){ S.set.open=false; } announce(); refresh(); animate(); }
const bc=('BroadcastChannel' in window)?new BroadcastChannel('skjold-s1'):null;
function publish(){ if(!bc) return; const it=INPUTS[S.input]; const set={}; for(const k in SDEF) set[k]=S.set[k]; bc.postMessage({type:'state',power:S.power,main:S.main,input:S.input,wl:S.wl,aux:S.aux,usb:S.usb,preset:S.preset,vol:S.vol,muted:S.muted,hp:S.hp,paused:S.paused,maxVol:maxVol(),title:it.t,sub:it.s,st:it.st||'',name:devName(),err:S.err,btDev:S.btDev,presets:PRESETS.map(p=>p[0]),set}); }
if(bc) bc.onmessage=e=>{ const m=e.data||{}; S.lastAct=performance.now();
  if(m.type==='hello') return publish();
  if(m.type==='set'&&/^n(Aux|Usb)[12]$/.test(m.k)){ const L=m.k.startsWith('nAux')?AUXSRC:USBSRC; L[+m.k.slice(-1)-1][0]=String(m.v||'').slice(0,14)||(m.k.startsWith('nAux')?'AUX '+m.k.slice(-1):'PC '+m.k.slice(-1)); syncInputs(); }
  else if(m.type==='updSync'&&m.version){ SWVER=m.version; }
  else if(m.type==='set'&&m.k in SDEF){ S.set[m.k]=m.v; LEDK=[1,0.55,0.22,0][S.set.led]; if(S.vol>maxVol()) S.vol=maxVol(); }
  else if(m.type==='setup'){ const U=S.setup; if(m.step>=8){ U.on=false; } else { U.on=true; U.step=m.step; if(m.ssid!==undefined) U.ssid=m.ssid; if(m.name) U.name=m.name; if(m.upd!==undefined) U.upd=m.upd; U.connecting=!!m.connecting; } if(!S.power) pwrBtn.userData.act(); }
  else if(m.type==='setupTest'){ S.setup.testCh=m.ch; S.setup.testT=performance.now(); say(m.ch==='L'?['Venstre','Left','Vänster','Venstre'][S.set.lang]:['Høyre','Right','Höger','Højre'][S.set.lang]); }
  else if(m.type==='input') selectInput(m.i);
  else if(m.type==='wl'){ S.wl=m.v; S.input=0; S.wlT=performance.now(); syncInputs(); }
  else if(m.type==='src'){ if(S.input===1) S.aux=m.v; else if(S.input===3) S.usb=m.v; else if(S.input===2) S.preset=m.v; S.menuT=performance.now(); syncInputs(); }
  else if(m.type==='vol'){ S.vol=Math.min(maxVol(),m.v); S.muted=false; S.volT=performance.now(); }
  else if(m.type==='mute'){ S.muted=!S.muted; S.volT=S.muteT=performance.now(); }
  else if(m.type==='power'){ pwrBtn.userData.act(); return; }
  else if(m.type==='pause') return togglePause();
  else if(m.type==='next') return nextTrack();
  else if(m.type==='forget'){ S.btDev=[]; S.btPaired=false; if(S.wl==='bt'){ S.wl='air'; syncInputs(); } }
  else if(m.type==='reset'){ Object.assign(S.set,SDEF); LEDK=1; }
  else if(m.type==='presets'&&Array.isArray(m.list)){ m.list.slice(0,6).forEach((p,i)=>{ PRESETS[i]=[p[0],p[1]]; NOWP[i]=p[2]||['Direkte',p[0]]; }); syncInputs(); }
  else if(m.type==='previewClock'){ S.clockPrevT=performance.now(); }
  else if(m.type==='setup') return startSetup();
  else if(m.type==='testVoice') return announce(true);
  refresh(); animate(); };
function refresh(){ setTimeout(publish,0);
  inBtns.forEach((b,i)=>setLed(b.userData.led,S.power&&i===S.input,1,b.userData.ledOff)); setLed(pwrBtn.userData.led,S.main&&S.power,1,pwrBtn.userData.ledOff); if(pwrBtn.userData.sym) pwrBtn.userData.sym.color.set(S.power?0xffffff:(S.main?0x9a9a9a:0x6a6a6c));
  vip.rotation.set(0,0,S.main?-0.16:0.16); knob.rotation.y=-(S.vol/100)*Math.PI*1.5;
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
  const alu=S.fm==='alu'; Object.entries(fronts).forEach(([k,g])=>{g.visible=k===S.f&&!rund&&!alu; g.position.y=S.ex?-35:0;}); Object.entries(frontsR).forEach(([k,g])=>{g.visible=k===S.f&&rund&&!alu; g.position.y=S.ex?-35:0;});
  Object.entries(frontsA).forEach(([k,g])=>{g.visible=k===S.f&&!rund&&alu; g.position.y=S.ex?-35:0;}); Object.entries(frontsRA).forEach(([k,g])=>{g.visible=k===S.f&&rund&&alu; g.position.y=S.ex?-35:0;});
  { const lc=['black','wine','purple','blue','grey','teal','red'].includes(S.fcol); frontInk.forEach(m=>m.color.set(alu?(lc?0xe6e6e3:0x2a2a2c):0x161617)); }
  lidRoot.visible=!rund;
  Object.entries(disp).forEach(([k,g])=>{g.visible=k===S.f; const sh=(S.v==='plate'?-1.2:0); g.children.forEach(c=>{ if(c.userData.by===undefined) c.userData.by=c.position.y;
    if(c.name.endsWith('bilde')){ const royk=S.ac==='royk'; c.position.y=royk?(S.fm==='alu'?-HD-1-2-0.04:c.userData.by)+(S.ex?-35:0):-(HD-2.7)-0.02+sh; c.material.blending=royk?THREE.AdditiveBlending:THREE.NormalBlending; c.material.transparent=royk; c.material.color.set(royk?0xd8d8d8:0xffffff); c.material.needsUpdate=true; }
    else c.position.y=c.userData.by+sh; });}); frontWalls.forEach(w=>w.visible=w.userData.disp===S.f);
  { const dA=S.fm==='alu'?1:0; [...inBtns,pwrBtn,knob,hpJack].forEach(g=>{ if(g.userData.baseY===undefined) g.userData.baseY=g.position.y; g.position.y=g.userData.baseY+dA+(S.ex?-35:0); });
    parts.children.filter(c=>c.material&&frontInk.includes(c.material)).forEach(c=>{ if(c.userData.by0===undefined) c.userData.by0=c.position.y; c.position.y=c.userData.by0+dA; }); }
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
document.querySelectorAll('[data-fm]').forEach(b=>b.onclick=()=>{S.fm=b.dataset.fm; sync();});
$('fcolRow').innerHTML=Object.entries(COLS).map(([k,v])=>'<button data-fcol="'+k+'" title="'+v[0]+'" style="flex:0 0 26px;height:26px;padding:0;border-radius:50%!important;background:#'+v[1].toString(16).padStart(6,'0')+'"></button>').join('');
document.querySelectorAll('[data-fcol]').forEach(b=>b.onclick=()=>{S.fm='alu'; S.fcol=b.dataset.fcol; sync();});
document.querySelectorAll('[data-surf]').forEach(b=>b.onclick=()=>{S.surf=b.dataset.surf; sync();}); document.querySelectorAll('[data-col]').forEach(b=>b.onclick=()=>{S.col=b.dataset.col; sync();});
$('xray').onclick=()=>{S.xray=!S.xray; sync();};
$('inputs').innerHTML=INPUTS.map((it,i)=>'<button data-i="'+i+'">'+it.n+'</button>').join('')+'<button id="pairBtn">Hold: BT-paring</button><button id="rebootBtn">Hold power: omstart</button>';
document.querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>selectInput(+b.dataset.i)); $('pairBtn').onclick=()=>holdPair(); $('rebootBtn').onclick=()=>holdReboot();
syncInputs();
$('pwr').onclick=()=>pwrBtn.userData.act(); $('main').onclick=()=>rk.userData.act?rk.userData.act():rk.children[0].userData.act();
$('mute').onclick=()=>{S.muted=!S.muted; S.volT=S.muteT=performance.now(); refresh(); animate();}; $('vol').oninput=e=>{S.vol=Math.min(maxVol(),+e.target.value); S.muted=false; S.volT=performance.now(); refresh(); animate();};
// ---------- 3D picking: hover label, click to operate, scroll on knob = volume ----------
const cv=stage._renderer.domElement, cam=stage._camera, ray=new THREE.Raycaster(), ptr=new THREE.Vector2(), tip=$('tip');
const hit=e=>{ const r=cv.getBoundingClientRect(); ptr.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1); ray.setFromCamera(ptr,cam);
  const hs=ray.intersectObjects(root.children,true).filter(h=>{for(let o=h.object;o;o=o.parent) if(!o.visible) return false; const m=h.object.material; return !(m&&m.transparent&&m.opacity<0.5);});
  return hs.length&&hs[0].object.userData.label?hs[0].object:null; };
let down=null;
cv.addEventListener('pointermove',e=>{ const o=hit(e); cv.style.cursor=o&&o.userData.act?'pointer':''; if(o){tip.style.display='block'; tip.textContent=o.userData.label; tip.style.left=(e.clientX+14)+'px'; tip.style.top=(e.clientY+12)+'px';} else tip.style.display='none'; });
cv.addEventListener('pointerleave',()=>tip.style.display='none');
{ let wd=null; const wOn=()=>S.welcome&&S.power&&!booting(); const host=cv.parentElement||document;
  host.addEventListener('pointerdown',e=>{ if(!wOn()) return; const o=hit(e); if(o&&o.userData.act){ wd=[e.clientX,e.clientY]; e.stopImmediatePropagation(); } },true);
  host.addEventListener('pointerup',e=>{ if(!wd) return; const m=Math.hypot(e.clientX-wd[0],e.clientY-wd[1]); wd=null; if(m>6||!wOn()) return; e.stopImmediatePropagation(); S.welcome=false; S.lastAct=performance.now(); drawOLED(); drawTFT(); refresh(); },true);
  host.addEventListener('wheel',e=>{ if(!wOn()) return; const o=hit(e); if(o&&o.userData.label&&o.userData.label.indexOf('Volum')===0){ e.preventDefault(); e.stopImmediatePropagation(); } },{capture:true,passive:false}); }
let holdTO=0, held=false; cv.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY]; held=false; clearTimeout(holdTO); const o=hit(e); if(o&&o.userData.hold){ const ms=o.userData.holdMs||1200; if(ms>2000){ S.knobHoldT=performance.now(); S.holdWhat=o.userData.holdKind||'knob'; S.holdObj=o; animate(); } holdTO=setTimeout(()=>{ held=true; S.knobHoldT=0; o.userData.hold(); },ms); }});
cv.addEventListener('pointerup',e=>{ clearTimeout(holdTO); if(S.knobHoldT){ const dt=performance.now()-S.knobHoldT, o=S.holdObj; S.knobHoldT=0; if(dt>800&&o&&o.userData.hold2){ held=false; o.userData.hold2(); return; } refresh(); } if(held){ held=false; return; } if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4) return; const o=hit(e); if(o&&o.userData.act) o.userData.act(); });
let wheelT=0; cv.addEventListener('wheel',e=>{ const o=hit(e); if(!o||o.userData.label.indexOf('Volum')!==0) return; e.preventDefault(); e.stopImmediatePropagation();
  if(S.set.open){ const n=performance.now(); if(n-wheelT<140) return; wheelT=n; const d=e.deltaY>0?1:-1; S.set.t=n; if(S.set.page){ return; }
    if(S.set.edit){ const [k,mn,mx]=curList()[S.set.idx].num; S.set[k]=Math.max(mn,Math.min(mx,S.set[k]-d)); } else { S.set.idx=Math.max(0,Math.min(curList().length-1,S.set.idx+d)); S.set.confirm=0; } refresh(); animate(); return; }
  if(menuOpen()){ const n=performance.now(); if(n-wheelT<140) return; wheelT=n; const d=e.deltaY>0?1:-1; const cl=(v,m)=>Math.max(0,Math.min(m,v)); if(S.input===2) S.preset=cl(S.preset+d,5); else if(S.input===3) S.usb=cl(S.usb+d,1); else S.aux=cl(S.aux+d,1); S.menuT=n; syncInputs(); announce(); refresh(); animate(); return; }
  S.vol=Math.max(0,Math.min(maxVol(),S.vol+(e.deltaY>0?2:-2))); S.muted=false; S.volT=performance.now(); refresh(); animate(); },{capture:true,passive:false});
setInterval(()=>{ if(S.f==='tft'&&S.power) drawTFT(); },80);
['pointerdown','wheel','keydown','input'].forEach(ev=>document.addEventListener(ev,()=>{ const was=screenDim(); S.lastAct=performance.now(); if(was) refresh(); },{capture:true,passive:true}));
let dimWas=0; setInterval(()=>{ const n=performance.now(); if(S.power&&AUTOMS[S.set.auto]&&n-S.lastAct>AUTOMS[S.set.auto]){ S.power=false; refresh(); }
  const d=screenDim(); if(d!==dimWas||!S.power){ dimWas=d; drawOLED(); drawTFT(); } },1000);
sync();
startBoot();
window.__S=S; window.__sync=sync;
if($('welcome')) $('welcome').onclick=()=>{ S.welcome=true; S.main=true; S.power=true; startBoot(); refresh(); };
