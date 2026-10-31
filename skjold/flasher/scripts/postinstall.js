// Bygger native moduler (drivelist, mountutils …) for Electron. electron-builder gjør dette uansett ved `npm run dist`,
// så en feil her (f.eks. uten nett til Electron-headere) skal ikke stoppe `npm install`.
const { spawnSync } = require('child_process');
const r = spawnSync(process.platform === 'win32' ? 'npx.cmd' : 'npx', ['electron-builder', 'install-app-deps'], { stdio: 'inherit', shell: process.platform === 'win32' });
if (r.status !== 0) {
  console.warn('\n[skjold-flasher] ADVARSEL: electron-builder install-app-deps feilet. `npm start` kan mangle native moduler;');
  console.warn('[skjold-flasher] kjør `npm run rebuild` når du har nett. `npm run dist` bygger dem på nytt uansett.\n');
}
