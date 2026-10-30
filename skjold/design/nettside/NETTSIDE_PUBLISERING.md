# Skjold-nettsiden: publisering med GitHub og Cloudflare Pages

Nettsiden er `Skjold Nettside.dc.html`. `index.html` sender besøkende dit. Siden bruker filene i prosjektet direkte: 3D-modellene, bruksanvisningene og nedlastingene. Hele prosjektmappen skal derfor ligge i repoet.

## 1. Legg prosjektet på GitHub
1. Last ned prosjektet som zip. Pakk det ut.
2. Lag et nytt repo på github.com, for eksempel `skjold`. Det må være **public** hvis filene skal være åpen kildekode.
3. Gjør så dette i mappen:
   ```
   git init && git add . && git commit -m "Skjold"
   git branch -M main
   git remote add origin https://github.com/<bruker>/skjold.git
   git push -u origin main
   ```
4. Lim inn repo-lenken i nettsidens innstilling `repoUrl` (Tweaks), så peker knappen «Se koden på GitHub» dit.

## 2. Cloudflare Pages
1. Gå til dash.cloudflare.com → Workers & Pages → Create → Pages → Connect to Git.
2. Velg repoet `skjold`.
3. Framework preset: **None**. Build command: *(tom)*. Build output directory: `/`.
4. Trykk Deploy. Siden ligger nå på `skjold.pages.dev`.

## 3. Eget domene
1. Gå til Pages-prosjektet → Custom domains → Set up a domain → `skjold.smarthjemexperten.no`.
2. Ligger `smarthjemexperten.no` på Cloudflare, lages CNAME-posten automatisk. Hvis ikke: legg inn CNAME `skjold` → `skjold.pages.dev` hos domeneleverandøren.
3. HTTPS ordnes automatisk.

Hver `git push` til `main` publiserer en ny versjon i løpet av ett minutt.

## Bilder
Bildene på nettsiden kan byttes ut ved å dra et foto inn i feltet i editoren. Bildene lagres i `.image-slots.state.json`, og den fila må også pushes.

## Interesseskjema
Skjemaet sender til `/api/interesse` (`functions/api/interesse.js`). Cloudflare Pages kjører det automatisk.
1. Gå til Workers & Pages → KV → Create namespace: `skjold-interesse`.
2. Gå til Pages-prosjektet → Settings → Functions → KV namespace bindings. Legg til variabelen `INTERESSE` og velg `skjold-interesse`.
3. Under Settings → Variables legger du inn `ADMIN_NOKKEL` som en hemmelig verdi du finner på selv. Du kan også legge inn `VARSEL_WEBHOOK` (Discord, Slack eller Homey) for å få varsel når noen melder seg.
4. Se alle som har meldt interesse: `https://skjold.smarthjemexperten.no/api/interesse?nokkel=<ADMIN_NOKKEL>`
