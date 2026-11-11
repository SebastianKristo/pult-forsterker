// Lydtagger for biblioteket, «Spill noe til …» og podkastsammendrag (pi/skjold_libtag.py, skjold_ask.py, skjold_podsum.py).
import { credFor, getBase, isRelayBase } from './api';

async function call<T>(path: string, body?: unknown, timeoutMs = 20000): Promise<T> {
  const base = getBase();
  const ctl = new AbortController();
  const t = window.setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const init: RequestInit = { cache: 'no-store', signal: ctl.signal, ...(isRelayBase(base) ? { credentials: credFor(base) } : {}) };
    if (body !== undefined) Object.assign(init, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const r = await fetch(base + path, init);
    const j = (await r.json().catch(() => { if (r.ok) throw new Error('Uventet svar fra Skjold'); return {}; })) as T & { error?: string };
    if (!r.ok) throw new Error(j.error || 'HTTP ' + r.status);
    return j;
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw new Error('Tidsavbrudd');
    throw e;
  } finally { clearTimeout(t); }
}

export const MOODS = ['glad', 'rolig', 'trist', 'energisk', 'mørk', 'drømmende'] as const;
export interface TagStatus { running: boolean; paused: boolean; done: number; errors: number; total: number; progress: number; current: string; error: string | null; moods: Record<string, number> }
export interface TagHit { id: string; title: string; artist: string; album: string; genre: string; year: number; duration: number; cover: string; bpm: number; energy: number; mood: string; acoustic: number; instrumental: number }
export interface TagFilter { mood?: string; energy?: string; acoustic?: string; instrumental?: string; bpm?: string; q?: string }
export interface AskQuery { genres: string[]; moods: string[]; energy: string; decade: number | null; language: string; artists_like: string[]; duration_min: number | null; kilder: string[] }
export interface AskResult { ok: boolean; query: AskQuery; how: 'llm' | 'regler'; summary: string; source?: string; playing?: string; error?: string }
export interface AiCfg { provider: '' | 'ollama' | 'anthropic'; ollamaUrl: string; ollamaModel: string; anthropicKey: string; anthropicModel: string; hasKey: boolean }
export interface OllamaTest { ok: boolean; url: string; models: string[]; version?: string; error?: string }
export interface PodFollow { kind: 'rss' | 'nrk' | 'ma'; id: string; title: string }
export interface PodItem { show: string; title: string; summary: string; url?: string; nrk?: string; image?: string }
export interface PodSum { follow: PodFollow[]; time: string; enabled: boolean; llm: boolean; voiceVol: number; maxEps: number; lastRun: string; llmReady: boolean; last: { text: string; items: PodItem[]; at: number } }

export const ai = {
  tags: () => call<TagStatus>('/api/library/tags'),
  tagsAction: (action: 'start' | 'pause') => call<TagStatus>('/api/library/tags', { action }),
  search: (f: TagFilter) => call<{ items: TagHit[]; count: number }>('/api/library/search?' + new URLSearchParams(Object.entries(f).filter(([, v]) => v) as [string, string][]).toString()),
  ask: (text: string, room = '') => call<AskResult>('/api/ask', { text, room }, 60000),
  aiCfg: () => call<AiCfg>('/api/ai'),
  aiSet: (b: Partial<AiCfg> & { clearKey?: boolean }) => call<AiCfg>('/api/ai', b),
  aiTest: (url: string) => call<OllamaTest>('/api/ai/test', { url }, 15000),
  podsum: () => call<PodSum>('/api/podsum'),
  podsumSet: (b: Partial<PodSum> | { action: 'morgen' }) => call<PodSum>('/api/podsum', b),
  podsumPreview: () => call<PodSum['last']>('/api/podsum/preview', {}, 120000),
  podsumRun: () => call<{ ok: boolean }>('/api/podsum/run', {}),
  podsumPlay: (i: number) => call<{ ok: boolean; playing: string }>('/api/podsum/play', { i }),
};
