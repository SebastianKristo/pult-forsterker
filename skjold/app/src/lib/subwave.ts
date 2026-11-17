// SUB/WAVE-stasjonene (plugin) som eget valg i Bibliotek og Kilder. Hentes én gang fra /api/subwave og ved behov på nytt.
import { signal } from '@preact/signals';
import { api } from './api';

export interface SwStation { i: number; name: string; image?: string; admin?: boolean }
export const swStations = signal<SwStation[]>([]);
export const swPlaying = signal<number | null>(null);
let loaded = 0;

export function loadSw(force = false): void {
  if (!force && Date.now() - loaded < 60000) return;
  loaded = Date.now();
  api.subwave(true).then((r) => { swStations.value = r.configured ? r.stations ?? [] : []; swPlaying.value = r.playing_station ?? null; })
    .catch(() => { swStations.value = []; });
}

/** Bibliotek-valget for SUB/WAVE når pluginen har stasjoner (lastes i bakgrunnen første gang). */
export function swLibs(): [string, string][] {
  loadSw();
  return swStations.value.length ? [['sw', 'SUB/WAVE']] : [];
}

export async function playSw(i: number): Promise<void> {
  swPlaying.value = i;
  await api.subwavePost({ station: i, play: true });
}
