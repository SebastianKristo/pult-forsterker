# Skjold-hjem – steder, hovedenhet og reserve via Cloudflare

Mål: én innlogging i appen (iOS/Android) og web-UI-et gir tilgang til alle Skjold-enheter, gruppert i **steder** (Hjem, Hytta …).
Øverst i appen/web-UI-et er en **stedsvelger** (meny som bytter sted). Hvert sted har en **hovedenhet** (valgt av brukeren) og en
**reserveliste**. Hovedenheten er stedets kontaktpunkt mot skyen; går den offline, tar neste i reservelista over til hovedenheten er
tilbake (automatisk tilbakefall).

## Deler
1. **Sky** – Cloudflare Worker `skjold-hjem` (mappe `skjold/sky/`), én Durable Object per sted (`Sted`), D1/KV ikke nødvendig.
   Adresse: `https://skjold-styring.smarthjemexperten.no` (Worker-rute). Brukerinnlogging: Cloudflare Access foran
   `/` og `/api/hjem/*` (Worker leser `Cf-Access-Authenticated-User-Email`; lokalt/test: header `X-Skjold-User`).
   Enheter går utenom Access på `/enhet/*` og autentiseres med egen enhetsnøkkel.
2. **Enhet** – `pi/ki_amp_daemon.py`: modul «sky» som holder én WebSocket ut til skyen, svarer på relé-forespørsler mot sitt
   eget API, og (når den er aktiv hovedenhet) også videresender til andre Skjold-enheter på samme LAN (oppdaget via mDNS).
3. **Klienter** – web-UI (`skjold/app`), iOS (`skjold/ios`), Android (`skjold/android`): stedsvelger + bruk av skyens API når
   enheten ikke nås direkte på LAN.

## Datamodell (i `Sted`-objektet, lagret i Durable Object storage)
```json
{ "id": "st_ab12", "navn": "Hytta", "eier": "navn@epost",
  "medlemmer": ["navn@epost"],
  "enheter": [ {"id": "<daemon id = hostname>", "navn": "Skjold Core", "produkt": "core", "rom": "Stue",
                "noekkelHash": "sha256…", "lagtTil": 1730000000} ],
  "hoved": "<enhets-id>", "reserve": ["<id>", "<id>"] }
```
Brukerens liste over steder: Durable Object `Konto` per e-post (`idFromName(epost)`) med `{steder: [{id, navn}]}`.

## Rolle: aktiv hovedenhet
- Skyen kjenner hvilke enheter som har åpen WebSocket.
- **Aktiv hovedenhet** = `hoved` hvis tilkoblet, ellers første tilkoblede i `reserve`, ellers første tilkoblede enhet.
- Ved endring sender skyen `{"t":"rolle","aktiv":"<id>","hoved":"<id>"}` til alle enheter i stedet. Bytte skjer straks når
  en enhet kobler fra (WebSocket close / ingen ping på 45 s) eller hovedenheten kobler til igjen (tilbakefall).
- Forespørsel til en enhet: rett til enheten hvis den er tilkoblet; ellers via aktiv hovedenhet (`via`), som prøver LAN-adressen.

## API for klienter (bak Access) – alle svar JSON
| Metode | Sti | Hva |
|---|---|---|
| GET | `/api/hjem/steder` | `[{id, navn, rolle:"eier"\|"medlem", enheter, online}]` |
| POST | `/api/hjem/steder` `{navn}` | nytt sted |
| PATCH | `/api/hjem/steder/{sted}` `{navn?, hoved?, reserve?}` | endre navn / hovedenhet / reserve |
| DELETE | `/api/hjem/steder/{sted}` | slett sted (bare eier) |
| GET | `/api/hjem/steder/{sted}/enheter` | `[{id, navn, produkt, rom, online, aktivHoved, hoved, reserveNr, lan, sist}]` |
| POST | `/api/hjem/steder/{sted}/kobling` | `{kode:"K7Q2XM", utloper}` – sekssifret kode (gyldig 10 min) som tastes inn på enheten |
| DELETE | `/api/hjem/steder/{sted}/enheter/{id}` | fjern enhet |
| ANY | `/api/hjem/steder/{sted}/enheter/{id}/api/...` | **relé** til enhetens eget API (`/api/status`, `/api/volume` …), samme svar som lokalt |
| GET | `/api/hjem/steder/{sted}/enheter/{id}/api/events` | SSE fra enheten via relé |
| GET | `/` | web-UI-et (samme bygg som på enhetene), som da bruker relé-stiene |

## Enhet ↔ sky (WebSocket `wss://…/enhet/ws`)
- Kobling første gang: `POST /enhet/kobl {kode, id, navn, produkt}` → `{sted, noekkel}`; enheten lagrer `noekkel` i
  `/var/lib/ki-amp/sky.json` (0600). Deretter `GET /enhet/ws` med `Authorization: Bearer <id>.<noekkel>` (Upgrade: websocket).
- Meldinger (JSON, én per ramme):
  - sky → enhet: `{"t":"req","rid":"…","m":"GET","p":"/api/status","h":{…},"b":"<base64>|null","til":"<id>"}` (`til` ≠ egen id
    ⇒ enheten er hovedenhet og skal videresende til `til` på LAN)
  - enhet → sky: `{"t":"res","rid":"…","s":200,"h":{"content-type":"application/json"},"b":"<base64>"}`
  - SSE: sky → `{"t":"sub","rid":"…","p":"/api/events","til":"<id>"}`, enhet → `{"t":"ev","rid":"…","d":"<data-linje>"}` …,
    sky → `{"t":"unsub","rid":"…"}`
  - `{"t":"hei","id","navn","produkt","versjon","lan":[{id,navn,ip,port,produkt}]}` ved tilkobling og når LAN-lista endres
  - `{"t":"ping"}` / `{"t":"pong"}` hvert 20. s; `{"t":"rolle",…}` fra skyen
- Enhetens lokale API: `GET/POST /api/sky` – `{koblet, sted, stedNavn, aktivHoved, erHoved, tilkoblet}`;
  `POST /api/sky {kode}` kobler til, `POST /api/sky {koble_fra:true}` kobler fra.

## Klienter: stedsvelger
- Øverst (web: header ved enhetsnavnet; app: tittel på Hjem/Rom) en meny «Hjem ▾» som lister steder fra `/api/hjem/steder`
  pluss «Dette nettverket» (LAN-oppdagelse som i dag). Valgt sted huskes.
- Romlisten viser stedets enheter (online/offline), med merke «Hoved» og «Reserve 1/2 …», og «aktiv» på den som er
  kontaktpunkt nå. I Innstillinger → Steder: gi nytt navn, velg hovedenhet, sorter reserveliste, legg til enhet (vis kode),
  fjern enhet, lag/slett sted.
- Er enheten på samme LAN (svarer på sin lokale adresse) brukes den direkte; ellers relé via skyen.
