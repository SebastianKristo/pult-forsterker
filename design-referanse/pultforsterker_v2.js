const stage = document.querySelector('three-d-stage');
const { THREE } = await stage.ready;
const V2 = THREE.Vector2, V3 = THREE.Vector3;

const M = {
  shell: new THREE.MeshStandardMaterial({ name:'anthracite', color:0x2c2d30, roughness:0.55, metalness:0.12 }),
  face:  new THREE.MeshStandardMaterial({ name:'anthracite_face', color:0x37383c, roughness:0.42, metalness:0.18 }),
  knob:  new THREE.MeshStandardMaterial({ name:'black_anodized', color:0x18181a, roughness:0.35, metalness:0.3 }),
  knurl: new THREE.MeshStandardMaterial({ name:'black_knurl', color:0x202023, roughness:0.45, metalness:0.3, flatShading:true }),
  alu:   new THREE.MeshStandardMaterial({ name:'aluminium', color:0xc9c8c3, roughness:0.32, metalness:0.35 }),
  dark:  new THREE.MeshStandardMaterial({ name:'black_hardware', color:0x141415, roughness:0.45, metalness:0.2 }),
  glass: new THREE.MeshStandardMaterial({ name:'smoked_acrylic', color:0x060708, roughness:0.05, metalness:0.15 }),
  red:   new THREE.MeshStandardMaterial({ name:'post_red', color:0xa3261d, roughness:0.35, metalness:0.1 }),
  pcb:   new THREE.MeshStandardMaterial({ name:'pcb', color:0x1f4a7a, roughness:0.6 }),
  rubber:new THREE.MeshStandardMaterial({ name:'rubber', color:0x161616, roughness:0.95 }),
  white: new THREE.MeshStandardMaterial({ name:'indicator', color:0xe8e8e4, roughness:0.5 }),
};

function rr(hw, hh, r, cx=0, cy=0, seg=10){
  const pts=[], C=[[-hw+r,hh-r,90],[-hw+r,-hh+r,180],[hw-r,-hh+r,270],[hw-r,hh-r,0]];
  for(const [x,y,a0] of C) for(let i=0;i<=seg;i++){const a=(a0+90*i/seg)*Math.PI/180; pts.push(new V2(cx+x+r*Math.cos(a), cy+y+r*Math.sin(a)));}
  return pts;
}
const circ=(cx,cy,r,n=48)=>Array.from({length:n},(_,i)=>new V2(cx+r*Math.cos(i/n*2*Math.PI), cy+r*Math.sin(i/n*2*Math.PI)));
function shape(outer, holes=[]){const s=new THREE.Shape(outer); for(const h of holes) s.holes.push(new THREE.Path(h)); return s;}
function geo(s, depth, b=0){return new THREE.ExtrudeGeometry(s,{depth,bevelEnabled:b>0,bevelThickness:b,bevelSize:b,bevelSegments:3,curveSegments:24});}
function mesh(name, g, mat, parent, pos=[0,0,0], print){const m=new THREE.Mesh(g,mat); m.name=name; m.position.set(...pos); m.castShadow=m.receiveShadow=true; if(print) m.userData.print=print; parent.add(m); return m;}
// flat extrusion upward (STL z)
const extZ=(name,s,z0,depth,mat,parent,print,b=0)=>mesh(name,geo(s,depth,b),mat,parent,[0,0,z0+b],print);
// panel extrusion: shape in (x,z), extruded toward −y from y0
function extY(name,s,y0,depth,mat,parent,print,b=0){const m=mesh(name,geo(s,depth,b),mat,parent,[0,y0-b,0],print); m.rotation.x=Math.PI/2; return m;}
const basis=(x,y,z)=>new THREE.Matrix4().makeBasis(new V3(...x),new V3(...y),new V3(...z));
const faceFront=m=>(m.setRotationFromMatrix(basis([1,0,0],[0,0,1],[0,-1,0])),m);
const faceBack=m=>(m.setRotationFromMatrix(basis([-1,0,0],[0,0,1],[0,1,0])),m);
const toZ=m=>(m.rotation.x=Math.PI/2,m);

// ---------- dimensions (mm; x right, y back, z up; lid top = z 3) ----------
const H=48, zb=-H, FZ=-24;               // body height, front feature centre line
const SCREWS=[[90,50],[-90,50],[90,-50],[-90,-50]];
const DISP={x:-30}, KNOB={x:70}, PWR={x:-80,z:0};
const BTNS=[[20,8.5],[37,8.5],[20,-8.5],[37,-8.5]]; // 2×2: AirPlay, BT / AUX, USB  (x, z-offset)

const inner=new THREE.Group(); inner.name='pultforsterker';
const lid=new THREE.Group(); lid.name='lokk'; inner.add(lid);
const body=new THREE.Group(); body.name='kasse'; inner.add(body);

// ---------- LID: original outline, lip, screw holes, cable notch; ears only in desk-mount variant ----------
const screwHoles=()=>SCREWS.map(([x,y])=>circ(x,y,1.7,32));
extZ('lokk_underside', shape([new V2(-15,60),...rr(100,60,6),new V2(15,60),new V2(15,47),new V2(-15,47)], screwHoles()), 0,0.7,M.shell,lid,'lid');
extZ('lokk_kjerne', shape(rr(100,60,6), screwHoles()), 0.7,1.5,M.shell,lid,'lid');
const bv=0.6;
extZ('lokk_topp', shape(rr(100-bv,60-bv,6-bv), SCREWS.map(([x,y])=>circ(x,y,3.2+bv,40))), 1.6,0.2,M.shell,lid,'lid',bv);
const lipO=[new V2(-15,57.3),...rr(97.3,57.3,3.3),new V2(15,57.3)];
const lipI=[new V2(-15,54.9),...rr(94.9,54.9,0.9,0,0,4),new V2(15,54.9)].reverse();
extZ('lokk_kant', shape([...lipO,...lipI]), -1.6,1.6,M.shell,lid,'lid');
const ears=new THREE.Group(); ears.name='pultfeste_ører'; lid.add(ears);
for(const sx of [1,-1]) for(const sy of [1,-1])
  extZ('lokk_øre', shape(rr(9.5,11,3,sx*108.5,sy*40,8),[rr(5,2.3,2.29,sx*110,sy*40,8)]), 0,3,M.shell,ears,'lid');
for(const [x,y] of SCREWS){
  toZ(mesh('skrue',new THREE.CylinderGeometry(3,3,0.8,32),M.dark,lid,[x,y,2.5]));
  mesh('skrue_spor',new THREE.BoxGeometry(3.6,0.6,0.2),M.shell,lid,[x,y,2.92]);
}

// ---------- BODY ----------
// side walls + rounded corners (front and back straight runs are separate panels)
const uO=rr(100,60,6), uI=rr(97.3,57.3,3.3);
const half=(pts,sgn)=>pts.filter(p=>sgn*p.x>=93.99);
const sideShape=sgn=>{const o=half(uO,sgn), i=half(uI,sgn); return shape([...o,...i.reverse()]);};
extZ('kasse_side_h', sideShape(1), zb,H,M.shell,body,'body');
extZ('kasse_side_v', sideShape(-1), zb,H,M.shell,body,'body');
extZ('kasse_bunn', shape(rr(100,60,6)), zb,2.5,M.shell,body,'body');
// front wall (y −57.3 … −60)
extY('kasse_front', shape([new V2(-94,zb),new V2(94,zb),new V2(94,0),new V2(-94,0)],[
  rr(28.5,15,1,DISP.x,FZ,4), ...BTNS.map(([x,dz])=>circ(x,FZ+dz,6.1,40)), circ(PWR.x,FZ,8.1,48), circ(KNOB.x,FZ,3.75,40),
]), -57.3,2.7,M.shell,body,'body');
// raised faceplate (y −60 … −62.6) with display bezel
extY('kasse_frontplate', shape(rr(94-bv,23-bv,3-bv,0,FZ,8),[
  rr(35+bv,19+bv,2+bv,DISP.x,FZ,8), ...BTNS.map(([x,dz])=>circ(x,FZ+dz,6.1+bv,40)), circ(PWR.x,FZ,8.1+bv,48), circ(KNOB.x,FZ,3.75+bv,40),
]), -59.4,2,M.face,body,'body',bv);
// back wall
const P={pwr:76, dc:54, usb:36, aux:20, ant:-4, posts:[-30,-45,-65,-80]};
extY('kasse_bakpanel', shape([new V2(-94,zb),new V2(94,zb),new V2(94,0),new V2(-94,0)],[
  rr(9.6,6.4,0.4,P.pwr,FZ,2), circ(P.dc,FZ,5.6,40), rr(4.7,1.8,1.6,P.usb,FZ,6), circ(P.aux,FZ,3.1,32), circ(P.ant,FZ,3.3,32),
  ...P.posts.map(x=>circ(x,FZ,2.6,24)),
]), 60,2.7,M.shell,body,'body');
// bosses + ribs
const bh=H-2.5-1.6;
for(const [x,y] of SCREWS){
  extZ('kasse_skruetårn', shape(circ(x,y,4,40),[circ(x,y,1.3,24)]), zb+2.5,bh,M.shell,body,'body');
  const sx=Math.sign(x), sy=Math.sign(y);
  extZ('kasse_ribbe', shape(rr(3.6,1,0.01,x+sx*5.6,y,1)), zb+2.5,bh-4,M.shell,body,'body');
  extZ('kasse_ribbe', shape(rr(1,3.6,0.01,x,y+sy*5.6,1)), zb+2.5,bh-4,M.shell,body,'body');
}
const feet=new THREE.Group(); feet.name='føtter'; body.add(feet);
for(const [x,y] of [[85,45],[-85,45],[85,-45],[-85,-45]]) toZ(mesh('gummifot',new THREE.CylinderGeometry(7,7,3,40),M.rubber,feet,[x,y,zb-1.5]));

// ---------- front controls ----------
mesh('oled_vindu', geo(shape(rr(34.9,18.9,1.9,DISP.x,FZ,8)),2.4), M.glass, body, [0,-60,0], 'glass').rotation.x=Math.PI/2;
const cvs=document.createElement('canvas'); cvs.width=512; cvs.height=256;
const tex=new THREE.CanvasTexture(cvs); tex.colorSpace=THREE.SRGBColorSpace; tex.anisotropy=8;
faceFront(mesh('oled_bilde',new THREE.PlaneGeometry(55,27.5),new THREE.MeshBasicMaterial({name:'oled',map:tex,toneMapped:false}),body,[DISP.x,-62.42,FZ]));

const knob=new THREE.Group(); knob.name='volumknapp'; knob.position.set(KNOB.x,-62.6,FZ); body.add(knob);
const kProf=[new V2(0,0.8),new V2(16.4,0.8),new V2(17,1.4),new V2(17,16.2),new V2(16.5,17.3),new V2(15.4,17.8),new V2(0,17.6)];
mesh('knapp_kropp',new THREE.LatheGeometry(kProf,96),M.knob,knob).rotation.x=Math.PI;
mesh('knapp_rifling',new THREE.CylinderGeometry(17.05,17.05,9,90,1,true),M.knurl,knob,[0,-7,0]);
mesh('knapp_markør',new THREE.BoxGeometry(1.2,0.4,5.5),M.white,knob,[0,-17.75,10]);
// metal push buttons (black oxidized, LED ring) — real parts, see README
const M_btn=new THREE.MeshStandardMaterial({name:'black_oxidized_steel',color:0x1d1d20,roughness:0.28,metalness:0.45});
const M_cap=new THREE.MeshStandardMaterial({name:'black_oxidized_cap',color:0x252528,roughness:0.35,metalness:0.4});
function metalButton(name,x,z,rh,rc){
  const g=new THREE.Group(); g.name=name; g.position.set(x,-62.6,z); body.add(g);
  mesh(name+'_flens',new THREE.CylinderGeometry(rh-0.3,rh,1.6,64),M_btn,g,[0,-0.8,0]);
  const led=new THREE.MeshStandardMaterial({name:'led_ring',color:0x18181a,roughness:0.3});
  mesh(name+'_ledring',new THREE.CylinderGeometry(rc+0.55,rc+0.55,0.35,64),led,g,[0,-1.65,0]);
  mesh(name+'_hette',new THREE.CylinderGeometry(rc-0.2,rc,1.2,64),M_cap,g,[0,-2.1,0]);
  mesh(name+'_hus',new THREE.CylinderGeometry(rc+1,rc+1,18,32),M_btn,body,[x,-48.3,z]);
  return {g,led};
}
const inBtns=BTNS.map(([x,dz],i)=>metalButton('input_knapp_'+i,x,FZ+dz,7,5));
const pwrBtn=metalButton('power_knapp',PWR.x,FZ,9.5,6.6);
const symC=document.createElement('canvas'); symC.width=symC.height=256;
{const g=symC.getContext('2d'); g.strokeStyle='#fff'; g.lineWidth=22; g.lineCap='round';
 g.beginPath(); g.arc(128,138,70,-Math.PI/2+0.75,-Math.PI/2-0.75+2*Math.PI); g.stroke(); g.beginPath(); g.moveTo(128,40); g.lineTo(128,128); g.stroke();}
const symTex=new THREE.CanvasTexture(symC); symTex.colorSpace=THREE.SRGBColorSpace;
const symMat=new THREE.MeshBasicMaterial({name:'power_symbol',map:symTex,transparent:true,depthWrite:false,toneMapped:false});
faceFront(mesh('power_symbol',new THREE.PlaneGeometry(7,7),symMat,pwrBtn.g,[0,-2.72,0]));
const setLed=(m,on,k=1)=>{m.emissive.set(on?0xffffff:0); m.emissiveIntensity=on?1.8*k:0; m.color.set(on?(k<0.5?0x4a4a4a:0xffffff):0x18181a);};

function label(name,text,w,h,parent,pos,rot){
  const c=document.createElement('canvas'); c.width=512; c.height=Math.round(512*h/w);
  const g=c.getContext('2d'); g.fillStyle='#a3a29d'; g.font=`500 ${Math.round(c.height*0.62)}px "Helvetica Neue",Helvetica,Arial,sans-serif`;
  g.textAlign='center'; g.textBaseline='middle'; if('letterSpacing' in g) g.letterSpacing=`${Math.round(c.height*0.14)}px`; g.fillText(text,c.width/2,c.height/2);
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8;
  const m=mesh(name,new THREE.PlaneGeometry(w,h),new THREE.MeshStandardMaterial({name:'trykk',map:t,transparent:true,depthWrite:false,roughness:0.8}),parent,pos);
  m.castShadow=false; rot(m); return m;
}
['AIRPLAY','BT','AUX','USB'].forEach((t,i)=>label('etikett_'+t,t,12,2.1,body,[BTNS[i][0],-62.62,FZ+BTNS[i][1]-8.4],faceFront));
label('etikett_power','POWER',14,2.1,body,[PWR.x,-62.62,FZ-12.6],faceFront);
label('etikett_vol','VOL · PUSH MUTE',30,2.6,body,[KNOB.x,-62.62,FZ-20.6],faceFront);

// internals behind the front
mesh('oled_modul_glass',new THREE.BoxGeometry(60.5,1.4,37),M.dark,body,[DISP.x,-56.6,FZ]);
mesh('oled_modul_pcb',new THREE.BoxGeometry(70,1.6,40),M.pcb,body,[DISP.x,-55.1,FZ]);
mesh('kontroll_pcb',new THREE.BoxGeometry(26,1.6,26),M.pcb,body,[KNOB.x,-48.5,FZ]);
mesh('enkoder_ec11',new THREE.BoxGeometry(12,6.5,13),M.dark,body,[KNOB.x,-52.6,FZ]);



// ---------- back hardware ----------
const rocker=new THREE.Group(); rocker.name='strømbryter'; rocker.position.set(P.pwr,60,FZ); body.add(rocker);
mesh('bryter_ramme',new THREE.BoxGeometry(21,2.4,15),M.dark,rocker,[0,1.2,0]);
const vipp=mesh('bryter_vippe',new THREE.BoxGeometry(17,3,11),M.dark,rocker,[0,2.4,0]);
mesh('bryter_I',new THREE.BoxGeometry(0.8,0.2,3.2),M.alu,vipp,[0,1.55,3]);
const ringY=(name,r,h,mat,x,y=60,r2=r)=>mesh(name,new THREE.CylinderGeometry(r2,r,h,40),mat,body,[x,y+h/2,FZ]);
ringY('dc_mutter',7,1.6,M.alu,P.dc); ringY('dc_kjerne',3.2,1.8,M.dark,P.dc);
mesh('usb_c',new THREE.BoxGeometry(8.6,0.4,2.8),M.alu,body,[P.usb,60.1,FZ]);
ringY('aux_mutter',4.6,1.4,M.alu,P.aux); ringY('aux_hull',1.8,1.6,M.dark,P.aux);
P.posts.forEach((x,i)=>{const mat=i%2?M.dark:M.red; ringY('pol_base',5,3,mat,x); ringY('pol_hode',4.6,7,mat,x,63);});
// BT antenna (SMA): upright when free-standing, straight back when desk-mounted
ringY('sma_mutter',4.2,2,M.alu,P.ant); ringY('sma_hylse',3.2,7,M.alu,P.ant,62);
mesh('antenne_ledd',new THREE.SphereGeometry(4.6,32,16),M.dark,body,[P.ant,73,FZ]);
const antUp=toZ(mesh('antenne',new THREE.CylinderGeometry(3.4,5,100,40),M.dark,body,[P.ant,73,FZ+52]));
const antBack=mesh('antenne',new THREE.CylinderGeometry(3.4,5,100,40),M.dark,body,[P.ant,73+52,FZ]);
const bl=(n,t,x,w=16)=>label(n,t,w,2.6,body,[x,60.01,FZ+12],faceBack);
bl('etikett_power','POWER',P.pwr); bl('etikett_dc','DC 19V',P.dc); bl('etikett_usb','USB',P.usb,10); bl('etikett_aux','AUX',P.aux,10);
bl('etikett_bt','BT',P.ant,8); bl('etikett_r','R  +  −',(P.posts[0]+P.posts[1])/2,18); bl('etikett_l','L  +  −',(P.posts[2]+P.posts[3])/2,18);

// ---------- assemble ----------
const root=new THREE.Group(); root.name='Pultforsterker';
root.add(inner); inner.rotation.x=-Math.PI/2; inner.scale.setScalar(0.001);
root.updateMatrixWorld(true);
antUp.visible=false; antBack.visible=false; ears.visible=false; feet.visible=true;
const c=new THREE.Box3().setFromObject(inner).getCenter(new V3()); inner.position.sub(c);
stage.setObject(root);

// ---------- OLED UI ----------
const INPUTS=[
  {key:'AIR', name:'AirPlay', title:'Midnight City', sub:'M83 · iPhone', len:243},
  {key:'BT', name:'Bluetooth', title:'Teardrop', sub:'Massive Attack', len:330},
  {key:'AUX', name:'AUX', title:'Analog inngang', sub:'3,5 mm jack'},
  {key:'USB', name:'USB', title:'USB-lyd', sub:'PC · 48 kHz'},
];
const S={input:0, vol:42, power:true, open:false, mount:false, playing:true, muted:false, standby:false, bt:'connected', btDev:'iPhone', hold:0, ov:null, pHold:0, boot:0};
// ov = {type:'pairing'|'connected'|'bt_off'|'bt_needed', t0}
const T0=performance.now()-102000;
const mmss=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
function draw(){
  const g=cvs.getContext('2d'); g.setTransform(1,0,0,1,0,0); g.fillStyle='#000'; g.fillRect(0,0,512,256);
  if(S.power&&(!S.standby||S.pHold>0)){
    const now=(performance.now()-T0)/1000;
    g.scale(4,4); const W='#eef6ff', D='#7d8a94', O='#2a3036', F='"Helvetica Neue",Arial,sans-serif';
    g.textBaseline='middle';
    const ovT=S.ov?(performance.now()-S.ov.t0)/1000:0;
    const btIcon=(cx,cy,s,col)=>{g.strokeStyle=col; g.lineWidth=1.3; g.lineJoin='round'; g.beginPath();
      g.moveTo(cx-s*0.55,cy-s*0.45); g.lineTo(cx+s*0.5,cy+s*0.5); g.lineTo(cx,cy+s); g.lineTo(cx,cy-s); g.lineTo(cx+s*0.5,cy-s*0.5); g.lineTo(cx-s*0.55,cy+s*0.45); g.stroke();};
    const pwrIcon=(cx,cy,r,col)=>{g.strokeStyle=col; g.lineWidth=1.4; g.lineCap='round'; g.beginPath(); g.arc(cx,cy,r,-Math.PI/2+0.7,-Math.PI/2-0.7+2*Math.PI); g.stroke(); g.beginPath(); g.moveTo(cx,cy-r-1.5); g.lineTo(cx,cy-1); g.stroke(); g.lineCap='butt';};
    if(S.pHold>0){ // holding POWER
      const t=S.pHold;
      g.strokeStyle=O; g.lineWidth=2; g.beginPath(); g.arc(64,22,11,0,Math.PI*2); g.stroke();
      g.strokeStyle=W; g.beginPath(); g.arc(64,22,11,-Math.PI/2,-Math.PI/2+Math.PI*2*t); g.stroke();
      g.strokeStyle=W; g.lineWidth=1.4; g.beginPath(); g.arc(64,22,5,-Math.PI*0.25,Math.PI*1.35); g.stroke();
      g.fillStyle=W; g.beginPath(); g.moveTo(68.5,14.5); g.lineTo(69.5,19.5); g.lineTo(64.5,18.5); g.fill();
      g.font=`bold 9px ${F}`; g.textAlign='center'; g.fillText('Hold for omstart',64,44);
      g.fillStyle=D; g.font=`6px ${F}`; g.fillText('Slipp for å avbryte',64,54); g.textAlign='left';
      tex.needsUpdate=true; return;
    }
    if(S.boot){ // restart / startup splash
      const bt=(performance.now()-S.boot.t0)/1000;
      g.textAlign='center';
      if(S.boot.type==='restart'&&bt<1.2){
        g.fillStyle=W; g.font=`bold 10px ${F}`; g.fillText('Starter på nytt …',64,30);
        g.fillStyle=D; g.font=`6px ${F}`; g.fillText('Lagrer innstillinger',64,42);
      } else {
        const k=Math.min(1,(bt-(S.boot.type==='restart'?1.2:0))/1.6);
        pwrIcon(64,20,7,W);
        g.fillStyle=W; g.font=`bold 9px ${F}`; if('letterSpacing' in g) g.letterSpacing='1.5px'; g.fillText('PULTFORSTERKER',64,40); if('letterSpacing' in g) g.letterSpacing='0px';
        g.fillStyle=O; g.fillRect(34,50,60,2); g.fillStyle=W; g.fillRect(34,50,60*Math.max(0,k),2);
        g.fillStyle=D; g.font=`5.5px ${F}`; g.fillText(k<0.5?'Starter AirPlay':(k<0.9?'Starter Bluetooth':'Klar'),64,58);
      }
      g.textAlign='left'; tex.needsUpdate=true; return;
    }
    if(S.hold>0){ // holding AIRPLAY
      btIcon(64,20,7,W);
      g.fillStyle=W; g.font=`bold 9px ${F}`; g.textAlign='center';
      g.fillText(S.bt==='off'?'Slå på Bluetooth':'Slå av Bluetooth',64,38);
      g.fillStyle=D; g.font=`6px ${F}`; g.fillText('Hold AIRPLAY …',64,47); g.textAlign='left';
      g.fillStyle=O; g.fillRect(24,54,80,2.5); g.fillStyle=W; g.fillRect(24,54,80*S.hold,2.5);
      tex.needsUpdate=true; return;
    }
    if(S.ov){
      g.textAlign='center';
      if(S.ov.type==='pairing'){
        for(let k=0;k<3;k++){const r=((ovT*10+k*7)%21); g.strokeStyle=`rgba(238,246,255,${Math.max(0,1-r/21)})`; g.lineWidth=0.8; g.beginPath(); g.arc(64,19,6+r,0,Math.PI*2); g.stroke();}
        btIcon(64,19,6.5,W);
        g.fillStyle=W; g.font=`bold 10px ${F}`; g.fillText('Parring'+'.'.repeat(1+Math.floor(ovT*2)%3),64,41);
        g.fillStyle=D; g.font=`6.5px ${F}`; g.fillText('Synlig som «Pultforsterker»',64,52);
        g.font=`5.5px ${F}`; g.fillText('Hold AIRPLAY for å avbryte',64,60);
      } else if(S.ov.type==='connected'){
        btIcon(64,17,6.5,W);
        g.strokeStyle=W; g.lineWidth=1.4; g.beginPath(); g.moveTo(72,20); g.lineTo(75,23); g.lineTo(81,15); g.stroke();
        g.fillStyle=W; g.font=`bold 10px ${F}`; g.fillText('Tilkoblet',64,37);
        g.fillStyle=D; g.font=`7px ${F}`; g.fillText(S.btDev,64,48);
      } else if(S.ov.type==='bt_off'){
        btIcon(64,19,6.5,D); g.strokeStyle=W; g.lineWidth=1.4; g.beginPath(); g.moveTo(54,9); g.lineTo(74,29); g.stroke();
        g.fillStyle=W; g.font=`bold 10px ${F}`; g.fillText('Bluetooth av',64,41);
        g.fillStyle=D; g.font=`6px ${F}`; g.fillText('Hold AIRPLAY for å slå på',64,52);
      } else if(S.ov.type==='bt_needed'){
        btIcon(64,19,6.5,D);
        g.fillStyle=W; g.font=`bold 9px ${F}`; g.fillText('Bluetooth er av',64,40);
        g.fillStyle=D; g.font=`6px ${F}`; g.fillText('Hold AIRPLAY i 2 s for å slå på',64,51);
      }
      g.textAlign='left'; tex.needsUpdate=true; return;
    }
    g.font=`bold 6.5px ${F}`;
    let x=2; INPUTS.forEach((it,i)=>{const w=g.measureText(it.key).width+7;
      const off=it.key==='BT'&&S.bt==='off';
      if(i===S.input){g.fillStyle=W; g.fillRect(x,1,w,9.5); g.fillStyle='#000';} else {g.strokeStyle=off?O:D; g.lineWidth=0.6; if(off) g.setLineDash([1.2,1.2]); g.strokeRect(x+0.3,1.3,w-0.6,8.9); g.setLineDash([]); g.fillStyle=off?'#3d454c':D;}
      g.fillText(it.key,x+3.5,6);
      if(it.key==='BT'&&S.bt==='connected'&&i!==S.input){g.fillStyle=W; g.fillRect(x+w-2.6,2.6,1.4,1.4);}
      x+=w+2.5;});
    const it=INPUTS[S.input];
    // title (scrolls if too wide)
    g.save(); g.beginPath(); g.rect(0,14,128,14); g.clip();
    g.fillStyle=W; g.font=`bold 11px ${F}`; const tw=g.measureText(it.title).width;
    const off= tw>124 ? ((now*14)%(tw+30)) : 0;
    g.fillText(it.title,2-off,21); if(tw>124) g.fillText(it.title,2-off+tw+30,21); g.restore();
    g.fillStyle=D; g.font=`7px ${F}`; g.fillText(it.sub,2,31);
    if(it.len){ // play state + progress
      const t=S.playing?(now%it.len):102;
      g.fillStyle=W;
      if(S.playing){g.beginPath(); g.moveTo(2,37.5); g.lineTo(7,40.5); g.lineTo(2,43.5); g.fill();} else {g.fillRect(2,37.5,1.8,6); g.fillRect(5,37.5,1.8,6);}
      const px=11, pw=86; g.fillStyle=O; g.fillRect(px,40,pw,1.4); g.fillStyle=W; g.fillRect(px,40,pw*t/it.len,1.4); g.fillRect(px+pw*t/it.len-1,38.7,2,4);
      g.font=`6px ${F}`; g.textAlign='right'; g.fillText(mmss(t),126,40.8); g.textAlign='left';
    } else { // level meter for analog/USB
      for(let i=0;i<22;i++){const v=0.35+0.65*Math.abs(Math.sin(now*3.1+i*0.7)*Math.sin(now*1.7+i*0.31)); g.fillStyle=W; const h=1+v*6; g.fillRect(2+i*5.6,44-h,4,h);}
    }
    if(S.muted){ g.fillStyle=W; g.fillRect(2,50,4,5); g.beginPath(); g.moveTo(6,50); g.lineTo(10,47); g.lineTo(10,58); g.lineTo(6,55); g.fill();
      g.strokeStyle=W; g.lineWidth=1.2; g.beginPath(); g.moveTo(13,49.5); g.lineTo(19,55.5); g.moveTo(19,49.5); g.lineTo(13,55.5); g.stroke();
      g.font=`bold 12px ${F}`; g.textAlign='right'; g.fillText('MUTE',126,53.5); g.textAlign='left';
      g.fillStyle=D; g.font=`6px ${F}`; g.fillText('vol '+S.vol,26,53.5);
    } else {
    g.fillStyle=D; g.font=`bold 6px ${F}`; g.fillText('VOL',2,55.5);
    const segs=24,bx=17,sw=84/segs,on=Math.round(S.vol/100*segs);
    for(let i=0;i<segs;i++){g.fillStyle=i<on?W:O; const h=3+i*0.25; g.fillRect(bx+i*sw,59-h,sw-1,h);}
    g.fillStyle=W; g.font=`bold 12px ${F}`; g.textAlign='right'; g.fillText(String(S.vol),126,54.5); g.textAlign='left';
    }
  }
  tex.needsUpdate=true;
}
setInterval(()=>{ if(S.power&&(!S.standby||S.boot)&&!holdRAF&&!pRAF){ draw(); if(S.bt==='pairing') sync(); } },100);
const $=id=>document.getElementById(id);
function sync(){
  draw();
  knob.rotation.y=((S.vol/100)*270-135)*Math.PI/180;
  vipp.rotation.x=S.power?-0.2:0.2;
  const sb=S.power&&S.standby; setLed(pwrBtn.led,S.power,sb?0.12:1); symMat.color.set(S.power?(sb?0x3a3a3a:0xffffff):0x1a1a1a);
  $('stby').textContent=S.standby?'Standby':'På'; $('stby').classList.toggle('on',!S.standby);
  const pulse=S.bt==='pairing'?(0.5+0.5*Math.sin(performance.now()/180)):1;
  inBtns.forEach((b,i)=>setLed(b.led,S.power&&!S.standby&&(i===S.input||(i===1&&S.bt==='pairing')),i===1&&S.bt==='pairing'?pulse:1));
  $('btPair').textContent=S.bt==='off'?'Bluetooth: av':(S.bt==='pairing'?'Bluetooth: parrer …':'Bluetooth: tilkoblet'); $('btPair').classList.toggle('on',S.bt!=='off');
  $('mute').textContent=S.muted?'Mute på':'Mute av'; $('mute').classList.toggle('on',S.muted);
  lid.position.z=S.open?60:0;
  ears.visible=S.mount; feet.visible=!S.mount; antUp.visible=!S.mount; antBack.visible=S.mount;
  document.querySelectorAll('#inputs button').forEach((b,i)=>b.classList.toggle('on',i===S.input));
  $('volv').textContent=S.vol; $('pwr').textContent=S.power?'Hovedbryter på':'Hovedbryter av'; $('pwr').classList.toggle('on',S.power);
  $('open').classList.toggle('on',S.open); $('play').textContent=S.playing?'❚❚ Pause':'▶ Spill'; $('play').classList.toggle('on',S.playing); $('vMount').classList.toggle('on',S.mount); $('vFree').classList.toggle('on',!S.mount);
}
const press=(m,axis,amt)=>{const o=m.position[axis]; m.position[axis]=o+amt; setTimeout(()=>m.position[axis]=o,160);};
let ovTimer=null;
const showOv=(type,ms)=>{S.ov={type,t0:performance.now()}; clearTimeout(ovTimer); if(ms) ovTimer=setTimeout(()=>{S.ov=null; sync();},ms); sync();};
function btOn(){S.bt='pairing'; showOv('pairing'); ovTimer=setTimeout(()=>{ if(S.bt!=='pairing') return; S.bt='connected'; S.input=1; showOv('connected',2200); },6000);}
function btOff(){S.bt='off'; if(S.input===1) S.input=0; showOv('bt_off',2200);}
function selectInput(i){
  press(inBtns[i].g,'y',0.8);
  if(i===1&&S.bt==='off'){ showOv('bt_needed',2200); return; }
  if(i===1&&S.bt==='pairing'){ return; }
  S.ov=null; S.input=i; sync();
}
// press-and-hold on AIRPLAY (2 s) toggles Bluetooth
let holdRAF=0, holdStart=0, held=false;
function holdDown(){ held=false; holdStart=performance.now(); inBtns[0].g.position.y+=0.8;
  const step=()=>{ const t=(performance.now()-holdStart)/2000;
    if(t>0.15) S.hold=Math.min(1,t);
    if(t>=1){ S.hold=0; held=true; clearTimeout(holdRAF); holdRAF=0; (S.bt==='off')?btOn():(S.bt==='pairing'?btOff():btOff()); return; }
    draw(); holdRAF=setTimeout(step,30); };
  holdRAF=setTimeout(step,30); }
function holdUp(){ if(!holdStart) return; inBtns[0].g.position.y-=0.8; clearTimeout(holdRAF); holdRAF=0; const wasHold=held, wasShown=S.hold>0; holdStart=0; S.hold=0;
  if(!wasHold&&!wasShown){ S.ov=null; S.input=0; } sync(); }
INPUTS.forEach((it,i)=>{const b=document.createElement('button'); b.textContent=it.name;
  if(i===0){ b.title='Trykk: AirPlay · Hold 2 s: Bluetooth av/på'; b.onpointerdown=e=>{e.preventDefault(); holdDown();}; b.onpointerup=holdUp; b.onpointerleave=()=>{ if(holdStart) holdUp(); }; }
  else b.onclick=()=>selectInput(i);
  $('inputs').appendChild(b);});
$('btPair').onclick=()=>{ (S.bt==='off')?btOn():btOff(); };
$('mute').onclick=()=>{S.muted=!S.muted; press(knob,'y',1.5); sync();};
$('vol').oninput=e=>{S.vol=+e.target.value;sync();};
$('play').onclick=()=>{S.playing=!S.playing;sync();};
let pRAF=0, pStart=0, pLong=false, bootTimer=null;
function boot(type){ S.boot={type,t0:performance.now()}; S.ov=null; clearTimeout(bootTimer);
  bootTimer=setTimeout(()=>{S.boot=0; sync();}, type==='restart'?3000:1800); sync(); }
function pDown(){ if(!S.power) return; pLong=false; pStart=performance.now(); pwrBtn.g.position.y+=0.8;
  const step=()=>{ const t=(performance.now()-pStart)/3000;
    if(t>0.17) S.pHold=Math.min(1,t);
    if(t>=1){ S.pHold=0; pLong=true; clearTimeout(pRAF); pRAF=0; S.standby=false; boot('restart'); return; }
    draw(); pRAF=setTimeout(step,30); };
  pRAF=setTimeout(step,30); }
function pUp(){ if(!pStart) return; pwrBtn.g.position.y-=0.8; clearTimeout(pRAF); pRAF=0; const wasLong=pLong, wasShown=S.pHold>0; pStart=0; S.pHold=0;
  if(!wasLong&&!wasShown){ S.standby=!S.standby; if(!S.standby) boot('start'); else { S.boot=0; clearTimeout(bootTimer); } }
  sync(); }
$('stby').title='Trykk: av/på · Hold 3 s: omstart';
$('stby').onpointerdown=e=>{e.preventDefault(); pDown();}; $('stby').onpointerup=pUp; $('stby').onpointerleave=()=>{ if(pStart) pUp(); };
$('pwr').onclick=()=>{S.power=!S.power;sync();};
$('open').onclick=()=>{S.open=!S.open;sync();};
$('vMount').onclick=()=>{S.mount=true;sync();};
$('vFree').onclick=()=>{S.mount=false;sync();};
if(document.fonts) document.fonts.ready.then(draw);
sync();

// ---------- STL export (mm, visible printable parts) ----------
const shown=o=>{for(;o;o=o.parent) if(!o.visible) return false; return true;};
function stl(tag,file){
  root.updateMatrixWorld(true);
  const inv=new THREE.Matrix4().copy(inner.matrixWorld).invert(), tris=[];
  inner.traverse(m=>{ if(!m.isMesh||m.userData.print!==tag||!shown(m)) return;
    const g=m.geometry.index?m.geometry.toNonIndexed():m.geometry, mat=new THREE.Matrix4().multiplyMatrices(inv,m.matrixWorld), p=g.attributes.position;
    for(let i=0;i<p.count;i+=3) tris.push([0,1,2].map(k=>new V3().fromBufferAttribute(p,i+k).applyMatrix4(mat)));
  });
  const buf=new ArrayBuffer(84+tris.length*50), dv=new DataView(buf); dv.setUint32(80,tris.length,true);
  tris.forEach(([a,b,c],i)=>{const o=84+i*50, n=new V3().subVectors(b,a).cross(new V3().subVectors(c,a)).normalize();
    [n,a,b,c].forEach((v,j)=>{dv.setFloat32(o+j*12,v.x,true);dv.setFloat32(o+j*12+4,v.y,true);dv.setFloat32(o+j*12+8,v.z,true);});});
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([buf],{type:'model/stl'})); a.download=file; a.click();
}
const vn=()=>S.mount?'pultfeste':'frittstaende';
$('stlLid').onclick=()=>stl('lid',`pultforsterker_v2_lokk_${vn()}.stl`);
$('stlBody').onclick=()=>stl('body','pultforsterker_v2_kasse.stl');
$('stlGlass').onclick=()=>stl('glass','pultforsterker_v2_oled_vindu.stl');
window.__S=S; window.__sync=sync;
