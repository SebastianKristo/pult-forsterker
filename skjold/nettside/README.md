# Skjold Lab – nettsiden

Statisk nettsted for **skjold.smarthjemexperten.no**, nettsiden til **Skjold Lab**. Skjold Lab er merkenavnet (den som lager), mens produktene fortsatt heter Skjold S1, Skjold Node, Skjold Touch, Skjold Røst og Skjold Stav. Bruk «Skjold Lab» i logoen (`SKJOLD` + `LAB` i `.logo-lab`), bunnteksten, `og:site_name` og sidetitlene (`… – Skjold Lab`). Det er bygget med ren HTML, CSS og JavaScript, uten byggesteg. Interesseskjemaet sendes til en Cloudflare Pages Function.

Designreferansen ligger i `skjold/design/nettside/` (`*.dc.html`) og i `skjold/design/README.md` (tokens og animasjoner).

## Innhold

| Sti | Side |
|---|---|
| `index.html` | Forside |
| `s1/`, `node/`, `touch/`, `rost/`, `core/` | Produktsidene (hero-zoom, sticky bildesekvens, kilder, integrasjoner, spesifikasjoner). `touch/` har også en 3D-modell med `<model-viewer>` |
| `stav/` | Skjold Stav, fjernkontrollen fra `kabinett/fjernkontroll/` (med Skjold Dokk). Et byggeprosjekt som ikke er bygget eller testet ennå; siden sier det |
| `programvare/`, `sammenlign/`, `stotte/`, `om/` | Øvrige sider |
| `takk/`, `takk/feil/` | Svarsider for skjemaet uten JavaScript |
| `en/` | Engelske sider: `en/`, `en/s1/`, `en/node/`, `en/touch/`, `en/stav/`, `en/software/`, `en/compare/`, `en/support/`, `en/about/`, `en/thanks/`, `en/thanks/error/` |
| `404.html` | Feilside på norsk og engelsk (Cloudflare Pages bruker den automatisk) |
| `assets/skjold.css`, `assets/skjold.js` | Felles stil og oppførsel (reveal, zoom, bildesekvens, USB-demo, skjema) |
| `assets/img/` | Renders som PNG/JPEG og WebP (`<picture>`), `og.jpg` for deling |
| `assets/3d/skjold-touch.glb` | 3D-modellen av Touch (helsort, meter, Y opp), med skjermglass og skjermbildet fra renderen lagt inn som to flater |
| `assets/vendor/model-viewer-4.1.0/` | Google `<model-viewer>` 4.1.0 (BSD-3-Clause, med `LICENSE`), lagt inn lokalt så CSP-en kan beholde `script-src 'self'` |
| `functions/api/interesse.js` | Pages Function: `POST`/`GET /api/interesse` |
| `admin/`, `functions/api/admin/[[path]].js` | Visuell editor og API-et bak den (se «Redigere nettsiden») |
| `_headers`, `_redirects` | Sikkerhetshoder, caching og omdirigering fra de gamle `.dc.html`-navnene |
| `sitemap.xml`, `robots.txt`, `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` | |

Nav og bunntekst står i hver side. Endrer du menyen, må den endres i alle `index.html`-filene (også under `en/`) og i `404.html`.

**Språk:** norsk ligger på de vanlige adressene og engelsk under `/en/`. Hver side har `NO | EN` i menyen, som lenker til samme side på det andre språket, og har `hreflang` (`nb`, `en`, `x-default` = norsk) og `og:locale`. `sitemap.xml` lister begge språkene. Endrer du en tekst, endre den på begge språkene. Skjemaet på engelske sider sender `lang=en`, og da sender funksjonen besøkende uten JS til `/en/thanks/` eller `/en/thanks/error/`. Tekstene i `skjold.js` velges ut fra `<html lang>`.

Animasjonene følger designet: reveal 0,9 s `cubic-bezier(.2,.7,.2,1)` med 28 px, hero-zoom 0,86 → 1 og sticky bildesekvens over 400vh med overtoning på 0,7 s. Med `prefers-reduced-motion: reduce`, eller uten JavaScript, vises alt uten animasjon, og bildesekvensen blir vanlige blokker.

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
- Uten JavaScript poster skjemaet vanlig og får `303` til `/takk/` eller `/takk/feil/` (`/en/thanks/` eller `/en/thanks/error/` når `lang=en`).

## Redigere nettsiden

Nettsiden kan redigeres i nettleseren på **https://skjold.smarthjemexperten.no/admin/** – også fra mobilen. Klikk på en tekst for å skrive i den (fet, kursiv og lenker), klikk på et bilde for å bytte det eller endre alt-teksten, og bruk den oransje blokkrammen til å flytte (↑ ↓), kopiere eller slette seksjoner, fliser, kilder, rader og produktkort. «Sideinfo» endrer tittel, beskrivelse og delingsbilde. «HTML»-fanen viser kildekoden for avanserte endringer, og «+ Ny side» lager en kopi av en eksisterende side. Angre/gjør om: Ctrl+Z / Ctrl+Shift+Z.

**«Lagre og publiser»** lagrer siden som en commit på `main` i GitHub. Da kjører `.github/workflows/nettside.yml`, og siden er oppdatert om ca. ett minutt. Opplastede bilder committes med en gang til `assets/img/opplastet/` (de vises i editoren med en gang, men på nettsiden først når siden er publisert). Editoren endrer bare det du faktisk har endret – resten av filen lagres tegn for tegn som før – så historikken i Git viser nøyaktig hva som ble endret.

### Oppsett (én gang)

1. **GitHub-token:** github.com → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
   - Repository access: *Only select repositories* → `SebastianKristo/pult-forsterker`
   - Permissions → Repository permissions → **Contents: Read and write** (Metadata: Read følger med)
   - Sett en utløpsdato du husker, og lag et nytt token når det går ut.
2. **Cloudflare:** Workers & Pages → `skjold` → Settings → Variables and Secrets → Add (Production):
   - `GITHUB_TOKEN` (type *Secret*) = tokenet fra punkt 1
   - `ADMIN_NOKKEL` (Secret) finnes fra før – det er dette passordet du logger inn med
   - Valgfritt: `GITHUB_REPO` (standard `SebastianKristo/pult-forsterker`), `GITHUB_BRANCH` (standard `main`), `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL` (standard Sebastian Kristo Jemtland &lt;sebastian@kristo.no&gt;)
   - Publiser på nytt (eller vent til neste push) så funksjonen får de nye verdiene.
3. Åpne https://skjold.smarthjemexperten.no/admin/ og logg inn med `ADMIN_NOKKEL`.

### Hvordan det virker

| Fil | Rolle |
|---|---|
| `admin/index.html`, `admin/editor.js`, `admin/editor.css` | Editoren. Siden vises i en iframe (skript slått av), og bare endrede elementer skrives på nytt ved lagring. |
| `functions/api/admin/[[path]].js` | API: `GET pages`, `GET page?path=`, `POST page`, `POST upload`, `POST new`, `GET ping`. Leser og skriver via GitHub Contents API. |

- Innlogging: `Authorization: Bearer <ADMIN_NOKKEL>`, sammenlignet i konstant tid. Etter 10 feil forsøk fra samme IP på 15 min blokkeres IP-en (telles i KV `INTERESSE`, nøkkel `arl:<hash>`).
- Bare `.html`-filer under `skjold/nettside` kan endres (ikke `admin/` eller `functions/`, ingen `..`). Bilder: PNG, JPG, WebP, GIF eller AVIF, maks 5 MB, sjekket på filinnholdet (SVG er ikke tillatt).
- Har noen andre endret filen siden du åpnet den (f.eks. en commit fra PC-en), avvises lagringen med beskjed om å laste siden på nytt, i stedet for å overskrive.
- `/admin/` har `noindex` (meta og `X-Robots-Tag`), `Cache-Control: no-store`, er stengt i `robots.txt` og står ikke i `sitemap.xml`. Det er ingen lenke til den fra nettsiden.
- Nøkkelen lagres bare i fanen (sessionStorage), eller i nettleseren hvis du krysser av for «Husk meg».

## Bilder

Renders fra 3D-modellene ligger i `assets/img/` som `.png` og `.webp`. Når de skal byttes mot foto, legg inn begge formatene med samme navn, for eksempel:

```sh
python3 -c "from PIL import Image; Image.open('01-s1.png').save('01-s1.webp', quality=86, method=6)"
```

Nye bilder legges inn som WebP med JPEG som reserve, maks ca. 1800 px bredt. Originalene (store PNG-er) holdes utenfor nettsiden:

```sh
python3 -c "from PIL import Image; im=Image.open('original.png').convert('RGB'); im.thumbnail((1800,1800)); im.save('navn.webp', quality=82, method=6); im.save('navn.jpg', quality=82, optimize=True, progressive=True)"
```

| Filer | Brukes på |
|---|---|
| `s1-skra`, `s1-front`, `s1-topp`, `s1-bak` | S1 (hero, bildesekvens), forsiden, sammenlign |
| `node-tft-skra`, `node-tft-front`, `node-tft-topp`, `node-tft-bak` | Node (hero, bildesekvens), forsiden, sammenlign |
| `touch-skraa`, `touch-front`, `touch-side`, `touch-bak`, `touch-eksplodert` | Touch, helsort med stoff (hero, bildesekvens, «Slik er den bygget»), forsiden |
| `familie-lab`, `familie-lab-m` | Forsiden: hele familien på skrivebordet (også `og.jpg`) |
| `stav-*` | Stav: renders fra `kabinett/fjernkontroll/render/` og `dokk/render/`, og skjermbildene |

### 3D-modellen på Touch

`touch/` og `en/touch/` laster `/assets/vendor/model-viewer-4.1.0/model-viewer.min.js` som `type="module"`, og `<model-viewer>` henter `/assets/3d/skjold-touch.glb`. Biblioteket er lagt inn lokalt (som Redoc og PDF.js), så `script-src` kan fortsatt være `'self'`. CSP-en i `_headers` har to tillegg for det: `'wasm-unsafe-eval'` i `script-src` (model-viewer setter opp en WebAssembly-dekoder) og `blob:` i `img-src` og `connect-src` (teksturen i GLB-fila, skjermbildet, lastes som en blob-URL). Bytt versjon ved å legge en ny mappe ved siden av og endre stien i de to sidene.
