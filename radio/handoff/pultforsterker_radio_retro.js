const stage = document.querySelector('three-d-stage');
const { THREE } = await stage.ready;
const V2 = THREE.Vector2, V3 = THREE.Vector3;

// woven fabric texture (one tile = 3 mm)
function weave(){
  const c=document.createElement('canvas'); c.width=c.height=96; const g=c.getContext('2d');
  g.fillStyle='#808080'; g.fillRect(0,0,96,96);
  const n=6, s=96/n;
  for(let j=0;j<n;j++) for(let i=0;i<n;i++){
    const over=(i+j)%2===0, x=i*s, y=j*s;
    const gr=over?g.createLinearGradient(x,y,x,y+s):g.createLinearGradient(x,y,x+s,y);
    gr.addColorStop(0,'#5a5a5a'); gr.addColorStop(.5,'#c8c8c8'); gr.addColorStop(1,'#5a5a5a');
    g.fillStyle=gr; g.fillRect(x+1,y+1,s-2,s-2);
  }
  for(let k=0;k<900;k++){g.fillStyle=`rgba(${Math.random()<.5?255:0},${Math.random()<.5?255:0},${Math.random()<.5?255:0},.05)`; g.fillRect(Math.random()*96,Math.random()*96,1.5,1.5);}
  const t=new THREE.CanvasTexture(c); t.wrapS=t.wrapT=THREE.RepeatWrapping; t.repeat.set(1/3,1/3); t.anisotropy=8; return t;
}
const wt=weave();
const PAL={
  light:{shell:0xebe8e1,panel:0xf3f1ec,fabric:0xb4b0a7,cap:0xf7f6f2,capText:'#3b3a37',text:'#55534e',textDim:'#9a978f',led:0xd2cfc8,feet:0xa9a69f},
  dark:{shell:0x1f1f21,panel:0x2a2a2d,fabric:0x3a3a3d,cap:0x3c3c40,capText:'#f0eee9',text:'#a8a6a0',textDim:'#8a8882',led:0x4a4a4e,feet:0x141414},
};
const M = {
  shell: new THREE.MeshStandardMaterial({ name:'shell', roughness:0.72 }),
  panel: new THREE.MeshStandardMaterial({ name:'panel', roughness:0.6 }),
  fabric:new THREE.MeshStandardMaterial({ name:'fabric_melange', roughness:1, map:wt, bumpMap:wt, bumpScale:0.6 }),
  alu:   new THREE.MeshStandardMaterial({ name:'aluminium', color:0xd4d3ce, roughness:0.3, metalness:0.75 }),
  knurl: new THREE.MeshStandardMaterial({ name:'aluminium_knurl', color:0xc8c7c2, roughness:0.4, metalness:0.75, flatShading:true }),
  cap:   new THREE.MeshStandardMaterial({ name:'button_cap', roughness:0.45 }),
  dark:  new THREE.MeshStandardMaterial({ name:'black_hardware', color:0x1a1a1b, roughness:0.45, metalness:0.2 }),
  glass: new THREE.MeshStandardMaterial({ name:'black_acrylic', color:0x050506, roughness:0.04, metalness:0.2 }),
  red:   new THREE.MeshStandardMaterial({ name:'post_red', color:0xa3261d, roughness:0.35 }),
  pcb:   new THREE.MeshStandardMaterial({ name:'pcb', color:0x1f4a7a, roughness:0.6 }),
  pcbG:  new THREE.MeshStandardMaterial({ name:'pcb_green', color:0x1d5a3a, roughness:0.6 }),
  feet:  new THREE.MeshStandardMaterial({ name:'feet', roughness:0.95 }),
  cone:  new THREE.MeshStandardMaterial({ name:'speaker_cone', color:0x2a2a2c, roughness:0.85 }),
};
let C=PAL.light;
function applyPalette(dark){C=dark?PAL.dark:PAL.light; for(const k of ['shell','panel','fabric','cap','feet']) M[k].color.set(C[k]);}
function rr(hw,hh,r,cx=0,cy=0,seg=10){const pts=[],C=[[-hw+r,hh-r,90],[-hw+r,-hh+r,180],[hw-r,-hh+r,270],[hw-r,hh-r,0]];
  for(const [x,y,a0] of C) for(let i=0;i<=seg;i++){const a=(a0+90*i/seg)*Math.PI/180; pts.push(new V2(cx+x+r*Math.cos(a),cy+y+r*Math.sin(a)));} return pts;}
const circ=(cx,cy,r,n=48)=>Array.from({length:n},(_,i)=>new V2(cx+r*Math.cos(i/n*2*Math.PI),cy+r*Math.sin(i/n*2*Math.PI)));
function shape(o,h=[]){const s=new THREE.Shape(o); for(const p of h) s.holes.push(new THREE.Path(p)); return s;}
const geo=(s,depth,b=0)=>new THREE.ExtrudeGeometry(s,{depth,bevelEnabled:b>0,bevelThickness:b,bevelSize:b,bevelSegments:3,curveSegments:24});
function mesh(name,g,mat,parent,pos=[0,0,0],print){const m=new THREE.Mesh(g,mat); m.name=name; m.position.set(...pos); m.castShadow=m.receiveShadow=true; if(print) m.userData.print=print; parent.add(m); return m;}
const extZ=(n,s,z0,d,mat,p,pr,b=0)=>mesh(n,geo(s,d,b),mat,p,[0,0,z0+b],pr);
function extY(n,s,y0,d,mat,p,pr,b=0){const m=mesh(n,geo(s,d,b),mat,p,[0,y0-b,0],pr); m.rotation.x=Math.PI/2; return m;}
const basis=(x,y,z)=>new THREE.Matrix4().makeBasis(new V3(...x),new V3(...y),new V3(...z));
const faceFront=m=>(m.setRotationFromMatrix(basis([1,0,0],[0,0,1],[0,-1,0])),m);
const faceBack=m=>(m.setRotationFromMatrix(basis([-1,0,0],[0,0,1],[0,1,0])),m);
const toZ=m=>(m.rotation.x=Math.PI/2,m);

const cvs=document.createElement('canvas'); cvs.width=640; cvs.height=480;
const tex=new THREE.CanvasTexture(cvs); tex.colorSpace=THREE.SRGBColorSpace; tex.anisotropy=8;
const press=(m)=>{const o=m.position.y; m.position.y=o+0.8; setTimeout(()=>m.position.y=o,160);};
const setLed=(m,on)=>{m.emissive.set(on?0xfff4e0:0); m.emissiveIntensity=on?2:0; m.color.set(on?0xffffff:C.led);};

async function loadSTL(url){const b=await (await fetch(url)).arrayBuffer(), dv=new DataView(b), n=dv.getUint32(80,true), pos=new Float32Array(n*9);
  for(let i=0;i<n;i++) for(let j=0;j<9;j++) pos[i*9+j]=dv.getFloat32(84+i*50+12+j*4,true);
  const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(pos,3)); g.computeVertexNormals(); return g;}
const CT=await (await fetch('retro/shell_contours.json')).json();
const SHELLS={deep:{geo:await loadSTL('retro/deep.stl'),ymin:-52,ymax:52,ct:CT.deep}, shell:{geo:await loadSTL('retro/shell.stl'),ymin:-42.5,ymax:42.5,ct:CT.shell}};
// the shell bottom has slots, so the sliced bottom run hits the outer surface: rebuild the lower half from the clean upper half
const fixCt=a=>{const N=a.length; return a.map(([x,z],k)=>{ if(z>=0) return [x,z]; const [mx,mz]=a[(N-k)%N], r=Math.hypot(x,z), rm=Math.hypot(mx,mz); return r>rm?[mx,-mz]:[x,z]; });};

for(const c of [CT.deep,CT.shell]){ const N=c.recess.length, rad=p=>Math.hypot(p[0],p[1]);
  // back slices hit the bottom slots: clamp the lower half to the mirrored upper half, scaled by the (clean) front asymmetry
  c.recess=c.recess.map((p,k)=>{ if(p[1]>=0) return p; const m=(N-k)%N, lim=rad(c.recess[m])*rad(c.inner[k])/rad(c.inner[m]), r=rad(p); return r>lim?[p[0]*lim/r,p[1]*lim/r]:p; }); }
const poly=a=>a.map(([x,z])=>new V2(x,z));
const shrink=(P,d)=>P.map(p=>{const r=Math.hypot(p.x,p.y); return new V2(p.x*(r-d)/r,p.y*(r-d)/r);});
const zAt=(P,x,sgn)=>Math.max(...P.filter(p=>Math.abs(p.x-x)<4&&sgn*p.y>0).map(p=>sgn*p.y));
M.shellPrint=new THREE.MeshStandardMaterial({name:'shell_pla',roughness:0.62});
M.grillPla=new THREE.MeshStandardMaterial({name:'grill_pla',roughness:0.7,side:THREE.DoubleSide});
M.face=new THREE.MeshStandardMaterial({name:'faceplate_pla',roughness:0.85});
let TH;
function applyTheme(k){TH=THEMES[k]; applyPalette(false); M.shellPrint.color.set(TH.shell); M.grillPla.color.set(TH.grill); M.face.color.set(TH.face); M.cap.color.set(TH.cap); C={...C,capText:TH.capText};}
function icon(kind,col,txt){
  const c=document.createElement('canvas'); c.width=c.height=256; const g=c.getContext('2d');
  g.strokeStyle=col; g.fillStyle=col; g.lineWidth=18; g.lineCap='round'; g.lineJoin='round';
  const tri=(x,d)=>{g.beginPath(); g.moveTo(x,88); g.lineTo(x+d*62,128); g.lineTo(x,168); g.closePath(); g.fill();};
  if(txt){g.font='bold 150px "Helvetica Neue",Arial,sans-serif'; g.textAlign='center'; g.textBaseline='middle'; g.fillText(txt,128,136);}
  else if(kind==='power'){g.beginPath(); g.arc(128,140,70,-Math.PI/2+0.72,-Math.PI/2-0.72+2*Math.PI); g.stroke(); g.beginPath(); g.moveTo(128,42); g.lineTo(128,130); g.stroke();}
  else if(kind==='source'){g.beginPath(); g.roundRect(70,70,130,116,12); g.stroke(); g.beginPath(); g.moveTo(36,128); g.lineTo(128,128); g.stroke(); g.beginPath(); g.moveTo(100,98); g.lineTo(130,128); g.lineTo(100,158); g.stroke();}
  else if(kind==='prev'){tri(124,-1); tri(186,-1); g.fillRect(52,88,16,80);}
  else if(kind==='next'){tri(132,1); tri(70,1); g.fillRect(188,88,16,80);}
  else if(kind==='star'){g.beginPath(); for(let i=0;i<10;i++){const r=i%2?36:84,a=-Math.PI/2+i*Math.PI/5; g.lineTo(128+r*Math.cos(a),132+r*Math.sin(a));} g.closePath(); g.fill();}
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8; return t;
}


// superellipse fitted to the inner opening of the uploaded shell: a 116, b 71.6, n 2.6
const se=(a,b,n=2.6,N=200,cx=0,cz=0)=>Array.from({length:N},(_,i)=>{const t=i/N*2*Math.PI, c=Math.cos(t), s=Math.sin(t); return new V2(cx+a*Math.sign(c)*Math.abs(c)**(2/n), cz+b*Math.sign(s)*Math.abs(s)**(2/n));});
const seIn=(x,z,a,b,n=2.6)=>Math.abs(x/a)**n+Math.abs(z/b)**n<1;
function sdRR(x,z,k){const qx=Math.abs(x-k.x)-k.hw+k.r, qz=Math.abs(z-k.z)-k.hh+k.r; return Math.hypot(Math.max(qx,0),Math.max(qz,0))+Math.min(Math.max(qx,qz),0)-k.r;}
function inPoly(p,poly){let c=false; for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j]; if((a.y>p.y)!==(b.y>p.y)&&p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x) c=!c;} return c;}
function subtract(Cp,K){ // Cp minus rounded rect K (K crosses one side of Cp)
  const n=Cp.length, ins=Cp.map(p=>sdRR(p.x,p.y,K)<0);
  let e=-1,j=-1; for(let i=0;i<n;i++){ if(ins[i]&&!ins[(i+1)%n]) e=(i+1)%n; if(!ins[i]&&ins[(i+1)%n]) j=i; }
  const outside=[]; for(let i=e;;i=(i+1)%n){outside.push(Cp[i]); if(i===j) break;}
  const Kp=rr(K.hw,K.hh,K.r,K.x,K.z,16), kin=Kp.map(p=>inPoly(p,Cp)), m=Kp.length;
  let s=0; for(let i=0;i<m;i++) if(kin[i]&&!kin[(i-1+m)%m]) s=i;
  const arc=[]; for(let i=s;kin[i%m]&&arc.length<m;i++) arc.push(Kp[i%m]);
  const d=(p,q)=>Math.hypot(p.x-q.x,p.y-q.y); if(d(arc[0],Cp[j])>d(arc[arc.length-1],Cp[j])) arc.reverse();
  return [...outside,...arc];
}
function build(){
const SH=SHELLS[S.depth], YMIN=SH.ymin, YMAX=SH.ymax;
const IN=poly(SH.ct.inner), OUT=poly(SH.ct.outer), REC=poly(SH.ct.recess);   // contours sliced from the uploaded shell
const A=116, Bz=71.6, CL=0.35;
const GT=1.6, DOME=10;                             // grille shell thickness, pillow height (as Grill vA)
const FPY=YMIN+12, FT=3, FY=FPY;                   // faceplate front (grille rests on it)
const GY=FPY-GT;
const K={x:68,z:-20,hw:62,hh:56,r:24};             // grille cut-out revealing the faceplate
const SPK={x:-52,z:0};
const DISP={x:50,z:6,hw:32,hh:25};
const PRE=[0,1,2,3,4,5].map(i=>[20+i*12,-30]);
const PILL=[{k:'source',x:22,z:-44},{k:'prev',x:36,z:-44},{k:'next',x:50,z:-44}];
const KNOB={x:98,z:-8,r:14};
const MAGS=[[-96,40],[-96,-40],[-18,56],[-18,-56]];
const inner=new THREE.Group(); inner.name='pultforsterker_radio_retro';
const shell=new THREE.Group(); shell.name='kasse'; inner.add(shell);
const base=new THREE.Group(); base.name='innmat'; inner.add(base);
const xBasis=basis([0,1,0],[0,0,1],[1,0,0]);
function extX(n,sh,x0,d,mat,p,pr){const m=mesh(n,geo(sh,d),mat,p,[x0,0,0],pr); m.setRotationFromMatrix(xBasis); return m;}
const rect=(x0,z0,x1,z1)=>[new V2(x0,z0),new V2(x1,z0),new V2(x1,z1),new V2(x0,z1)];

// uploaded shell (unchanged)
mesh('skall_fra_3mf',SH.geo,M.shellPrint,shell);

// ---------- faceplate (new, printed, fits the shell opening) ----------
const fp=new THREE.Group(); fp.name='faceplate'; shell.add(fp);
extY('faceplate', shape(shrink(IN,CL),[
  circ(SPK.x,SPK.z,36,80), rr(DISP.hw-2,DISP.hh-2,1,DISP.x,DISP.z,4),
  ...PRE.map(([x,z])=>rr(5.8,3.6,2,x,z,4)), ...PILL.map(b=>rr(5.8,3.6,2,b.x,b.z,4)), circ(KNOB.x,KNOB.z,4,32),
  ...MAGS.map(([x,z])=>circ(x,z,3.1,24)),
]), FPY+FT,FT,M.face,fp,'panel');
// stiffening rim on the back, 6 mm deep, follows the shell wall
extY('faceplate_krage', shape(shrink(IN,CL),[shrink(IN,CL+2).reverse()]), FPY+FT+6,6,M.face,fp,'panel');

// ---------- grille (new): domed "pillow" like Grill vA, perforated, magnetic, with the curved cut-out ----------
const grill=new THREE.Group(); grill.name='grill'; shell.add(grill);
const gpoly=subtract(shrink(IN,CL+0.4),K), perfP=shrink(IN,4);
function edgeDist(x,z){let d=1e9; for(let i=0,n=gpoly.length;i<n;i++){const p=gpoly[i],q=gpoly[(i+1)%n], dx=q.x-p.x, dz=q.y-p.y, t=Math.max(0,Math.min(1,((x-p.x)*dx+(z-p.y)*dz)/(dx*dx+dz*dz||1))); d=Math.min(d,Math.hypot(x-p.x-t*dx,z-p.y-t*dz));} return d;}
const domeH=(x,z)=>{const t=Math.min(1,edgeDist(x,z)/28); return DOME*t*t*(3-2*t);};
const holes=[]; const P=5.4;
for(let j=-16;j<=16;j++) for(let i=-26;i<=26;i++){const x=(i+(j&1)*0.5)*P, z=j*P*0.866;
  if(!inPoly(new V2(x,z),perfP)||sdRR(x,z,K)<3.4||MAGS.some(([mx,mz])=>Math.hypot(x-mx,z-mz)<7)) continue; holes.push(circ(x,z,1.6,12));}
{ const g=new THREE.ExtrudeGeometry(shape(gpoly,holes),{depth:GT,bevelEnabled:false,curveSegments:8});
  const p=g.attributes.position; for(let i=0;i<p.count;i++) p.setZ(i,p.getZ(i)+domeH(p.getX(i),p.getY(i)));
  g.computeVertexNormals();
  const m=mesh('grill',g,M.grillPla,grill,[0,FPY,0],'grill'); m.rotation.x=Math.PI/2; }
const M_mag=new THREE.MeshStandardMaterial({name:'neodymium_nickel',color:0xbfc2c6,roughness:0.25,metalness:0.9});
for(const [x,z] of MAGS){ const h=domeH(x,z);
  mesh('grill_boss',new THREE.CylinderGeometry(4.5,4.5,h,28),M.grillPla,grill,[x,FPY-h/2,z],'grill');
  mesh('grill_magnet',new THREE.CylinderGeometry(3,3,2,24),M_mag,grill,[x,FPY-1.2,z]); mesh('face_magnet',new THREE.CylinderGeometry(3,3,2,24),M_mag,shell,[x,FPY+1,z]); }

// ---------- controls ----------
extY('skjermvindu', shape(rr(DISP.hw,DISP.hh,2.5,DISP.x,DISP.z,8)), FY+0.2,0.8,M.glass,fp,'glass',0.2);
faceFront(mesh('skjerm_bilde',new THREE.PlaneGeometry(57.6,43.2),new THREE.MeshBasicMaterial({name:'tft',map:tex,toneMapped:false}),fp,[DISP.x,FY-1.25,DISP.z]));
function pill(name,x,z,kind,txt){
  const g=new THREE.Group(); g.name=name; fp.add(g);
  extY(name+'_hette', shape(rr(5.2,3.1,1.8,x,z,6)), FY,6,M.cap,g,'keys',0.4);
  faceFront(mesh(name+'_ikon',new THREE.PlaneGeometry(5,5),new THREE.MeshBasicMaterial({name:'ikon',map:icon(kind,C.capText,txt),transparent:true,depthWrite:false,toneMapped:false}),g,[x,FY-6.82,z]));
  const ring=new THREE.MeshStandardMaterial({name:'led',color:0x2a2a2c,roughness:0.4});
  faceFront(mesh(name+'_led',new THREE.CircleGeometry(0.6,20),ring,fp,[x,FY-0.02,z+5.2]));
  return {g,ring};
}
const preBtns=PRE.map(([x,z],i)=>pill('preset_'+(i+1),x,z,null,String(i+1)));
const btns={}; for(const b of PILL) btns[b.k]=pill(b.k+'_knapp',b.x,b.z,b.k);
label('etikett_source','SOURCE',12,1.8,fp,[PILL[0].x,FY-0.02,PILL[0].z-5.6],faceFront,TH.text);
label('etikett_vol','VOLUME · PUSH MUTE',26,1.8,fp,[KNOB.x,FY-0.02,KNOB.z-KNOB.r-3],faceFront,TH.text);
const knob=new THREE.Group(); knob.name='volumknapp'; knob.position.set(KNOB.x,FY,KNOB.z); fp.add(knob);
const kr=KNOB.r, kp=[new V2(0,0.6),new V2(kr-0.5,0.6),new V2(kr,1.2),new V2(kr,14.6),new V2(kr-0.8,15.6),new V2(kr-2.4,16),new V2(0,16)];
mesh('knapp_kropp',new THREE.LatheGeometry(kp,96),M.alu,knob).rotation.x=Math.PI;
mesh('knapp_rifling',new THREE.CylinderGeometry(kr+0.05,kr+0.05,7,110,1,true),M.knurl,knob,[0,-5,0]);
mesh('knapp_markør',new THREE.CylinderGeometry(0.9,0.9,0.4,24),M.dark,knob,[0,-16.2,kr-4.5]);
// power: 12 mm metal button in the shell's top hole
const pg=new THREE.Group(); pg.name='power_knapp_topp'; pg.position.set(0,5.5,77.3); shell.add(pg);
const pring=new THREE.MeshStandardMaterial({name:'led_ring',color:0x2a2a2c,roughness:0.3});
toZ(mesh('power_flens',new THREE.CylinderGeometry(7.2,7.5,1.4,48),M.alu,pg,[0,0,0.7]));
toZ(mesh('power_hette',new THREE.CylinderGeometry(4.8,4.8,1.2,48),M.alu,pg,[0,0,1.8]));
const pr=mesh('power_ledring',new THREE.RingGeometry(4.9,5.7,48),pring,pg,[0,0,1.45]);
btns.power={g:pg,ring:pring}; setLed(pring,true);

// ---------- back plate (new), sits in the rear recess, 4 × M3 into the ring ----------
const BZ=-34, PB={pwr:44, dc:22, usb:6, aux:-8, posts:[-26,-40], sw:-58};
const BY=YMAX-0.3;
const RECP=shrink(REC,0.3), BSCR=[22,68,112,158].map(k=>{const p=shrink(REC,3.5)[k]; return [p.x,p.y];});
extY('bakplate', shape(RECP,[rr(9.6,6.4,0.4,PB.pwr,BZ,2), circ(PB.dc,BZ,5.6,40), rr(4.7,1.8,1.6,PB.usb,BZ,6), circ(PB.aux,BZ,3.1,32), circ(PB.sw,BZ,3.1,32),
  ...PB.posts.map(x=>circ(x,BZ,2.6,24)), ...BSCR.map(([x,z])=>circ(x,z,1.7,16)), ...[-30,-20,-10,0,10,20,30].flatMap(dx=>[20,34].map(dz=>rr(1.2,4.5,1.1,dx,dz,4)))]), BY,2.7,M.face,shell,'back');
const rocker=new THREE.Group(); rocker.position.set(PB.pwr,BY,BZ); shell.add(rocker);
mesh('bryter_ramme',new THREE.BoxGeometry(21,2.4,15),M.dark,rocker,[0,1.2,0]);
mesh('bryter_vippe',new THREE.BoxGeometry(17,3,11),M.dark,rocker,[0,2.4,0]).rotation.x=-0.2;
const ringY=(n,r,h,mat,x,y=BY)=>mesh(n,new THREE.CylinderGeometry(r,r,h,40),mat,shell,[x,y+h/2,BZ]);
ringY('dc_mutter',7,1.6,M.alu,PB.dc); ringY('dc_kjerne',3.2,1.8,M.dark,PB.dc);
mesh('usb_c',new THREE.BoxGeometry(8.6,0.4,2.8),M.alu,shell,[PB.usb,BY+0.1,BZ]);
ringY('aux_mutter',4.6,1.4,M.alu,PB.aux); ringY('aux_hull',1.8,1.6,M.dark,PB.aux);
PB.posts.forEach((x,i)=>{const mat=i%2?M.dark:M.red; ringY('pol_base',5,3,mat,x); ringY('pol_hode',4.6,7,mat,x,BY+3);});
ringY('vippe_mutter',4.6,1.6,M.alu,PB.sw);
const tog=mesh('vippe_spak',new THREE.CylinderGeometry(1.4,1.8,11,20),M.alu,shell,[PB.sw,BY+6,BZ]);
const bl=(n,t,x,w=16)=>label(n,t,w,2.6,shell,[x,BY+0.01,BZ+12],faceBack,TH.text);
bl('e_pwr','POWER',PB.pwr); bl('e_dc','DC 19V',PB.dc); bl('e_usb','USB',PB.usb,10); bl('e_aux','AUX',PB.aux,10); bl('e_out','OUT + −',(PB.posts[0]+PB.posts[1])/2,16); bl('e_spk','INT·EXT',PB.sw,14);

// ---------- divider (sealed speaker chamber left, electronics right) ----------
const WX=6, wy0=FPY+FT, wy1=BY-2.7-0.2, wzT=zAt(IN,WX,1)-0.6, wzB=zAt(IN,WX,-1)-0.6;
extX('skillevegg', shape(rect(wy0,-wzB,wy1,wzT),[circ(wy0+20,-wzB+14,4,24)]), WX-1.2,2.4,M.face,shell,'wall');
const boards=[{n:'pcb_1_esp32_dac',y:wy0+48,z:22,w:70,h:50,mat:M.pcb},{n:'pcb_2_forsterker',y:wy0+40,z:-36,w:50,h:30,mat:M.pcbG}];
for(const b of boards){ mesh(b.n,new THREE.BoxGeometry(1.6,b.w,b.h),b.mat,base,[WX+7,b.y,b.z]);
  for(const [dy,dz] of [[1,1],[1,-1],[-1,1],[-1,-1]]) toZ(mesh('avstand',new THREE.CylinderGeometry(2.5,2.5,6,16),M.face,base,[WX+3.6,b.y+dy*(b.w/2-4),b.z+dz*(b.h/2-4)])).rotation.set(0,0,Math.PI/2);}
mesh('forsterker_kjøleribbe',new THREE.BoxGeometry(10,22,14),M.alu,base,[WX+13,wy0+40,-36]);
const spk=new THREE.Group(); spk.name='høyttaler_78mm'; spk.position.set(SPK.x,FPY+FT,SPK.z); base.add(spk);
const prof=[new V2(0,6),new V2(31,1.6),new V2(39,0.6),new V2(39,2.4),new V2(21,20),new V2(18,36),new V2(0,36)];
mesh('høyttaler_kurv',new THREE.LatheGeometry(prof,64),M.dark,spk);
mesh('høyttaler_membran',new THREE.CylinderGeometry(33,12,6,64,1,true),M.cone,spk,[0,3.5,0]);
mesh('høyttaler_magnet',new THREE.CylinderGeometry(17,17,12,40),M.alu,spk,[0,30,0]);

// ---------- legs: tapered, splayed, glued into 8 mm pockets ----------
for(const [x,y] of [[-82,-28],[82,-28],[-82,28],[82,28]]){
  const zb=-zAt(OUT,x,-1);
  const leg=mesh('bein',new THREE.CylinderGeometry(4,2.6,24,28),M.alu,shell,[x+Math.sign(x)*2,y+Math.sign(y)*1.5,zb-10],'legs');
  leg.rotation.set(Math.PI/2,0,0); leg.rotateZ(0); leg.rotation.x=Math.PI/2+Math.sign(y)*0.12; leg.rotation.y=-Math.sign(x)*0.16;
}

const root=new THREE.Group(); root.name='PultforsterkerRadioRetro';
root.add(inner); inner.rotation.x=-Math.PI/2; inner.scale.setScalar(0.001);
root.updateMatrixWorld(true);
inner.position.sub(new THREE.Box3().setFromObject(inner).getCenter(new V3()));
return {root,inner,shell,grill,fp,knob,preBtns,btns,tog};
}
function label(name,text,w,h,parent,pos,rot,col=C.text,wt=500){
  const c=document.createElement('canvas'); c.width=512; c.height=Math.round(512*h/w);
  const g=c.getContext('2d'); g.fillStyle=col; g.font=`${wt} ${Math.round(c.height*0.62)}px "Helvetica Neue",Helvetica,Arial,sans-serif`;
  g.textAlign='center'; g.textBaseline='middle'; if('letterSpacing' in g) g.letterSpacing=`${Math.round(c.height*0.14)}px`; g.fillText(text,c.width/2,c.height/2);
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8;
  const m=mesh(name,new THREE.PlaneGeometry(w,h),new THREE.MeshStandardMaterial({name:'trykk',map:t,transparent:true,depthWrite:false,roughness:0.8}),parent,pos);
  m.castShadow=false; rot(m); return m;
}

// ---------- UI ----------
const INPUTS=[
  {key:'RAD',name:'Radio',radio:true},
  {key:'AIR',name:'AirPlay',title:'Midnight City',sub:'M83 · iPhone',len:243},
  {key:'BT',name:'Bluetooth',title:'Teardrop',sub:'Massive Attack',len:330},
  {key:'AUX',name:'AUX',title:'Analog inngang',sub:'3,5 mm jack'},
  {key:'USB',name:'USB',title:'USB-lyd',sub:'PC · 48 kHz'},
];
const STATIONS=[
  {name:'NRK P1',track:'Kjærlighetsvisa',artist:'Kari Bremnes',kbps:192},
  {name:'NRK P3',track:'Blinding Lights',artist:'The Weeknd',kbps:192},
  {name:'NRK Jazz',track:'So What',artist:'Miles Davis',kbps:128},
  {name:'Radio Norge',track:'Sommerfuglen i vinterland',artist:'Halvdan Sivertsen',kbps:128},
  {name:'NRK Klassisk',track:'Morgenstemning',artist:'Edvard Grieg',kbps:192},
  {name:'BBC Radio 6 Music',track:'Teardrop',artist:'Massive Attack',kbps:128},
];
const S={theme:'sennep', depth:'deep', fpOff:false, input:0, st:1, vol:35, open:false, ext:false, bare:false, tune:0, dark:true};
const THEMES={sennep:{label:'Sennep',shell:0xd9a21b,grill:0xdccba0,face:0x5b4636,cap:0xefe6d0,capText:'#4a3a2c',text:'#e9dcc0'},
  mint:{label:'Mint',shell:0x9fcfbf,grill:0xf1ead8,face:0x3e3a36,cap:0xf4efe2,capText:'#3e3a36',text:'#e8e2d2'},
  kirsebær:{label:'Kirsebær',shell:0xa3262a,grill:0xe7dcc4,face:0x2b2523,cap:0xefe7d6,capText:'#2b2523',text:'#e0d6c4'},
  sort:{label:'Sort',shell:0x222224,grill:0x9a9893,face:0x121213,cap:0xd9d7d1,capText:'#1d1d1e',text:'#b9b7b1'}};
const T0=performance.now()-102000;
const mmss=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
const ART={};
function art(key,seed,title){
  if(ART[key]) return ART[key];
  const c=document.createElement('canvas'); c.width=c.height=400; const g=c.getContext('2d');
  let r=seed*9301+49297; const rnd=()=>((r=(r*9301+49297)%233280)/233280);
  const h=Math.floor(rnd()*360);
  const bg=g.createLinearGradient(0,0,400,400); bg.addColorStop(0,`hsl(${h},55%,${30+rnd()*25}%)`); bg.addColorStop(1,`hsl(${(h+60+rnd()*80)%360},60%,${12+rnd()*20}%)`);
  g.fillStyle=bg; g.fillRect(0,0,400,400);
  for(let i=0;i<5;i++){g.globalAlpha=.35+rnd()*.4; g.fillStyle=`hsl(${(h+rnd()*180)%360},70%,${40+rnd()*40}%)`;
    if(rnd()<.5){g.beginPath(); g.arc(rnd()*400,rnd()*400,40+rnd()*140,0,Math.PI*2); g.fill();} else g.fillRect(rnd()*400,rnd()*400,60+rnd()*200,10+rnd()*60);}
  g.globalAlpha=1; g.fillStyle='rgba(255,255,255,.92)'; g.font='bold 34px "Helvetica Neue",Arial,sans-serif'; g.fillText(title.toUpperCase().slice(0,16),24,366);
  return ART[key]=c;
}
function draw(){
  const g=cvs.getContext('2d'); g.setTransform(2,0,0,2,0,0); g.fillStyle='#0b0c0e'; g.fillRect(0,0,320,240);
  const now=(performance.now()-T0)/1000, Wc='#f4f6f8', Dm='#8b939b', O='#2a2f35', AC='#ffb547', F='"Helvetica Neue",Arial,sans-serif';
  g.textBaseline='middle';
  const it=INPUTS[S.input], tuning=it.radio&&performance.now()-S.tune<900;
  g.fillStyle=it.radio?AC:Dm; g.font=`bold 11px ${F}`; if('letterSpacing' in g) g.letterSpacing='1.2px';
  g.fillText(it.radio?`RADIO · ${S.st+1}/6`:it.name.toUpperCase(),12,14); if('letterSpacing' in g) g.letterSpacing='0px';
  g.fillStyle=Dm; g.textAlign='right'; g.fillText(new Date().toTimeString().slice(0,5),308,14); g.textAlign='left';
  let cover,l1,l2,l3;
  if(it.radio){const st=STATIONS[S.st]; cover=art('st'+S.st,S.st+3,st.track); l1=st.name; l2=tuning?'Kobler til'+'.'.repeat(1+Math.floor(now*3)%3):st.track; l3=tuning?'':st.artist;}
  else {cover=it.len?art('in'+S.input,S.input+11,it.title):null; l1=it.title; l2=it.sub; l3='';}
  const ax=12, ay=28, as=128;
  g.save(); g.beginPath(); g.roundRect(ax,ay,as,as,8); g.clip();
  if(cover&&!tuning) g.drawImage(cover,ax,ay,as,as); else {g.fillStyle='#16181c'; g.fillRect(ax,ay,as,as);
    for(let i=0;i<12;i++){const v=0.3+0.7*Math.abs(Math.sin(now*3.1+i*0.7)*Math.sin(now*1.7+i*0.31)); const hh=6+v*60; g.fillStyle=Dm; g.fillRect(ax+12+i*9.5,ay+as/2+36-hh,5,hh);}}
  g.restore();
  const tx=152, tw=156;
  const clip=(txt,y,font,col)=>{g.save(); g.beginPath(); g.rect(tx,y-12,tw,24); g.clip(); g.fillStyle=col; g.font=font;
    const w=g.measureText(txt).width, off=w>tw?((now*20)%(w+40)):0; g.fillText(txt,tx-off,y); if(w>tw) g.fillText(txt,tx-off+w+40,y); g.restore();};
  clip(l1,44,`bold 20px ${F}`,Wc); clip(l2,74,`15px ${F}`,Wc); if(l3) clip(l3,94,`13px ${F}`,Dm);
  if(it.radio){g.fillStyle=Dm; g.font=`11px ${F}`; g.fillText(`${STATIONS[S.st].kbps} kbps · Lyrion`,tx,148);}
  else if(it.len){const t=now%it.len; g.fillStyle=O; g.fillRect(tx,140,tw,3); g.fillStyle=Wc; g.fillRect(tx,140,tw*t/it.len,3);
    g.fillStyle=Dm; g.font=`11px ${F}`; g.fillText(mmss(t),tx,154); g.textAlign='right'; g.fillText(mmss(it.len),tx+tw,154); g.textAlign='left';}
  // source strip
  g.font=`bold 11px ${F}`; let x=12;
  INPUTS.forEach((q,i)=>{const w=g.measureText(q.key).width+14;
    if(i===S.input){g.fillStyle=Wc; g.beginPath(); g.roundRect(x,172,w,20,10); g.fill(); g.fillStyle='#0b0c0e';}
    else {g.strokeStyle=O; g.lineWidth=1.2; g.beginPath(); g.roundRect(x+.6,172.6,w-1.2,18.8,9.4); g.stroke(); g.fillStyle=Dm;}
    g.fillText(q.key,x+7,182.5); x+=w+6;});
  g.fillStyle=Dm; g.font=`bold 11px ${F}`; g.fillText(S.ext?'EXT':'VOL',12,220);
  const segs=30, sw=(250-44)/segs, on=Math.round(S.vol/100*segs);
  for(let i=0;i<segs;i++){g.fillStyle=i<on?Wc:O; const hh=4+i*0.3; g.fillRect(44+i*sw,226-hh,sw-2,hh);}
  g.fillStyle=Wc; g.font=`bold 20px ${F}`; g.textAlign='right'; g.fillText(String(S.vol),308,218); g.textAlign='left';
  tex.needsUpdate=true;
}
setInterval(draw,100);
const $=id=>document.getElementById(id);
let B;
function rebuild(){applyTheme(S.theme); B=build(); stage.setObject(B.root); document.querySelectorAll('#themes button').forEach(b=>b.classList.toggle('on',b.dataset.v===S.theme)); document.querySelectorAll('#depths button').forEach(b=>b.classList.toggle('on',b.dataset.v===S.depth)); sync();}
function sync(){
  draw();
  const {knob,preBtns,tog,shell,grill}=B;
  knob.rotation.y=((S.vol/100)*270-135)*Math.PI/180;
  preBtns.forEach((b,i)=>setLed(b.ring,S.input===0&&i===S.st));
  tog.rotation.x=S.ext?0.35:-0.35;
  grill.position.y=S.bare?-40:0; B.fp.position.y=S.fpOff?-45:0; $('fp').classList.toggle('on',S.fpOff);
  document.querySelectorAll('#inputs button').forEach((b,i)=>b.classList.toggle('on',i===S.input));
  document.querySelectorAll('#presets button').forEach((b,i)=>b.classList.toggle('on',S.input===0&&i===S.st));
  $('volv').textContent=S.vol; $('spkInt').classList.toggle('on',!S.ext); $('spkExt').classList.toggle('on',S.ext);
  $('grill').classList.toggle('on',S.bare);
}
const flash=b=>{press(b.g); setLed(b.ring,true); setTimeout(()=>setLed(b.ring,false),500);};
const tune=()=>{S.tune=performance.now();};
const station=i=>{S.input=0; S.st=(i+6)%6; tune(); sync();};
INPUTS.forEach((it,i)=>{const b=document.createElement('button'); b.textContent=it.name; b.onclick=()=>{flash(B.btns.source); S.input=i; if(it.radio) tune(); sync();}; $('inputs').appendChild(b);});
STATIONS.forEach((s,i)=>{const b=document.createElement('button'); b.textContent=i+1; b.title=s.name; b.onclick=()=>{press(B.preBtns[i].g); station(i);}; $('presets').appendChild(b);});
$('prev').onclick=()=>{B.btns.prev&&flash(B.btns.prev); station(S.st-1);}; $('next').onclick=()=>{B.btns.next&&flash(B.btns.next); station(S.st+1);};
$('vol').oninput=e=>{S.vol=+e.target.value; sync();};
$('spkInt').onclick=()=>{S.ext=false; sync();}; $('spkExt').onclick=()=>{S.ext=true; sync();};
$('grill').onclick=()=>{S.bare=!S.bare; sync();};
$('fp').onclick=()=>{S.fpOff=!S.fpOff; sync();};
if(document.fonts) document.fonts.ready.then(draw);
for(const k in THEMES){const b=document.createElement('button'); b.textContent=THEMES[k].label; b.dataset.v=k; b.onclick=()=>{S.theme=k; rebuild();}; $('themes').appendChild(b);}
for(const [k,n] of [['deep','Dyp (104)'],['shell','Grunn (85)']]){const b=document.createElement('button'); b.textContent=n; b.dataset.v=k; b.onclick=()=>{S.depth=k; rebuild();}; $('depths').appendChild(b);}
rebuild();

function stl(tag,file){
  const {root,inner}=B; root.updateMatrixWorld(true);
  const inv=new THREE.Matrix4().copy(inner.matrixWorld).invert(), tris=[];
  inner.traverse(m=>{ if(!m.isMesh||m.userData.print!==tag) return;
    const g=m.geometry.index?m.geometry.toNonIndexed():m.geometry, mat=new THREE.Matrix4().multiplyMatrices(inv,m.matrixWorld), p=g.attributes.position;
    for(let i=0;i<p.count;i+=3) tris.push([0,1,2].map(k=>new V3().fromBufferAttribute(p,i+k).applyMatrix4(mat)));
  });
  const buf=new ArrayBuffer(84+tris.length*50), dv=new DataView(buf); dv.setUint32(80,tris.length,true);
  tris.forEach(([a,b,c],i)=>{const o=84+i*50, n=new V3().subVectors(b,a).cross(new V3().subVectors(c,a)).normalize();
    [n,a,b,c].forEach((v,j)=>{dv.setFloat32(o+j*12,v.x,true);dv.setFloat32(o+j*12+4,v.y,true);dv.setFloat32(o+j*12+8,v.z,true);});});
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([buf],{type:'model/stl'})); a.download=file; a.click();
}
const parts=[['Faceplate','panel'],['Grill','grill'],['Bakplate','back'],['Skillevegg','wall'],['Tastehetter','keys'],['Skjermvindu','glass'],['Bein ×4','legs']];
for(const [n,t] of parts){const b=document.createElement('button'); b.textContent=n; b.onclick=()=>{const o=S.bare,f=S.fpOff; S.bare=false; S.fpOff=false; sync(); stl(t,'radio_retro_'+S.depth+'_'+t+'.stl'); S.bare=o; S.fpOff=f; sync();}; $('stl').appendChild(b);}
window.__S=S; window.__sync=sync;
