# Skjold – siste endringer (oppgave for Claude Code)

**Fast regel:** Mobilappen og web-UI-et skal være **piksel-identiske** med designfilene `app/Skjold App v2.dc.html` og `web/Skjold S1 Web v3.dc.html`. Samme farger, avstander, skriftstørrelser, ikoner, rekkefølge og tekst. Ikke «forbedre» eller tolke. Ved tvil: designfilen gjelder.

## Web (`web/Skjold S1 Web v3.dc.html`)
1. **YT Music og Navidrome:** høyre kolonne «Ditt system» skjules når et av disse bibliotekene er åpent (`showSys: page !== 'lib'`).
2. **YT Music og Navidrome:** køen vises ikke. Biblioteket bruker hele bredden.
3. **Radio – ny side** (inspirert av YT Music og Navidrome, ikke kopiert):
   - Søkefelt øverst + knappen «Administrer favoritter» (åpner Innstillinger → Radio).
   - Stor topp-kort med kanalen som spiller (eller første favoritt): uskarpt bakgrunnslys fra kanalfargen, «SPILLER NÅ» med rød prikk, kanalnavn, sjanger og hva som spilles nå. Knappene «Spill» og «Legg til favoritter».
   - Sjangerfiltre: Alle, Pop og hits, Nyheter og prat, Klassisk, Jazz, Rock, Lokal (bare de som har kanaler vises).
   - Horisontale hyller: Dine favoritter, Populære i Norge, to sjangre. Kvadratiske kanalbilder med «DIREKTE»-merke på kanalen som spiller.
   - Søk: «Norske kanaler» først, så «Fra hele verden · Radio Browser». Hver rad har spill og ★/☆ for favoritt.
   - Kanaler som ikke er favoritter kan spilles direkte (`rTmp`).
4. **Radio-innstillinger:** favorittlisten, endring av rekkefølge, legg til med strøm-URL osv. er flyttet hit under overskriften «Favoritter». Knapper og oppstart kommer under.
5. Inntil **50** radiofavoritter (var 6). Telleren viser «N favoritter».

## Mobil (`app/Skjold App v2.dc.html`)
- Samme radio-oppsett som web, tilpasset mobil: mindre topp-kort, hyller og sjangerfiltre som kan sveipes sidelengs, knappen heter «Favoritter».
- Favoritthåndteringen er flyttet til Innstillinger → Radio.
- Inntil 50 favoritter.

## Felles (`felles/skjold_settings.js`, samme fil i `app/` og `web/`)
- `MAXRADIO: 50`.
- Raden «Administrer favoritter» er fjernet fra innstillingskategorien Radio, fordi listen nå ligger direkte der.

## Flasher (`flasher/Skjold Flasher.dc.html`)
1. **Velg lagring** (var «Velg SD-kort»): velg mellom «SD-kort» og «USB-pinne eller SSD». Listen viser bare disker av valgt type.
2. **Skrivebeskyttelse:** disker som er skrivebeskyttet får et rødt merke med hengelås og kan ikke velges. Teksten forteller hvordan det løses:
   - SD-kort: skyv låsen på siden av kortet opp.
   - USB: slå av bryteren for skrivebeskyttelse, eller velg en annen disk.
   - Sjekk det i koden: `BLKROSET` (Linux), `IOMedia Writable` (macOS), `IOCTL_DISK_IS_WRITABLE` (Windows).
3. **Start fra USB:** en egen boks forklarer krav per modell (Pi 4 / Pi 3B / 3B+) og ber deg ta ut SD-kortet. Ferdig-skjermen sier «USB-disken er klar» og ber deg bruke en blå USB 3-port.
4. **Nettverk:** velg mellom Wi-Fi og Ethernet.
   - Wi-Fi: SSID og passord som før.
   - Ethernet: valgfri fast IP (IP/prefiks, ruter, DNS). Av = DHCP. IP-feltet valideres.
   - Ferdig-skjermen legger til «Koble en nettverkskabel …» når du har valgt Ethernet.
   - Lagres i `skjold-setup.json`: `{ "net": "wifi"|"eth", "ssid", "psk", "static": { "ip", "gw", "dns" } | null }`.

## Etter bygging
Sammenlign skjermbilder av ferdig app og web side om side med designfilene. Avvik skal rettes.
