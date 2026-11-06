# Dokumentasjon

- `KI_Pultforsterker_Bildeveiledning.pdf` – LEGO-stil, steg 0–16 med 3D-bilder og lodde-nærbilder. Skriv ut dobbeltsidig.
- `KI_Pultforsterker_Byggeveiledning.pdf` / `byggeveiledning.md` – tekstveiledning med alle koblingstabellene.
- `steg/` – alle stegbildene og nærbildene. `bilder/` – planer, oppriss og renders.

## Skjold Kassett

NFC-kassettspiller som starter radio, NRK, Navidrome, Music Assistant eller rutiner. Bygg, kobling og lisens: [kabinett/kassett/LES_MEG.md](../kabinett/kassett/LES_MEG.md). API: `GET /api/nfc`, `POST /api/nfc/{scan,remove,cards,learn}`, `DELETE /api/nfc/cards/{uid}`.
