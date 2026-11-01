// Skjold Node rev B — LID ONLY, variant for 12 × 12 mm tactile switches with round caps (instead of 12 mm metal buttons).
// A printed carrier under the lid holds the 4 switches; caps stick 1.5 mm through the lid, and their skirt keeps them from falling out. Base unchanged.
// Skjold Node rev B — 3D-printed enclosure for Raspberry Pi 4 / 3B(+), 1.8" ST7735S TFT, EC11 knob, 4 × 12 mm metal push buttons,
// logo inlays (AMS: lid top + base underside). Run via new Function('saveFile','log',src).
// User faces the +y side (no ports); ports exit at −y (power/video/audio) and +x (USB/Ethernet). Screen content is rotated 180° in software.
return (async()=>{
const mod=await import('https://esm.sh/manifold-3d@3.0.0');
const wasm=await mod.default({locateFile:()=> 'https://cdn.jsdelivr.net/npm/manifold-3d@3.0.0/manifold.wasm'}); wasm.setup(); const {Manifold,CrossSection}=wasm;
const {FontLoader}=await import('https://esm.sh/three@0.170.0/examples/jsm/loaders/FontLoader.js');
const fontB=new FontLoader().parse(await (await fetch('https://unpkg.com/three@0.170.0/examples/fonts/helvetiker_bold.typeface.json')).json());
const fontR=new FontLoader().parse(await (await fetch('https://unpkg.com/three@0.170.0/examples/fonts/helvetiker_regular.typeface.json')).json());
const arc=(cx,cy,r,a0,a1,n=12)=>Array.from({length:n+1},(_,i)=>{const a=a0+(a1-a0)*i/n;return [cx+r*Math.cos(a),cy+r*Math.sin(a)];});
const rr=(hw,hh,r,cx=0,cy=0)=>{const Q=Math.PI;r=Math.max(0.05,Math.min(r,hw,hh));return [...arc(cx+hw-r,cy-hh+r,r,-Q/2,0),...arc(cx+hw-r,cy+hh-r,r,0,Q/2),...arc(cx-hw+r,cy+hh-r,r,Q/2,Q),...arc(cx-hw+r,cy-hh+r,r,Q,1.5*Q)];};
const circ=(cx,cy,r,n=48)=>Array.from({length:n},(_,i)=>[cx+r*Math.cos(i/n*2*Math.PI),cy+r*Math.sin(i/n*2*Math.PI)]);
const prism=(p,z0,z1)=>Manifold.extrude(new CrossSection([p],'Positive'),z1-z0).translate([0,0,z0]);
const cyl=(x,y,r,z0,z1)=>prism(circ(x,y,r),z0,z1);
const U=a=>a.filter(Boolean).reduce((s,m)=>s?s.add(m):m,null);
const holeX=(p_yz,x0,x1)=>Manifold.extrude(new CrossSection([p_yz.map(([y,z])=>[-z,y])],'Positive'),x1-x0).rotate([0,90,0]).translate([x0,0,0]);
const holeY=(p_xz,y0,y1)=>Manifold.extrude(new CrossSection([p_xz.map(([x,z])=>[x,-z]).reverse()],'Positive'),y1-y0).rotate([-90,0,0]).translate([0,y0,0]);
// 2D marks in a reading frame (u right, v up) mapped to box xy
function textCS(t,u,v,size,font,map,align='center'){ const sh=font.generateShapes(t,size); let mn=[1e9,1e9],mx=[-1e9,-1e9];
  const polys=sh.map(s=>{ const o=s.getPoints(6).map(p=>[p.x,p.y]); o.forEach(p=>{mn=[Math.min(mn[0],p[0]),Math.min(mn[1],p[1])];mx=[Math.max(mx[0],p[0]),Math.max(mx[1],p[1])];}); return [o,...s.holes.map(h=>h.getPoints(6).map(p=>[p.x,p.y]))]; });
  const du=align==='left'?u-mn[0]:u-(mn[0]+mx[0])/2, dv=v-(mn[1]+mx[1])/2; let cs=null;
  for(const g of polys){ const c=new CrossSection(g.map(pl=>pl.map(([a,b])=>map(a+du,b+dv))),'EvenOdd'); cs=cs?cs.add(c):c; } return {cs,w:mx[0]-mn[0]}; }
const polyCS=(pts,map)=>new CrossSection([pts.map(([a,b])=>map(a,b))],'EvenOdd');
const BARS=[[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]];   // Skjold mark, 41 × 42 units, top-aligned
function logoCS(u,v,h,map){ const k=h/42; let cs=null; BARS.forEach(([x,bh])=>{ const c=polyCS(rr(2.3*k,bh*k/2,2.3*k,u+(x+2.3)*k,v+h/2-bh*k/2),map); cs=cs?cs.add(c):c; }); return {cs,w:41*k}; }
const tri=(u,v,s,dir)=>[[u-dir*s*0.5,v-s*0.6],[u+dir*s*0.55,v],[u-dir*s*0.5,v+s*0.6]];

const P={W:91,D:74,cy:6,R:5,wall:2,floor:2.5,zTop:32,lid:2,ch:0.8,so:4,pcb:1.4,inlay:0.6};
const IW=P.W/2-P.wall, ID=P.D/2-P.wall, CY=P.cy, Y0=CY-P.D/2, Y1=CY+P.D/2;   // y −31 … +43
const bx=x=>-42.5+x, by=y=>-28+y;
const zP=P.floor+P.so, zPt=zP+P.pcb;
const piHoles=[[3.5,3.5],[61.5,3.5],[3.5,52.5],[61.5,52.5]].map(([x,y])=>[bx(x),by(y)]);
const S={pcb:[53,35],x0:-12,glass:[45.8,34],gt:2.4,pt:1.6,act:[35.04,28.03]};
S.x1=S.x0+S.pcb[0]; S.gx=S.x1-0.6-S.glass[0]/2;
const knob=[-27,7];
const btnY=32.5, btns=[[30,'RADIO'],[10,'AIR / BT'],[-10,'prev'],[-30,'next']].map(([x,l])=>({x,y:btnY,l}));
const userMap=(u,v)=>[-u,-v];          // lid top as seen by the user standing at +y
const underMap=(u,v)=>[-u,v];          // base underside, box rolled over sideways

const PORTS={
 pi4:{back:[['usb',9],['usb',27],['eth',45.75]], front:[['rr',11.2,6.25,3.25,1.6,2],['rr',26,5.5,3.5,1.6,1.5],['rr',39.5,5.5,3.5,1.6,1.5],['c',53.5,3.75,3.4]]},
 pi3:{back:[['eth',10.25],['usb',29],['usb',47]], front:[['rr',10.6,5.5,3.25,1.5,1.5],['rr',32,8.5,4.25,3.1,1.5],['c',53.5,3.75,3.4]]}};

// ---------- LID ----------
const zT=P.zTop, zL=P.zTop+P.lid;
let lid=Manifold.hull([prism(rr(P.W/2,P.D/2,P.R,0,CY),zT,zL-P.ch),prism(rr(P.W/2-P.ch,P.D/2-P.ch,P.R-P.ch,0,CY),zL-0.01,zL)]);
let lip=prism(rr(IW-0.25,ID-0.25,P.R-2.25,0,CY),zT-2.5,zT).subtract(prism(rr(IW-1.45,ID-1.45,P.R-3.45,0,CY),zT-3,zT+0.1));
lip=lip.subtract(prism(rr(42,6,0.5,0,Y1-4),zT-4,zT+0.1));            // gap on the button side for the M12 nuts
lid=lid.add(lip);
lid=lid.add(U(piHoles.map(([x,y])=>cyl(x,y,x<0?2.2:2.5,zPt+0.2,zT+0.1))));
const fz=zT-S.gt-S.pt-0.2, pw=S.pcb[0]/2+0.2, ph=S.pcb[1]/2+0.2, sc=(S.x0+S.x1)/2;
lid=lid.add(prism(rr(pw+1.2,ph+1.2,1.5,sc,0),fz,zT+0.1).subtract(prism(rr(pw,ph,0.5,sc,0),fz-1,zT+1)).subtract(prism(rr(4,ph+3,0.1,S.x0-2,0),fz-1,zT-0.4)));
const cb=[[-1,21.5],[-1,-21.5],[35,21.5],[35,-21.5]];
lid=lid.add(U(cb.map(([x,y])=>cyl(x,y,2.6,fz+0.2,zT+0.1))));
cb.forEach(([x,y])=>{ lid=lid.subtract(cyl(x,y,0.85,fz,zT-0.6)); });
piHoles.forEach(([x,y])=>{ lid=lid.subtract(cyl(x,y,1.05,zPt,zT-0.6)); });
const aw=S.act[0]/2+0.3, ah=S.act[1]/2+0.3;
lid=lid.subtract(Manifold.hull([prism(rr(aw,ah,0.8,S.gx,0),zT-1,zL-0.6),prism(rr(aw+0.6,ah+0.6,1.4,S.gx,0),zL-0.01,zL+0.5)]));
lid=lid.subtract(prism(rr(S.glass[0]/2+0.15,S.glass[1]/2+0.15,0.5,S.gx,0),zT-0.5,zT+0.2));
lid=lid.subtract(cyl(knob[0],knob[1],3.6,zT-3,zL+1)).subtract(cyl(knob[0]+7.8,knob[1],1.3,zT-1,zL-0.8));
// ---- tactile switches: MEASURE YOURS. H = switch base to cap top with cap fitted.
const T={body:12,bh:3.6,H:13.5,capTop:11.5,skirt:13,capH:6.5,rise:1.5,hole:11.9};
const zSw=zL+T.rise-T.H, posts=[-20,0,20];
btns.forEach(b=>{ lid=lid.subtract(cyl(b.x,b.y,T.hole/2,zT-3,zL+1)); });
lid=lid.add(U(posts.map(x=>cyl(x,btnY,2.3,zSw,zT+0.1))));
posts.forEach(x=>{ lid=lid.subtract(cyl(x,btnY,0.85,zSw-1,zT-1)); });
let car=prism(rr(39,7.9,3,0,btnY),zSw-2,zSw);
btns.forEach(b=>{ const iw=T.body/2+0.2;
  car=car.add(prism(rr(iw+1,iw+1,1.2,b.x,b.y),zSw-0.01,zSw+2.5).subtract(prism(rr(iw,iw,0.4,b.x,b.y),zSw-1,zSw+3)).subtract(prism(rr(8,3.6,0.2,b.x,b.y),zSw-1,zSw+3)));
  [-1,1].forEach(s=>{ car=car.subtract(prism(rr(0.9,3.6,0.4,b.x+s*6.25,b.y),zSw-3,zSw+1)); }); });
posts.forEach(x=>{ car=car.subtract(cyl(x,btnY,1.15,zSw-3,zSw+1)).subtract(cyl(x,btnY,2.1,zSw-3,zSw-1.2)); });
// lid inlay: logo top-right (user view) + button legends above each button
const top=[logoCS(8.6,19,6,userMap), textCS('SKJOLD',16.6,19.2,4.4,fontB,userMap,'left'), textCS('N O D E',16.8,13.6,2.4,fontB,userMap,'left')];
btns.forEach(b=>{ const u=-b.x, v=-(b.y-12.6);
  if(b.l==='prev') top.push({cs:polyCS(tri(u-1.9,v,3.4,-1),userMap).add(polyCS(tri(u+1.6,v,3.4,-1),userMap))});
  else if(b.l==='next') top.push({cs:polyCS(tri(u-1.6,v,3.4,1),userMap).add(polyCS(tri(u+1.9,v,3.4,1),userMap))});
  else top.push(textCS(b.l,u,v,2.9,fontB,userMap)); });
const topCS=top.reduce((s,o)=>s?s.add(o.cs):o.cs,null);
const lidInlay=Manifold.extrude(topCS,P.inlay).translate([0,0,zL-P.inlay]).intersect(lid);
const lidS=lid.subtract(lidInlay);

// ---------- small parts ----------
let kn=Manifold.hull([cyl(0,0,11,0,13),cyl(0,0,10.2,13.8,14)]);
kn=kn.subtract(cyl(0,0,6.3,-1,2.6));
kn=kn.subtract(cyl(0,0,3.08,-1,12).subtract(prism([[1.55,-5],[5,-5],[5,5],[1.55,5]],-2,13)));
const knLine=prism(rr(0.5,4.5,0.5,0,6.2),13.4,15).intersect(kn); kn=kn.subtract(knLine);
const clamp=prism(rr(3,24.5,1.5),0,1.6).subtract(cyl(0,21.5,1.25,-1,3)).subtract(cyl(0,-21.5,1.25,-1,3));

const parts={lidS,lidInlay,car}; for(const k in parts) log(k,'genus',parts[k].genus(),'tris',parts[k].numTri(),'vol',parts[k].volume().toFixed(1));
function stl(m){ const me=m.getMesh(),vp=me.vertProperties,np=me.numProp,tv=me.triVerts,n=tv.length/3,buf=new ArrayBuffer(84+n*50),dv=new DataView(buf); dv.setUint32(80,n,true);
  const V=i=>[vp[i*np],vp[i*np+1],vp[i*np+2]];
  for(let i=0;i<n;i++){ const a=V(tv[i*3]),b=V(tv[i*3+1]),c=V(tv[i*3+2]),u=b.map((q,j)=>q-a[j]),v=c.map((q,j)=>q-a[j]); let nn=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]; const l=Math.hypot(...nn)||1;
    [...nn.map(q=>q/l),...a,...b,...c].forEach((q,j)=>dv.setFloat32(84+i*50+j*4,q,true)); } return new Blob([buf]); }
// 3MF with two objects (body + inlay) so the slicer assigns two filaments
const {zipSync,strToU8}=await import('https://esm.sh/fflate@0.8.2');
function obj(id,m,name){ const me=m.getMesh(),vp=me.vertProperties,np=me.numProp,tv=me.triVerts; let s=`<object id="${id}" name="${name}" type="model"><mesh><vertices>`;
  for(let i=0;i<vp.length/np;i++) s+=`<vertex x="${vp[i*np].toFixed(4)}" y="${vp[i*np+1].toFixed(4)}" z="${vp[i*np+2].toFixed(4)}"/>`; s+='</vertices><triangles>';
  for(let i=0;i<tv.length;i+=3) s+=`<triangle v1="${tv[i]}" v2="${tv[i+1]}" v3="${tv[i+2]}"/>`; return s+'</triangles></mesh></object>'; }
function mf(title,a,an,b,bn){ const model=`<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">${title}</metadata><resources>${obj(1,a,an)}${obj(2,b,bn)}<object id="3" type="model"><components><component objectid="1"/><component objectid="2"/></components></object></resources><build><item objectid="3"/></build></model>`;
  return new Blob([zipSync({'[Content_Types].xml':strToU8('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'),
    '_rels/.rels':strToU8('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'),
    '3D/3dmodel.model':strToU8(model)})]); }
const flip=m=>m.rotate([180,0,0]).translate([0,0,zL]);
function mfC(title,parts){ const n=parts.length; const objs=parts.map(([m,nm],i)=>obj(i+1,m,nm)).join('');
  const model='<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">'+title+'</metadata><resources>'+objs+'<object id="'+(n+1)+'" type="model"><components>'+parts.map((_,i)=>'<component objectid="'+(i+1)+'"/>').join('')+'</components></object></resources><build><item objectid="'+(n+1)+'"/></build></model>';
  const cfg='<?xml version="1.0" encoding="UTF-8"?><config><object id="'+(n+1)+'"><metadata key="name" value="'+title+'"/><metadata key="extruder" value="'+parts[0][2]+'"/>'+parts.map(([m,nm,ex],i)=>'<part id="'+(i+1)+'" subtype="normal_part"><metadata key="name" value="'+nm+'"/><metadata key="extruder" value="'+ex+'"/></part>').join('')+'</object></config>';
  return new Blob([zipSync({'[Content_Types].xml':strToU8('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="text/xml"/></Types>'),
    '_rels/.rels':strToU8('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'),
    '3D/3dmodel.model':strToU8(model),'Metadata/model_settings.config':strToU8(cfg)})]); }
const pre='node/taktil/skjold_node_taktil_';
await saveFile(pre+'2_lokk_forside_ned.3mf',mf('Skjold Node lokk taktile knapper',flip(lidS),'lokk',flip(lidInlay),'logo_og_tekst'));
await saveFile(pre+'2_lokk_print_forside_ned.stl',stl(flip(lidS))); await saveFile(pre+'2_lokk_innlegg.stl',stl(flip(lidInlay)));
await saveFile(pre+'2_lokk_CREALITY_PLA_gronn_tekst_PETG_sort.3mf',mfC('Skjold Node lokk taktil',[[flip(lidS),'lokk_PLA_gronn',2],[flip(lidInlay),'tekst_PETG_sort',1]]));
await saveFile(pre+'5_knappeholder.stl',stl(car.translate([0,0,-(zSw-2)])));
await saveFile(pre+'5_knappeholder_CREALITY_PETG_sort.3mf',mfC('Skjold Node knappeholder',[[car.translate([0,0,-(zSw-2)]),'holder_PETG_sort',1]]));
const A='node/assembly_taktil/';
await saveFile(A+'lid.stl',stl(lidS)); await saveFile(A+'lid_inlay.stl',stl(lidInlay)); await saveFile(A+'carrier.stl',stl(car));
await saveFile('node/params_taktil.json',JSON.stringify({P,S,knob,btns,piHoles,zPt,fz,CY,T,zSw},null,1));
})();
