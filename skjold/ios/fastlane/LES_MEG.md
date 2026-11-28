# App Store-oppføringen (fastlane)

Alt som står på App Store-siden til Skjold Lab ligger her:

| Fil/mappe | Hva |
|---|---|
| `metadata/no/`, `metadata/en-GB/` | Navn, undertittel, reklametekst, beskrivelse, nøkkelord og nettadresser (norsk og engelsk) |
| `metadata/*.txt` | Opphavsrett og kategorier (Musikk, Verktøy) |
| `review_notes.txt` | Merknader til App Review (demomodus, tillatelser, kontosletting) |
| `screenshots/no/`, `screenshots/en-GB/` | Skjermbilder. Størrelsen bestemmer enheten (iPhone 6,9″, iPad 13″, Apple Watch). Lages med `.github/workflows/ios-skjermbilder.yml` |
| `personvern.json` | Svarene i «Personvern i appen» (App Privacy) |
| `Deliverfile`, `Fastfile`, `Appfile` | Oppsettet til fastlane |

## Last opp (på Macen)

```
brew install fastlane
cd skjold/ios
export REVIEW_PHONE="+47 …"          # telefonnummeret ditt, bare Apple ser det
fastlane appstore                     # tekster, nettadresser, gjennomgangsinfo og skjermbilder
fastlane personvern                   # «Personvern i appen»
```

Første gang spør fastlane om Apple-ID, passord og tofaktorkode. Det lagres i nøkkelringen på Macen, ikke i repoet.

**Gjøres for hånd i App Store Connect** (fastlane kan ikke, eller det tar ett minutt):
- **Aldersgrense:** svar «Ingen» på alt, som gir 4+.
- **Priser og tilgjengelighet:** Gratis, og velg land.
- **Bygg:** velg bygget fra TestFlight under versjonen.

## Send inn

```
fastlane send_inn
```

Velger nyeste bygg og sender versjonen til App Review. Når den er godkjent, trykker du **Gi ut denne versjonen** i App Store Connect.
