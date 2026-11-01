import { render } from 'preact';
import './styles.css';
import { App } from './app';
import { loadSettings, mode, startPolling } from './lib/store';

if (mode.value === 'app' || mode.value === 'setup') { startPolling(); void loadSettings(); }
else {
  // Polling starter først når en forsterker er valgt
  const stop = mode.subscribe((m) => { if (m === 'app' || m === 'setup') { startPolling(); stop(); } });
}
render(<App />, document.getElementById('app')!);
