# Skjold-hjem – sky-relé (Cloudflare Worker)

Worker `skjold-hjem` som samler Skjold-enheter i **steder** og videreformidler (relé) app/web-UI-kall til enheter som
ikke nås direkte. Kontrakten (API og meldingsformat) står i [`docs/SKJOLD_HJEM.md`](../../docs/SKJOLD_HJEM.md).

- `src/index.js` – Worker + Durable Objects (ingen byggesteg):
  - `Sted` (én per sted): data, enhetsnøkler (bare SHA-256 lagres), koblingskoder, WebSocket til enhetene
    (Hibernation API), valg av aktiv hovedenhet, relé (`req`/`res`, 25 s tidsavbrudd ⇒ 504) og SSE-relé (`sub`/`ev`/`unsub`).
  - `Konto` (én per e-post): brukerens liste over steder.
  - `Koder` (én, navn «koder»): indeks koblingskode → sted, slik at `/enhet/kobl` finner stedet.
- Web-UI-et (`skjold/app`) legges ut som statiske filer fra `../app/dist` (bygges før deploy). Alt utenom `/api/*` og
  `/enhet/*` serveres derfra.
- Durable Objects er SQLite-baserte (`new_sqlite_classes`) og virker på gratisplanen.

## Legge ut

```sh
cd skjold/app && npm ci && npm run build      # web-UI → skjold/app/dist
cd ../sky && npm ci && npx wrangler deploy
```

GitHub Actions (`.github/workflows/sky.yml`) gjør det samme ved push til `main` som endrer `skjold/sky/**` eller
`skjold/app/**`. Krever secrets `CLOUDFLARE_API_TOKEN` (rettighet «Workers Scripts: Edit», og «Workers Routes: Edit» hvis
ruten ligger i wrangler.toml) og `CLOUDFLARE_ACCOUNT_ID`; uten dem hoppes jobben over med en advarsel.

## Oppsett i Cloudflare (én gang)

**Bytte fra det gamle domenet.** Skyen lå før på `skjold-styring.smarthjemexperten.no`. Enheter og apper med eldre
programvare bruker fortsatt den adressen, så la den stå til alt er oppdatert. Legg `hjem.skjold-lab.com` til som et
ekstra domene på Workeren, og som et ekstra domene i de **samme** to Access-applikasjonene (ikke lag nye). Da er
AUD-taggen den samme, og `ACCESS_AUD` trenger ikke endres.

1. **Adresse**: Workers & Pages → `skjold-hjem` → Settings → Domains & Routes → *Add Custom Domain*
   `hjem.skjold-lab.com` (eller fjern `#` foran `routes` i `wrangler.toml`).
2. **Cloudflare Access** (Zero Trust → Access → Applications → *Add an application* → *Self-hosted*):
   - Applikasjon «Skjold-hjem»: domene `hjem.skjold-lab.com`, sti tom (hele nettstedet), policy
     *Allow* for e-postene/gruppa som skal ha tilgang (f.eks. «Emails ending in» eller en liste). Innlogging med
     engangskode på e-post eller Google.
   - Applikasjon «Skjold-hjem enheter»: samme domene, sti `enhet/` (dekker `/enhet/*`), policy med handling **Bypass**
     for *Everyone*. Enhetene autentiseres med egen nøkkel, ikke Access.
   - Kopier **Application Audience (AUD) Tag** fra «Skjold-hjem» (Overview-fanen).
3. **Variabler** (Workers & Pages → `skjold-hjem` → Settings → Variables and Secrets, eller `npx wrangler secret put`):
   - `ACCESS_TEAM_DOMAIN` = teamnavnet ditt (`<team>` eller `<team>.cloudflareaccess.com`, står under Zero Trust → Settings)
   - `ACCESS_AUD` = AUD-taggen fra punkt 2
   Workeren stoler bare på innloggingen når begge er satt: JWT-en i `Cf-Access-Jwt-Assertion` (eller cookien
   `CF_Authorization`) verifiseres mot `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`. Uten dem svarer
   `/api/hjem/*` 401. `keep_vars = true` gjør at deploy ikke nullstiller dem.

## Lokalt og tester

```sh
npm ci
npm test                                   # node:test + Miniflare (workerd): steder, kobling, WS, relé, failover, SSE, Access
npx wrangler dev --var DEV_INSECURE:1      # http://localhost:8787, bruker settes med headeren X-Skjold-User
```

`DEV_INSECURE=1` godtar `X-Skjold-User` uten Access – **aldri** i produksjon. Enhetsmodulen (`pi/ki_amp_daemon.py`)
testes mot den ekte Workeren med `python3 -m unittest discover -s pi/tests` (starter `test/server.mjs`).

Eksempel lokalt:

```sh
U='-H X-Skjold-User:meg@example.no'
curl -s $U -XPOST localhost:8787/api/hjem/steder -d '{"navn":"Hytta"}'          # → {"id":"st_…"}
curl -s $U -XPOST localhost:8787/api/hjem/steder/st_…/kobling                   # → {"kode":"K7Q2XM", …}
# på enheten:  curl -XPOST localhost:8765/api/sky -d '{"kode":"K7Q2XM","url":"http://<pc>:8787"}'
curl -s $U localhost:8787/api/hjem/steder/st_…/enheter/<id>/api/status
```

## Begrensninger

- Én WebSocket-melding er maks 1 MiB hos Cloudflare: relé-svar over ca. 700 kB avvises av enheten (413).
- Gratisplanen: 100 000 forespørsler/dag og begrenset Durable Object-tid; WebSocket Hibernation og automatisk
  `ping`→`pong`-svar gjør at stedet sover mellom forespørslene. Hver 30. s vekkes stedet av en alarm (sjekker at
  enhetene lever, > 45 s uten livstegn ⇒ frakoblet) så lenge noen enhet er tilkoblet.
