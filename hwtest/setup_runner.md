# Maskinvaretester på en ekte Skjold-Pi

`hwtest/` inneholder pytest-tester som kjører på en Raspberry Pi med Skjold installert. Pi-en er koblet til GitHub som *self-hosted runner*. Workflowen `.github/workflows/hwtest.yml` kjører dem:

- etter hver «Skjold release»
- manuelt (Actions → Maskinvaretest → Run workflow)
- på PR-er med etiketten **hw-test**

Hvis ingen runner er online, hoppes jobben over og blir grønn.

## 1. Koble til Pi-en (ca. 10 min)

1. På GitHub: **Settings → Actions → Runners → New self-hosted runner**. Velg Linux / ARM64 og kopier tokenet fra `--token …`.
2. På Pi-en, i en checkout av repoet:

   ```bash
   sudo bash hwtest/setup_runner.sh <TOKEN> sebastiankristo/pult-forsterker plughw:CODEC
   ```

   Det tredje argumentet er opptakskortet. Det kan utelates, og da hoppes lydtestene over.

   Skriptet gjør dette:
   - installerer numpy, pytest, matplotlib, alsa-utils og avahi-utils
   - lager brukeren `skjoldci` (i gruppen `audio`), som får passordløs sudo **bare** for `pi/update.sh` og `systemctl restart/is-active`
   - laster ned actions-runner for linux-arm64 og registrerer den med etiketten `skjold-hw`
   - installerer runneren som systemd-tjeneste
3. Sjekk at runneren står som **Idle** i listen.

## 2. Lydsløyfe (for lydtestene)

Testene spiller testsignaler gjennom ALSA `default`, altså hele kjeden med dmix, CamillaDSP, volum og EQ. Samtidig tar de opp fra `HWTEST_CAPTURE`.

- **Anbefalt:** DAC/forsterker-utgang → dempeledd (høyttalerutgang!, f.eks. 1:20 spenningsdeler) → linjeinngang på et USB-lydkort (Behringer UCA202 o.l.). `arecord -l` viser navnet, typisk `plughw:CODEC`.
  - Linjeutgang før forsterkeren kan kobles direkte.
- **Kun programvare:** `sudo modprobe snd-aloop` og `HWTEST_CAPTURE=hw:Loopback,1,0`. Dette tester DSP-kjeden, men ikke den analoge delen.

Valgfrie innstillinger legges i `/opt/actions-runner/.env`:

| Variabel | Betydning |
|---|---|
| `HWTEST_CAPTURE` | ALSA-opptaksenhet |
| `HWTEST_THDN_MAX` | THD+N-grense i dB, standard −40 |
| `HWTEST_RADIO_URL` | radiostrøm for radiotesten |
| `HWTEST_SERVICES` | kommaseparerte tjenester som skal være aktive |
| `HWTEST_RESTART=1` | tester også oppstartstid etter omstart av ki-amp |

## 3. Sikkerhet

En self-hosted runner kjører kode fra repoet med tilgang til hjemmenettet ditt. Derfor:

- **Hold repoet privat**, eller sett *Settings → Actions → General → Fork pull request workflows* til «Require approval for all outside collaborators».
- Workflowen kjører aldri for PR-er fra forks (`head.repo == repo`). Den kjører bare når etiketten `hw-test` er satt, og bare samarbeidspartnere kan sette den.
- Runneren går som egen bruker med begrenset sudo. Bruk den ikke til andre repoer.

## 4. Kjøre lokalt

```bash
SKJOLD_URL=http://127.0.0.1:8765 HWTEST_CAPTURE=plughw:CODEC python3 hwtest/run.py
```

Resultater havner i `hwtest-out/`: `junit.xml`, `summary.md`, opptak og PNG-spektre.

## 5. Slå på kjøringen i workflowen

`GITHUB_TOKEN` har ikke lov til å lese runner-listen. Gjør ett av disse:

- **Enklest:** Settings → Secrets and variables → Actions → *Variables* → `HWTEST_ENABLED` = `1`. Testene kjøres da alltid, og jobben venter i kø til Pi-en er online. Sett variabelen til `0` når Pi-en er frakoblet over lengre tid.
- **Automatisk:** Lag en fine-grained PAT med *Administration: read* på repoet og legg den som secret `HWTEST_RUNNER_TOKEN`. Da hoppes testen over av seg selv når ingen runner er online.
