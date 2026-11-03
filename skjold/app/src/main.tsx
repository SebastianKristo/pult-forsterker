import { render } from 'preact';
import './styles.css';
import { App } from './app';
import { loadSettings, mode, startPolling } from './lib/store';
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
render(<App />, document.getElementById('app')!);
