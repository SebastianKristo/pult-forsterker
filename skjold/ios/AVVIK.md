# Avvik mot designet

Status 2026-11-02. Appen bygger uten feil eller advarsler (Any iOS Simulator Device). Simulatoren for iOS 27.2 er ikke installert på maskinen, så skjermbildene i `skjermer/` er **ikke** sammenlignet med kjørende app ennå. Listen under er kjente avvik fra koden.

## Mangler fra designpakken
| Hva | Hvorfor | Midlertidig løsning |
|---|---|---|
| `renders/cut/01–04-*.png` (velkomst-hero) | Ikke med i zip-filen | S1-renderen er klippet ut av `01-velkomst.png` (`hero-s1`). Node-bildene vises som strektegning. Legg ekte renders inn som `hero-01-s1`, `hero-03-s1`, `hero-02-node`, `hero-04-node` i Assets, så brukes de automatisk. |
| `logo/brands/navidrome.png`, `lyrion_fav.png` | Ikke med i zip-filen | Bokstavmerke. Legg inn `brand-navidrome` / `brand-lyrion` i Assets. |
| `README.md`, punkt 3 (REST/WebSocket-API) | Ikke med i zip-filen | `DeviceLink` sender `POST http://<navn>.local/api/<type>` med samme meldinger som designets BroadcastChannel. Endepunktene må rettes når API-et er kjent. |
| Logo for NRK Alltid Nyheter | Ikke på static.nrk.no | Hentes via Radio Browser, ellers fargeforløp. |

## Bevisste avvik
- Fant vi ingen enheter med Bonjour, vises designets to demo-kort (S1 og Node) på «Finn forsterker».
- QR-skanning bruker kamera der det finnes. I simulatoren går den videre etter 2,2 s, slik designet gjør.
- Spilleposisjonen går fremover mens det spilles. I designet står den stille på 0:45.
- Oppsettet huskes. Etter første fullføring starter appen rett i hovedappen (introen vises fortsatt).
- «7 favoritter» brytes på to linjer i skjermbilde 19. Det ser ut som en layoutfeil i designet, så her står teksten på én linje.
- Statuslinjen og hjemindikatoren er systemets egne, ikke designets attrapper.

## Gjenstår
1. Installer iOS 27.2-simulatoren (Xcode → Settings → Components). Ta skjermbilde av alle 20 skjermene på iPhone 15 Pro, sammenlign mot `skjermer/` og legg inn avvikene her.
2. Kontroller linjehøyder: Sora har en annen naturlig linjehøyde enn CSS `line-height`. Bare ekstra linjeavstand er lagt til, ingen negativ.
