# Fasit — slik skal appen se ut

Skjermbildene er tatt direkte fra `../Skjold App v2.dc.html` (370 × 780 pt, 2x). Appen er ferdig når hver skjerm på telefonen ligger oppå bildet med samme plassering, størrelse, font og farge.

| Fil | Skjerm |
|---|---|
| 01-oppsett-finn.png | Oppsett trinn 1: finn enhet |
| 02-oppsett-wifi.png | Oppsett trinn 2: Wi-Fi |
| 03-hjem.png | Hjem med minispiller |
| 04-spiller.png | Fullskjermspiller (dras ned for å lukke) |
| 05-lyd.png | Lyd / EQ |
| 06-rom.png | Rom og grupper |
| 07-innstillinger.png | Innstillinger |

Hvite sirkler under «Kilder» er tjenestelogoer (lastes fra nett, ikke med i bildet).

## Regler for utvikler
1. Åpne `Skjold App v2.dc.html` i nettleser og les mål, farger og tekst rett fra koden. Ikke tegn etter øyemål.
2. Ikke legg til elementer som ikke finnes i fasit (power-knapp i header, stor spiller på Hjem, Radio-fane, «Leter …»-knapp, mDNS-tekst).
3. Ikke fjern elementer som finnes (Nylig spilt, fremdriftslinje i oppsett, minispiller).
4. Font: Sora + IBM Plex Mono. Ikke systemfont.
5. Safe area: kun `env(safe-area-inset-top/bottom)`, én gang.
6. Lever skjermbilder fra iPhone side om side med disse før neste runde.
