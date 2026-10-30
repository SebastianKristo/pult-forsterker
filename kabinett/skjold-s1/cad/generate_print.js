// Skjold S1 front plate for FDM (K2 + CFS): manifold khaki plate + black inlay, face-down, as 3MF + STL. Run via new Function('REVB','saveFile','log',src).
return (async()=>{
const mod=await import('https://esm.sh/manifold-3d@3.0.0');
const wasm=await mod.default({locateFile:()=> 'https://cdn.jsdelivr.net/npm/manifold-3d@3.0.0/manifold.wasm'}); wasm.setup(); const {Manifold,CrossSection}=wasm;
const {FontLoader}=await import('https://esm.sh/three@0.170.0/examples/jsm/loaders/FontLoader.js');
const {zipSync,strToU8}=await import('https://esm.sh/fflate@0.8.2');
const font=new FontLoader().parse(await (await fetch('https://unpkg.com/three@0.170.0/examples/fonts/helvetiker_bold.typeface.json')).json());
const P=REVB.plate, L=P.layers, HW=REVB.W/2, RT=9, DX=REVB.dispX, T=P.t;
const arc=(cx,cy,r,a0,a1,n=12)=>Array.from({length:n+1},(_,i)=>{const a=a0+(a1-a0)*i/n; return [cx+r*Math.cos(a),cy+r*Math.sin(a)];});
const rr=(hw,hh,r,cx=0,cy=0)=>{const Q=Math.PI; return [...arc(cx+hw-r,cy-hh+r,r,-Q/2,0),...arc(cx+hw-r,cy+hh-r,r,0,Q/2),...arc(cx-hw+r,cy+hh-r,r,Q/2,Q),...arc(cx-hw+r,cy-hh+r,r,Q,1.5*Q)];};
const circ=(cx,cy,r,n=64)=>Array.from({length:n},(_,i)=>[cx+r*Math.cos(i/n*2*Math.PI),cy+r*Math.sin(i/n*2*Math.PI)]);
const prism=(poly,z0,z1)=>Manifold.extrude(new CrossSection([poly],'Positive'),z1-z0).translate([0,0,z0]);
const thru=REVB.front.filter(f=>!f.screw).slice(1), inserts=REVB.front.filter(f=>f.screw);
function textCS(t,x,y,size){ const sh=font.generateShapes(t,size); let cs=null, mn=[1e9,1e9], mx=[-1e9,-1e9];
  const polys=sh.map(s=>{ const o=s.getPoints(8).map(p=>[p.x,p.y]); o.forEach(p=>{mn=[Math.min(mn[0],p[0]),Math.min(mn[1],p[1])]; mx=[Math.max(mx[0],p[0]),Math.max(mx[1],p[1])];}); return [o,...s.holes.map(h=>h.getPoints(8).map(p=>[p.x,p.y]))]; });
  const dx=x-(mn[0]+mx[0])/2, dy=y-(mn[1]+mx[1])/2; for(const g of polys){ const c=new CrossSection(g.map(pl=>pl.map(([a,b])=>[a+dx,b+dy])),'EvenOdd'); cs=cs?cs.add(c):c; } return cs; }
const V=(vp,np,i)=>[vp[i*np],-vp[i*np+1],T-vp[i*np+2]]; // face-down: 180° about X
function stl(m){ const me=m.getMesh(), vp=me.vertProperties, np=me.numProp, tv=me.triVerts, n=tv.length/3, buf=new ArrayBuffer(84+n*50), dv=new DataView(buf); dv.setUint32(80,n,true);
  for(let i=0;i<n;i++){ const a=V(vp,np,tv[i*3]),b=V(vp,np,tv[i*3+1]),c=V(vp,np,tv[i*3+2]); const u=[b[0]-a[0],b[1]-a[1],b[2]-a[2]], v=[c[0]-a[0],c[1]-a[1],c[2]-a[2]]; let nn=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]; const l=Math.hypot(...nn)||1;
    [...nn.map(q=>q/l),...a,...b,...c].forEach((q,j)=>dv.setFloat32(84+i*50+j*4,q,true)); } return buf; }
function obj3mf(id,m){ const me=m.getMesh(), vp=me.vertProperties, np=me.numProp, tv=me.triVerts; let s=`<object id="${id}" type="model"><mesh><vertices>`;
  for(let i=0;i<vp.length/np;i++){ const p=V(vp,np,i); s+=`<vertex x="${p[0].toFixed(4)}" y="${p[1].toFixed(4)}" z="${p[2].toFixed(4)}"/>`; } s+='</vertices><triangles>';
  for(let i=0;i<tv.length;i+=3) s+=`<triangle v1="${tv[i]}" v2="${tv[i+1]}" v3="${tv[i+2]}"/>`; return s+'</triangles></mesh></object>'; }
for(const k of ['oled','tft']){
  const fw=P.face[k], cv=P.cover[k], vw=P.view[k], cav=[cv[0]+2*P.cavClr,cv[1]+2*P.cavClr,cv[2]+P.cavClr];
  let plate=prism(rr(HW-2,22,RT-2),0,T);
  let voids=prism(rr(vw[0]/2,vw[1]/2,vw[2],DX,0),-1,L.back+0.05).add(prism(rr(cav[0]/2,cav[1]/2,cav[2],DX,0),L.back,L.back+L.cavity)).add(prism(rr(fw[0]/2,fw[1]/2,fw[2],DX,0),L.back+L.cavity-0.05,T+1));
  thru.forEach(f=>{ voids=voids.add(prism(circ(f.x,f.y-24,f.hp?3.2:f.d/2),-1,T+1)); if(f.hp) voids=voids.add(prism(circ(f.x,f.y-24,5.2),-1,2.4)); }); inserts.forEach(f=>{ voids=voids.add(prism(circ(f.x,f.y-24,P.insertD/2,40),-1,P.insertDepth)); });
  plate=plate.subtract(voids);
  let cs=null; for(const [t,x,y] of [['AIRPLAY',22,17.6],['BT',38,17.6],['AUX',22,-17.6],['USB',38,-17.6],['POWER',-76,13.4],['PULTFORSTERKER',60,19.6]]){ const c=textCS(t,x,y,2.6); cs=cs?cs.add(c):c; }
  cs=cs.add(new CrossSection([rr(fw[0]/2+P.frame,fw[1]/2+P.frame,fw[2]+P.frame,DX,0),rr(fw[0]/2,fw[1]/2,fw[2],DX,0).reverse()],'EvenOdd'));
  { const cx=-68.6, cy=-16, s=0.9; cs=cs.add(new CrossSection([[...arc(cx,cy,2*s,0,Math.PI,16),...arc(cx,cy,1.4*s,Math.PI,0,16)]],'Positive')); [-1,1].forEach(sx=>{ cs=cs.add(new CrossSection([rr(0.55*s,0.95*s,0.3*s,cx+sx*1.7*s,cy-0.6*s)],'Positive')); }); }
  const inlay=Manifold.extrude(cs,0.4).translate([0,0,T-0.4]).intersect(plate); plate=plate.subtract(inlay);
  log(k,'plate genus',plate.genus(),'tris',plate.numTri(),'inlay tris',inlay.numTri());
  const nm='print/skjold_s1_frontplate_'+k;
  await saveFile(nm+'_khaki.stl',new Blob([stl(plate)])); await saveFile(nm+'_sort_innlegg.stl',new Blob([stl(inlay)]));
  const model=`<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">Skjold S1 frontplate ${k}</metadata><resources>${obj3mf(1,plate)}${obj3mf(2,inlay)}<object id="3" type="model"><components><component objectid="1"/><component objectid="2"/></components></object></resources><build><item objectid="3" transform="1 0 0 0 1 0 0 0 1 130 130 0"/></build></model>`;
  await saveFile(nm+'.3mf',new Blob([zipSync({'[Content_Types].xml':strToU8('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'),
    '_rels/.rels':strToU8('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'),'3D/3dmodel.model':strToU8(model)})]));
}
})();
