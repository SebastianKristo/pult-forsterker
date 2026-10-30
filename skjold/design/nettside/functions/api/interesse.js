// Cloudflare Pages Function: POST /api/interesse
// Lagrer interessemeldinger i KV. Knytt et KV-namespace med navnet INTERESSE i Pages → Settings → Functions → KV bindings.
// Valgfritt: sett miljøvariabelen VARSEL_WEBHOOK (f.eks. Discord/Slack/Homey webhook) for å få beskjed ved nye meldinger.
// Se alle: GET /api/interesse?nokkel=<ADMIN_NOKKEL> (sett ADMIN_NOKKEL som hemmelig variabel).
export async function onRequestPost({ request, env }) {
  let b; try { b = await request.json(); } catch { return new Response('bad json', { status: 400 }); }
  const epost = String(b.epost || '').trim().slice(0, 200), navn = String(b.navn || '').trim().slice(0, 120);
  if (!navn || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(epost)) return new Response('invalid', { status: 422 });
  const rec = { navn, epost, produkt: String(b.produkt || '').slice(0, 20), type: String(b.type || '').slice(0, 20),
    melding: String(b.melding || '').slice(0, 2000), spraak: b.spraak === 'en' ? 'en' : 'no', tid: new Date().toISOString(),
    land: request.headers.get('cf-ipcountry') || '' };
  await env.INTERESSE.put('i:' + rec.tid + ':' + epost.toLowerCase(), JSON.stringify(rec));
  if (env.VARSEL_WEBHOOK) await fetch(env.VARSEL_WEBHOOK, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: `Ny interesse for Skjold ${rec.produkt} (${rec.type}): ${rec.navn} <${rec.epost}> ${rec.melding}` }) }).catch(() => {});
  return Response.json({ ok: true });
}
export async function onRequestGet({ request, env }) {
  const k = new URL(request.url).searchParams.get('nokkel');
  if (!env.ADMIN_NOKKEL || k !== env.ADMIN_NOKKEL) return new Response('forbidden', { status: 403 });
  const list = await env.INTERESSE.list({ prefix: 'i:' }), out = [];
  for (const { name } of list.keys) out.push(JSON.parse(await env.INTERESSE.get(name)));
  return Response.json(out);
}
