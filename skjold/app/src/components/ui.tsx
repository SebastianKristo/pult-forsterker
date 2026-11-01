import type { ComponentChildren, JSX } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';

export function Logo({ lg = false, word = true }: { lg?: boolean; word?: boolean }) {
  const hs = lg ? [11, 16, 21, 16, 11] : [8, 12, 16, 12, 8];
  return (
    <div class={'logo' + (lg ? ' lg' : '')}>
      <div class="bars">{hs.map((h, i) => <i key={i} style={{ height: h + 'px' }} />)}</div>
      {word && <span class="word">SKJOLD</span>}
    </div>
  );
}

export function Icon({ d, size = 18, sw = 1.8, color, style }: { d: string; size?: number; sw?: number; color?: string; style?: JSX.CSSProperties }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color ?? 'currentColor'} stroke-width={sw} stroke-linecap="round" stroke-linejoin="round" style={style}>
      <path d={d} />
    </svg>
  );
}

export function Toggle({ on, onChange, red = false, disabled = false, label }: { on: boolean; onChange: (v: boolean) => void; red?: boolean; disabled?: boolean; label?: string }) {
  return <button type="button" class={'toggle' + (on ? ' on' : '') + (red ? ' red' : '')} role="switch" aria-checked={on} aria-label={label} disabled={disabled} onClick={() => onChange(!on)} />;
}

export function Chip({ on = false, sq = false, onClick, children, dot, title }: { on?: boolean; sq?: boolean; onClick?: () => void; children: ComponentChildren; dot?: boolean | null; title?: string }) {
  return (
    <button type="button" class={'chip' + (on ? ' on' : '') + (sq ? ' sq' : '')} onClick={onClick} title={title}>
      {children}
      {dot !== undefined && <i class={'dot' + (dot ? ' on' : '')} />}
    </button>
  );
}

export function Stepper({ value, min, max, fmt, onChange }: { value: number; min: number; max: number; fmt: (v: number) => string; onChange: (v: number) => void }) {
  return (
    <div class="stepper">
      <button type="button" class="btn square" aria-label="Mindre" onClick={() => onChange(Math.max(min, value - 1))}>−</button>
      <span class="v">{fmt(value)}</span>
      <button type="button" class="btn square" aria-label="Mer" onClick={() => onChange(Math.min(max, value + 1))}>+</button>
    </div>
  );
}

/** Confirm-on-second-tap action button (as in the design: "Trykk igjen"). */
export function ConfirmButton({ label, onConfirm, safe = false, danger = false, className = '' }: { label: string; onConfirm: () => void; safe?: boolean; danger?: boolean; className?: string }) {
  const [armed, setArmed] = useState(false);
  useEffect(() => { if (!armed) return; const t = setTimeout(() => setArmed(false), 4000); return () => clearTimeout(t); }, [armed]);
  return (
    <button type="button" class={'btn sm ' + (armed || danger ? 'danger ' : '') + className} onClick={() => { if (safe || armed) { setArmed(false); onConfirm(); } else setArmed(true); }}>
      {armed ? 'Trykk igjen' : label}
    </button>
  );
}

/**
 * Slider som eier verdien sin mens den dras og i 800 ms etter slipp (innkommende status ignoreres da, så den ikke hopper).
 * onCommit(v, false) mens den dras (maks hvert 100 ms), onCommit(v, true) ved slipp.
 */
export function Slider({ value, min = 0, max = 100, step = 1, onCommit, className = 'range', vertical = false, label }: { value: number; min?: number; max?: number; step?: number; onCommit: (v: number, final: boolean) => void; className?: string; vertical?: boolean; label?: string }) {
  const [local, setLocal] = useState(value);
  const drag = useRef(false);
  const released = useRef(0);
  const last = useRef(0);
  const sent = useRef<number | null>(null);
  const relT = useRef(0);
  const latest = useRef(value); latest.current = value;
  useEffect(() => {
    if (drag.current || Date.now() - released.current < 800) return;
    setLocal(value);
  }, [value]);
  useEffect(() => () => clearTimeout(relT.current), []);
  const release = (v: number) => {
    drag.current = false; released.current = Date.now();
    if (sent.current !== v) { sent.current = v; onCommit(v, true); }
    clearTimeout(relT.current);
    relT.current = window.setTimeout(() => { if (!drag.current) setLocal(latest.current); }, 850);
  };
  return (
    <input
      type="range" min={min} max={max} step={step} value={local} class={vertical ? 'vrange' : className} aria-label={label}
      onPointerDown={() => { drag.current = true; sent.current = null; }}
      onPointerUp={(e) => release(+(e.currentTarget as HTMLInputElement).value)}
      onPointerCancel={(e) => release(+(e.currentTarget as HTMLInputElement).value)}
      onInput={(e) => {
        const v = +(e.currentTarget as HTMLInputElement).value; setLocal(v);
        const now = Date.now();
        if (now - last.current >= 100) { last.current = now; sent.current = v; onCommit(v, false); }
      }}
      onChange={(e) => release(+(e.currentTarget as HTMLInputElement).value)}
    />
  );
}

export function Section({ title, action, children }: { title: string; action?: ComponentChildren; children: ComponentChildren }) {
  return (
    <div class="col gap10">
      <div class="row between"><span class="h2">{title}</span>{action}</div>
      {children}
    </div>
  );
}

export const PLAY = 'M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z';
export function PlayPauseIcon({ playing, size = 28 }: { playing: boolean; size?: number }) {
  return playing ? (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4.5" width="4" height="15" rx="1.2" /><rect x="14" y="4.5" width="4" height="15" rx="1.2" /></svg>
  ) : (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><path d={PLAY} /></svg>
  );
}
export function PrevIcon({ size = 26 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="5" width="2.4" height="14" rx="1" /><path d="M20 5.8v12.4a1 1 0 0 1-1.55.83L9.3 12.83a1 1 0 0 1 0-1.66l9.15-6.2A1 1 0 0 1 20 5.8z" /></svg>;
}
export function NextIcon({ size = 26 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="17.6" y="5" width="2.4" height="14" rx="1" /><path d="M4 5.8v12.4a1 1 0 0 0 1.55.83l9.15-6.2a1 1 0 0 0 0-1.66l-9.15-6.2A1 1 0 0 0 4 5.8z" /></svg>;
}
export function MuteIcon({ muted }: { muted: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4 9h3l5-4v14l-5-4H4z" fill="currentColor" />
      {muted ? <path d="M16 9l5 6M21 9l-5 6" /> : <path d="M16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12" />}
    </svg>
  );
}
export function PowerIcon({ size = 18 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v8" /><path d="M6.3 6.6a8 8 0 1 0 11.4 0" /></svg>;
}
export const S1_ICON = 'M3 7.5h18a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1zM4.5 9.8h5v3.4h-5zM11.6 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 10.3a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M11.6 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M13.8 13.7a.6.6 0 1 0 1.2 0a.6.6 0 1 0-1.2 0M16.4 12a2.3 2.3 0 1 0 4.6 0a2.3 2.3 0 1 0-4.6 0M18.7 10.2v1.2M3.5 16.5v1M20.5 16.5v1';
export const NODE_ICON = 'M4 6h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 18 18H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 6zM19.5 8h2v2.6h-2zM19.5 11.4h2v2.6h-2zM19.5 14.6h2v2h-2zM5 7.8h9M8 18v1.2M11.5 18v1.2M6.2 11.2h4.6v4.6H6.2zM15.2 15.3a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0';
export const CORE_ICON = 'M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM8 8h8v8H8zM12 4V2M12 22v-2M4 12H2M22 12h-2M10 11h4M10 13h4';
export const PRODUCT_ICON: Record<'s1' | 'node' | 'core', string> = { s1: S1_ICON, node: NODE_ICON, core: CORE_ICON };

/** Kildeikoner (skjold_settings.js · srcIcon): bakgrunn, farge, strek-sti, fyll-sti, merke-sti, størrelse. */
export const SRC_ICON: Record<string, { bg: string; fg: string; st: string; fi: string; fp: string; sz: string }> = {"Radio": {"bg": "#d9a441", "fg": "#0b0b0c", "st": "M4 9h16v11H4zM8 9l9-5M14 13h3M14 16h3", "fi": "M9.5 12.5a2 2 0 1 0 0 4 2 2 0 0 0 0-4z", "fp": "", "sz": "47%"}, "AirPlay": {"bg": "linear-gradient(160deg,#3a3a3e,#0b0b0c)", "fg": "#ffffff", "st": "", "fi": "", "fp": "M11.908.183a12.012 12.012 0 00-8.044 3.172c-4.882 4.475-5.166 12.08-.692 16.962.204.244.448.447.692.692a.315.315 0 00.408-.04l.53-.61a.32.32 0 000-.448C.53 15.965.243 9.253 4.23 4.982 8.217.711 14.889.427 19.16 4.414c4.271 3.986 4.555 10.655.568 14.927-.203.203-.365.407-.568.57a.32.32 0 000 .447l.53.611a.37.37 0 00.446.04c4.882-4.516 5.166-12.081.692-16.962a11.98 11.98 0 00-8.92-3.864zm.387 3.518A8.607 8.607 0 006.143 6c-3.458 3.213-3.66 8.623-.447 12.08.122.123.243.285.406.407a.319.319 0 00.447 0l.53-.61a.32.32 0 000-.446A7.263 7.263 0 014.8 12.183c0-3.946 3.212-7.16 7.158-7.16s7.16 3.253 7.16 7.199a7.207 7.207 0 01-2.238 5.209.319.319 0 000 .447l.529.61c.122.121.325.162.447.04a8.599 8.599 0 00.408-12.122 8.494 8.494 0 00-5.97-2.705zm-.266 3.316A5.198 5.198 0 008.34 8.48c-2.075 1.993-2.115 5.247-.122 7.322l.121.123a.319.319 0 00.447 0l.53-.611a.32.32 0 000-.448 3.814 3.814 0 01-1.098-2.683 3.732 3.732 0 013.742-3.742 3.732 3.732 0 013.742 3.742c0 1.017-.406 1.951-1.139 2.683a.32.32 0 000 .448l.53.61a.32.32 0 00.447 0c2.034-1.992 2.116-5.246.123-7.321a5.128 5.128 0 00-3.633-1.586zm.006 7.744a.599.599 0 00-.402.146l-.04.041-7.159 8.055a.506.506 0 00.041.69.437.437 0 00.283.124h14.36a.495.495 0 00.489-.488.463.463 0 00-.121-.326l-7.08-8.055a.5.5 0 00-.37-.187z", "sz": "48%"}, "Blåtann": {"bg": "#0082fc", "fg": "#ffffff", "st": "", "fi": "", "fp": "M12 0C6.76 0 3.1484 2.4895 3.1484 12S6.76 24 12 24c5.24 0 8.8516-2.4895 8.8516-12S17.24 0 12 0zm-.7773 1.6816l6.2148 6.2149L13.334 12l4.1035 4.1035-6.2148 6.2149V14.125l-3.418 3.42-1.2422-1.2442L10.8515 12l-4.289-4.3008 1.2422-1.2441 3.418 3.4199V1.6816zm1.748 4.2442v3.9687l1.9844-1.9843-1.9844-1.9844zm0 8.1816v3.9668l1.9844-1.9844-1.9844-1.9824Z", "sz": "46%"}, "Spotify": {"bg": "#000000", "fg": "#1ed760", "st": "", "fi": "", "fp": "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z", "sz": "100%"}, "AUX": {"bg": "#3a3a37", "fg": "#f2f2ee", "st": "M12 2.5v3M9.5 5.5h5v4h-5zM10.8 9.5h2.4v8.2a1.2 1.2 0 0 1-2.4 0zM10.8 13h2.4", "fi": "", "fp": "", "sz": "47%"}, "USB": {"bg": "#2a2a2c", "fg": "#f2f2ee", "st": "M12 3v15M8 9v2.5l4 3M16 8v3l-4 3", "fi": "M12 2l-2 3h4zM12 18a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zM7 7.5h2v2H7zM16 6.5a1.1 1.1 0 1 0 0 2.2 1.1 1.1 0 0 0 0-2.2z", "fp": "", "sz": "47%"}};
export function SrcCircle({ label, size = 64 }: { label: string; size?: number }) {
  const ic = SRC_ICON[label] ?? { bg: '#2a2a2c', fg: '#f2f2ee', st: '', fi: '', fp: '', sz: '47%' };
  return (
    <div class="src-circle" style={{ width: size + 'px', height: size + 'px', background: ic.bg, color: ic.fg }}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style={{ width: ic.sz, height: ic.sz, display: 'block' }}>
        {ic.st && <path d={ic.st} />}{ic.fi && <path d={ic.fi} fill="currentColor" stroke="none" />}{ic.fp && <path d={ic.fp} fill="currentColor" stroke="none" />}
      </svg>
    </div>
  );
}
export function Chevron({ dir = 'right', size = 16, color = 'currentColor', sw = 2 }: { dir?: 'right' | 'left' | 'down' | 'up'; size?: number; color?: string; sw?: number }) {
  const d = { right: 'M9 5l7 7-7 7', left: 'M15 5l-7 7 7 7', down: 'M6 9l6 6 6-6', up: 'M6 15l6-6 6 6' }[dir];
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} stroke-width={sw} stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg>;
}
