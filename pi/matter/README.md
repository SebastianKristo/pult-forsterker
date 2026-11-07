# Skjold Matter

Skjold som Matter-enhet, bygget på [matter.js](https://github.com/project-chip/matter.js) (`@matter/main`, låst versjon i `package-lock.json`).
Tjenesten `skjold-matter.service` snakker med daemonen på `127.0.0.1:8765`. Den bruker SSE (`/api/events`) for status og REST for kommandoer.
Matter er en plugin som ikke ligger på enheten før du installerer den under **Integrasjoner → Matter → Installer**. Da installeres Node 20 og matter.js via `install.sh` (ca. 150 MB disk, ca. 120 MB RAM). **Avinstaller** kjører `uninstall.sh`, som fjerner tjenesten, matter.js, paringsdata og Node.js hvis Skjold installerte den. På enheter med under 1,5 GB minne (Pi 3) vises en advarsel. Etter det holder `update.sh` tjenesten oppdatert så lenge `/var/lib/ki-amp/matter.on` finnes.

## Endepunkter

| # | Matter-enhetstype | Skjold | Apple Hjem | Google Home | Alexa | SmartThings / Home Assistant |
|---|---|---|---|---|---|---|
| 1 | Speaker (0x0022): OnOff + LevelControl | OnOff = av/på (strøm), nivå 0–254 = volum 0–100 | **Vises ikke** – Apple Hjem støtter ikke Matter-høyttalere | Høyttaler med av/på og volum | «Speaker»: av/på, volum | `media_player`/`switch` + `number` (nivå) |
| 1b | Dimmable Light «Volum» | nivå = volum, av = dempet | Lampe med glidebryter (volum) | Lys med lysstyrke | Lys | `light` |
| 2 | On/Off Plug-in Unit «Demp» | på = dempet | Stikkontakt | Plugg | Plugg | `switch` |
| 3–8 | On/Off Plug-in Unit «Favoritt 1–6» | på = spill radiofavoritten, av = slå av Skjold | 6 stikkontakter | 6 plugger | 6 plugger | 6 × `switch` |
| 9 | Mode Select «Kilde» | modus = inngang (AirPlay, Blåtann, Radio …) | vises ikke (Hjem støtter ikke Mode Select ennå) | vises som modusvelger der den støttes | rutiner | `select` |

**Apple Hjem:** bruk heller Skjolds HomeKit-støtte (Integrasjoner → Apple Hjem). Den viser Skjold som TV/høyttaler med kilder, fjernkontroll og en «Volum»-glidebryter. Matter passer best for Google Home, Alexa, SmartThings og Home Assistant. Legger du Skjold til via Matter i Apple Hjem, får du «Volum» (lampe) og bryterne, men ikke selve høyttaleren.

Merk: Matter-spesifikasjonen bruker OnOff på en Speaker til demping. Her er OnOff i stedet satt til strøm, slik Skjold-brukere forventer. Demping har et eget endepunkt.
Endepunkter av samme type skilles med en TagList i Common Number-navnerommet. Navnene kan uansett endres i appen.

## Lokalt API (bare 127.0.0.1)

- `GET http://127.0.0.1:8767/status`: `{running, commissioned, fabrics, qr, manual, tilstand, endpoints}`. Daemonen gjør dette tilgjengelig som `GET /api/matter`.
- `POST /reset`: glemmer alle paringer og lager en ny paringskode. Tjenesten starter så på nytt.

## Test

```bash
cd pi/matter
npm ci
npm test                    # mappingene
SKJOLD_MATTER_DRYRUN=1 SKJOLD_MATTER_DIR=/tmp/m node index.js   # bygger noden og skriver paringskoden (uten nettverk)
```
