// Skjold website motion: scroll reveal, hero zoom, sticky image sequence. window.SKJOLD_FX.init()
(function(){
function init(){
  if(window.__skjoldFx) return; window.__skjoldFx=true;
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const io=new IntersectionObserver(es=>es.forEach(e=>{ if(e.isIntersecting){ e.target.style.opacity='1'; e.target.style.transform='none'; io.unobserve(e.target); } }),{threshold:0.12});
  const prep=()=>document.querySelectorAll('[data-reveal]:not([data-rv])').forEach((el,i)=>{ el.setAttribute('data-rv','1'); if(reduce) return; const d=+(el.getAttribute('data-reveal')||0);
    el.style.opacity='0'; el.style.transform='translateY(28px)'; el.style.transition='opacity .9s cubic-bezier(.2,.7,.2,1) '+d+'ms, transform .9s cubic-bezier(.2,.7,.2,1) '+d+'ms'; io.observe(el); });
  const tick=()=>{ const vh=innerHeight;
    document.querySelectorAll('[data-zoom]').forEach(el=>{ const r=el.getBoundingClientRect(), p=Math.max(0,Math.min(1,1-(r.top+r.height*0.3)/vh)); el.style.transform='scale('+(0.86+0.14*p).toFixed(4)+')'; el.style.opacity=String(0.35+0.65*Math.min(1,p*1.6)); });
    document.querySelectorAll('[data-scrolly]').forEach(box=>{ const r=box.getBoundingClientRect(), n=box.querySelectorAll('[data-frame]').length, span=r.height-vh, p=Math.max(0,Math.min(0.9999,-r.top/Math.max(1,span))), f=p*n, i=Math.floor(f);
      box.querySelectorAll('[data-frame]').forEach((fr,j)=>{ const on=j===i; fr.style.opacity=on?'1':'0'; fr.style.transform=on?'scale(1)':(j<i?'scale(1.04)':'scale(.96)'); });
      box.querySelectorAll('[data-cap]').forEach((c,j)=>{ const on=j===i; c.style.opacity=on?'1':'0'; c.style.transform=on?'none':'translateY('+(j<i?-16:16)+'px)'; });
      box.querySelectorAll('[data-dot]').forEach((d,j)=>{ d.style.background=j===i?'#1d1d1b':'#cfccc2'; d.style.width=j===i?'22px':'7px'; }); });
  };
  let raf=0; addEventListener('scroll',()=>{ cancelAnimationFrame(raf); raf=requestAnimationFrame(tick); },{passive:true}); addEventListener('resize',tick);
  new MutationObserver(()=>{ prep(); tick(); }).observe(document.body,{childList:true,subtree:true});
  prep(); tick(); }
window.SKJOLD_FX={init};
})();
