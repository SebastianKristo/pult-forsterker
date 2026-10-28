// Rendrer LEGO-aktige monteringssteg av pultforsterkeren (three.js + Playwright/swiftshader) -> steps/step_NN.png
const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
const THREE_SRC=fs.readFileSync(path.join(process.env.SCRATCH,'node_modules/three/build/three.min.js'),'utf8');
const OUT=path.join(__dirname,'steps');fs.mkdirSync(OUT,{recursive:true});

const PAGE=`<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}canvas{display:block}</style></head><body>
<script>${THREE_SRC}</script>
<script>
const W=1400,H=1000;
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(W,H);renderer.setClearColor(0xffffff);renderer.outputEncoding=THREE.sRGBEncoding;document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff,0x808080,1.3));
const key=new THREE.DirectionalLight(0xffffff,1.1);key.position.set(150,250,200);scene.add(key);
const fill=new THREE.DirectionalLight(0xffffff,0.3);fill.position.set(-200,100,-200);scene.add(fill);
const std=(c,r=0.7,m=0.1)=>new THREE.MeshStandardMaterial({color:c,roughness:r,metalness:m});
const M={shell:std(0x2c2d30,0.75),plate:std(0x37383c,0.6,0.2),btn:std(0x1d1d20,0.3,0.45),alu:std(0xb8b8bc,0.35,0.8),gold:std(0xc9a227,0.35,0.9),red:std(0xa3261d,0.5),dark:std(0x141415,0.5),
 pcbG:std(0x2a8a4a,0.7),pcbB:std(0x2d5fb0,0.7),pcbR:std(0xb03030,0.7),pcbK:std(0x303033,0.7),pcbP:std(0x7b3fa0,0.7),acr:std(0x060708,0.2),glass:std(0x000000,0.1),white:std(0xffffff),knob:std(0x18181a,0.3,0.7),
 dimw:std(0xc8c8cc,0.8),hole:std(0xffffff,0.9),hi:new THREE.MeshStandardMaterial({color:0xe8562a,roughness:0.6,emissive:0xe8562a,emissiveIntensity:0.25})};
const root=new THREE.Group();scene.add(root);
const PARTS=[];
function part(step,offset,build){const g=new THREE.Group();g.userData={step,offset:offset||[0,0,0]};root.add(g);build(g);PARTS.push(g);return g;}
function rrect(w,h,r){const s=new THREE.Shape();s.moveTo(-w/2+r,-h/2);s.lineTo(w/2-r,-h/2);s.quadraticCurveTo(w/2,-h/2,w/2,-h/2+r);s.lineTo(w/2,h/2-r);s.quadraticCurveTo(w/2,h/2,w/2-r,h/2);s.lineTo(-w/2+r,h/2);s.quadraticCurveTo(-w/2,h/2,-w/2,h/2-r);s.lineTo(-w/2,-h/2+r);s.quadraticCurveTo(-w/2,-h/2,-w/2+r,-h/2);return s;}
const box=(g,w,h,d,mat,x,y,z)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);m.position.set(x,y,z);g.add(m);return m;};
const cyl=(g,r,len,mat,x,y,z,axis,r2)=>{const m=new THREE.Mesh(new THREE.CylinderGeometry(r2==null?r:r2,r,len,40),mat);if(axis==='z')m.rotation.x=Math.PI/2;m.position.set(x,y,z);g.add(m);return m;};
function textPlane(g,text,w,h,x,y,z,rot,col,weight){const c=document.createElement('canvas');c.width=512;c.height=Math.round(512*h/w);const q=c.getContext('2d');q.fillStyle=col||'#a3a29d';let fs=Math.round(c.height*0.62);q.font=(weight||500)+' '+fs+'px Helvetica,Arial,sans-serif';q.textAlign='center';q.textBaseline='middle';while(q.measureText(text).width>c.width*0.92&&fs>8){fs-=2;q.font=(weight||500)+' '+fs+'px Helvetica,Arial,sans-serif';}q.fillText(text,c.width/2,c.height/2);const t=new THREE.CanvasTexture(c);t.encoding=THREE.sRGBEncoding;const m=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false}));m.position.set(x,y,z);rot&&rot(m);g.add(m);return m;}
const FZ=62,BZ=-60;

// ---- 1 kasse ----
part(1,[0,0,0],g=>{box(g,200,2.5,120,M.shell,0,1.25,0);box(g,200,48,2.7,M.shell,0,24,60-1.35,0);box(g,200,48,2.7,M.shell,0,24,-60+1.35);box(g,2.7,48,120,M.shell,100-1.35,24,0);box(g,2.7,48,120,M.shell,-100+1.35,24,0);
 for(const sx of[-1,1])for(const sz of[-1,1])cyl(g,4,45.5,M.shell,sx*90,2.5+45.5/2,sz*50,'y');
 // hull-markeringer front/bak (mørke skiver) så man ser hvor ting skal
 [[-80,8.2],[20,6.2],[37,6.2],[70,3.7]].forEach(([x,r])=>cyl(g,r,0.4,M.hole,x,24,60.2,'z'));cyl(g,6.2,0.4,M.hole,20,24+8.5,60.2,'z');cyl(g,6.2,0.4,M.hole,37,24+8.5,60.2,'z');cyl(g,6.2,0.4,M.hole,20,24-8.5,60.2,'z');cyl(g,6.2,0.4,M.hole,37,24-8.5,60.2,'z');
 box(g,57,30,0.4,M.hole,-30,24,60.2);
 box(g,19.4,13,0.4,M.hole,76,24,-60.2);cyl(g,5.7,0.4,M.hole,54,24,-60.2,'z');box(g,9.6,3.8,0.4,M.hole,36,24,-60.2);cyl(g,3.2,0.4,M.hole,20,24,-60.2,'z');[-30,-45,-65,-80].forEach(x=>cyl(g,3.2,0.4,M.hole,x,24,-60.2,'z'));});
// ---- 2 varmeinnsatser ----
part(2,[0,30,0],g=>{for(const sx of[-1,1])for(const sz of[-1,1])cyl(g,2.4,5,M.gold,sx*90,45.5,sz*50,'y');});
// ---- 3 KCD1 + DC ----
part(3,[0,0,-45],g=>{box(g,21,15,2.4,M.dark,76,24,BZ-1.2);box(g,17,11,3,M.dark,76,24,BZ-2.4);box(g,19,12.6,14,M.dark,76,24,BZ+7);textPlane(g,'I  O',10,4,76,24,BZ-4,m=>m.rotation.y=Math.PI,'#ddd');
 cyl(g,7,1.6,M.alu,54,24,BZ-0.8,'z');cyl(g,3.2,1.8,M.dark,54,24,BZ-1.2,'z');cyl(g,5.5,12,M.dark,54,24,BZ+6,'z');cyl(g,7,2,M.alu,54,24,BZ+3.5,'z');});
// ---- 4 USB-C + AUX ----
part(4,[0,0,-45],g=>{box(g,22,8,1.2,M.alu,36,24,BZ-0.3);box(g,8.6,2.8,1.4,M.dark,36,24,BZ-0.6);for(const s of[-1,1])cyl(g,1.3,1.6,M.dark,36+s*8.5,24,BZ-0.3,'z');box(g,12,6,20,M.dark,36,24,BZ+10);
 cyl(g,4.6,1.4,M.alu,20,24,BZ-0.7,'z');cyl(g,1.8,1.6,M.dark,20,24,BZ-1,'z');cyl(g,3,14,M.dark,20,24,BZ+7,'z');});
// ---- 5 terminaler ----
part(5,[0,0,-50],g=>{[[-30,M.red],[-45,M.dark],[-65,M.red],[-80,M.dark]].forEach(([x,mat])=>{cyl(g,5,3,mat,x,24,BZ-1.5,'z');cyl(g,4.6,7,mat,x,24,BZ-6.5,'z');cyl(g,3,12,M.gold,x,24,BZ+6,'z');cyl(g,5,2,M.gold,x,24,BZ+3,'z');});});
// ---- 6 OLED-kort innvendig ----
part(6,[0,0,-45],g=>{box(g,70,40,1.6,M.pcbB,-30,24,60-2.7-2.2);box(g,60.5,37,1.4,M.glass,-30,24,60-2.7-0.7);for(const sx of[-1,1])for(const sy of[-1,1])cyl(g,1.5,6,M.white,-30+sx*32,24+sy*17,60-2.7-3,'z');});
// ---- 7 akryl + frontplate ----
part(7,[0,0,45],g=>{const fp=new THREE.Mesh(new THREE.ExtrudeGeometry(rrect(188,46,3),{depth:2,bevelEnabled:false}),M.plate);fp.position.set(0,24,60);g.add(fp);box(g,70,38,1.8,M.acr,-30,24,60-0.5);
 [[-80,8.2],[20,6.2],[37,6.2],[70,3.7]].forEach(([x,r])=>cyl(g,r,0.4,M.hole,x,24,62.2,'z'));[[20,8.5],[37,8.5],[20,-8.5],[37,-8.5]].forEach(([x,dz])=>cyl(g,6.2,0.4,M.hole,x,24+dz,62.2,'z'));
 for(const sx of[-1,1])for(const sy of[-1,1])cyl(g,1.6,0.6,M.dark,sx*88,24+sy*17,62.2,'z');});
// ---- 8 knapper ----
function mb(g,x,y,rh,rc){const fl=cyl(g,rh,1.6,M.btn,x,y,FZ+0.8,'z',rh-0.3);cyl(g,rc+0.55,0.35,M.white,x,y,FZ+1.65,'z');cyl(g,rc,1.2,M.btn,x,y,FZ+2.1,'z',rc-0.2);cyl(g,rc+1,18,M.btn,x,y,FZ-11,'z');cyl(g,rc+2,2,M.alu,x,y,FZ-4,'z');}
part(8,[0,0,45],g=>{mb(g,-80,24,9.5,6.6);[[20,8.5],[37,8.5],[20,-8.5],[37,-8.5]].forEach(([x,dz])=>mb(g,x,24+dz,7,5));});
// ---- 9 encoder + knott ----
part(9,[0,0,45],g=>{box(g,26,26,1.6,M.pcbG,70,24,60-2.7-6);cyl(g,3.5,12,M.alu,70,24,60,'z');cyl(g,15,17,M.knob,70,24,FZ+9,'z',16.4);box(g,1.2,5.5,0.4,M.white,70,24+10,FZ+17.75);});
// ---- 10 forsterker + Pi ----
const pcb=(g,x,zp,w,d,mat,h=1.6)=>box(g,w,h,d,mat,x,2.5+h/2,-zp);
part(10,[0,40,0],g=>{pcb(g,55,15,72,57,M.pcbB);box(g,18,9,18,M.pcbK,55,2.5+1.6+4.5,-15+10);box(g,8,12,8,M.pcbK,40,2.5+1.6+6,-15-15);box(g,8,12,8,M.pcbK,70,2.5+1.6+6,-15-15);box(g,30,8,6,M.pcbG,55,2.5+1.6+4,-15-26);
 for(const s of[-1,1])cyl(g,2.5,8,M.white,55+s*25,2.5+4,-15+s*21,'y');
 pcb(g,-55,22,65,30,M.pcbG);box(g,12,3,12,M.pcbK,-55,2.5+1.6+1.5,-22);box(g,50,2.5,2.5,M.dark,-55,2.5+1.6+1.25,-22+12);for(const sx of[-1,1])for(const sz of[-1,1])cyl(g,2,8,M.white,-55+sx*29,2.5+4,-22+sz*11.5,'y');
 textPlane(g,'A',14,14,55,12,-15+0,m=>m.rotation.x=-Math.PI/2,'#fff',700);textPlane(g,'B',12,12,-55,12,-22,m=>m.rotation.x=-Math.PI/2,'#fff',700);});
// ---- 11 små kort (VHB) ----
part(11,[0,40,0],g=>{pcb(g,-55,-8,32,17,M.pcbP);pcb(g,-85,45,20,11,M.pcbK);pcb(g,0,42,75,28,M.pcbR);for(let i=0;i<4;i++)box(g,15,12,10,M.pcbK,-28+i*18,2.5+1.6+6,-42);
 pcb(g,55,-38,60,28,M.pcbK);box(g,60,1.6,28,M.pcbK,55,2.5+1.6+8,38);pcb(g,5,-3,22,12,M.pcbG);
 [['C',-55,-8],['D',-85,45],['E',0,42],['F',55,-38],['G',5,-3]].forEach(([t,x,z])=>textPlane(g,t,10,10,x,16,-z,m=>m.rotation.x=-Math.PI/2,'#e8562a',700));});
// ---- ledninger ----
function wire(g,pts,col,r){const c=new THREE.CatmullRomCurve3(pts.map(p=>new THREE.Vector3(...p)));g.add(new THREE.Mesh(new THREE.TubeGeometry(c,32,r||1.1,8,false),std(col,0.5)));}
part(12,[0,0,0],g=>{wire(g,[[54,24,-58],[66,18,-52],[76,24,-58]],0xc0392b);wire(g,[[76,20,-56],[40,12,-50],[0,10,-46]],0xc0392b);wire(g,[[76,20,-56],[-30,14,-50],[-85,6,-45]],0xc0392b);
 wire(g,[[-10,10,-46],[20,8,-38],[55,6,-40]],0xc0392b);wire(g,[[54,22,-58],[30,10,-52],[-85,5,-46]],0x222222);wire(g,[[54,22,-58],[55,8,-44]],0x222222);});
part(13,[0,0,0],g=>{wire(g,[[-30,24,-58],[-10,12,-46],[48,6,-40]],0xc0392b);wire(g,[[-45,24,-58],[-15,12,-47],[52,6,-40]],0x222222);wire(g,[[-65,24,-58],[-20,12,-48],[58,6,-40]],0xc0392b);wire(g,[[-80,24,-58],[-25,12,-49],[62,6,-40]],0x222222);});
part(14,[0,0,0],g=>{wire(g,[[20,24,-58],[12,8,-48],[5,5,3]],0x1aa39a,1.2);wire(g,[[-55,6,8],[-25,6,6],[5,5,3]],0x1aa39a,1.2);wire(g,[[5,5,3],[30,5,-10],[55,6,-40]],0x1aa39a,1.2);wire(g,[[5,5,3],[0,8,-42]],0x1aa39a,1.2);});
part(15,[0,0,0],g=>{wire(g,[[-50,8,-10],[-45,14,20],[-30,8,56]],0xd9b300,0.5);wire(g,[[-45,8,-10],[-50,10,2],[-55,6,8]],0xd9b300,0.5);wire(g,[[-40,8,-10],[0,16,20],[20,20,55]],0x3f7fd9,0.5);wire(g,[[-40,8,-10],[-60,16,30],[-80,20,55]],0x3f7fd9,0.5);
 wire(g,[[-35,8,-10],[20,14,20],[55,8,38]],0x3f7fd9,0.5);wire(g,[[-35,8,-10],[-15,12,-30],[0,8,-42]],0x3f7fd9,0.5);wire(g,[[-30,8,-10],[-10,10,-5],[5,5,3]],0x3f7fd9,0.5);wire(g,[[-30,8,-10],[20,16,30],[70,10,55]],0x3f7fd9,0.5);
 wire(g,[[36,24,-58],[0,12,-30],[-45,8,-22]],0x202020,1.2);});
// ---- 16 lokk ----
part(16,[0,55,0],g=>{const l=new THREE.ExtrudeGeometry(rrect(200,120,6),{depth:3,bevelEnabled:false});l.rotateX(-Math.PI/2);const m=new THREE.Mesh(l,M.plate);m.position.y=48;g.add(m);for(const sx of[-1,1])for(const sz of[-1,1])box(g,14,3,10,M.plate,sx*107,49.5,sz*35);for(const sx of[-1,1])for(const sz of[-1,1])cyl(g,1.7,0.4,M.dark,sx*90,51.1,sz*50,'y');});

// arrows
const arrows=new THREE.Group();scene.add(arrows);
function arrow(from,to){const d=new THREE.Vector3(...to).sub(new THREE.Vector3(...from));const len=d.length();const a=new THREE.ArrowHelper(d.clone().normalize(),new THREE.Vector3(...from),len,0xe8562a,Math.min(10,len*0.3),Math.min(5,len*0.15));a.line.material.linewidth=2;arrows.add(a);
 const t=new THREE.Mesh(new THREE.CylinderGeometry(0.7,0.7,len-Math.min(10,len*0.3),8),std(0xe8562a));t.position.copy(new THREE.Vector3(...from).add(d.clone().multiplyScalar(0.5*(len-Math.min(10,len*0.3))/len)));t.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.clone().normalize());arrows.add(t);}
const cam=new THREE.PerspectiveCamera(28,W/H,1,3000);
window.renderStep=function(n,view){
 arrows.clear();
 if(n===0){for(const g of PARTS){const st=g.userData.step;g.visible=(st===1||st===7||st===16);const o=st===7?[0,0,45]:(st===16?[0,55,0]:[0,0,0]);g.position.set(...o);g.traverse(m=>{if(m.isMesh){if(m.userData.orig===undefined)m.userData.orig=m.material;m.material=m.userData.orig;}});}
  const v=view||{theta:-0.6,phi:1.05,dist:520,target:[0,24,0]};const t=new THREE.Vector3(...v.target);cam.position.set(t.x+v.dist*Math.sin(v.phi)*Math.sin(v.theta),t.y+v.dist*Math.cos(v.phi),t.z+v.dist*Math.sin(v.phi)*Math.cos(v.theta));cam.lookAt(t);renderer.render(scene,cam);return;}
 for(const g of PARTS){const s=g.userData.step;g.visible=s<=n;const o=g.userData.offset;const isNew=s===n;
  g.position.set(isNew?o[0]:0,isNew?o[1]:0,isNew?o[2]:0);
  g.traverse(m=>{if(m.isMesh){if(m.userData.orig===undefined)m.userData.orig=m.material;m.material=(m.geometry.type==='TubeGeometry'&&s<n)?M.dimw:m.userData.orig;}});
  if(isNew&&(o[0]||o[1]||o[2])){const b=new THREE.Box3().setFromObject(g);const c=b.getCenter(new THREE.Vector3());arrow([c.x,c.y,c.z],[c.x-o[0],c.y-o[1],c.z-o[2]]);}
  if(isNew&&!(o[0]||o[1]||o[2])){g.traverse(m=>{if(m.isMesh&&m.geometry.type==='TubeGeometry'){}});}
 }
 const v=view||{theta:-0.6,phi:1.05,dist:520,target:[0,24,0]};
 const t=new THREE.Vector3(...v.target);cam.position.set(t.x+v.dist*Math.sin(v.phi)*Math.sin(v.theta),t.y+v.dist*Math.cos(v.phi),t.z+v.dist*Math.sin(v.phi)*Math.cos(v.theta));cam.lookAt(t);
 renderer.render(scene,cam);
};
</script></body></html>`;

const VIEWS={front:{theta:-0.6,phi:1.05,dist:520,target:[0,24,0]},back:{theta:Math.PI-0.6,phi:1.05,dist:520,target:[0,24,0]},top:{theta:-0.25,phi:0.35,dist:520,target:[0,24,0]},wire:{theta:-0.2,phi:0.3,dist:430,target:[0,20,0]},frontclose:{theta:-0.45,phi:1.2,dist:380,target:[0,24,30]},backclose:{theta:Math.PI-0.5,phi:1.15,dist:380,target:[0,24,-30]}};
const STEPS=[[0,'front'],[1,'front'],[2,'top'],[3,'backclose'],[4,'backclose'],[5,'backclose'],[6,'top'],[7,'frontclose'],[8,'frontclose'],[9,'frontclose'],[10,'top'],[11,'top'],[12,'wire'],[13,'wire'],[14,'wire'],[15,'wire'],[16,'front']];
(async()=>{const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});const p=await b.newPage({viewport:{width:1400,height:1000}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
 await p.setContent(PAGE);await p.waitForTimeout(500);
 for(const[n,v]of STEPS){await p.evaluate(([n,v])=>window.renderStep(n,v),[n,VIEWS[v]]);await p.waitForTimeout(100);await p.screenshot({path:path.join(OUT,`step_${String(n).padStart(2,'0')}.png`)});}
 console.log(errs.length?errs:'ok');await b.close();})();
