# Skjold Tårn – konsept

**Konsept, ikke ferdig produkt.** Mål og basstall er beregnet fra omtrentlige T/S-parametre. Simuler før du kutter, og bygg delefilteret etter en kjent oppskrift for elementparet eller med aktiv deling.

Dette er et par gulvhøyttalere å bygge selv.
- **Drives av:** Skjold S1 (2 × 40 W) direkte, eller Node med ekstern forsterker.
- **Etter bygging:** mål dem med **Skjold Sertifisert**, som gir en EQ-profil for akkurat dine høyttalere. Profilen deles i profildatabasen, så andre som bygger samme Tårn får en ferdig profil.
- **Sammen med Skjold Sub:** blir det et 2.1-oppsett.

## Varianter

| | Tårn (2-veis) | Tårn Pro (2,5-veis) |
|---|---|---|
| Elementer per side | 1 × SB Acoustics SB17NRX2C35-8 (6,5″) + SB26STAC-C000-4 (26 mm tweeter) | 2 × SB17NRX2C35-8 + SB26STAC |
| Kasse (B×D×H) | 200 × 260 × 980 mm + sokkel 30 mm og pigger | 200 × 300 × 980 mm + sokkel |
| Netto volum | ca. 32 l | ca. 38 l |
| Tuning / port | ca. 35 Hz, port Ø50 × ca. 110 mm bak | ca. 32 Hz, Ø50 |
| F3 (beregnet) | ca. 40 Hz | ca. 36–38 Hz |
| Delefilter | passivt, 2. orden ved ca. 2–2,5 kHz, med L-pad for tweeteren | passivt; nederste bass rulles av ved ca. 300–400 Hz |
| Følsomhet (anslag) | ca. 86–87 dB | ca. 88–89 dB |

Tweeteren er på 4 Ω og bass-mellomtonen på 8 Ω. Det jevnes ut med L-pad i filteret.
- **Aktiv deling:** S1 har to kanaler. Aktiv deling krever derfor fire forsterkerkanaler, med to S1-er eller en 4-kanals TPA3255.
- **Anbefalt start:** passivt filter, deretter Skjold Sertifisert og romkorreksjon.

## Kutteliste per kasse, MDF 18 mm (Tårn; Pro i parentes)

| Del | Mål (mm) | Antall |
|---|---|---|
| Sider | 980 × 260 (300) | 2 |
| Front/bak | 980 × 164 | 2 |
| Topp/bunn | 164 × 224 (264) | 2 |
| Avstiver (midt) | 164 × 224 (264), med hull Ø100 | 1–2 |
| Utsparinger front | tweeter Ø75, bass Ø146 (× 2 i Pro) | |
| Bak | port Ø50, terminalpanel 70 × 70 | |

**Printede deler (K2):** frontplate eller frontramme i mørk farge med gullstripe og SKJOLD, sokkel i deler, portflare, terminalpanel og lister.

## Bilder
`render/taarn_samlet.png`, `taarn_par.png`, `taarn_eksplodert.png`, `taarn_snitt.png` og tilsvarende for `pro_*`. Kilde: `skjold_taarn.scad`.

## Prisestimat per par (nov. 2026, ca.)
Tårn: ca. 6 590 kr · Tårn Pro: ca. 8 970 kr (uten S1/Node). Ferdige gulvhøyttalere i samme klasse: ca. 10 000–20 000 kr per par (anslag).
