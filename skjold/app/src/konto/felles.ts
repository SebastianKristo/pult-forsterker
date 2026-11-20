// Felles for konto-siden: API-kall, stiler og meldinger.
export async function kall<T>(metode: string, sti: string, kropp?: unknown): Promise<T> {
  const r = await fetch(sti, { method: metode, credentials: 'include', headers: kropp ? { 'content-type': 'application/json' } : {}, body: kropp ? JSON.stringify(kropp) : undefined });
  const ct = r.headers.get('content-type') || '';
  if (!ct.includes('json')) throw new Error('Logg inn på Skjold-hjem');
  const j = await r.json();
  if (!r.ok) throw Object.assign(new Error(j.feil || j.melding || j.error || 'HTTP ' + r.status), { status: r.status, data: j });
  return j as T;
}
export const S = {
  kort: 'background:var(--kort);border:1px solid var(--kant);border-radius:20px;padding:22px 24px;display:flex;flex-direction:column;gap:12px',
  knapp: 'height:42px;padding:0 18px;border-radius:21px;border:1px solid var(--kant);background:#1b1b1c;cursor:pointer;font-size:14px;font-weight:600',
  gull: 'height:42px;padding:0 20px;border-radius:21px;border:none;background:var(--gull);color:#0b0b0c;cursor:pointer;font-size:14px;font-weight:600',
  felt: 'height:46px;border-radius:12px;border:1px solid var(--kant);background:#101011;padding:0 14px;font-size:15px;width:100%',
  rad: 'display:flex;align-items:center;gap:14px;padding:14px 0;border-top:1px solid #1d1d1f',
  liten: 'font-size:12.5px;color:var(--demp);line-height:1.45'
};
export const melding = { vis: (_t: string) => {} };
export const visMelding = (t: string) => melding.vis(t);
export const tid = (t: number) => (t ? new Date(t * 1000).toLocaleString('nb-NO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '–');
