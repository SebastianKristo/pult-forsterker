# Fjernstyring av Skjold – styring.skjold-lab.com

Med Cloudflare Tunnel kan du styre Skjold (web-UI-et på port 8765) fra hvor som helst, uten å åpne porter i ruteren.
`cloudflared` på Pi-en kobler seg ut til Cloudflare, og Cloudflare sender `https://styring.skjold-lab.com`
videre til `http://localhost:8765`. Domenet ligger allerede i Cloudflare, så det trengs ingen DNS-endring utenom dette.

## 1. Lag tunnelen (én gang, i nettleseren)
1. Gå til **Cloudflare dashboard → Zero Trust → Networks → Tunnels → Create a tunnel**.
2. Velg **Cloudflared**, gi den et navn (f.eks. `skjold-node`) og trykk **Save tunnel**.
3. Kopier **tokenet** fra installasjonskommandoen som vises (den lange teksten etter `--token` / `service install`).
4. Under **Public hostnames → Add a public hostname**:
   - Subdomain: `styring` · Domain: `skjold-lab.com`
   - Service: **HTTP** · URL: `localhost:8765`
   - Lagre.

## 2. Beskytt den med innlogging (viktig!)
Uten dette kan alle som kjenner adressen styre Skjold – og se innloggingene til musikktjenestene.
1. **Zero Trust → Access → Applications → Add an application → Self-hosted**.
2. Application domain: `styring.skjold-lab.com`.
3. Policy: **Allow** · Include: **Emails** → din e-post (f.eks. jemtlands@proton.me).
4. Lagre. Første gang du åpner adressen får du en kode på e-post.

## 3. Installer på Pi-en
```bash
cd ~/pult-forsterker && git pull && sudo bash pi/install_fjernstyring.sh <TOKEN>
```
Åpne så https://styring.skjold-lab.com – du får det samme web-UI-et som på `http://<pi>:8765`.

## Flere enheter
Én tunnel per Pi: gi hver sitt vertsnavn (f.eks. `skjold-stue…`, `skjold-kjokken…`) og legg dem i samme Access-applikasjon,
eller bruk én tunnel på den ene Pi-en og legg til flere *public hostnames* som peker på de andres IP (`http://192.168.1.43:8765`).

## Slå av
```bash
sudo cloudflared service uninstall
```
