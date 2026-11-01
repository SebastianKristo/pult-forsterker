import assert from 'assert';
import { execFileSync } from 'child_process';
import { sha512crypt } from '../shared/sha512crypt';
import { buildBootFiles, ethKeyfile, ethNetworkConfig, FIRSTRUN_CMDLINE, hostnameFromName, isIPv4, parseCidr, patchCmdline, patchConfigTxt, validate, validateStatic, wpaPsk } from '../shared/bootconfig';
import { mediaKind } from '../shared/drivefilter';
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
assert.strictEqual(JSON.parse(buildBootFiles({ ...o, lyrionServer: true }, 'systemd', 'x').find(f => f.name === 'skjold-setup.json')!.content).lyrion_server, true);
assert.ok(buildBootFiles(o, 'systemd', 'x').find(f => f.name === 'skjold-install.sh')!.content.includes('install_lyrion.sh'));

// --- Fast IP / Ethernet ---
assert.ok(isIPv4('192.168.1.1') && !isIPv4('256.1.1.1') && !isIPv4('1.2.3') && !isIPv4('01.2.3.4') && !isIPv4('a.b.c.d'));
assert.deepStrictEqual(parseCidr('192.168.1.50/24'), { ip: '192.168.1.50', prefix: 24 });
assert.deepStrictEqual(parseCidr(' 10.0.0.5 '), { ip: '10.0.0.5', prefix: 24 });
for (const bad of ['192.168.1.50/33', '192.168.1.50/0', '127.0.0.1/8', '0.0.0.0', '224.0.0.1', '192.168.1', '192.168.1.50/']) assert.strictEqual(parseCidr(bad), null, bad);
assert.strictEqual(validateStatic({ ip: '192.168.1.50/24', gw: '192.168.1.1', dns: '1.1.1.1, 8.8.8.8' }), null);
assert.ok(validateStatic({ ip: '192.168.1.300/24', gw: '', dns: '' }));
assert.ok(validateStatic({ ip: '192.168.1.50/24', gw: 'ruter', dns: '' }));
assert.ok(validateStatic({ ip: '192.168.1.50/24', gw: '', dns: '1.1.1' }));
const eth: SetupOptions = { ...o, net: 'eth', ssid: '', wifiPassword: '', staticIp: { ip: '192.168.1.50/24', gw: '192.168.1.1', dns: '1.1.1.1 8.8.8.8' } };
assert.strictEqual(validate(eth), null);                          // Ethernet trenger ikke SSID/passord
assert.ok(validate({ ...eth, staticIp: { ip: '192.168.1.50/40', gw: '', dns: '' } }));
assert.strictEqual(validate({ ...eth, staticIp: null }), null);    // DHCP
const ethJson = JSON.parse(buildBootFiles(eth, 'skjold').find(f => f.name === 'skjold-setup.json')!.content);
assert.strictEqual(ethJson.net, 'eth');
assert.deepStrictEqual(ethJson.static, { ip: '192.168.1.50/24', gw: '192.168.1.1', dns: '1.1.1.1,8.8.8.8' });
assert.strictEqual(ethJson.wifi, undefined);
assert.strictEqual(JSON.parse(buildBootFiles({ ...eth, staticIp: null }, 'skjold')[0].content).static, null);
const wifiJson = JSON.parse(buildBootFiles(o, 'skjold')[0].content);
assert.strictEqual(wifiJson.net, 'wifi'); assert.strictEqual(wifiJson.ssid, 'Hjemme "5G"'); assert.strictEqual(wifiJson.psk, 'hemmelig123');
assert.strictEqual(wifiJson.static, null); assert.ok(wifiJson.wifi);
const kf = ethKeyfile(eth.staticIp!);
assert.ok(kf.includes('type=ethernet') && kf.includes('interface-name=eth0') && kf.includes('method=manual'));
assert.ok(kf.includes('address1=192.168.1.50/24,192.168.1.1\n') && kf.includes('dns=1.1.1.1;8.8.8.8;\n'));
assert.ok(ethKeyfile({ ip: '10.0.0.9', gw: '', dns: '' }).includes('address1=10.0.0.9/24\n'));
assert.ok(ethKeyfile({ ip: '10.0.0.9/16', gw: '10.0.0.1', dns: '' }).includes('dns=10.0.0.1;'));   // DNS faller tilbake til ruteren
const frEth = buildBootFiles(eth, 'systemd', 'x').find(f => f.name === 'firstrun.sh')!.content;
assert.ok(frEth.includes('skjold-eth.nmconnection') && frEth.includes('address1=192.168.1.50/24,192.168.1.1'));
assert.ok(!frEth.includes('skjold-wifi.nmconnection'));
assert.ok(!buildBootFiles({ ...eth, staticIp: null }, 'systemd', 'x').find(f => f.name === 'firstrun.sh')!.content.includes('skjold-eth'));
assert.ok(!fr.includes('skjold-eth'));
assert.strictEqual(patchCmdline('a rootwait\n', eth), 'a rootwait' + FIRSTRUN_CMDLINE + '\n');   // ingen Wi-Fi-regdom
const nc = buildBootFiles(eth, 'cloudinit', 'x').find(f => f.name === 'network-config')!.content;
assert.strictEqual(nc, ethNetworkConfig(eth.staticIp!));
assert.ok(nc.includes('ethernets:') && nc.includes('dhcp4: false') && nc.includes('- "192.168.1.50/24"') && nc.includes('via: "192.168.1.1"')
  && nc.includes('nameservers:') && nc.includes('- "8.8.8.8"') && !nc.includes('wifis'));
const ncDhcp = buildBootFiles({ ...eth, staticIp: null }, 'cloudinit', 'x').find(f => f.name === 'network-config')!.content;
assert.ok(ncDhcp.includes('eth0:') && ncDhcp.includes('dhcp4: true') && !ncDhcp.includes('addresses'));
assert.ok(buildBootFiles(o, 'cloudinit', 'x').find(f => f.name === 'network-config')!.content.includes('wifis:'));

// --- Lagringstype og USB-oppstart ---
const dk = (x: Partial<Parameters<typeof mediaKind>[0]>) => mediaKind({ device: '/dev/sdb', description: '', busType: 'USB', isCard: null, isUSB: true, ...x } as Parameters<typeof mediaKind>[0]);
assert.strictEqual(dk({ isCard: true as unknown as null }), 'sd');
assert.strictEqual(dk({ device: '/dev/mmcblk0' }), 'sd');
assert.strictEqual(dk({ description: 'Generic- SD/MMC' }), 'sd');
assert.strictEqual(dk({ description: 'Apple SDXC Reader Media' }), 'sd');
assert.strictEqual(dk({ description: 'Samsung Flash Drive' }), 'usb');
assert.strictEqual(dk({ description: 'Samsung PSSD T7' }), 'usb');
const pi3 = { ...o, device: 'node-pi3' as const };
assert.ok(patchConfigTxt('dtparam=audio=on\n', pi3).includes('[pi3]\nprogram_usb_boot_mode=1\n[all]'));
assert.strictEqual(patchConfigTxt('x\n', o), 'x\n');                           // Pi 4
assert.strictEqual(patchConfigTxt('x\n', { ...pi3, media: 'usb' }), 'x\n');    // skrives til USB: ingen vits
assert.strictEqual(patchConfigTxt('program_usb_boot_mode=1\n', pi3), 'program_usb_boot_mode=1\n');
console.log('alle tester ok');
