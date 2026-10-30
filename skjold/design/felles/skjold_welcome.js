// Skjold welcome / gift animation — shared by Skjold S1 (OLED 128×64, TFT 320×240) and Skjold Node (TFT 160×128).
// On the device the same text comes from /var/lib/skjold/velkomst.json (set with `sudo skjold-velkomst ...` over SSH).
(function(){
const F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86', COLS=['#e8893a','#4a8cff','#f2f2ee','#d8cfb4','#e85a6a'];
const rnd=(i,k)=>{ const x=Math.sin(i*127.1+k*311.7)*43758.5453; return x-Math.floor(x); };
const LS=(g,v)=>{ if('letterSpacing' in g) g.letterSpacing=v; };
function draw(g,w,h,ms,o={}){ const title=o.title||'Gratulerer med dagen', name=o.name||'Pappa', mono=!!o.mono, s=Math.min(w/160,h/128*1.25), wide=w/h>1.7;
  g.save(); g.fillStyle='#000'; g.fillRect(0,0,w,h); const t=ms/1000;
  // confetti
  const N=mono?26:46; for(let i=0;i<N;i++){ const sp=0.35+rnd(i,1)*0.5, x=rnd(i,2)*w+Math.sin(t*1.6+i)*6*s, y=((rnd(i,3)*1.2+t*sp)%1.2-0.1)*h, a=t*3+i, sz=(1.4+rnd(i,4)*1.8)*s;
    g.globalAlpha=Math.min(1,t*2)*(mono?0.8:0.95); g.fillStyle=mono?W:COLS[i%COLS.length]; g.save(); g.translate(x,y); g.rotate(a); g.fillRect(-sz/2,-sz*0.3,sz,sz*0.6*Math.abs(Math.cos(a))+0.4); g.restore(); }
  g.globalAlpha=1;
  // Skjold bars dancing
  const bars=[[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]], k=(wide?0.32:0.42)*s, bx=w/2-20.5*k, by=wide?h*0.12:h*0.14, inn=Math.min(1,t/0.6);
  bars.forEach(([x,bh],i)=>{ const dance=0.65+0.35*Math.abs(Math.sin(t*4.2+i*0.9)); g.fillStyle=W; g.globalAlpha=inn; g.beginPath(); g.roundRect(bx+x*k,by,4.6*k,bh*k*dance*inn,2.3*k); g.fill(); });
  g.globalAlpha=1;
  // text
  const ta=Math.max(0,Math.min(1,(t-0.5)/0.5)), ty=(1-ta)*6*s; g.textAlign='center'; g.globalAlpha=ta;
  const tY=wide?h*0.62:h*0.58, nY=wide?h*0.86:h*0.80;
  g.fillStyle=mono?Dm:'#d8cfb4'; g.font='600 '+(wide?6.5:9)*s+'px '+F; LS(g,(wide?0.6:0.8)*s+'px'); g.fillText(title,w/2,tY+ty);
  const nb=Math.max(0,Math.min(1,(t-0.9)/0.45)), pop=nb<1?1+0.25*Math.sin(nb*Math.PI):1; g.globalAlpha=nb; g.save(); g.translate(w/2,nY); g.scale(pop,pop);
  g.fillStyle=W; g.font='700 '+(wide?17:26)*s+'px '+F; LS(g,'0px'); g.fillText(name,0,0); g.restore();
  // hint
  if(t>3){ const p=0.45+0.55*(0.5+0.5*Math.sin((t-3)*3)); g.globalAlpha=p*(mono?0.9:1); g.fillStyle=Dm; g.font=(wide?4.6:6.5)*s+'px '+F; LS(g,'0px'); g.fillText(o.hint||'Trykk en knapp for å starte',w/2,h-(wide?1.5:4)*s); }
  g.restore(); g.textAlign='left'; LS(g,'0px'); }
window.SKJOLD_WELCOME={draw};
})();
