// Intro-animasjon og velkomstside (Skjold App v2: introView, heroView, sc-if welcome). Portert 1:1 fra designfilen.
import { useEffect, useState } from 'preact/hooks';
import { leaveWelcome } from '../lib/store';

const an = (n: string, d: number, s: number, e?: string) => n + ' ' + d + 's ' + (e || 'cubic-bezier(.2,.7,.2,1)') + ' ' + s + 's both';

export function Intro({ onDone }: { onDone: () => void }) {
  useEffect(() => { const t = setTimeout(onDone, 4700); return () => clearTimeout(t); }, []);
  const bars = [26, 40, 56, 40, 26].map((ht, i) => <div key={i} style={{ width: '7px', height: ht + 'px', borderRadius: '4px', transformOrigin: 'bottom', animation: an('skjBar', 0.5, 1.05 + i * 0.1) + ', ' + an('skjBarInk', 1.6, 1.05 + i * 0.1, 'ease') }} />);
  return (
    <div onClick={onDone} data-testid="intro" style={{ position: 'absolute', inset: 0, zIndex: 60, background: '#060607', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', cursor: 'pointer', animation: an('skjOut', 0.6, 4.05, 'ease-in') }}>
      <svg viewBox="0 0 350 760" preserveAspectRatio="xMidYMax slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
        <defs><linearGradient id="skjW" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16232a" /><stop offset="1" stop-color="#060607" /></linearGradient></defs>
        <path d="M0 560 L40 500 L70 520 L120 430 L150 470 L190 400 L235 470 L262 445 L300 500 L350 470 L350 600 L0 600 Z" fill="#10161b" style={{ animation: an('skjRise', 1.4, 0.05, 'ease-out') }} />
        <path d="M0 600 L30 560 L75 585 L110 520 L150 590 L0 600 Z M200 600 L245 535 L280 570 L320 525 L350 555 L350 600 Z" fill="#0b0f12" style={{ animation: an('skjRise', 1.4, 0.2, 'ease-out') }} />
        <rect x="0" y="600" width="350" height="160" fill="url(#skjW)" style={{ animation: an('skjFade', 1.2, 0.3, 'ease-out') }} />
        <path d="M0 600 L30 640 L75 615 L110 680 L150 610 L0 600 Z M200 600 L245 665 L280 630 L320 675 L350 645 L350 600 Z" fill="#0b0f12" opacity={0.45} style={{ animation: an('skjFade', 1.2, 0.4, 'ease-out') }} />
        <path d="M196 0 L184 92 L200 98 L172 196 L190 202 L160 300" fill="none" stroke="#fdf3d6" stroke-width="2.4" stroke-linejoin="miter" pathLength={1} stroke-dasharray="1" style={{ filter: 'drop-shadow(0 0 6px #f0c46a) drop-shadow(0 0 16px rgba(240,196,106,.7))', animation: an('skjBolt', 0.9, 0.6, 'linear') }} />
        <path d="M184 92 L160 140 L166 150 L150 190" fill="none" stroke="#fdf3d6" stroke-width="1.2" pathLength={1} stroke-dasharray="1" style={{ filter: 'drop-shadow(0 0 6px #f0c46a)', animation: an('skjBolt', 0.8, 0.68, 'linear') }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(70% 50% at 50% 30%, #fff6dc, rgba(240,196,106,.4) 60%, transparent)', pointerEvents: 'none', animation: an('skjFlash', 0.9, 0.78, 'linear') }} />
      <div style={{ position: 'absolute', left: '-30%', right: '-30%', top: '6%', height: '38%', background: 'radial-gradient(60% 50% at 40% 60%, rgba(70,160,140,.35), transparent 70%), radial-gradient(40% 40% at 70% 40%, rgba(90,110,170,.25), transparent 70%)', filter: 'blur(30px)', animation: an('skjSky', 3.6, 0.1, 'ease-out') }} />
      <div style={{ position: 'absolute', width: '420px', height: '420px', borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(217,164,65,.22), transparent)', marginTop: '-80px', animation: an('skjGlow', 1.8, 0.85, 'ease-out') }} />
      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', gap: '6px', height: '56px', marginTop: '-80px', animation: an('skjShake', 0.35, 0.82, 'linear') }}>{bars}</div>
      <div style={{ position: 'relative', marginTop: '30px', fontSize: '30px', fontWeight: 600, color: '#f2f2ee', paddingLeft: '.24em', animation: an('skjWord', 1.3, 1.6) }}>SKJOLD</div>
      <div style={{ position: 'relative', marginTop: '18px', width: '150px', height: '1px', background: 'linear-gradient(90deg, transparent, #d9a441, transparent)', animation: an('skjLine', 1, 2.4) }} />
    </div>
  );
}

const HERO: [string, string, string][] = [['./renders/cut/01-s1.png', 'Skjold S1', 'Forsterker med skjerm og knapper'], ['./renders/cut/03-s1.png', 'Skjold S1', 'Forsterker med skjerm og knapper'], ['./renders/cut/02-node.png', 'Skjold Node', 'Liten spiller for flere rom'], ['./renders/cut/04-node.png', 'Skjold Node', 'Liten spiller for flere rom']];

function Hero() {
  const [i, setI] = useState(0);
  const [gen, setGen] = useState(0);
  useEffect(() => { const t = setInterval(() => setI((x) => (x + 1) % HERO.length), 2800); return () => clearInterval(t); }, [gen]);
  const cur = HERO[i]!;
  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <div style={{ position: 'absolute', left: '-10%', right: '-10%', top: '8%', bottom: '14%', background: 'radial-gradient(closest-side, rgba(217,164,65,.16), rgba(217,164,65,.04) 60%, transparent)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', left: '18%', right: '18%', bottom: '17%', height: '18px', borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(0,0,0,.9), transparent)' }} />
      {HERO.map((x, j) => <img key={j} src={x[0]} alt={x[1]} draggable={false} style={{ position: 'absolute', left: '-6%', width: '112%', top: '-8%', transition: 'opacity .9s ease, transform 2.8s cubic-bezier(.2,.7,.2,1)', opacity: j === i ? 1 : 0, transform: j === i ? 'translateX(0) scale(1)' : 'translateX(' + (j < i ? -14 : 14) + 'px) scale(.97)', filter: 'drop-shadow(0 0 1px rgba(255,255,255,.18))', pointerEvents: 'none' }} />)}
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <span style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}><span style={{ fontSize: '14px', fontWeight: 600 }}>{cur[1]}</span><span style={{ fontSize: '12px', color: '#8b8b86' }}>{cur[2]}</span></span>
        <div style={{ display: 'flex', gap: '5px' }}>{HERO.map((_, j) => <button key={j} aria-label={'Bilde ' + (j + 1)} onClick={() => { setI(j); setGen((g) => g + 1); }} style={{ width: (j === i ? 18 : 6) + 'px', height: '6px', borderRadius: '3px', border: 'none', padding: 0, cursor: 'pointer', background: j === i ? '#d9a441' : '#3a3a37', transition: 'width .3s' }} />)}</div>
      </div>
    </div>
  );
}

export function Welcome() {
  const [intro, setIntro] = useState(true);
  return (
    <div class="dshell" data-testid="welcome">
      {intro && <Intro onDone={() => setIntro(false)} />}
      <div style="flex:1;display:flex;flex-direction:column;padding:8px 20px 18px;gap:18px;min-height:0;overflow:hidden">
        <div style="display:flex;align-items:center;gap:10px;padding-top:4px">
          <div style="display:flex;align-items:flex-start;gap:3px;height:16px"><div style="width:3px;height:8px;border-radius:2px;background:#f2f2ee" /><div style="width:3px;height:12px;border-radius:2px;background:#f2f2ee" /><div style="width:3px;height:16px;border-radius:2px;background:#f2f2ee" /><div style="width:3px;height:12px;border-radius:2px;background:#f2f2ee" /><div style="width:3px;height:8px;border-radius:2px;background:#f2f2ee" /></div>
          <span style="font-family:'Sora',sans-serif;font-size:14px;font-weight:600;letter-spacing:3px">SKJOLD</span>
        </div>
        <div style="position:relative;height:250px;flex-shrink:0"><Hero /></div>
        <div style="display:flex;flex-direction:column;gap:10px">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#8b8b86">VELKOMMEN</span>
          <h1 style="margin:0;font-size:28px;font-weight:600;line-height:1.15">Musikk i hvert rom</h1>
          <p style="margin:0;font-size:13px;color:#a9a9a3;line-height:1.5;text-wrap:pretty">Appen styrer Skjold S1 og Skjold Node. Velg kilde, juster lyden og samle rommene til ett system.</p>
        </div>
        <button onClick={leaveWelcome} style="margin-top:auto;height:52px;flex-shrink:0;border-radius:14px;border:none;background:#d9a441;color:#0b0b0c;font-size:15px;font-weight:600;cursor:pointer">Kom i gang</button>
      </div>
    </div>
  );
}
