import assert from 'assert';
import { execFileSync } from 'child_process';
import { sha512crypt } from '../shared/sha512crypt';
import { buildBootFiles, FIRSTRUN_CMDLINE, hostnameFromName, patchCmdline, validate, wpaPsk } from '../shared/bootconfig';
import type { SetupOptions } from '../shared/types';

// Testvektorer fra Drepper sin spesifikasjon
assert.strictEqual(sha512crypt('Hello world!', 'saltstring'),
  '$6$saltstring$svn8UoSVapNtMuq1ukKS4tPQd8iKwSMHWjl/O817G3uBnIFNjnQJuesI68u4OTLiBFdcbYEdFCoEOfaS35inz1');
assert.strictEqual(sha512crypt('Hello world!', 'saltstringsaltstring', 10000),
  '$6$rounds=10000$saltstringsaltst$OW1/O6BYHV6BcXZu8QVeXbDWra3Oeqh0sbHbbMCVNSnCM/UrjmM0Dp8vOuZeHBy/YTBmSK6H9qs/y3RnOaw5v.');
try { // sammenlign med openssl hvis tilgjengelig
  const ref = execFileSync('openssl', ['passwd', '-6', '-salt', 'Ab12./xyz', 'blåbær æøå 123'], { encoding: 'utf8' }).trim();
  assert.strictEqual(sha512crypt('blåbær æøå 123', 'Ab12./xyz'), ref);
  console.log('openssl-sammenligning ok');
} catch (e) { if (e instanceof assert.AssertionError) throw e; console.log('openssl ikke tilgjengelig – hopper over'); }

assert.strictEqual(hostnameFromName('Stue'), 'skjold-stue');
assert.strictEqual(hostnameFromName('Kjøkken & bad'), 'skjold-kjokken-bad');
assert.strictEqual(hostnameFromName(''), 'skjold');

const o: SetupOptions = { device: 's1', preset: true, ssid: 'Hjemme "5G"', wifiPassword: 'hemmelig123', country: 'NO', name: 'Stue',
  hostname: 'skjold-stue', lang: 'nb', ssh: true, user: 'skjold', userPassword: 'passord1', sshKey: '' };
assert.strictEqual(validate(o), null);
const names = (m: 'skjold' | 'systemd' | 'cloudinit', x = o) => buildBootFiles(x, m, 'fastsalt').map(f => f.name).sort();
assert.deepStrictEqual(names('skjold'), ['skjold-setup.json']);
assert.deepStrictEqual(names('systemd'), ['firstrun.sh', 'skjold-install.sh', 'skjold-setup.json']);
assert.deepStrictEqual(names('cloudinit'), ['network-config', 'skjold-install.sh', 'skjold-setup.json', 'user-data']);
assert.deepStrictEqual(names('cloudinit', { ...o, preset: false }), ['skjold-install.sh', 'skjold-setup.json', 'user-data']);
const files = buildBootFiles(o, 'systemd', 'fastsalt');
const fr = files.find(f => f.name === 'firstrun.sh')!.content;
assert.ok(fr.includes("HN='skjold-stue'"));
assert.ok(fr.includes('$6$fastsalt$'));
assert.ok(fr.includes(`psk=${wpaPsk('Hjemme "5G"', 'hemmelig123')}`));
assert.ok(!fr.includes('hemmelig123'));
// WPA-PSK testvektor fra IEEE 802.11i
assert.strictEqual(wpaPsk('IEEE', 'password'), 'f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e');
const json = JSON.parse(files.find(f => f.name === 'skjold-setup.json')!.content);
assert.strictEqual(json.wifi.ssid, 'Hjemme "5G"');
assert.strictEqual(patchCmdline('console=tty1 root=PARTUUID=x rootwait\n', o),
  'console=tty1 root=PARTUUID=x rootwait cfg80211.ieee80211_regdom=NO' + FIRSTRUN_CMDLINE + '\n');
const ud = buildBootFiles(o, 'cloudinit', 'fastsalt').find(f => f.name === 'user-data')!.content;
assert.ok(ud.startsWith('#cloud-config') && ud.includes('skjold-install.service'));
assert.ok(validate({ ...o, wifiPassword: 'kort' }));
assert.ok(validate({ ...o, userPassword: '', sshKey: '' }));
console.log('alle tester ok');
