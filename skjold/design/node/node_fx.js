// Skjold Node screen effects (160×128), same look as Skjold S1: boot splash, reboot, source switch. window.SKJOLD_NODE_FX
(function(){
const F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86', LS=(g,v)=>{ if('letterSpacing' in g) g.letterSpacing=v; };
function icoAir(g,x,y,k,col){ g.save(); g.translate(x,y); g.scale(k,k); g.strokeStyle=col; g.fillStyle=col; g.lineWidth=1.2; g.lineJoin='round'; g.lineCap='round';
  g.beginPath(); g.moveTo(-3,4); g.lineTo(-7,4); g.quadraticCurveTo(-8,4,-8,3); g.lineTo(-8,-6); g.quadraticCurveTo(-8,-7,-7,-7); g.lineTo(7,-7); g.quadraticCurveTo(8,-7,8,-6); g.lineTo(8,3); g.quadraticCurveTo(8,4,7,4); g.lineTo(3,4); g.stroke();
  g.beginPath(); g.moveTo(0,1); g.lineTo(5,8); g.lineTo(-5,8); g.closePath(); g.fill(); g.restore(); }
function icoBT(g,x,y,k,col){ g.save(); g.translate(x,y); g.scale(k,k); g.strokeStyle=col; g.lineWidth=1.3; g.lineJoin='round'; g.lineCap='round';
  g.beginPath(); g.moveTo(-4,-4); g.lineTo(4,4); g.lineTo(0,8); g.lineTo(0,-8); g.lineTo(4,-4); g.lineTo(-4,4); g.stroke(); g.restore(); }
function icoRadio(g,x,y,k,col){ g.save(); g.translate(x,y); g.scale(k,k); g.strokeStyle=col; g.fillStyle=col; g.lineWidth=1.2; g.lineCap='round';
  g.beginPath(); g.arc(0,0,1.8,0,7); g.fill(); [4.5,7.5].forEach(r=>{ g.beginPath(); g.arc(0,0,r,-0.7,0.7); g.stroke(); g.beginPath(); g.arc(0,0,r,Math.PI-0.7,Math.PI+0.7); g.stroke(); }); g.restore(); }
const ICO=[icoRadio,icoAir,icoBT];
const BOOT=2600;
function splash(g,ms,w=160,h=128){ const t=ms/BOOT, bars=[[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]];
  g.fillStyle='#000'; g.fillRect(0,0,w,h); g.font='600 13px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; LS(g,'2px');
  const unit=41*0.62+6+g.measureText('SKJOLD').width, sc=Math.min(w*0.84/unit,h*0.5/(42*0.62));
  const k=sc*0.62, mw=41*k; g.font='600 '+(13*sc)+'px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; LS(g,(2*sc)+'px');
  const tw=g.measureText('SKJOLD').width, gap=6*sc, x0=(w-(mw+gap+tw))/2, y0=h/2-21*k-4;
  bars.forEach(([x,bh],i)=>{ const a=Math.max(0,Math.min(1,(t*5-i*0.45))); g.globalAlpha=a; g.fillStyle=W; g.beginPath(); g.roundRect(x0+x*k,y0,4.6*k,bh*k*a,2.3*k); g.fill(); });
  const ta=Math.max(0,Math.min(1,(t-0.45)*3)); g.globalAlpha=ta; g.fillStyle=W; g.textBaseline='middle'; g.fillText('SKJOLD',x0+mw+gap,h/2-4-2*sc);
  g.font='500 '+(4.6*sc)+'px "IBM Plex Mono",Menlo,monospace'; LS(g,(1.6*sc)+'px'); g.fillStyle=Dm; g.fillText('NODE',x0+mw+gap+1,h/2-4+10.5*sc);
  const p=Math.max(0,Math.min(1,(t-0.6)/0.4)); g.globalAlpha=ta; g.fillStyle='#2a2a28'; g.fillRect(40,104,80,2); g.fillStyle=W; g.fillRect(40,104,80*p,2);
  g.globalAlpha=1; LS(g,'0px'); g.textBaseline='alphabetic'; return ms<BOOT; }
const RB=380+3420;
function reboot(g,ms,now){ g.fillStyle='#000'; g.fillRect(0,0,160,128);
  if(ms<380){ const u=ms/380, h=Math.max(0.6,40*(1-u*u)), w=156*(u<0.7?1:1-(u-0.7)/0.3); g.fillStyle=W; g.globalAlpha=0.9; g.fillRect(80-w/2,64-h/2,w,h); g.globalAlpha=1; return true; }
  if(ms>=RB) return false;
  const T=ms-380, fade=Math.min(1,T/250,(3420-T)/300); g.globalAlpha=Math.max(0,fade);
  g.fillStyle=Dm; g.font='bold 7px '+F; LS(g,'1px'); g.fillText('OMSTART',8,14); LS(g,'0px'); g.fillStyle='#2a2a28'; g.fillRect(7,17,146,0.6);
  const ST=['Stopper lydtjenester','Starter Raspberry Pi','Kobler til Lyrion'], D=900, cur=Math.min(3,Math.floor(T/D));
  ST.forEach((l,i)=>{ const y=38+i*17, done=i<cur, act=i===cur, cx=11.7;
    if(done){ g.strokeStyle=W; g.lineWidth=1.3; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(cx-2.7,y-3.3); g.lineTo(cx-0.7,y-1.3); g.lineTo(cx+2.8,y-5.8); g.stroke(); }
    else if(act){ for(let k=0;k<8;k++){ const an=k/8*Math.PI*2+now/140; g.fillStyle='rgba(242,242,238,'+(0.2+0.8*((k/8+now/1120)%1)).toFixed(2)+')'; g.beginPath(); g.arc(cx+Math.cos(an)*3,y-3.5+Math.sin(an)*3,0.65,0,Math.PI*2); g.fill(); } }
    else { g.fillStyle='#3a3a37'; g.beginPath(); g.arc(cx,y-3.5,1.1,0,Math.PI*2); g.fill(); }
    g.fillStyle=done||act?W:'#55554f'; g.font=(act?'bold ':'')+'10px '+F; g.fillText(l,22,y); });
  const p=Math.min(1,T/(3*D)); g.fillStyle='#2a2a28'; g.fillRect(7,112,146,2); g.fillStyle=W; g.fillRect(7,112,146*(1-Math.pow(1-p,2)),2);
  g.globalAlpha=1; return true; }
const SW=950, NAMES=['RADIO','AIRPLAY','BLÅTANN'], SUBS=['Lyrion · favoritter','iPhone · via Wi-Fi','Sebastians iPhone'];
function switchSrc(g,ms,from,to){ if(ms>=SW) return false; const u=Math.min(1,ms/230), e=u<0.5?4*u*u*u:1-Math.pow(-2*u+2,3)/2, fo=Math.min(1,(SW-ms)/180);
  g.fillStyle='#000'; g.fillRect(0,0,160,128); const c=from+(to-from)*e;
  ICO.forEach((ico,i)=>{ const v=i-c, d=1-Math.min(1,Math.abs(v)); g.globalAlpha=fo*Math.max(0,0.25+0.75*d-Math.max(0,Math.abs(v)-1)*0.6); ico(g,80+v*48,48,1.8+1.0*d,d>0.5?W:Dm); });
  g.globalAlpha=fo*Math.min(1,Math.max(0,(ms-120)/120)); g.textAlign='center'; g.fillStyle=W; g.font='bold 14px '+F; LS(g,'1.5px'); g.fillText(NAMES[to],80,96); LS(g,'0px');
  g.fillStyle=Dm; g.font='9px '+F; g.fillText(SUBS[to],80,110); g.textAlign='left'; g.globalAlpha=1; return true; }
window.SKJOLD_NODE_FX={splash,reboot,switchSrc,icoAir,icoBT,icoRadio,BOOT,RB,SW};
})();
