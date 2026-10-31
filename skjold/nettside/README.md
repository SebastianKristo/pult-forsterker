# Skjold-nettsiden

Statisk nettsted for **skjold.smarthjemexperten.no**. Det er bygget med ren HTML, CSS og JavaScript, uten byggesteg. Interesseskjemaet sendes til en Cloudflare Pages Function.

Designreferansen ligger i `skjold/design/nettside/` (`*.dc.html`) og i `skjold/design/README.md` (tokens og animasjoner).

## Innhold

| Sti | Side |
|---|---|
| `index.html` | Forside |
| `s1/`, `node/` | Produktsidene (hero-zoom, sticky bildesekvens, kilder, integrasjoner, spesifikasjoner) |
| `programvare/`, `sammenlign/`, `stotte/`, `om/` | Øvrige sider |
| `takk/`, `takk/feil/` | Svarsider for skjemaet uten JavaScript |
| `404.html` | Feilside (Cloudflare Pages bruker den automatisk) |
| `assets/skjold.css`, `assets/skjold.js` | Felles stil og oppførsel (reveal, zoom, bildesekvens, USB-demo, skjema) |
| `assets/img/` | Renders som PNG og WebP (`<picture>`), `og.jpg` for deling |
| `functions/api/interesse.js` | Pages Function: `POST`/`GET /api/interesse` |
| `_headers`, `_redirects` | Sikkerhetshoder, caching og omdirigering fra de gamle `.dc.html`-navnene |
| `sitemap.xml`, `robots.txt`, `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` | |

Nav og bunntekst står i hver side. Endrer du menyen, må den endres i alle `index.html`-filene og i `404.html`.

Animasjonene følger designet: reveal 0,9 s `cubic-bezier(.2,.7,.2,1)` med 28 px, hero-zoom 0,86 → 1 og sticky bildesekvens over 400vh med overtoning på 0,7 s. Med `prefers-reduced-motion: reduce`, eller uten JavaScript, vises alt uten animasjon, og bildesekvensen blir vanlige blokker.

**Om-siden:** baktanke-teksten er en plassholder, merket med `<!-- PLASSHOLDER -->` i `om/index.html`. Eieren skriver den selv. Fjern klassen `plassholder` når teksten er på plass.

## Forhåndsvisning lokalt

Statisk (skjemaet svarer da med 404/501):

```sh
cd skjold/nettside
python3 -m http.server 8000
# http://localhost:8000
```

Med Pages Function og en lokal KV:

```sh
cd skjold/nettside
npx wrangler pages dev . --kv INTERESSE --binding ADMIN_NOKKEL=test
# http://localhost:8788  ·  liste: http://localhost:8788/api/interesse?nokkel=test
```

## Cloudflare Pages

Bruk Cloudflares Git-integrasjon. Det trengs ingen GitHub Actions-workflow.

1. dash.cloudflare.com → Workers & Pages → Create → Pages → **Connect to Git** → velg `SebastianKristo/pult-forsterker`.
2. Production branch: `main`. Framework preset: **None**. Build command: *(tom)*. Build output directory: `/`. **Root directory: `skjold/nettside`**.
   - Functions-mappen hentes fra rotmappen (`skjold/nettside/functions`).
   - Under Build watch paths kan du sette include-stien til `skjold/nettside/*`, så bygges siden bare når den er endret.
3. KV: Workers & Pages → KV → Create namespace `skjold-interesse`. Gå så til Pages-prosjektet → Settings → Bindings → Add → KV namespace. Variabelnavn: **`INTERESSE`**. Gjør dette for både Production og Preview.
4. Settings → Variables and Secrets:
   - `ADMIN_NOKKEL` (Secret) er en lang tilfeldig verdi du lager selv.
   - `VARSEL_WEBHOOK` er valgfri: en Discord-, Slack- eller Homey-webhook som får varsel ved nye meldinger.
5. Custom domains → Set up a domain → `skjold.smarthjemexperten.no`. Ligger sonen på Cloudflare, lages CNAME-posten automatisk. Hvis ikke, legg inn CNAME `skjold` → `<prosjekt>.pages.dev`.

Hver push til `main` publiserer en ny versjon.

### Se innmeldinger

- JSON: `https://skjold.smarthjemexperten.no/api/interesse?nokkel=<ADMIN_NOKKEL>`
- CSV: legg til `&format=csv`

Hver e-postadresse lagres som én nøkkel (`i:<epost>`). En ny innsending fra samme adresse overskriver den gamle.

### Vern i funksjonen

- Validering av navn og e-post, lengdegrenser og hvitlister for produkt og type
- Honningfelt `nettsted`: roboter får «ok», men ingenting lagres
- Maks 8 KB per forespørsel, og Origin må være samme domene
- Rate-limit: 5 innsendinger per IP per 10 min. Bare en hash av IP-en lagres, med TTL. KV er «eventually consistent», så dette er et grovt vern. Trengs mer, legg på en Cloudflare WAF rate limiting-regel for `/api/interesse`.
- Admin-nøkkelen sammenlignes i konstant tid. CSV-eksporten nøytraliserer formler.
- Uten JavaScript poster skjemaet vanlig og får `303` til `/takk/` eller `/takk/feil/`.

## Bilder

Renders fra 3D-modellene ligger i `assets/img/` som `.png` og `.webp`. Når de skal byttes mot foto, legg inn begge formatene med samme navn, for eksempel:

```sh
python3 -c "from PIL import Image; Image.open('01-s1.png').save('01-s1.webp', quality=86, method=6)"
```
