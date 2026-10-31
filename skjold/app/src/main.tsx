import { render } from 'preact';
import './styles.css';
import { App } from './app';
import { loadSettings, mode, startPolling } from './lib/store';

if (mode.value !== 'find') { startPolling(); void loadSettings(); }
else {
  // Polling starter først når en forsterker er valgt
  const stop = mode.subscribe((m) => { if (m !== 'find') { startPolling(); stop(); } });
}
render(<App />, document.getElementById('app')!);
