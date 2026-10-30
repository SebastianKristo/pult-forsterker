import assert from 'assert';
import { execFileSync } from 'child_process';
import { sha512crypt } from '../shared/sha512crypt';
import { buildBootFiles, hostnameFromName, validate } from '../shared/bootconfig';
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
const files = buildBootFiles(o, 'fastsalt');
const names = files.map(f => f.name).sort();
assert.deepStrictEqual(names, ['custom.toml', 'skjold-setup.json', 'ssh', 'userconf.txt']);
const toml = files.find(f => f.name === 'custom.toml')!.content;
assert.ok(toml.includes('ssid = "Hjemme \\"5G\\""'));
assert.ok(toml.includes('hostname = "skjold-stue"'));
const json = JSON.parse(files.find(f => f.name === 'skjold-setup.json')!.content);
assert.strictEqual(json.wifi.ssid, 'Hjemme "5G"');
assert.ok(files.find(f => f.name === 'userconf.txt')!.content.startsWith('skjold:$6$fastsalt$'));
assert.ok(validate({ ...o, wifiPassword: 'kort' }));
assert.ok(validate({ ...o, userPassword: '', sshKey: '' }));
assert.deepStrictEqual(buildBootFiles({ ...o, preset: false, ssh: false }).map(f => f.name).sort(), ['custom.toml', 'skjold-setup.json']);
console.log('alle tester ok');
