// Finn forsterkeren (appen) og oppsettsveiviseren (etter Skjold Oppsett.dc.html).
import { useEffect, useState } from 'preact/hooks';
import { api, CANDIDATE_HOSTS, getBase, normHost, setBase, type Status } from '../lib/api';
import { loadSettings, mode, refresh, setSetting, settings, showToast, status } from '../lib/store';
import { LANGS, NAMES } from '../lib/settings';
import { Logo, S1_ICON, Icon } from '../components/ui';

interface Found { base: string; st: Status }

export function FindDevice() {
  const [found, setFound] = useState<Found[]>([]);
  const [scanning, setScanning] = useState(false);
  const [manual, setManual] = useState('');
  const [err, setErr] = useState('');
  const scan = async () => {
    setScanning(true); setFound([]);
    const cur = getBase();
    const list = [...new Set([...(cur ? [cur] : []), ...CANDIDATE_HOSTS])];
    await Promise.all(list.map(async (b) => {
      try { const st = await api.statusAt(b); setFound((f) => (f.some((x) => x.base === b) ? f : [...f, { base: b, st }])); } catch { /* ikke her */ }
    }));
    setScanning(false);
  };
  useEffect(() => { void scan(); }, []);
  const connect = async (b: string) => {
    setErr('');
    try {
      const st = await api.statusAt(b, 4000);
      setBase(b); status.value = st; await loadSettings(); void refresh();
      mode.value = settings.value.setupDone ? 'app' : 'setup';
    } catch { setErr('Fikk ikke svar fra ' + b.replace(/^https?:\/\//, '') + '. Sjekk at telefonen er på samme Wi-Fi.'); }
  };
  return (
    <div class="setup-shell">
      <div class="setup-col">
        <Logo lg />
        <main>
          <span class="kicker">Koble til</span>
          <h1>Finn Skjold</h1>
          <p class="lead">Telefonen må være på samme Wi-Fi som forsterkeren. Adressen står på skjermen til forsterkeren under oppstart.</p>
          <div class="col gap10">
            {found.map((f) => (
              <button key={f.base} class="opt" style={{ minHeight: '72px' }} onClick={() => connect(f.base)}>
                <span class="row gap12"><Icon d={S1_ICON} size={34} sw={1.1} /><span class="col"><span>{f.st.name || 'Skjold S1'}</span><span class="mono muted" style={{ fontSize: '11px' }}>{f.base.replace(/^https?:\/\//, '')} · v{f.st.version}</span></span></span>
                <span class="mark">Koble til</span>
              </button>
            ))}
            {!found.length && <div class="banner info"><span>{scanning ? 'Leter etter skjold.local …' : 'Fant ingen forsterker automatisk.'}</span></div>}
            <button class="btn" disabled={scanning} onClick={scan}>{scanning ? 'Leter …' : 'Let på nytt'}</button>
          </div>
          <form class="col gap8" onSubmit={(e) => { e.preventDefault(); if (manual.trim()) void connect(normHost(manual)); }}>
            <span class="kicker">Skriv inn adresse</span>
            <input class="field" inputMode="url" autoCapitalize="off" autoCorrect="off" placeholder="skjold.local eller 192.168.1.50" value={manual} onInput={(e) => setManual(e.currentTarget.value)} data-testid="host" />
            <button class="btn primary big" type="submit" disabled={!manual.trim()}>Koble til</button>
          </form>
          {err && <div class="banner bad"><span>{err}</span></div>}
        </main>
      </div>
    </div>
  );
}

const STEPS = ['Språk', 'Wi-Fi', 'Navn', 'Høyttalertest', 'Lyrion', 'Ferdig'];

export function Setup() {
  const [step, setStep] = useState(0);
  const st = settings.value, s = status.value;
  const [nameCustom, setNameCustom] = useState(st.nameCustom);
  const [tested, setTested] = useState<Record<string, string>>({});
  const next = () => setStep((n) => Math.min(STEPS.length - 1, n + 1));
  const finish = () => { setSetting('setupDone', true); mode.value = 'app'; };
  const test = async (ch: 'L' | 'R') => {
    try { await api.speakerTest(ch); setTested((t) => ({ ...t, [ch]: 'ok' })); }
    catch { setTested((t) => ({ ...t, [ch]: 'kommer' })); showToast('Kommer: høyttalertest finnes ikke i API-et ennå'); }
  };
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
            <h1>Velg språk</h1><p class="lead">Brukes for talebeskjeder og på skjermen.</p>
            <div class="col gap8">{LANGS.map((l, i) => <button key={l} class={'opt' + (st.lang === i ? ' on' : '')} onClick={() => setSetting('lang', i)}><span>{l}</span>{st.lang === i && <span class="mark">✓</span>}</button>)}</div>
          </>}
          {step === 1 && <>
            <h1>Wi-Fi</h1>
            <p class="lead">Forsterkeren er allerede på nettet ({s?.name ?? 'Skjold'} svarer). Wi-Fi settes ellers i Skjold Flasher når SD-kortet skrives.</p>
            <div class="banner info"><span><strong>Kommer:</strong> bytte Wi-Fi fra appen krever /api/wifi på forsterkeren.</span></div>
          </>}
          {step === 2 && <>
            <h1>Hvor står den?</h1><p class="lead">Navnet vises i AirPlay, Blåtann og i appen.</p>
            <div class="col gap8">{NAMES.map((n, i) => <button key={n} class={'opt' + (st.name === i && !st.nameCustom ? ' on' : '')} onClick={() => { setSetting('name', i); setSetting('nameCustom', ''); setNameCustom(''); }}><span>{n}</span>{st.name === i && !st.nameCustom && <span class="mark">✓</span>}</button>)}</div>
            <input class="field" placeholder="Eget navn" value={nameCustom} maxLength={24} onInput={(e) => setNameCustom(e.currentTarget.value)} onChange={(e) => setSetting('nameCustom', e.currentTarget.value.trim())} />
          </>}
          {step === 3 && <>
            <h1>Høyttalertest</h1><p class="lead">Trykk på en side. Du skal høre en tone fra riktig høyttaler.</p>
            <div class="row gap12">{(['L', 'R'] as const).map((ch) => <button key={ch} class={'side grow' + (tested[ch] ? ' on' : '')} onClick={() => test(ch)}><span class="k">{ch}</span><span class="l">{ch === 'L' ? 'Venstre' : 'Høyre'}{tested[ch] === 'kommer' ? ' · kommer' : tested[ch] ? ' ✓' : ''}</span></button>)}</div>
          </>}
          {step === 4 && <>
            <h1>Lyrion og radio</h1>
            <p class="lead">Radiofavorittene hentes fra Lyrion Music Server på nettet ditt.</p>
            <div class={'banner ' + (s?.lyrion ? 'ok' : 'warn')}><span>{s?.lyrion ? 'Lyrion er funnet.' : 'Lyrion ble ikke funnet. Radio virker når Lyrion kjører på nettet.'}</span></div>
          </>}
          {step === 5 && <>
            <h1>Klar</h1><p class="lead">{s?.name ?? 'Skjold'} er satt opp. Programvare {s?.version ?? ''}. Du kan endre alt senere under Innstillinger.</p>
          </>}
        </main>
        <button class="btn primary big" onClick={step === STEPS.length - 1 ? finish : next}>{step === STEPS.length - 1 ? 'Ferdig' : 'Neste'}</button>
      </div>
    </div>
  );
}
