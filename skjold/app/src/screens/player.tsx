// Felles avspillingsdeler: omslag, transport, volum, kildevalg, radiofavoritter.
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, coverUrl, type InputId, type Status } from '../lib/api';
import { act, hold, inputLabel, showToast, status, playPause, setVolume } from '../lib/store';
import { art } from '../lib/settings';
import { Chip, MuteIcon, NextIcon, PlayPauseIcon, PowerIcon, PrevIcon, Slider } from '../components/ui';

export const SRC_COLOR: Record<string, string> = {
  radio: 'var(--src-radio)', bt: 'var(--src-bt)', usb: 'var(--src-bt)', airplay: 'var(--src-air)', aux: 'var(--src-aux)', aux2: 'var(--src-aux)', spotify: 'var(--src-spotify)', plex: 'var(--src-plex)'
};

/** Én linje under tittelen der det er trangt: «Artist · Album». */
export function subLine(t: { sub: string; album?: string }): string { return [t.sub, t.album].filter(Boolean).join(' · '); }

export function nowTitle(s: Status | null): { title: string; sub: string; album?: string } {
  if (!s) return { title: 'Ikke tilkoblet', sub: '' };
  if (!s.power) return { title: 'Standby', sub: 'Trykk på av/på for å slå på' };
  const src = s.source_label || inputLabel(s.input);
  // Lyrion sender ofte tittel/album som mellomrom for radiostrømmer – da er det ingen låt, bare kanalen.
  const ti = (s.title || '').trim(), ar = (s.artist || '').trim(), al = (s.album || '').trim();
  const kanal = s.input === 'radio' && !s.source_label ? (s.radio_now?.name || s.station || '').trim() : '';
  if (kanal) return { title: kanal, sub: ti ? [ti, ar].filter(Boolean).join(' – ') : (s.radio_now?.now || '').trim() || 'Radio' };
  if (ti) return { title: ti, sub: ar || src, album: al };
  if (s.input === 'bt' && s.bt_device) return { title: s.bt_device, sub: 'Blåtann' };
  return { title: src, sub: s.playing ? 'Spiller' : 'Klar' };
}

export function Art({ s, size = 'big' }: { s: Status | null; size?: 'big' | 'small' }) {
  const t = nowTitle(s);
  const a = art(t.title + (s?.input ?? ''));
  const url = coverUrl(s);
  const [bad, setBad] = useState(false);
  useEffect(() => setBad(false), [url]);
  return (
    <div class="art" style={{ background: a.bg, color: a.ink, padding: size === 'small' ? 0 : undefined }} data-testid="art">
      {url && !bad && <img key={url} src={url} alt="" draggable={false} data-testid="cover" onError={() => setBad(true)} />}
      {size === 'big' && (!url || bad) && (
        <>
          <span class="kicker" style={{ color: a.ink, opacity: 0.8 }}>{s ? inputLabel(s.input) : ''}</span>
          <span class="big" style={{ fontSize: '30px' }}>{t.title}</span>
        </>
      )}
      {size === 'big' && s?.input === 'radio' && !s.source_label && s.playing && <span class="live" style={{ position: 'absolute', top: '16px', right: '16px' }}>DIREKTE</span>}
    </div>
  );
}

export function Transport({ s }: { s: Status | null }) {
  const off = !s || !s.power || s.input === 'aux' || s.input === 'aux2';
  return (
    <div class="transport">
      <button class="tbtn" aria-label="Forrige" disabled={off} onClick={() => act(() => api.transport('previous'))}><PrevIcon /></button>
      <button class="tbtn main" aria-label={s?.playing ? 'Pause' : 'Spill'} disabled={off}
        onClick={playPause} data-testid="playpause"><PlayPauseIcon playing={!!s?.playing} /></button>
      <button class="tbtn" aria-label="Neste" disabled={off} onClick={() => act(() => api.transport('next'))}><NextIcon /></button>
    </div>
  );
}

export function VolumeRow({ s }: { s: Status | null }) {
  const v = s?.volume ?? 0;
  return (
    <div class="volrow">
      <button class={'btn square' + (s?.mute ? ' danger' : '')} aria-label={s?.mute ? 'Slå på lyd' : 'Demp'} onClick={() => act(() => api.mute(!s?.mute), { mute: !s?.mute })}><MuteIcon muted={!!s?.mute} /></button>
      <Slider value={v} label="Volum" onCommit={setVolume} />
      <span class="v" data-testid="vol">{v}</span>
      <span class="lbl">VOL</span>
    </div>
  );
}

export function PowerButton({ s }: { s: Status | null }) {
  return (
    <button class={'pwr' + (s?.power ? ' on' : '')} aria-label={s?.power ? 'Standby' : 'Slå på'} title={s?.power ? 'Standby' : 'Slå på'}
      onClick={() => act(() => api.power(!s?.power), { power: !s?.power })}><PowerIcon /></button>
  );
}

const ALL_INPUTS: InputId[] = ['airplay', 'bt', 'spotify', 'radio', 'aux', 'aux2', 'usb'];
export function InputChips({ s }: { s: Status | null }) {
  const list = s?.inputs?.length ? s.inputs : ALL_INPUTS;
  return (
    <div class="chips" data-testid="inputs">
      {list.map((id) => (
        <Chip key={id} on={s?.input === id && !(id === 'radio' && s?.source_label)} onClick={() => act(() => api.input(id), { input: id })}>
          <i style={{ width: '8px', height: '8px', borderRadius: '50%', background: SRC_COLOR[id] }} />
          {inputLabel(id)}
        </Chip>
      ))}
    </div>
  );
}

/** Bakgrunn for omslag: ekte omslag, kanallogo eller fargeplassholder. */
export function artFor(s: Status | null): { bg: string; ink: string; img: string | null } {
  const t = nowTitle(s);
  const img = coverUrl(s) || (s?.input === 'radio' ? s.radio_now?.image || null : null);
  const key = s?.input === 'radio' ? (s.radio_now?.name || s.station || t.title) : t.title;
  const a = art(key);
  return { bg: img ? 'url("' + img.replace(/"/g, '') + '") center / cover no-repeat, ' + a.bg : a.bg, ink: a.ink, img };
}
/** Linje over tittelen i spilleren: kilde · enhet. */
export function sourceLine(s: Status | null): string {
  if (!s) return '';
  const src = inputLabel(s.input);
  if (s.input === 'airplay' && s.airplay_device) return src + ' · ' + s.airplay_device;
  if (s.input === 'bt' && s.bt_device) return src + ' · ' + s.bt_device;
  if (s.input === 'radio') return src + (s.radio_now?.name || s.station ? ' · ' + (s.radio_now?.name || s.station) : '');
  return src;
}

/** Spiller-kort med alt: brukes i fullskjermspilleren (telefon) og på «Spiller nå» (PC). */
export function PlayerBody() {
  const s = status.value;
  const t = nowTitle(s);
  const dur = s?.duration ?? 0, pos = s?.position ?? 0;
  return (
    <div class="col gap16">
      <Art s={s} />
      <div class="col gap4">
        <span class="ellip" style={{ fontSize: '22px', fontWeight: 600 }} data-testid="now-title">{t.title}</span>
        <span class="ellip muted">{t.sub}</span>
        {t.album && <span class="ellip muted" style={{ fontSize: '13px', opacity: 0.8 }} data-testid="album">{t.album}</span>}
        {s?.input === 'airplay' && s.airplay_device && <span class="ellip muted" style={{ fontSize: '11px' }}>Fra {s.airplay_device}</span>}
      </div>
      {dur > 0 && (
        <SeekBar pos={pos} dur={dur} seek={canSeek(s) ? seekTo : null} />
      )}
      <Transport s={s} />
      <VolumeRow s={s} />
      <InputChips s={s} />
    </div>
  );
}

/** Kan låten som spilles spoles? Lyrion-strømmer med varighet (Navidrome, YouTube Music, bibliotek) og Plex. */
export function canSeek(s: Status | null): boolean {
  return !!s && (s.duration ?? 0) > 0 && (s.source === 'plex' || s.input === 'radio');
}
/** Spol: viser ny posisjon med en gang (hold), og sier fra hvis kilden ikke kan spoles. */
export async function seekTo(pos: number): Promise<void> {
  hold({ position: pos }, 2500);
  try { await api.seek(pos); } catch (e) { showToast(e instanceof Error ? e.message : 'Kunne ikke spole'); }
}

/** Fremdriftslinje som kan dras eller trykkes for å spole (når `seek` er satt). Tidene oppdateres mens du drar. */
export function SeekBar({ pos, dur, seek, variant = 'desk' }: { pos: number; dur: number; seek?: ((p: number) => void) | null; variant?: 'desk' | 'phone' }) {
  const [drag, setDrag] = useState<number | null>(null);
  const el = useRef<HTMLDivElement>(null);
  const at = (x: number) => { const r = el.current!.getBoundingClientRect(); return Math.max(0, Math.min(1, (x - r.left) / r.width)) * dur; };
  const p = Math.min(drag ?? pos, dur), pct = dur > 0 ? Math.min(100, (p / dur) * 100) : 0;
  const on = !!seek && dur > 0;
  const down = (e: PointerEvent) => { if (!on) return; e.stopPropagation(); try { el.current!.setPointerCapture(e.pointerId); } catch { /* ignore */ } setDrag(at(e.clientX)); };
  const move = (e: PointerEvent) => { if (drag !== null) setDrag(at(e.clientX)); };
  const up = (e: PointerEvent) => { if (drag === null) return; const v = at(e.clientX); setDrag(null); seek!(v); };
  const key = (e: KeyboardEvent) => {
    if (!on) return;
    const d = e.key === 'ArrowRight' ? 10 : e.key === 'ArrowLeft' ? -10 : 0;
    if (d) { e.preventDefault(); seek!(Math.max(0, Math.min(dur - 1, pos + d))); }
  };
  const phone = variant === 'phone';
  const track = phone ? 'rgba(242,242,238,.22)' : 'var(--line, #2e2e30)', fill = phone ? 'rgba(242,242,238,.9)' : 'var(--ink, #f2f2ee)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <div ref={el} data-seek role={on ? 'slider' : undefined} tabIndex={on ? 0 : undefined} aria-label={on ? 'Spol' : undefined}
        aria-valuemin={0} aria-valuemax={Math.round(dur)} aria-valuenow={Math.round(p)} aria-valuetext={mmss(p) + ' av ' + mmss(dur)}
        onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={() => setDrag(null)} onKeyDown={key}
        style={{ height: '18px', display: 'flex', alignItems: 'center', position: 'relative', cursor: on ? 'pointer' : 'default', touchAction: on ? 'none' : 'auto' }}>
        <div style={{ flex: 1, height: drag !== null ? '7px' : '5px', borderRadius: '4px', background: track, overflow: 'hidden', transition: 'height .15s' }}>
          <div style={{ height: '100%', width: pct.toFixed(2) + '%', background: fill, borderRadius: '4px' }} />
        </div>
        {on && <div style={{ position: 'absolute', left: `calc(${pct.toFixed(2)}% - 7px)`, width: '14px', height: '14px', borderRadius: '50%', background: fill, boxShadow: '0 1px 4px rgba(0,0,0,.4)', transform: drag !== null ? 'scale(1.25)' : 'scale(1)', transition: 'transform .15s' }} />}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: "'IBM Plex Mono',monospace", fontSize: phone ? '10px' : '11px', color: phone ? 'rgba(242,242,238,.6)' : 'var(--muted, #8b8b86)' }}>
        <span>{mmss(p)}</span><span>{phone ? '−' + mmss(dur - p) : mmss(dur)}</span>
      </div>
    </div>
  );
}

export function mmss(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}
