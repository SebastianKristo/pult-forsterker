// Finn forsterkeren (appen) og oppsettsveiviseren (etter Skjold Oppsett.dc.html).
import { useEffect, useState } from 'preact/hooks';
import { cmpVersion, fetchLatestRelease, getBase, needsHost, normHost, PRODUCT_HW, PRODUCT_LABEL, PRODUCT_SHORT, probe, productOf, setBase, type Release } from '../lib/api';
import { loadSettings, mode, product, reconnect, setSetting, settings, status } from '../lib/store';
import { NAMES } from '../lib/settings';
import { Logo, Icon, PRODUCT_ICON } from '../components/ui';
import { remember, scan, type Found } from '../lib/discover';

export function FindDevice() {
  const [found, setFound] = useState<Found[]>([]);
  const [phase, setPhase] = useState('');
  const [scanning, setScanning] = useState(false);
  const [manual, setManual] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState('');
  const [gen, setGen] = useState(0);
  useEffect(() => {
    setFound([]); setScanning(true); setErr('');
    const h = scan((f) => setFound((l) => [...l, f]), setPhase);
    void h.done.finally(() => setScanning(false));
    return () => h.cancel();
  }, [gen]);
  const connect = async (b: string) => {
    setErr(''); setBusy(b);
    const st = await probe(b, 4000);
    setBusy('');
    if (!st) { setErr('Fikk ikke svar fra ' + b.replace(/^https?:\/\//, '') + '. Sjekk at telefonen er på samme Wi-Fi, og at appen har lov til å bruke lokalt nettverk.'); return; }
    setBase(b); remember(b, st); status.value = st; reconnect(); await loadSettings();
    mode.value = settings.value.setupDone ? 'app' : 'setup';
  };
  const hasHost = !!getBase() || !needsHost();
  return (
    <div class="setup-shell">
      <div class="setup-col">
        <div class="row between"><Logo lg />{hasHost && <button class="link" onClick={() => { mode.value = 'app'; }}>Avbryt</button>}</div>
        <main>
          <span class="kicker">Koble til</span>
          <h1>Finn Skjold</h1>
          <p class="lead">Telefonen må være på samme Wi-Fi som enheten. Adressen står også på skjermen under oppstart.</p>
          <div class="col gap10" data-testid="found">
            {found.map((f) => {
              const p = productOf(f.st);
              return (
                <button key={f.base} class="opt" style={{ minHeight: '72px' }} onClick={() => connect(f.base)} disabled={!!busy}>
                  <span class="row gap12" style={{ minWidth: 0 }}><Icon d={PRODUCT_ICON[p]} size={34} sw={1.1} />
                    <span class="col" style={{ minWidth: 0 }}><span class="ellip">{f.st.name || PRODUCT_LABEL[p]}</span>
                      <span class="mono muted ellip" style={{ fontSize: '11px' }}>{PRODUCT_SHORT[p]} · {f.base.replace(/^https?:\/\//, '').replace(/:8765$/, '')} · v{f.st.version}</span></span></span>
                  <span class="mark">{busy === f.base ? '…' : 'Koble til'}</span>
                </button>
              );
            })}
            {(scanning || !found.length) && <div class="banner info"><span>{scanning ? (phase || 'Leter …') : 'Fant ingen enhet automatisk. Skriv inn IP-adressen under.'}</span></div>}
            <button class="btn" disabled={scanning} onClick={() => setGen((g) => g + 1)}>{scanning ? 'Leter …' : 'Let på nytt'}</button>
          </div>
          <form class="col gap8" onSubmit={(e) => { e.preventDefault(); if (manual.trim()) void connect(normHost(manual)); }}>
            <span class="kicker">Skriv inn adresse</span>
            <input class="field" inputMode="url" autoCapitalize="off" autoCorrect="off" placeholder="192.168.1.50" value={manual} onInput={(e) => setManual(e.currentTarget.value)} data-testid="host" />
            <button class="btn primary big" type="submit" disabled={!manual.trim() || !!busy}>Koble til</button>
          </form>
          {err && <div class="banner bad"><span>{err}</span></div>}
        </main>
      </div>
    </div>
  );
}

const STEPS = ['Enhet', 'Wi-Fi', 'Rom', 'Oppdatering'];

export function Setup() {
  const [step, setStep] = useState(0);
  const st = settings.value, s = status.value, p = product.value;
  const [nameCustom, setNameCustom] = useState(st.nameCustom);
  const [rel, setRel] = useState<Release | null | undefined>(undefined);
  const next = () => setStep((n) => Math.min(STEPS.length - 1, n + 1));
  const finish = () => { setSetting('setupDone', true); mode.value = 'app'; };
  useEffect(() => { if (step === 3 && rel === undefined) fetchLatestRelease(st.updChannel === 1).then(setRel).catch(() => setRel(null)); }, [step]);
  const newer = rel && s ? cmpVersion(rel.tag.replace(/^skjold-/, ''), s.version) > 0 : false;
  return (
    <div class="setup-shell">
      <div class="setup-rail">
        <Logo lg />
        <div class="col gap4">
          {STEPS.map((n, i) => <div key={n} class={'rail-step' + (i === step ? ' cur' : i < step ? ' done' : '')}><span class="d">{i < step ? '✓' : i + 1}</span><span>{n}</span></div>)}
        </div>
      </div>
      <div class="setup-col">
        <div class="row between"><span class="kicker">Oppsett · {step + 1} av {STEPS.length}</span>
          {step > 0 ? <button class="link" onClick={() => setStep(step - 1)}>Tilbake</button> : <button class="link" onClick={() => { mode.value = 'app'; }}>Hopp over</button>}</div>
        <div class="dots">{STEPS.map((_, i) => <i key={i} class={i <= step ? 'on' : ''} />)}</div>
        <main>
          {step === 0 && <>
            <h1>Enheten</h1><p class="lead">Appen er koblet til denne enheten.</p>
            <div class="card dev-card">
              <span class="ico"><Icon d={PRODUCT_ICON[p]} size={30} sw={1.2} /></span>
              <span class="col gap4" style={{ minWidth: 0 }}><span class="n ellip">{s?.name ?? PRODUCT_LABEL[p]}</span><span class="hw ellip">{PRODUCT_HW[p]}</span><span class="hw mono">{getBase().replace(/^https?:\/\//, '') || location.host} · v{s?.version ?? '–'}</span></span>
              <span class="type-badge">{PRODUCT_SHORT[p]}</span>
            </div>
            <button class="link" style={{ alignSelf: 'flex-start' }} onClick={() => { mode.value = 'find'; }}>Ikke riktig enhet? Finn en annen</button>
          </>}
          {step === 1 && <>
            <h1>Wi-Fi</h1>
            <p class="lead">{s?.name ?? 'Skjold'} er allerede på nettet og svarer. Wi-Fi settes ellers i Skjold Flasher når SD-kortet skrives.</p>
            <div class="banner ok"><span>Tilkoblet</span></div>
          </>}
          {step === 2 && <>
            <h1>Hvilket rom?</h1><p class="lead">Navnet vises i AirPlay, Blåtann, Spotify og i appen.</p>
            <div class="col gap8">{NAMES.map((n, i) => <button key={n} class={'opt' + (st.name === i && !st.nameCustom ? ' on' : '')} onClick={() => { setSetting('name', i); setSetting('nameCustom', ''); setNameCustom(''); }}><span>{n}</span>{st.name === i && !st.nameCustom && <span class="mark">✓</span>}</button>)}</div>
            <input class="field" placeholder="Eget navn" value={nameCustom} maxLength={24} onInput={(e) => setNameCustom(e.currentTarget.value)} onChange={(e) => setSetting('nameCustom', e.currentTarget.value.trim())} />
          </>}
          {step === 3 && <>
            <h1>Oppdatering</h1><p class="lead">Programvare på enheten: {s?.version ?? '–'}.</p>
            {rel === undefined && <div class="banner info"><span>Ser etter oppdatering …</span></div>}
            {rel === null && <div class="banner info"><span>Fant ingen utgivelser (eller ingen internett). Du kan se etter senere under Innstillinger → Oppdatering.</span></div>}
            {rel && <div class={'banner ' + (newer ? 'warn' : 'ok')}><span><strong>{rel.name}</strong> · {rel.date}<br />{newer ? 'Ny versjon tilgjengelig – Innstillinger → Oppdatering.' : 'Enheten er oppdatert.'}</span></div>}
            <div class="list"><div class="item"><div><div class="n">Oppdater automatisk</div></div><div class="ctl"><button class={'toggle' + (st.updAuto ? ' on' : '')} role="switch" aria-checked={st.updAuto} onClick={() => setSetting('updAuto', !st.updAuto)} /></div></div></div>
          </>}
        </main>
        <button class="btn primary big" onClick={step === STEPS.length - 1 ? finish : next}>{step === STEPS.length - 1 ? 'Ferdig' : 'Neste'}</button>
      </div>
    </div>
  );
}
