# KI Pultforsterker – Homey-app

Installeres som utvikler-app (ikke i App Store):

```bash
npm install -g homey          # Homey CLI
homey login
cd no.kristo.ki-pultforsterker
homey app install             # eller `homey app run` for live-logg
```

Krav: Pi-en i forsterkeren kjører `ki_amp_daemon.py` (port 8765) på samme nett som Homey.

Legg til enhet: Enheter → + → KI Pultforsterker → forsterkeren dukker opp via mDNS. Finner den ikke, sett IP under enhetens innstillinger.

Bildene (forsterkerens front i designfargene) og enhetsikonet `icon.svg` lages av `make_icons.py` (trenger `pip install cairosvg`).
