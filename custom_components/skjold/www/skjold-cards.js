/* Skjold-kort for Home Assistant-dashbordet (lastes automatisk av integrasjonen).
 *   type: custom:skjold-card       – én Skjold: cover, tittel, kilder, avspilling, volum, radiofavoritter
 *   type: custom:skjold-rom-card   – alle Skjold-enheter: hurtigstyring per rom
 * Bruker bare HA-tjenester (media_player.*), og følger HA-temaet (var(--card-background-color) osv.). */
(() => {
  const ACC = 'var(--skjold-accent, #d9a441)';
  const LOGO = '<svg viewBox="0 0 42 46" fill="currentColor"><rect x="1" y="2" width="4.6" height="22" rx="2.3"/><rect x="9" y="2" width="4.6" height="33" rx="2.3"/><rect x="18.7" y="2" width="4.6" height="42" rx="2.3"/><rect x="28.4" y="2" width="4.6" height="33" rx="2.3"/><rect x="36.4" y="2" width="4.6" height="22" rx="2.3"/></svg>';
  const I = {
    play: 'M8 5v14l11-7z', pause: 'M6 4h4v16H6zM14 4h4v16h-4z', prev: 'M6 5h2v14H6zM20 5v14L9 12z', next: 'M16 5h2v14h-2zM4 5v14l11-7z',
    power: 'M12 3v9M6.3 7.3a8 8 0 1 0 11.4 0', vol: 'M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12', mute: 'M4 9h3l5-4v14l-5-4H4zM16 9l5 6M21 9l-5 6',
  };
  const ico = (d, s = 20, fill = true) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" ${fill ? 'fill="currentColor"' : 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'}><path d="${d}"/></svg>`;
  const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const isSkjold = (st) => st && st.entity_id.startsWith('media_player.') && ['s1', 'node', 'core', 'touch'].includes(st.attributes.product);
  const PNAME = { s1: 'Skjold S1', node: 'Skjold Node', core: 'Skjold Core', touch: 'Skjold Touch' };
  const BASE_CSS = `
    :host { display: block; }
    ha-card { overflow: hidden; position: relative; color: var(--primary-text-color); }
    button { border: 0; background: none; color: inherit; font: inherit; cursor: pointer; padding: 0; -webkit-tap-highlight-color: transparent; }
    button:active { transform: scale(.95); }
    .mut { color: var(--secondary-text-color); } .ell { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    input[type=range] { -webkit-appearance: none; appearance: none; width: 100%; height: 6px; border-radius: 3px; outline: none; margin: 0;
      background: linear-gradient(90deg, ${ACC} var(--p,40%), var(--divider-color, rgba(127,127,127,.3)) var(--p,40%)); }
    input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%; background: var(--primary-text-color); box-shadow: 0 1px 5px rgba(0,0,0,.35); }
    input[type=range]::-moz-range-thumb { width: 20px; height: 20px; border: 0; border-radius: 50%; background: var(--primary-text-color); }
    .art { background: var(--secondary-background-color) center/cover no-repeat; display: flex; align-items: center; justify-content: center; color: var(--secondary-text-color); }
    .chip { flex: none; height: 32px; padding: 0 12px; border-radius: 16px; border: 1px solid var(--divider-color); font-size: 13px; }
    .chip.on { background: var(--primary-text-color); color: var(--card-background-color, #fff); border-color: transparent; }`;

  class SkjoldCard extends HTMLElement {
    setConfig(c) { if (!c.entity) throw new Error('Velg en Skjold-mediaspiller (entity)'); this._c = { favoritter: true, kilder: true, ...c }; this._sig = ''; }
    static getStubConfig(hass) { const e = Object.values(hass.states).find(isSkjold); return { entity: e ? e.entity_id : '' }; }
    static getConfigForm() {
      return { schema: [
        { name: 'entity', required: true, selector: { entity: { domain: 'media_player', integration: 'skjold' } } },
        { name: 'navn', selector: { text: {} } },
        { name: 'kilder', selector: { boolean: {} } }, { name: 'favoritter', selector: { boolean: {} } } ],
        computeLabel: (s) => ({ entity: 'Skjold-enhet', navn: 'Navn (valgfritt)', kilder: 'Vis kilder', favoritter: 'Vis radiofavoritter' }[s.name]) };
    }
    getCardSize() { return this._c && this._c.favoritter ? 7 : 4; }
    set hass(h) {
      this._h = h; const st = h.states[this._c.entity];
      if (!this.shadowRoot) { this.attachShadow({ mode: 'open' }); }
      if (!st) { this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px">Fant ikke ${esc(this._c.entity)}</div></ha-card>`; return; }
      const a = st.attributes, on = st.state !== 'off' && st.state !== 'unavailable', playing = st.state === 'playing';
      const sig = JSON.stringify([st.state, a.media_title, a.media_artist, a.entity_picture, a.source, a.source_list, a.volume_level, a.is_volume_muted, a.presets, a.radio_now && a.radio_now.n]);
      if (sig === this._sig && !this._drag) return; this._sig = sig;
      const img = a.entity_picture || '';
      const vol = Math.round((a.volume_level || 0) * 100);
      const presets = (a.presets || []).slice(0, 12), now = a.radio_now ? a.radio_now.n : 0;
      this.shadowRoot.innerHTML = `<style>${BASE_CSS}
        .bg { position: absolute; inset: -40px; background: center/cover no-repeat; filter: blur(40px) saturate(1.3); opacity: .28; pointer-events: none; }
        .in { position: relative; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
        .top { display: flex; gap: 14px; align-items: center; }
        .art.big { width: 112px; height: 112px; border-radius: 14px; flex: none; box-shadow: 0 8px 24px rgba(0,0,0,.25); } .art.big svg { width: 44px; height: 44px; opacity: .55; }
        .meta { flex: 1; min-width: 0; } .k { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; display: flex; gap: 6px; align-items: center; }
        .dot { width: 7px; height: 7px; border-radius: 50%; background: ${on ? ACC : 'var(--disabled-text-color, #888)'}; }
        .t { font-size: 20px; font-weight: 600; margin-top: 6px; line-height: 1.2; } .a { font-size: 14px; margin-top: 2px; }
        .pw { width: 38px; height: 38px; border-radius: 50%; flex: none; display: flex; align-items: center; justify-content: center; border: 1px solid var(--divider-color); align-self: flex-start; }
        .pw.on { background: ${ACC}; color: #111; border-color: transparent; }
        .ctl { display: flex; align-items: center; justify-content: center; gap: 22px; }
        .pp { width: 54px; height: 54px; border-radius: 50%; background: var(--primary-text-color); color: var(--card-background-color, #fff); display: flex; align-items: center; justify-content: center; }
        .vol { display: flex; align-items: center; gap: 12px; } .vol .n { width: 30px; text-align: right; font-variant-numeric: tabular-nums; }
        .src { display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none; }
        .fav { display: grid; grid-template-columns: repeat(auto-fill, minmax(76px, 1fr)); gap: 8px; }
        .fav button { text-align: left; } .fav .art { aspect-ratio: 1; border-radius: 10px; position: relative; font-size: 12px; font-weight: 600; color: #fff; align-items: flex-end; justify-content: flex-start; padding: 7px; }
        .fav .on .art { box-shadow: inset 0 0 0 2px ${ACC}; } .fav .nr { position: absolute; top: 6px; left: 7px; font-size: 10px; opacity: .8; }
        .fav .lbl { font-size: 11px; margin-top: 4px; }
        h4 { margin: 0; font-size: 13px; font-weight: 600; }</style>
        <ha-card>${img ? `<div class="bg" style="background-image:url('${esc(img)}')"></div>` : ''}<div class="in">
          <div class="top"><div class="art big" style="${img ? `background-image:url('${esc(img)}')` : ''}">${img ? '' : LOGO}</div>
            <div class="meta"><div class="k mut"><span class="dot"></span><span class="ell">${esc(on ? (a.source || '') : 'Standby')}</span></div>
              <div class="t ell">${esc(a.media_title || this._c.navn || a.friendly_name || 'Skjold')}</div><div class="a ell mut">${esc(a.media_artist || a.media_channel || '')}</div></div>
            <button class="pw ${on ? 'on' : ''}" data-a="power" title="Av/på">${ico(I.power, 18, false)}</button></div>
          <div class="ctl"><button data-a="prev" title="Forrige">${ico(I.prev, 24)}</button><button class="pp" data-a="pp" title="Spill/pause">${ico(playing ? I.pause : I.play, 24)}</button><button data-a="next" title="Neste">${ico(I.next, 24)}</button></div>
          <div class="vol"><button data-a="mute" title="Lyd av">${ico(a.is_volume_muted ? I.mute : I.vol, 22, false)}</button><input type="range" min="0" max="100" value="${vol}" style="--p:${vol}%"><span class="n">${vol}</span></div>
          ${this._c.kilder && (a.source_list || []).length ? `<div class="src">${a.source_list.map((s) => `<button class="chip ${s === a.source ? 'on' : ''}" data-src="${esc(s)}">${esc(s)}</button>`).join('')}</div>` : ''}
          ${this._c.favoritter && presets.length ? `<h4>Radiofavoritter</h4><div class="fav">${presets.map((p) => `<button data-n="${p.n}" class="${p.n === now ? 'on' : ''}"><div class="art" style="${p.image && /^https:/.test(p.image) ? `background-image:url('${esc(p.image)}')` : `background:hsl(${(p.n * 47) % 360} 30% 32%)`}"><span class="nr">${p.n}</span>${p.image && /^https:/.test(p.image) ? '' : esc(p.title)}</div><div class="lbl ell mut">${esc(p.title)}</div></button>`).join('')}</div>` : ''}
        </div></ha-card>`;
      const r = this.shadowRoot, e = this._c.entity, call = (svc, data = {}) => this._h.callService('media_player', svc, { entity_id: e, ...data });
      r.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => ({
        power: () => call(on ? 'turn_off' : 'turn_on'), pp: () => call('media_play_pause'), prev: () => call('media_previous_track'),
        next: () => call('media_next_track'), mute: () => call('volume_mute', { is_volume_muted: !a.is_volume_muted }) }[b.dataset.a]())));
      r.querySelectorAll('[data-src]').forEach((b) => b.addEventListener('click', () => call('select_source', { source: b.dataset.src })));
      r.querySelectorAll('[data-n]').forEach((b) => b.addEventListener('click', () => call('play_media', { media_content_type: 'preset', media_content_id: b.dataset.n })));
      const v = r.querySelector('input[type=range]'), n = r.querySelector('.vol .n');
      v.addEventListener('input', () => { this._drag = true; v.style.setProperty('--p', v.value + '%'); n.textContent = v.value; });
      v.addEventListener('change', () => { this._drag = false; call('volume_set', { volume_level: Number(v.value) / 100 }); });
    }
  }

  class SkjoldRomCard extends HTMLElement {
    setConfig(c) { this._c = { tittel: 'Skjold', ...c }; this._sig = ''; }
    static getStubConfig() { return { tittel: 'Skjold' }; }
    static getConfigForm() {
      return { schema: [{ name: 'tittel', selector: { text: {} } },
        { name: 'entities', selector: { entity: { domain: 'media_player', integration: 'skjold', multiple: true } } }],
        computeLabel: (s) => ({ tittel: 'Tittel', entities: 'Enheter (tomt = alle Skjold)' }[s.name]) };
    }
    getCardSize() { return 4; }
    set hass(h) {
      this._h = h; if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
      const list = (this._c.entities && this._c.entities.length ? this._c.entities.map((id) => h.states[id]).filter(Boolean) : Object.values(h.states).filter(isSkjold))
        .sort((x, y) => String(x.attributes.friendly_name).localeCompare(String(y.attributes.friendly_name)));
      const sig = JSON.stringify(list.map((s) => [s.entity_id, s.state, s.attributes.media_title, s.attributes.entity_picture, s.attributes.volume_level, s.attributes.source]));
      if (sig === this._sig || this._drag) return; this._sig = sig;
      const playingAny = list.some((s) => s.state === 'playing');
      this.shadowRoot.innerHTML = `<style>${BASE_CSS}
        .in { padding: 14px 16px; } .hd { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; } .hd b { font-size: 16px; flex: 1; }
        .hd button { font-size: 13px; color: ${ACC}; }
        .rad { display: grid; grid-template-columns: 48px minmax(0,1fr) 40px; gap: 12px; align-items: center; padding: 10px 0; border-top: 1px solid var(--divider-color); }
        .rad:first-of-type { border-top: 0; } .rad.off { opacity: .5; }
        .art { width: 48px; height: 48px; border-radius: 10px; } .art svg { width: 20px; height: 20px; }
        .n { font-size: 14px; font-weight: 600; } .s { font-size: 12px; margin: 2px 0 8px; }
        .pp { width: 40px; height: 40px; border-radius: 50%; background: var(--primary-text-color); color: var(--card-background-color, #fff); display: flex; align-items: center; justify-content: center; }
        input[type=range] { height: 4px; } input[type=range]::-webkit-slider-thumb { width: 16px; height: 16px; }
        .tom { padding: 8px 0; }</style>
        <ha-card><div class="in"><div class="hd"><b>${esc(this._c.tittel)}</b>${playingAny ? '<button data-alle="pause">Pause alle</button>' : ''}</div>
        ${list.length ? list.map((s) => { const a = s.attributes, on = s.state !== 'off' && s.state !== 'unavailable', img = a.entity_picture || '', vol = Math.round((a.volume_level || 0) * 100);
          return `<div class="rad ${on ? '' : 'off'}" data-e="${esc(s.entity_id)}"><div class="art" style="${img ? `background-image:url('${esc(img)}')` : ''}">${img ? '' : LOGO}</div>
          <div style="min-width:0"><div class="n ell">${esc(a.friendly_name || PNAME[a.product] || 'Skjold')}</div>
          <div class="s ell mut">${esc(on ? [a.media_title, a.media_artist || a.source].filter(Boolean).join(' · ') : (s.state === 'unavailable' ? 'Frakoblet' : 'Standby'))}</div>
          <input type="range" min="0" max="100" value="${vol}" style="--p:${vol}%"></div>
          <button class="pp" title="Spill/pause">${ico(s.state === 'playing' ? I.pause : I.play, 18)}</button></div>`; }).join('')
          : '<div class="tom mut">Ingen Skjold-enheter funnet.</div>'}</div></ha-card>`;
      const r = this.shadowRoot;
      r.querySelectorAll('.rad').forEach((row) => {
        const e = row.dataset.e, v = row.querySelector('input');
        row.querySelector('.pp').addEventListener('click', () => h.callService('media_player', 'media_play_pause', { entity_id: e }));
        v.addEventListener('input', () => { this._drag = true; v.style.setProperty('--p', v.value + '%'); });
        v.addEventListener('change', () => { this._drag = false; h.callService('media_player', 'volume_set', { entity_id: e, volume_level: Number(v.value) / 100 }); });
      });
      const pa = r.querySelector('[data-alle]');
      if (pa) pa.addEventListener('click', () => h.callService('media_player', 'media_pause', { entity_id: list.filter((s) => s.state === 'playing').map((s) => s.entity_id) }));
    }
  }

  if (!customElements.get('skjold-card')) customElements.define('skjold-card', SkjoldCard);
  if (!customElements.get('skjold-rom-card')) customElements.define('skjold-rom-card', SkjoldRomCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === 'skjold-card')) {
    window.customCards.push(
      { type: 'skjold-card', name: 'Skjold – Spiller', description: 'Cover, kilder, avspilling, volum og radiofavoritter for én Skjold-enhet.', preview: true },
      { type: 'skjold-rom-card', name: 'Skjold – Alle rom', description: 'Alle Skjold-enheter med spill/pause og volum per rom.', preview: true });
  }
})();
