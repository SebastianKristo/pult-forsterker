import { render } from 'preact';
import './styles.css';
import { App } from './app';
import { go, loadSettings, mode, startPolling } from './lib/store';
import { api } from './lib/api';
import { lang } from './i18n';
import { startHjem } from './lib/hjem';

if (mode.value === 'app' || mode.value === 'setup') { startPolling(); void loadSettings(); void startHjem(); }
else {
  // Polling starter først når en forsterker er valgt
  const stop = mode.subscribe((m) => { if (m === 'app' || m === 'setup') { startPolling(); void startHjem(); stop(); } });
}
// Skjold Touch-skjermen åpner appen med ?kiosk=1
if (new URLSearchParams(location.search).has('kiosk')) {
  document.documentElement.classList.add('kiosk');
  addEventListener('contextmenu', (e) => e.preventDefault());
}
// Hurtigvalg fra PWA-ikonet (manifest «shortcuts»): ?snarvei=spillpause | neste | radio | kassetter
const snarvei = new URLSearchParams(location.search).get('snarvei');
if (snarvei && mode.value === 'app') {
  if (snarvei === 'spillpause') void api.transport('playpause').catch(() => {});
  else if (snarvei === 'neste') void api.transport('next').catch(() => {});
  else if (snarvei === 'radio') go('radio');
  else if (snarvei === 'kassetter') go('kass');
  try { history.replaceState(null, '', location.pathname + location.hash); } catch { /* ignore */ }
}
document.documentElement.lang = lang.value === 'en' ? 'en' : 'no';
render(<App />, document.getElementById('app')!);
