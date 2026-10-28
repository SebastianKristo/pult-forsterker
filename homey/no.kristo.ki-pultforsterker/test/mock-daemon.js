'use strict';
// Etterligner ki_amp_daemon.py sitt HTTP-API (port 8765) uten Pi. Brukes av testene og av `homey app run` mot PC-en.
const http = require('http');

function createMockDaemon({ port = 0 } = {}) {
  const state = { power: true, input: 'airplay', volume: 30, mute: false, bt_pairing: false,
    loudness: true, loudness_level: 5, playing: false, paused: false, cover: '', voice: true, preset: 0, presets: [{ n: 1, title: 'NRK P1' }, { n: 2, title: 'NRK P3' }, { n: 3, title: '' }, { n: 4, title: '' }, { n: 5, title: '' }, { n: 6, title: '' }], title: '', artist: '' };
  const calls = [];
  const server = http.createServer((req, res) => {
    let buf = '';
    req.on('data', (c) => { buf += c; });
    req.on('end', () => {
      const body = buf ? JSON.parse(buf) : {};
      calls.push({ method: req.method, path: req.url, body });
      const p = req.url;
      if (req.method === 'GET' && p === '/api/cover') {
        if (!state.cover) { res.writeHead(404); return res.end(); }
        res.writeHead(200, { 'Content-Type': 'image/png' }); return res.end(Buffer.from('89504e470d0a1a0a', 'hex'));
      }
      if (req.method === 'GET' && p === '/api/status') { /* bare status */ }
      else if (p === '/api/power') state.power = !!body.on;
      else if (p === '/api/toggle') state.power = !state.power;
      else if (p === '/api/input') { if (!['airplay', 'bt', 'aux', 'usb'].includes(body.input)) return fail(res, 'ukjent kilde'); state.input = body.input; }
      else if (p === '/api/volume') { if (body.volume !== undefined) state.volume = clamp(body.volume); if (body.delta !== undefined) state.volume = clamp(state.volume + body.delta); if (state.volume > 0) state.mute = false; }
      else if (p === '/api/mute') state.mute = !!body.mute;
      else if (p === '/api/transport') {
        const a = body.action;
        if (!['play', 'pause', 'playpause', 'next', 'previous', 'stop'].includes(a)) return fail(res, 'ukjent handling');
        if (!['airplay', 'bt'].includes(state.input)) { res.writeHead(409, { 'Content-Type': 'application/json' }); return res.end(JSON.stringify({ error: 'ingen avspilling på denne kilden' })); }
        if (a === 'play') { state.playing = true; state.paused = false; }
        else if (a === 'pause') { state.playing = false; state.paused = true; }
        else if (a === 'playpause') { state.playing = !state.playing; state.paused = !state.playing; }
        else if (a === 'stop') { state.playing = false; state.paused = false; }
        else { state.title = a === 'next' ? 'Neste låt' : 'Forrige låt'; state.playing = true; }
      }
      else if (p === '/api/preset') {
        const t = (state.presets[body.n - 1] || {}).title;
        if (!t && !body.save) { res.writeHead(409, { 'Content-Type': 'application/json' }); return res.end(JSON.stringify({ error: `radiokanal ${body.n} er ikke lagret` })); }
        if (body.save) state.presets[body.n - 1].title = state.title || 'Lagret';
        state.input = 'radio'; state.preset = body.n; state.playing = true; state.title = state.presets[body.n - 1].title;
      }
      else if (p === '/api/voice') { if (body.on !== undefined) state.voice = !!body.on; }
      else if (p === '/api/bt') state.bt_pairing = !!body.pairing;
      else if (p === '/api/loudness') { if (body.on !== undefined) state.loudness = !!body.on; if (body.level !== undefined) state.loudness_level = Math.max(0, Math.min(10, body.level)); }
      else { res.writeHead(404); return res.end('{}'); }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(state));
    });
  });
  const fail = (res, msg) => { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: msg })); };
  const clamp = (v) => Math.max(0, Math.min(100, Math.round(v)));
  return {
    state, calls, server,
    start: () => new Promise((r) => server.listen(port, '127.0.0.1', () => r(server.address().port))),
    stop: () => new Promise((r) => server.close(() => r())),
  };
}
module.exports = { createMockDaemon };

if (require.main === module) {
  const d = createMockDaemon({ port: Number(process.env.PORT || 8765) });
  d.start().then((p) => console.log(`Mock-daemon på http://127.0.0.1:${p}/api/status – Ctrl-C for å avslutte`));
  setInterval(() => { // simuler avspilling som starter/stopper
    d.state.playing = !d.state.playing; d.state.title = d.state.playing ? 'Midnight City' : ''; d.state.artist = d.state.playing ? 'M83' : '';
  }, 15000);
}
