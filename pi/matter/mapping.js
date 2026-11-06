// Rene mappinger mellom Skjold-daemonens status og Matter-attributter (testes i test/mapping.test.js).
export const FAVORITTER = 6;
export const MAKS_NIVAA = 254;

/** Skjold-volum 0–100 → Matter LevelControl.currentLevel 0–254. */
export function volumTilNivaa(v) {
  const n = Math.round((Math.max(0, Math.min(100, Number(v) || 0)) * MAKS_NIVAA) / 100);
  return n;
}

/** Matter-nivå 0–254 → Skjold-volum 0–100. */
export function nivaaTilVolum(l) {
  return Math.round((Math.max(0, Math.min(MAKS_NIVAA, Number(l) || 0)) * 100) / MAKS_NIVAA);
}

/** Kilder → ModeSelect.supportedModes (mode 0..n-1, label = kildenavn). */
export function kildeModuser(inputs, navn = {}) {
  return (inputs || []).map((id, i) => ({ label: String(navn[id] || id).slice(0, 64), mode: i, semanticTags: [] }));
}

export function kildeTilModus(inputs, input) {
  const i = (inputs || []).indexOf(input);
  return i < 0 ? 0 : i;
}

export function modusTilKilde(inputs, mode) {
  return (inputs || [])[mode] ?? null;
}

/** Status fra /api/status → ønsket Matter-tilstand for alle endepunktene. */
export function statusTilMatter(s) {
  const preset = Number(s.preset) || 0;
  const fav = [];
  for (let n = 1; n <= FAVORITTER; n++) fav.push(!!s.power && preset === n);
  return {
    hoyttaler: { onOff: !!s.power, level: volumTilNivaa(s.volume) },
    demp: !!s.mute,
    favoritter: fav,
    kilde: kildeTilModus(s.inputs, s.input),
  };
}

/** Matter-hendelse → kall mot daemonen ({sti, body}) eller null. */
export function hendelseTilKall(type, verdi, inputs) {
  switch (type) {
    case "onOff": return { sti: "/api/power", body: { on: !!verdi } };
    case "level": return { sti: "/api/volume", body: { volume: nivaaTilVolum(verdi) } };
    case "demp": return { sti: "/api/mute", body: { mute: !!verdi } };
    case "favoritt": return verdi.on ? { sti: "/api/preset", body: { n: verdi.n } } : { sti: "/api/power", body: { on: false } };
    case "kilde": {
      const k = modusTilKilde(inputs, verdi);
      return k ? { sti: "/api/input", body: { input: k } } : null;
    }
    default: return null;
  }
}
