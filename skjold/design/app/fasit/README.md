# Fasit: slik skal appen se ut (v3, 01.11.2026)

**Den eneste fasiten er `../Skjold App v2.dc.html`.** Bildene i `v3/` er en oversikt over hver skjerm. De er tatt fra designfilen med lav oppløsning. Les mål, farger og tekster fra koden. Ikke mål på bildene.

`_utdatert/` er de gamle bildene fra 31.10. **Ikke bruk dem.** De mangler det meste av det som er lagt til siden.

| Bilde | Skjerm | Tilstand i designfilen |
|---|---|---|
| 01-velkomst | Velkomst med rullende render av S1/Node | `welcome: true` |
| 02-oppsett-finn | Oppsett 1: legg til forsterker | `mode:'onboard', ob:0` |
| 03-oppsett-qr | Oppsett 1: skann QR | `ob:0, scan:true` |
| 04-oppsett-wifi | Oppsett 2: Wi-Fi-liste | `ob:1` |
| 05-oppsett-wifi-manuell-ssid | Oppsett 2: «Annet nettverk …», SSID og sikkerhet | `ob:1, net:'man'` |
| 06-oppsett-rom | Oppsett 3: rom + «Skriv eget navn» | `ob:2` |
| 07-oppsett-test | Test høyttalerne L/R | `ob:3` |
| 08-oppsett-ferdig | Programvare/oppdatering | `ob:4` |
| 09-hjem | Hjem | `mode:'app', tab:0` |
| 10-fullspiller | Fullskjermspiller | `full:true` |
| 11-ko | Kø | `full:true, queueOpen:true` |
| 12-lyd | Lyd / EQ per kilde | `tab:1` |
| 13-rom | Ditt system, rom og grupper | `tab:2` |
| 14-yt-music | YouTube Music-bibliotek | `sub:'lib', lib:'ytm'` |
| 15-navidrome | Navidrome-bibliotek | `sub:'lib', lib:'nd'` |
| 16-radio | Radio (oppdag) | `sub:'radio'` |
| 17-radio-sok | Radio, søk | `sub:'radio', q:'jazz'` |
| 18-innstillinger | Innstillinger | `tab:3` |
| 19-innst-radio-favoritter | Innstillinger → Radio (favoritter, legg til URL) | `tab:3, setCat:<radio>` |
| 20-innst-equalizer | Innstillinger → Equalizer | `tab:3, setCat:0` |

Åpne designfilen i nettleseren og kjør `window.__skjoldApp.setState({...})` i konsollen for å se en hvilken som helst tilstand.
