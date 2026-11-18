"""Oppsett-nett: når en Skjold-enhet ikke har nett, lager den sitt eget Wi-Fi med en oppsettside.

Slik virker det:
1. Enheten har verken nettverkskabel eller et Wi-Fi den får koblet til (ny enhet, tilbakestilt, eller flyttet).
2. Den starter et aksesspunkt «Skjold-oppsett-XXXX» (NetworkManager hotspot, WPA2) og svarer på alle DNS-oppslag med
   sin egen adresse, så telefonen åpner oppsettsiden av seg selv (fanget portal).
3. På siden velger du hjemmenettet og skriver passordet. Enheten slår av oppsett-nettet og kobler til.
   Går det ikke, kommer oppsett-nettet tilbake med feilmeldingen.

Alt går gjennom `nmcli`. Kommandoene kjøres via `run`, så logikken kan testes uten maskinvare.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time

CON = "skjold-oppsett"                       # navnet på tilkoblingen i NetworkManager
PASSWORD = "skjoldoppsett"                   # likt på alle enheter: står i veiledningen og på skjermen
IP = "10.42.0.1"                             # NetworkManager sin faste adresse for delt nett
DNS_CONF = "/etc/NetworkManager/dnsmasq-shared.d/skjold-oppsett.conf"
BOOT_GRACE_S = 45                            # gi vanlig Wi-Fi tid til å koble til etter oppstart
OFFLINE_S = 180                              # har enheten lagrede nett, venter vi så lenge uten nett før oppsett-nettet
RETRY_S = 300                                # med lagrede nett: slå av oppsett-nettet så ofte for å prøve dem igjen
MANUAL_S = 900                               # oppsett-nett startet for hånd: slås av etter så lang tid uten bruk
IDLE_S = 120                                 # … men ikke mens noen bruker oppsettsiden
KABEL_S = 600                                # «Bruk kabel» på Touch: vent så lenge på Ethernet før oppsett-nettet kommer igjen


def ssid_for(device_id: str) -> str:
    tail = "".join(c for c in str(device_id) if c.isalnum())[-4:].upper() or "0000"
    return "Skjold-oppsett-" + tail


def wifi_qr(ssid: str, password: str) -> str:
    """Teksten i QR-koden som kobler en telefon til nettet (samme format som på rutere)."""
    esc = lambda s: "".join("\\" + c if c in '\\;,:"' else c for c in s)
    return f"WIFI:T:WPA;S:{esc(ssid)};P:{esc(password)};;"


def parse_devices(out: str) -> list:
    """`nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device` → [{device, type, state, connection}]."""
    res = []
    for line in out.splitlines():
        p = line.replace("\\:", "\0").split(":")
        if len(p) >= 4:
            res.append({"device": p[0], "type": p[1], "state": p[2], "connection": ":".join(p[3:]).replace("\0", ":")})
    return res


class SetupNet:
    def __init__(self, ctx: dict, run=subprocess.run, clock=time.time, sleep=time.sleep):
        """ctx: device_id() -> str, changed(), scan() -> [{ssid, signal, security}], port (int)."""
        self.ctx, self.run, self.clock, self.sleep = ctx, run, clock, sleep
        self.active = False
        self.t_boot = clock()
        self.t_offline = 0.0          # når vi først så at nettet var borte
        self.t_start = 0.0
        self.t_hit = 0.0              # sist noen åpnet oppsettsiden
        self.error = ""               # siste mislykkede tilkobling, vises på siden
        self.joining = ""             # nettet vi prøver å koble til akkurat nå
        self.networks: list = []      # skannet rett før aksesspunktet startet (radioen kan ikke alltid skanne etterpå)
        self.manual = False           # startet fra Touch/appen («Koble til nytt Wi-Fi»), ikke fordi nettet var borte
        self.kabel_til = 0.0          # «Bruk kabel» valgt: oppsett-nettet er av, og vi venter på Ethernet til dette tidspunktet
        self.lock = threading.RLock()

    # --- nmcli
    def _nm(self, *args, timeout=20):
        try:
            r = self.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout or ""), (r.stderr or "")
        except FileNotFoundError:
            return 127, "", "nmcli finnes ikke"
        except subprocess.TimeoutExpired:
            return 124, "", "tidsavbrudd"

    def devices(self) -> list:
        return parse_devices(self._nm("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device")[1])

    def wifi_dev(self) -> str:
        return next((d["device"] for d in self.devices() if d["type"] == "wifi"), "")

    def online(self) -> bool:
        """Har enheten et vanlig nett (kabel eller Wi-Fi som ikke er vårt eget oppsett-nett)?"""
        return any(d["type"] in ("wifi", "ethernet") and d["state"].startswith("connected") and d["connection"] != CON
                   for d in self.devices())

    def ethernet(self) -> dict | None:
        """Ethernet-porten, hvis enheten har en: {device, state}. state fra nmcli: unavailable (ingen kabel),
        connecting (…) (kabel, henter adresse), connected, disconnected."""
        d = next((d for d in self.devices() if d["type"] == "ethernet"), None)
        return {"device": d["device"], "state": d["state"]} if d else None

    def bruk_kabel(self, on: bool = True):
        """Touch: «Bruk kabel». Slår av oppsett-nettet og venter på Ethernet i KABEL_S sekunder (av = oppsett-nettet igjen)."""
        if on:
            with self.lock:
                self.kabel_til, self.error = self.clock() + KABEL_S, ""
            self.stop()
            dev = (self.ethernet() or {}).get("device")
            if dev:
                self._nm("device", "connect", dev)       # be NetworkManager prøve kabelen med en gang
        else:
            with self.lock:
                self.kabel_til = 0.0
            self.start()
        self.ctx["changed"]()

    def has_profiles(self) -> bool:
        out = self._nm("-t", "-f", "TYPE,NAME", "connection", "show")[1]
        return any(l.startswith("802-11-wireless:") and l.split(":", 1)[1] != CON for l in out.splitlines())

    # --- av og på
    def ssid(self) -> str:
        return ssid_for(self.ctx["device_id"]())

    def start(self) -> bool:
        with self.lock:
            dev = self.wifi_dev()
            if not dev:
                return False
            # skann grundig før radioen blir aksesspunkt (etterpå ser den som regel bare seg selv); prøv igjen hvis tomt
            nets = []
            for _ in range(3):
                try:
                    nets = [n for n in (self.ctx["scan"]() or []) if not str(n.get("ssid", "")).startswith("Skjold-oppsett-")]
                except Exception:
                    nets = []
                if nets:
                    break
                self.sleep(3)
            if nets or not self.networks:
                self.networks = nets   # behold forrige liste hvis denne skanningen ble tom
            try:      # alle navn peker hit, så telefonen ser en «logg inn på nettverket»-side
                os.makedirs(os.path.dirname(DNS_CONF), exist_ok=True)
                with open(DNS_CONF, "w") as f:
                    f.write(f"# Skjold oppsett-nett: fanget portal\naddress=/#/{IP}\n")
            except OSError as e:
                print("Oppsett-nett: fikk ikke skrevet DNS-oppsettet:", e, flush=True)
            self._nm("connection", "delete", CON)
            code, _, err = self._nm("device", "wifi", "hotspot", "ifname", dev, "con-name", CON, "ssid", self.ssid(),
                                    "password", PASSWORD, timeout=30)
            if code:
                print("Oppsett-nett: kunne ikke starte:", err.strip()[:160], flush=True)
                return False
            self._nm("connection", "modify", CON, "connection.autoconnect", "no")
            self.active, self.t_start, self.t_hit, self.joining = True, self.clock(), 0.0, ""
            print(f"Oppsett-nett «{self.ssid()}» er på – åpne http://{IP}:{self.ctx.get('port', 8765)}/oppsett", flush=True)
        self.ctx["changed"]()
        return True

    def stop(self):
        with self.lock:
            was = self.active
            self._nm("connection", "down", CON)
            self._nm("connection", "delete", CON)
            try:
                os.unlink(DNS_CONF)
            except OSError:
                pass
            self.active = False
            self.manual = False
        if was:
            self.ctx["changed"]()

    # --- koble til hjemmenettet fra oppsettsiden
    def connect(self, ssid: str, psk: str = "", hidden: bool = False) -> bool:
        """Slår av oppsett-nettet og kobler til. Mislykkes det, kommer oppsett-nettet tilbake med feilmeldingen."""
        with self.lock:
            self.joining, self.error = ssid, ""
        self.ctx["changed"]()
        self.sleep(2)                      # la svaret til telefonen gå ut før nettet forsvinner
        self.stop()
        self.sleep(2)
        cmd = ["device", "wifi", "connect", ssid] + (["password", psk] if psk else []) + (["hidden", "yes"] if hidden else [])
        code, out, err = self._nm(*cmd, timeout=45)
        ok = code == 0
        with self.lock:
            self.joining = ""
            if ok:
                self.t_offline = 0.0
            else:
                msg = (err or out or "").strip()
                self.error = ("Feil passord for «%s»." % ssid) if ("Secrets were required" in msg or "802-1x" in msg or "password" in msg.lower()) \
                    else ("Fikk ikke koblet til «%s». Sjekk at nettet er i nærheten." % ssid)
                self._nm("connection", "delete", "id", ssid)        # ikke la et nett med feil passord bli liggende
        if ok:
            print(f"Oppsett-nett: koblet til «{ssid}»", flush=True)
        else:
            print(f"Oppsett-nett: fikk ikke koblet til «{ssid}» – starter oppsett-nettet igjen", flush=True)
            self.start()
        self.ctx["changed"]()
        return ok

    def start_manual(self) -> bool:
        """Start oppsett-nettet på forespørsel (også når enheten er på nett), så telefonen kan velge et nytt Wi-Fi."""
        ok = self.start()
        if ok:
            with self.lock:
                self.manual, self.t_hit = True, self.clock()
        return ok

    def connect_async(self, ssid: str, psk: str = "", hidden: bool = False):
        threading.Thread(target=self.connect, args=(ssid, psk, hidden), daemon=True).start()

    def hit(self):
        self.t_hit = self.clock()

    # --- kalles jevnlig (hvert 10.–20. sekund)
    def decide(self, now: float, online: bool, profiles: bool) -> str:
        """Hva skal skje nå? «start», «stop» eller «». Ren funksjon av tilstanden, for testing."""
        if self.joining:
            return ""
        if self.kabel_til and not self.active:   # venter på kabel (valgt på Touch)
            if online or now >= self.kabel_til:
                self.kabel_til = 0.0
                if online:
                    self.t_offline = 0.0
                    return ""
                self.t_offline = now - OFFLINE_S      # ingen kabel kom: oppsett-nettet igjen med en gang
            else:
                return ""
        if self.active:
            if self.manual:   # startet for hånd: stå til noen kobler til, eller 15 min uten at siden er i bruk
                return "stop" if now - max(self.t_start, self.t_hit) > MANUAL_S else ""
            if online:
                return "stop"                                  # kabel satt i, eller koblet til på annen måte
            if profiles and now - self.t_start > RETRY_S and now - self.t_hit > IDLE_S:
                return "stop"                                  # prøv de lagrede nettene igjen (ruteren var kanskje bare nede)
            return ""
        if online:
            self.t_offline = 0.0
            return ""
        if now - self.t_boot < BOOT_GRACE_S:
            return ""
        if not self.t_offline:
            self.t_offline = now
        if not profiles or now - self.t_offline >= OFFLINE_S:
            return "start"
        return ""

    def tick(self):
        try:
            act = self.decide(self.clock(), self.online(), self.has_profiles())
        except Exception as e:
            print("Oppsett-nett:", e, flush=True)
            return
        if act == "start":
            self.start()
        elif act == "stop":
            self.stop()
            self.t_offline = self.clock()      # tell ventetiden på nytt før oppsett-nettet eventuelt kommer tilbake

    def status(self) -> dict | None:
        if not (self.active or self.joining or self.error or self.kabel_til):
            return None
        port = self.ctx.get("port", 8765)
        return {"active": self.active, "manual": self.manual, "ssid": self.ssid(), "password": PASSWORD, "ip": IP, "url": f"http://{IP}:{port}/oppsett",
                "qr": wifi_qr(self.ssid(), PASSWORD), "joining": self.joining, "error": self.error,
                "kabel": bool(self.kabel_til), "ethernet": self.ethernet()}


PAGE = """<!doctype html>
<html lang="nb"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sett opp Skjold</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23151516'/%3E%3Crect x='17.36' y='15.20' width='3.68' height='17.60' rx='1.84' fill='%23f2f2ee'/%3E%3Crect x='23.76' y='15.20' width='3.68' height='26.40' rx='1.84' fill='%23f2f2ee'/%3E%3Crect x='30.16' y='15.20' width='3.68' height='33.60' rx='1.84' fill='%23d9a441'/%3E%3Crect x='36.56' y='15.20' width='3.68' height='26.40' rx='1.84' fill='%23f2f2ee'/%3E%3Crect x='42.96' y='15.20' width='3.68' height='17.60' rx='1.84' fill='%23f2f2ee'/%3E%3C/svg%3E">
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0b0b0c;color:#f2f2ee;font:16px/1.5 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:460px;margin:0 auto;padding:28px 18px 40px}
.merke{display:flex;gap:4px;align-items:flex-end;height:30px;margin-bottom:18px}
.merke i{width:5px;border-radius:3px;background:#f0c46a}
h1{font-size:26px;line-height:1.15;margin:0 0 6px;font-weight:600;letter-spacing:-.01em}
p{margin:0 0 18px;color:#a8a8a3}
.liste{display:flex;flex-direction:column;border:1px solid #242426;border-radius:14px;background:#141415;overflow:hidden}
.nett{display:flex;align-items:center;gap:12px;min-height:54px;padding:0 16px;border:0;border-top:1px solid #1f1f21;background:none;color:inherit;font:inherit;text-align:left;width:100%;cursor:pointer}
.nett:first-child{border-top:0}
.nett[aria-pressed=true]{background:#1c170d;color:#f0c46a}
.nett span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nett small{color:#8b8b86;font-size:12px}
label{display:block;margin:20px 0 6px;font-size:14px;color:#c9c9c4}
input{width:100%;height:50px;border-radius:12px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;font:inherit;padding:0 14px}
input:focus{outline:2px solid #f0c46a;outline-offset:1px}
.knapp{width:100%;height:54px;margin-top:20px;border:0;border-radius:27px;background:#f0c46a;color:#0b0b0c;font:inherit;font-weight:600;cursor:pointer}
.knapp:disabled{background:#2a2a2c;color:#6b6b67;cursor:default}
.lenke{display:block;margin:14px auto 0;border:0;background:none;color:#a8a8a3;font:inherit;font-size:14px;text-decoration:underline;cursor:pointer;min-height:44px}
.feil{margin:0 0 16px;padding:12px 14px;border-radius:12px;border:1px solid #7a2a20;background:rgba(224,90,74,.1);color:#f2a99f}
.ok{padding:16px;border-radius:14px;border:1px solid #242426;background:#141415}
.ok b{display:block;font-size:18px;margin-bottom:6px;color:#f2f2ee}
code{font:14px ui-monospace,Menlo,monospace;color:#f0c46a;word-break:break-all}
</style></head><body><main>
<div class="merke"><i style="height:16px"></i><i style="height:23px"></i><i style="height:30px"></i><i style="height:23px"></i><i style="height:16px"></i></div>
<div id="velg">
<h1>Koble Skjold til Wi-Fi</h1>
<p>Velg hjemmenettet ditt og skriv passordet. Etterpå finner du enheten i Skjold-appen.</p>
<div id="feil" class="feil" hidden></div>
<div class="liste" id="liste"><div class="nett"><span>Leter etter nett …</span></div></div>
<label for="ssid">Nettverksnavn</label><input id="ssid" autocomplete="off" autocapitalize="none" spellcheck="false">
<label for="psk">Passord</label><input id="psk" type="password" autocomplete="off" autocapitalize="none" spellcheck="false">
<button class="knapp" id="koble" disabled>Koble til</button>
<button class="lenke" id="igjen">Søk etter nett på nytt</button>
</div>
<div id="ferdig" class="ok" hidden>
<b>Kobler til …</b>
<span id="ftxt"></span>
</div>
<noscript><p>Siden trenger JavaScript. Du kan også koble til i Skjold-appen.</p></noscript>
<script>
(function(){
var $=function(i){return document.getElementById(i)},liste=$('liste'),ssid=$('ssid'),psk=$('psk'),koble=$('koble'),feil=$('feil');
function sjekk(){koble.disabled=!ssid.value.trim()}
function vis(n){
  liste.textContent='';
  if(!n.length){var d=document.createElement('div');d.className='nett';d.innerHTML='<span>Fant ingen nett. Skriv navnet under.</span>';liste.appendChild(d);return}
  n.forEach(function(x){var b=document.createElement('button');b.type='button';b.className='nett';b.setAttribute('aria-pressed','false');
    var s=document.createElement('span');s.textContent=x.ssid;var m=document.createElement('small');m.textContent=(x.security==='open'?'Åpent · ':'')+x.signal+' %';
    b.appendChild(s);b.appendChild(m);
    b.onclick=function(){[].forEach.call(liste.children,function(c){c.setAttribute('aria-pressed','false')});b.setAttribute('aria-pressed','true');ssid.value=x.ssid;sjekk();psk.focus()};
    liste.appendChild(b)});
}
function hent(){fetch('/api/wifi').then(function(r){return r.json()}).then(function(j){
  var sett={},n=(j.networks||[]).filter(function(x){if(!x.ssid||sett[x.ssid]||/^Skjold-oppsett-/.test(x.ssid))return false;sett[x.ssid]=1;return true});
  n.sort(function(a,b){return b.signal-a.signal});vis(n)}).catch(function(){vis([])})}
fetch('/api/oppsett').then(function(r){return r.json()}).then(function(j){if(j.error){feil.textContent=j.error;feil.hidden=false}}).catch(function(){});
ssid.oninput=sjekk;$('igjen').onclick=hent;
koble.onclick=function(){koble.disabled=true;koble.textContent='Kobler til …';
  fetch('/api/wifi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:ssid.value.trim(),psk:psk.value})})
   .then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j}})}).then(function(x){
     if(!x.ok){feil.textContent=x.j.error||'Fikk ikke koblet til.';feil.hidden=false;koble.disabled=false;koble.textContent='Koble til';return}
     $('velg').hidden=true;$('ferdig').hidden=false;
     $('ftxt').innerHTML='Skjold slår av oppsett-nettet og kobler til «'+ssid.value.trim().replace(/[<>&]/g,'')+'». Koble telefonen tilbake til hjemmenettet og åpne Skjold-appen, eller gå til <code>http://__NAVN__.local:__PORT__</code>.<br><br>Kommer nettet «__SSID__» tilbake om et minutt, var passordet feil. Koble til det igjen og prøv på nytt.';
   }).catch(function(){$('velg').hidden=true;$('ferdig').hidden=false;$('ftxt').textContent='Skjold kobler til. Koble telefonen tilbake til hjemmenettet og åpne Skjold-appen.'})};
hent();
})();
</script>
</main></body></html>
"""


def page(hostname: str, ssid: str, port: int = 8765) -> str:
    safe = "".join(c for c in hostname if c.isalnum() or c in "-.") or "skjold"
    return PAGE.replace("__NAVN__", safe).replace("__SSID__", ssid.replace("<", "").replace(">", "")).replace("__PORT__", str(port))
