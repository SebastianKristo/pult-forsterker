// Knappen «Spill på denne telefonen/PC-en» (se lib/localplay.ts).
import { canListen, localOn, startLocal, stopLocal, thisDevice } from '../lib/localplay';

const A = '#d9a441';

/** «Denne enheten»: spill det Skjold spiller på telefonen/PC-en (Skjold dempes og følger med). */
export function ListenHere({ compact = false }: { compact?: boolean }) {
  const on = localOn.value;
  if (!on && !canListen()) return null;
  const me = thisDevice();
  return (
    <button onClick={() => (on ? stopLocal() : startLocal())} aria-pressed={on} data-testid="listen-here"
      style={`display:flex;align-items:center;gap:10px;${compact ? 'height:40px;padding:0 14px;border-radius:999px;align-self:center' : 'padding:10px 12px;border-radius:12px;width:100%'};border:1px solid ${on ? A : 'rgba(242,242,238,.16)'};background:${on ? 'rgba(217,164,65,.16)' : 'rgba(0,0,0,.18)'};color:#f2f2ee;cursor:pointer;text-align:left;box-sizing:border-box`}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={on ? A : 'currentColor'} stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0">{/Telefon/.test(me) ? <path d="M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM11 18h2" /> : <path d="M4 5h16v11H4zM2 19h20" />}</svg>
      <span style="display:flex;flex-direction:column;gap:1px;min-width:0">
        <span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{on ? me + ' spiller' : 'Spill på ' + me.toLowerCase()}</span>
        {!compact && <span style="font-size:11px;color:rgba(242,242,238,.6)">{on ? 'Trykk for å flytte lyden tilbake til rommet' : 'Rommet dempes og følger med (kø, pause, spoling)'}</span>}
      </span>
    </button>
  );
}

