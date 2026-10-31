// Felles avspillingsdeler: omslag, transport, volum, kildevalg, radiofavoritter.
import { useEffect, useState } from 'preact/hooks';
import { api, coverUrl, type InputId, type Status } from '../lib/api';
import { act, inputLabel, status, go } from '../lib/store';
import { art } from '../lib/settings';
import { Chip, MuteIcon, NextIcon, PlayPauseIcon, PowerIcon, PrevIcon, Slider } from '../components/ui';

export const SRC_COLOR: Record<string, string> = {
  radio: 'var(--src-radio)', bt: 'var(--src-bt)', usb: 'var(--src-bt)', airplay: 'var(--src-air)', aux: 'var(--src-aux)', aux2: 'var(--src-aux)'
};

export function nowTitle(s: Status | null): { title: string; sub: string } {
  if (!s) return { title: 'Ikke tilkoblet', sub: '' };
  if (!s.power) return { title: 'Standby', sub: 'Trykk på av/på for å slå på' };
  const src = inputLabel(s.input);
  if (s.title) return { title: s.title, sub: [s.artist, s.album].filter(Boolean).join(' · ') || src };
  if (s.input === 'radio' && s.station) return { title: s.station, sub: 'Radio' };
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
      {url && !bad && <img src={url} alt="" onError={() => setBad(true)} />}
      {size === 'big' && (!url || bad) && (
        <>
          <span class="kicker" style={{ color: a.ink, opacity: 0.8 }}>{s ? inputLabel(s.input) : ''}</span>
          <span class="big" style={{ fontSize: '30px' }}>{t.title}</span>
        </>
      )}
      {size === 'big' && s?.input === 'radio' && s.playing && <span class="live" style={{ position: 'absolute', top: '16px', right: '16px' }}>DIREKTE</span>}
    </div>
  );
}

export function Transport({ s }: { s: Status | null }) {
  const off = !s || !s.power || s.input === 'aux' || s.input === 'aux2';
  return (
    <div class="transport">
      <button class="tbtn" aria-label="Forrige" disabled={off} onClick={() => act(() => api.transport('previous'))}><PrevIcon /></button>
      <button class="tbtn main" aria-label={s?.playing ? 'Pause' : 'Spill'} disabled={off}
        onClick={() => act(() => api.transport('playpause'), { playing: !s?.playing })}><PlayPauseIcon playing={!!s?.playing} /></button>
      <button class="tbtn" aria-label="Neste" disabled={off} onClick={() => act(() => api.transport('next'))}><NextIcon /></button>
    </div>
  );
}

export function VolumeRow({ s }: { s: Status | null }) {
  const v = s?.volume ?? 0;
  return (
    <div class="volrow">
      <button class={'btn square' + (s?.mute ? ' danger' : '')} aria-label={s?.mute ? 'Slå på lyd' : 'Demp'} onClick={() => act(() => api.mute(!s?.mute), { mute: !s?.mute })}><MuteIcon muted={!!s?.mute} /></button>
      <Slider value={v} label="Volum" onCommit={(nv) => act(() => api.volume(nv), { volume: nv })} />
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

const ALL_INPUTS: InputId[] = ['airplay', 'bt', 'radio', 'aux', 'aux2', 'usb'];
export function InputChips({ s }: { s: Status | null }) {
  const list = s?.inputs?.length ? s.inputs : ALL_INPUTS;
  return (
    <div class="chips" data-testid="inputs">
      {list.map((id) => (
        <Chip key={id} on={s?.input === id} onClick={() => act(() => api.input(id), { input: id })}>
          <i style={{ width: '8px', height: '8px', borderRadius: '50%', background: SRC_COLOR[id] }} />
          {inputLabel(id)}
        </Chip>
      ))}
    </div>
  );
}

export function PresetTiles({ cols = 3 }: { cols?: number }) {
  const s = status.value;
  const presets = s?.presets ?? [];
  const tiles = [1, 2, 3, 4, 5, 6].map((n) => presets.find((p) => p.n === n) ?? { n, title: '' });
  return (
    <div class="preset-grid" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
      {tiles.map((p) => {
        const a = art(p.title || String(p.n));
        return (
          <button key={p.n} class={'preset' + (s?.preset === p.n && s.input === 'radio' ? ' on' : '')} style={p.title ? { background: a.bg, color: a.ink } : undefined}
            onClick={() => (p.title ? act(() => api.playPreset(p.n), { preset: p.n, input: 'radio' }) : go('radio'))}>
            <span class="n">{p.n}</span>
            {p.title ? <span class="t">{p.title}</span> : <span class="e">+ Legg til</span>}
          </button>
        );
      })}
    </div>
  );
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
      </div>
      {dur > 0 && (
        <div class="col gap4">
          <div class="bar"><i style={{ width: Math.min(100, (pos / dur) * 100) + '%' }} /></div>
          <div class="row between mono muted" style={{ fontSize: '11px' }}><span>{mmss(pos)}</span><span>{mmss(dur)}</span></div>
        </div>
      )}
      <Transport s={s} />
      <VolumeRow s={s} />
      <InputChips s={s} />
    </div>
  );
}

export function mmss(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}
