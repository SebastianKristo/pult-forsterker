# Rettelser — mobilappen (Hjem)

Fasit: `design_handoff_skjold_komplett/app/Skjold App v2.dc.html`. Skjermbilde fra enhet 31.10.2026 avviker på punktene under. Bygg etter fasit, ikke tolk.

## 1. Toppen (feil)
- Ca. 120 pt tomrom mellom statuslinjen og SKJOLD-logoen. Safe-area legges trolig på to ganger (både `env(safe-area-inset-top)` og en egen header-/statuslinje-høyde).
- Riktig: kun `padding-top: env(safe-area-inset-top)` på rotelementet, så logo-raden med 4 px topp-padding. Ingen ekstra spacer.
- Sjekk `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` og `apple-mobile-web-app-status-bar-style: black-translucent` (eller native: ikke legg på padding når `SafeAreaView` allerede brukes).

## 2. Header
- Logo: 5 stolper 2,5 px brede (8/12/16/12/8 px høye) + «SKJOLD» 15 px, vekt 600, sperring 0,12em.
- Høyre: én pille, 32 px høy, prikk 6 px #6fcf7f + romnavn/gruppenavn, 12 px. Trykk → Rom-fanen.
- **Fjern power-knappen** fra headeren. Av/på ligger i romkortet/Innstillinger.

## 3. Aktivt rom-kort
- Grid `42px | 1fr | auto`, padding 12×14, radius 14, bakgrunn #141415, kant #242426, min-høyde 64.
- Ikon 42×42, radius 10, bakgrunn #1c170d, kant #5a4420, ikon #f0c46a.
- Tekst: romnavn 15/600 · modell («Skjold Node») 12/600 #f0c46a · maskinvare i IBM Plex Mono 10 px #8b8b86 med ellipsis.
- Høyre: «Bytt» 12 px #8b8b86.
- **Fjern** «AKTIVT ROM»-overskriften, «Node»-merket og «● På».

## 4. Spiller
- **Ingen stor spiller på Hjem.** Fjern hele kortet med cover, ⏮ ▶ ⏭ og volumslider.
- I stedet: minispiller festet over fanelinjen — marg 0 10 8, radius 14, bakgrunn #1b1b1d, kant #2a2a2c, grid `44px | 1fr | auto`, padding 8. Cover 44×44 r8 · linje 1 «Stue · Skjold Node» (Mono 9,5 px) · tittel 13/600 · undertittel 11 px · spill/pause 40×40.
- Trykk på minispilleren åpner fullskjermspilleren (dras ned for å lukke). Volum hører hjemme der.

## 5. Innhold på Hjem (i denne rekkefølgen)
1. Header
2. Aktivt rom-kort
3. **Nylig spilt** (mangler) — horisontal rulling, fliser 118×118
4. **Kilder** — runde ikoner 64×64 med etikett 11 px under, horisontal rulling. Ikke tekstpiller med fargeprikk.
5. **Radiofavoritter** + «Administrer» (13 px #d9a441) — horisontal rulling, fliser 96×96 r12 med nummer (Mono 9 px) øverst og kanalnavn 13/600 nederst, sjanger 11 px under. Ikke 3-kolonners rutenett.
   - Tomme plasser: vis ikke tre tomme «+ Legg til»-kort. Er listen tom, vis én stiplet knapp «Legg til radiokanal» som åpner Radio.

## 6. Fanelinje
- **4 faner:** Hjem · Lyd · Rom · Innstillinger. Fjern Radio-fanen (radio nås fra Radiofavoritter/Kilder).
- Aktiv fane: ikon i pille 30 px høy, radius 15, med bakgrunnsfarge; etikett 10,5 px.
- Høyde inkluderer `env(safe-area-inset-bottom)`.

## 7. Typografi og farger
- Font: Sora (300/400/600) + IBM Plex Mono (400/500). Skjermbildet bruker systemfont.
- Bakgrunn #0b0b0c, tekst #f2f2ee, dempet #8b8b86, aksent #d9a441 / #f0c46a, kort #141415, kant #242426.
- Seksjonstitler 17/600 (ikke ~22 som nå). Generelt er alt i skjermbildet ca. 20 % for stort — bruk px-verdiene fra fasit 1:1.

## 8. Oppsett — «Finn Skjold» (skjermbilde 22.28)
Fasit: onboarding trinn 1 i `Skjold App v2.dc.html` (`ob === 0`).

**Toppen**
- Samme tomrom som på Hjem (ca. 70 pt over logoen). Samme rettelse som punkt 1.
- Oppsett har **ingen** SKJOLD-logo og ingen «Avbryt» øverst. Riktig topp: liten etikett til venstre «OPPSETT · 1 AV 4» (IBM Plex Mono 10 px, sperring 0,12em, #8b8b86) og «Tilbake» (13 px #d9a441) til høyre fra trinn 2.
- Under etiketten: fremdriftslinje med 4 segmenter, 3 px høye, mellomrom 4 px. Fullført = #d9a441, resten #2a2a28. Mangler helt nå.

**Tittel og tekst**
- Tittel 26/600, linjehøyde 1,15 (nå ca. 34). Brødtekst 13 px #a9a9a3, linjehøyde 1,5.
- Bruk teksten fra fasit: «Legg til forsterker» / «Slå på forsterkeren. Den dukker opp her.»

**Søk**
- Fjern statusboksen «Ser etter Skjold med Bonjour/mDNS …» og den grå «Leter …»-knappen. En knapp som bare viser status er forvirrende.
- Riktig: funne enheter vises som kort (ikon 40 px, navn 14 px, serienr./status i Mono 10 px, «Sett opp» 12 px #f0c46a til høyre). Første funne enhet har gull-kant #d9a441 og bakgrunn #1c170d.
- Under kortene: én linje med pulserende prikk 8 px + «Leter etter flere …» (12 px #8b8b86).
- Bonjour/mDNS er fint som teknikk, men skal ikke stå i teksten til brukeren.

**Manuell adresse**
- Skal ikke ligge åpent som hovedvalg. Flytt til en tekstlenke nederst: «Skriv inn adresse manuelt» (13 px #d9a441). Trykk viser feltet + «Koble til».
- Nederst (margin-top: auto): «Skann QR-kode på skjermen», 50 px høy, radius 14, kant #2e2e30, gjennomsiktig.

**Deaktivert knapp**
- «Koble til» har mørk tekst på grå bakgrunn og kan ikke leses. Deaktivert: bakgrunn #242426, tekst #8b8b86. Aktiv: bakgrunn #d9a441, tekst #0b0b0c. (Rettet i fasit også.)

**Merk om Blåtann**
- Designet sier «Den dukker opp her via Blåtann». Hvis appen er en web-app på iOS, finnes ikke Web Bluetooth. Da er mDNS + QR + manuell IP riktig, og teksten skal være «Slå på forsterkeren. Den dukker opp her.» Bruker appen native Blåtann, behold teksten.

## 9. Fanelinjen står ikke i bunnen (skjermbilde 22.28.32)
Fanelinjen har ca. 50 pt tomt felt under seg. Safe-area nederst er lagt som marg **under** linjen, og/eller høyden regnes med `100vh` (som på iOS er høyere enn synlig område).

Riktig:
```css
html, body { height: 100%; margin: 0; background: #0b0b0c; }
.app { height: 100dvh; display: flex; flex-direction: column;
       padding-top: env(safe-area-inset-top); box-sizing: border-box; }
.innhold { flex: 1; min-height: 0; overflow-y: auto; }
.minispiller { flex-shrink: 0; margin: 0 10px 8px; }
.fanelinje { flex-shrink: 0; background: #0b0b0c; border-top: 1px solid #1c1c1e;
             padding: 4px 6px env(safe-area-inset-bottom);
             height: calc(58px + env(safe-area-inset-bottom)); box-sizing: border-box; }
```
- Ingen `margin-bottom`, `bottom:`-offset eller ekstra spacer under fanelinjen.
- Ikke `position: fixed` + `100vh`. Bruk flex-kolonnen over (eller `position: fixed; bottom: 0` uten noen annen nedre avstand).
- Fanelinjen har samme bakgrunn helt ned til kanten. Hjemindikatoren (iOS) ligger oppå linjens bakgrunn.
- React Native: bruk `SafeAreaView edges={['top']}` på skjermen og la tab-navigatoren selv håndtere bunnen. Ikke begge.

**Rom-skjermen avviker også** (se `fasit/06-rom.png`): tittelen skal ikke ha romvelger og power-knapp, «Legg til enhet» skal ikke vises både som tre kort og en stor gul knapp, og «Kommer:»-boksen skal fjernes. Grupper finnes i designet allerede («Alle rom» / «Bare Stue» + gruppekort).

## Sjekk etter retting
- Ta skjermbilde på iPhone med Dynamic Island og på Android, legg ved siden av `Skjold App v2.dc.html` (Hjem-fanen).
