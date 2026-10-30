"""Første oppstart: hotspot, captive portal og QR-koder på skjermen."""
import json, secrets, subprocess, pathlib, time
from . import display, bus

BOOT_CFG = pathlib.Path('/boot/firmware/skjold-setup.json')
DONE = pathlib.Path('/etc/skjold/setup-done')

def nmcli(*a): return subprocess.run(['nmcli', *a], check=True, capture_output=True, text=True).stdout

def serial_suffix():
    return pathlib.Path('/proc/device-tree/serial-number').read_text().strip('\x00')[-4:].upper()

def start_hotspot():
    ssid, pw = f'Skjold-Oppsett-{serial_suffix()}', secrets.token_urlsafe(6)[:8]
    nmcli('dev', 'wifi', 'hotspot', 'ifname', 'wlan0', 'ssid', ssid, 'password', pw)
    # dnsmasq i NetworkManager-delt modus: alle DNS-oppslag -> 10.42.0.1 (captive portal)
    pathlib.Path('/etc/NetworkManager/dnsmasq-shared.d/skjold.conf').write_text('address=/#/10.42.0.1\n')
    return ssid, pw

def connect(ssid, pw):
    nmcli('dev', 'wifi', 'connect', ssid, 'password', pw, 'ifname', 'wlan0')
    return nmcli('-g', 'IP4.ADDRESS', 'dev', 'show', 'wlan0').split('/')[0].strip()

def main():
    if BOOT_CFG.exists():                       # forhåndsinnstilt av Skjold Flasher
        c = json.loads(BOOT_CFG.read_text()); BOOT_CFG.unlink()
        ip = connect(c['wifi']['ssid'], c['wifi']['password'])
        bus.save_config({k: c[k] for k in ('name', 'lang') if k in c})
        display.show('setup_done', ip=ip, name=c.get('name', 'Skjold S1')); DONE.touch(); return
    ssid, pw = start_hotspot()
    display.show('setup_join', qr=f'WIFI:T:WPA;S:{ssid};P:{pw};;', ssid=ssid, pw=pw)
    for ev in bus.events():                     # fra skjold-web / skjold-improv
        if ev['type'] == 'client':  display.show('setup_open', qr='http://10.42.0.1/oppsett', ip='10.42.0.1')
        if ev['type'] == 'step':    display.show('setup_step', step=ev['step'], total=6)
        if ev['type'] == 'test':    subprocess.run(['speaker-test', '-D', 'skjold', '-t', 'wav', '-c', '2', '-s', '1' if ev['ch'] == 'L' else '2', '-l', '1'])
        if ev['type'] == 'wifi':
            ip = connect(ev['ssid'], ev['password']); bus.reply({'ok': True, 'ip': ip})
        if ev['type'] == 'done':
            nmcli('con', 'down', 'Hotspot'); DONE.touch()
            display.show('setup_done', ip=ev['ip'], name=ev['name']); return

if __name__ == '__main__': main()
