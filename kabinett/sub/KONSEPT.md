# Skjold Sub – konsept

**Konsept, ikke ferdig produkt.** Mål og basstall er beregnet fra omtrentlige T/S-parametre fra produsentene. Simuler med elementets datablad i WinISD eller VituixCAD før du kutter, og mål etterpå med romkorreksjonen.

Dette er en trådløs subwoofer som byggesett. Den er en Skjold-enhet (Core) satt til **«Er sub»** i synk-motoren (`docs/MULTIROOM.md` §3):
- Den får lyden over nettverket fra hovedenheten.
- Den summerer L+R til mono og lavpassfiltrerer i CamillaDSP (LR4, 24 dB/oktav).
- Den spiller synkront.
- Hovedenheten høypassfiltrerer de andre høyttalerne.

## Hvorfor Pi og ikke ESP32
Synk-motoren (`pi/skjold_sync`) og delefilteret kjører i daemonen og CamillaDSP. Det krever Linux, så ESP32 med squeezelite (som Røst) holder ikke. **Raspberry Pi Zero 2 W** har nok kraft til en monokanal med LR4 og Linkwitz-transform, og den er billig. Pi 4 virker også.

## Varianter

| | Sub 8 | Sub 10 |
|---|---|---|
| Element | Dayton RSS210HF-4 (8″, aluminium, 4 Ω) | Dayton RSS265HF-4 (10″, 4 Ω) |
| Kasse (B×D×H) | 320 × 320 × 360 mm + føtter | 380 × 380 × 420 mm + føtter |
| Netto volum (lukket) | ca. 24 l | ca. 43 l |
| Qtc / fc (beregnet) | ca. 0,54 / 36 Hz | ca. 0,56 / 31 Hz |
| F3 uten EQ (beregnet) | ca. 50 Hz | ca. 42 Hz |
| F3 med Linkwitz-transform i Skjold (beregnet, moderat nivå) | ca. 28 Hz | ca. 24 Hz |
| Forsterker | TPA3255-kort (mono/PBTL), 36 V-forsyning | samme |
| Elektronikk | Pi Zero 2 W + I²S-DAC (PCM5102 eller DAC+ Zero) | samme |

Den lukkede kassen er valgt fordi den er kompakt, tåler EQ godt og gir god transientrespons. Med port ville kassen bli mye større for samme dybde.

## Kutteliste MDF 18 mm (lim og skru, avrund kantene med fres eller printede hjørnelister)

| Del | Sub 8 | Sub 10 | Antall |
|---|---|---|---|
| Topp/bunn | 320 × 320 | 380 × 380 | 2 |
| Sider | 320 × 324 | 380 × 384 | 2 |
| Front/bak | 284 × 324 | 344 × 384 | 2 |
| Utsparing for element (front) | Ø186 | Ø232 | |
| Åpning for elektronikkpanel (bak) | 140 × 110 | 140 × 110 | |

**Printede deler (K2):** mørk frontramme med gullring og SKJOLD-logo, bakpanel for elektronikk (TPA3255, Pi, strøm og bryter), fire føtter.

## Bilder
`render/sub8_samlet.png`, `sub8_eksplodert.png`, `sub8_snitt.png` og tilsvarende for `sub10`. Kilde: `skjold_sub.scad` (`-D variant="sub10"`, `-D part="eksplodert"`).

## Prisestimat (nov. 2026, ca.)
Sub 8: ca. 4 300 kr · Sub 10: ca. 5 790 kr (Sonos Sub Mini til sammenligning: ca. 4 990 kr). Detaljert tabell med kilder: artifact «Skjold Sub og Tårn».
