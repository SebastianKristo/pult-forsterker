/** Av/på-knappen øverst til høyre: en meny med standby, sovetimer, omstart og slå av. */
import { useEffect, useState } from 'preact/hooks';
import { api, productOf, type Status } from '../lib/api';
import { act, deviceName, showToast } from '../lib/store';
import { PowerIcon } from '../components/ui';
import { loadPlugins, setPlugin, sleepLeft } from './plugins';

const A = '#d9a441';
const mmss = (s: number) => (s >= 3600 ? `${Math.floor(s / 3600)} t ${Math.floor((s % 3600) / 60)} min` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`);

export function PowerMenu({ s }: { s: Status | null }) {
  const [open, setOpen] = useState(false);
  const [ask, setAsk] = useState<'' | 'reboot' | 'off'>('');
  const on = !!s?.power, left = sleepLeft.value, rele = productOf(s) === 's1';
  useEffect(() => { if (open) void loadPlugins(); else setAsk(''); }, [open]);
  useEffect(() => { if (!left) return; const t = setInterval(() => { sleepLeft.value = Math.max(0, sleepLeft.value - 1); }, 1000); return () => clearInterval(t); }, [left > 0]);
  const close = () => setOpen(false);
  const power = (v: boolean) => { close(); void act(() => api.power(v), { power: v }); };
  const sov = async (min: number) => { const e = await setPlugin('sleep', min ? { enabled: true, minutes: min } : { minutes: 0 }); if (e) showToast(e); else showToast(min ? `Går i standby om ${min} min` : 'Sovetimer avbrutt'); };
  const sys = async (off: boolean) => { close(); try { await api.reboot(off); showToast(off ? 'Slår av …' : 'Starter på nytt …'); } catch (e) { showToast(e instanceof Error ? e.message : String(e)); } };
  return (
    <span style="position:relative;display:inline-flex">
      <button class={'pwr' + (on ? ' on' : '')} aria-label="Strøm" aria-expanded={open} title="Strøm" onClick={() => setOpen(!open)}><PowerIcon /></button>
      {open && <>
        <button onClick={close} aria-label="Lukk" style="position:fixed;inset:0;z-index:40;border:none;background:transparent;cursor:default" />
        <div class="pm" role="menu">
          <style>{CSS}</style>
          <div class="pm-hd"><span class="pm-dot" style={`background:${on ? '#6fcf7f' : '#8b8b86'}`} /><span style="display:flex;flex-direction:column;gap:1px;min-width:0"><b>{deviceName.value}</b><span>{on ? 'På' : 'Standby'}{left > 0 ? ' · standby om ' + mmss(left) : ''}</span></span></div>
          <button class="pm-row" onClick={() => power(!on)}>
            <span class="pm-ic" style={on ? '' : `color:${A}`}><PowerIcon /></span>
            <span class="pm-tx"><b>{on ? 'Standby' : 'Slå på'}</b><span>{on ? (rele ? 'Slår av forsterkeren (releet). Nettverk, AirPlay og app er fortsatt klare.' : 'Stopper lyden og demper utgangen. Nettverk, AirPlay og app er fortsatt klare.') : (rele ? 'Slår på forsterkeren og spiller videre.' : 'Slår på lyden igjen.')}</span></span>
          </button>
          <div class="pm-row pm-col">
            <span style="display:flex;gap:12px;align-items:flex-start;width:100%"><span class="pm-ic"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg></span>
              <span class="pm-tx"><b>Sovetimer</b><span>{left > 0 ? `Skrus ned og går i standby om ${mmss(left)}.` : 'Skrur gradvis ned det siste minuttet og går i standby.'}</span></span></span>
            <span class="pm-chips">{[15, 30, 60, 90].map((m) => <button key={m} onClick={() => void sov(m)}>{m} min</button>)}{left > 0 && <button class="x" onClick={() => void sov(0)}>Avbryt</button>}</span>
          </div>
          <div class="pm-sep" />
          {ask ? (
            <div class="pm-ask">
              <span>{ask === 'reboot' ? 'Starte på nytt? Musikken stopper i omtrent ett minutt.' : 'Slå av helt? Du må trekke ut og sette inn strømmen igjen for å starte den.'}</span>
              <span style="display:flex;gap:8px"><button class="pm-btn" onClick={() => setAsk('')}>Avbryt</button><button class="pm-btn pri" onClick={() => void sys(ask === 'off')}>{ask === 'reboot' ? 'Start på nytt' : 'Slå av'}</button></span>
            </div>
          ) : <>
            <button class="pm-row" onClick={() => setAsk('reboot')}>
              <span class="pm-ic"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5" /></svg></span>
              <span class="pm-tx"><b>Start på nytt</b><span>Hjelper hvis noe henger. Tar omtrent ett minutt.</span></span>
            </button>
            <button class="pm-row" onClick={() => setAsk('off')}>
              <span class="pm-ic" style="color:#e07a6a"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0" /></svg></span>
              <span class="pm-tx"><b>Slå av helt</b><span>Før du flytter den eller trekker ut strømmen.</span></span>
            </button>
          </>}
        </div>
      </>}
    </span>
  );
}

const CSS = `
.pm{position:absolute;top:calc(100% + 10px);right:0;z-index:41;width:320px;max-width:calc(100vw - 32px);background:#161618;border:1px solid #2e2e30;border-radius:16px;box-shadow:0 22px 60px rgba(0,0,0,.6);padding:6px;display:flex;flex-direction:column;animation:pmIn .16s ease-out}
@keyframes pmIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.pm-hd{display:flex;align-items:center;gap:10px;padding:10px 12px 12px}
.pm-hd b{font-size:14px;font-weight:600;color:#f2f2ee}
.pm-hd span span{font-size:12px;color:#8b8b86}
.pm-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.pm-row{display:flex;align-items:flex-start;gap:12px;width:100%;padding:10px 12px;border:none;border-radius:11px;background:transparent;color:#f2f2ee;text-align:left;cursor:pointer;font:inherit}
button.pm-row:hover{background:#1f1f22}
.pm-col{flex-direction:column;gap:10px;cursor:default}
.pm-ic{width:32px;height:32px;border-radius:9px;background:#222225;color:#c9c9c4;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.pm-ic svg{width:18px;height:18px}
.pm-tx{display:flex;flex-direction:column;gap:2px;min-width:0}
.pm-tx b{font-size:13.5px;font-weight:600}
.pm-tx span{font-size:12px;color:#8b8b86;line-height:1.4}
.pm-chips{display:flex;gap:6px;flex-wrap:wrap;padding-left:44px}
.pm-chips button{height:30px;padding:0 11px;border-radius:999px;border:1px solid #2e2e30;background:#1b1b1d;color:#f2f2ee;font-size:12px;cursor:pointer}
.pm-chips button:hover{border-color:#5a4420}
.pm-chips button.x{color:#f0c46a;border-color:#5a4420}
.pm-sep{height:1px;background:#242426;margin:6px 8px}
.pm-ask{display:flex;flex-direction:column;gap:10px;padding:10px 12px 12px;font-size:13px;color:#d1d1cc;line-height:1.45}
.pm-btn{flex:1;height:36px;border-radius:10px;border:1px solid #2e2e30;background:#1b1b1d;color:#f2f2ee;font-size:13px;cursor:pointer}
.pm-btn.pri{background:${A};border-color:${A};color:#0b0b0c;font-weight:600}
`;
