# Oppsett-nett: koble en Skjold-enhet til Wi-Fi uten skjerm og tastatur

Når en Skjold-enhet ikke har nett, lager den sitt eget Wi-Fi med en oppsettside. Det gjelder en ny enhet, en som er
tilbakestilt, og en som er flyttet til et sted der det lagrede nettet ikke finnes.

## Slik gjør du det

1. Vent til enheten har startet (ca. ett minutt). Nettet **Skjold-oppsett-XXXX** dukker opp på telefonen.
   XXXX er de fire siste tegnene i enhetens ID.
2. Koble telefonen til nettet. Passordet er `skjoldoppsett`.
3. Oppsettsiden åpner seg selv. Skjer det ikke, gå til `http://10.42.0.1:8765/oppsett`.
4. Velg hjemmenettet og skriv passordet.
5. Enheten slår av oppsett-nettet og kobler til. Koble telefonen tilbake til hjemmenettet og åpne Skjold-appen.

Kommer **Skjold-oppsett-XXXX** tilbake etter et minutt, var passordet feil. Koble til på nytt, så står feilmeldingen
øverst på siden.

## Når starter det?

| Situasjon | Hva skjer |
|---|---|
| Ingen lagrede Wi-Fi-nett og ingen nettverkskabel | Oppsett-nettet starter 45 sekunder etter oppstart |
| Lagrede nett, men uten nett i 3 minutter | Oppsett-nettet starter |
| Lagrede nett, og ingen bruker oppsettsiden | Enheten slår av oppsett-nettet hvert 5. minutt og prøver de lagrede nettene igjen |
| Nettverkskabel settes i, eller Wi-Fi kobler til | Oppsett-nettet slås av |

Skjold Touch viser nettnavnet og passordet på skjermen mens oppsett-nettet er på. `GET /api/status` har feltet
`setup_net` med `ssid`, `password`, `url` og `qr` (teksten til en Wi-Fi-QR-kode).

## Tilbakestilling

Holder du power-knappen på S1 i 10 sekunder, slettes innstillingene, Blåtann-paringene og de lagrede Wi-Fi-nettene.
Etter omstart starter oppsett-nettet. `KI_AMP_RESET_WIFI=0` i `/etc/ki-amp.env` beholder Wi-Fi-nettene.

## Slå av

Sett `KI_AMP_SETUP_NET=0` i `/etc/ki-amp.env` og start `ki-amp` på nytt. Da lager enheten aldri sitt eget nett.

## Teknisk

- Aksesspunktet lages med NetworkManager (`nmcli device wifi hotspot`), WPA2, adresse `10.42.0.1`.
- Alle DNS-oppslag svarer med enhetens adresse (`/etc/NetworkManager/dnsmasq-shared.d/skjold-oppsett.conf`), og port 80
  sender videre til oppsettsiden. Slik oppdager telefonen at nettet har en påloggingsside.
- Port 80 sender ellers videre til web-appen, så `http://<navn>.local` virker uten `:8765`.
- Koden ligger i `pi/skjold_setupnet.py`, med tester i `pi/tests/test_setupnet.py`.

Ikke prøvd på ekte maskinvare ennå. Det som bør sjekkes: at telefonen åpner oppsettsiden av seg selv, og at Pi-en
finner nett i nærheten mens den selv er aksesspunkt (listen skannes rett før aksesspunktet starter).
