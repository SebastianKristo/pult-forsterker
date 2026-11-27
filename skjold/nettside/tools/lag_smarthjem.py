#!/usr/bin/env python3
"""Lager smarthjem/index.html (norsk) og en/smart-home/index.html (engelsk): apper og integrasjoner fra Skjold Lab
for Homey og Home Assistant. Rediger APPER/HA/KORT/PROGRAMVARE under og kjør:  python3 tools/lag_smarthjem.py
Hode, meny og bunn hentes fra programvare/index.html og en/software/index.html, så stilen følger resten av siden."""
import html
import os
import re

HER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH = "https://github.com/SebastianKristo/"
HACS = "https://my.home-assistant.io/redirect/hacs_repository/?owner=SebastianKristo&repository={}&category={}"

# Hver oppføring: (kategori, navn, {nb, en}: (ingress, [punkter]), [(lenketekst nb, lenketekst en, url)])
L = lambda nb, en, url: (nb, en, url)
HOMEY = [
    ("SKJOLD · HOMEY", "Skjold for Homey",
     {"nb": ("Styr Skjold S1, Node, Touch, Core, Røst, Kassett, Hjul, Stav og Skjold Sensor fra Homey, og bruk dem i Flow. Alt går over det lokale nettverket.",
             ["Kilde, volum, spiller nå med albumbilde, radiokanaler og equalizer",
              "Skjold Sensor: temperatur, fukt, lys, bevegelse og tilstedeværelse",
              "Finner enhetene selv, eller legg dem til med IP-adresse"]),
      "en": ("Control Skjold S1, Node, Touch, Core, Røst, Kassett, Hjul, Stav and Skjold Sensor from Homey, and use them in Flows. Everything runs on your local network.",
             ["Source, volume, now playing with album art, radio stations and equalizer",
              "Skjold Sensor: temperature, humidity, light, motion and presence",
              "Finds devices automatically, or add them by IP address"])},
     [L("Kildekode", "Source code", GH + "pult-forsterker/tree/main/homey/no.kristo.skjold")]),
    ("HOMEY · VANNING", "OpenSprinkler for Homey",
     {"nb": ("Styr vanningsanlegget fra Homey. Appen kobler en OpenSprinkler-kontroller til Homey Pro over det lokale nettverket, uten sky.",
             ["Hver sone blir en egen enhet, med start, stopp, nedtelling og hurtigknapper for 5–60 minutter",
              "Se og endre programmene: dager, starttider (også soloppgang og solnedgang) og kjøretid per sone",
              "Regnpause, vannivå, regnsensor og full Flow-støtte",
              "Vannforbruk per sone fra en vannmåler i Homey, også i Homey Energi",
              "Slår på hovedventilen når en sone starter, og to widgets til dashbordet"]),
      "en": ("Control your irrigation from Homey. The app connects an OpenSprinkler controller to Homey Pro over your local network, with no cloud.",
             ["Every zone becomes its own device, with start/stop, countdown and quick buttons for 5–60 minutes",
              "View and edit programs: days, start times (including sunrise and sunset) and run time per zone",
              "Rain delay, water level, rain sensor and full Flow support",
              "Per-zone water usage from a Homey water meter, also in Homey Energy",
              "Opens a master valve when a zone starts, and two dashboard widgets"])},
     [L("Homey App Store", "Homey App Store", "https://homey.app/a/no.kristo.opensprinkler/"),
      L("Testversjon", "Test version", "https://homey.app/a/no.kristo.opensprinkler/test/"),
      L("Kildekode", "Source code", GH + "homey-opensprinkler")]),
    ("HOMEY · LYS", "Smart utelys",
     {"nb": ("Utelys som tennes og slukkes til riktig tid hele året. Appen regner ut hvor sola står der du bor, også midnattssol og mørketid, så du slipper å justere klokkeslett.",
             ["Tenn ved solnedgang, i skumringen eller når det er helt mørkt, og finjuster",
              "Nattpause som slukker om natten og tenner igjen om morgenen hvis det er mørkt",
              "Lyssensor for mørke, overskyede dager, statusenhet og egne flowkort",
              "Respekterer manuell styring til neste skifte mellom lyst og mørkt"]),
      "en": ("Outdoor lights that turn on and off at the right time all year. The app works out where the sun is for your location, including midnight sun and polar night, so you never adjust times.",
             ["Turn on at sunset, at dusk or when fully dark, and fine-tune",
              "Night pause that turns lights off overnight and back on in the morning if it is still dark",
              "Light sensor for dark, cloudy days, a status device and Flow cards",
              "Respects manual control until the next switch between light and dark"])},
     [L("Testversjon", "Test version", "https://homey.app/a/no.kristo.utelys/test/"),
      L("Kildekode", "Source code", GH + "homey-utelys")]),
    ("HOMEY · ENERGI", "KI Energi for Homey",
     {"nb": ("Energistyring for norske hjem. Viser hva strømmen faktisk koster, og styrer varme, varmtvannsbereder og elbillading så du holder deg under kapasitetstrinnet og bruker strømmen når den er billig.",
             ["Strømkalkulator: nettleie for 76 nettselskap, kapasitetstrinn, strømstøtte og Norgespris",
              "Selvlærende varmestyring som planlegger 36 timer fram etter pris og værvarsel",
              "Varmtvannsbereder i de billigste timene, hjemme/borte og elbillading",
              "Skyggemodus: viser hva den ville gjort før den får styre"]),
      "en": ("Energy management for Norwegian homes. Shows what electricity really costs, and controls heating, water heater and EV charging so you stay below the capacity tier and use power when it is cheap.",
             ["Electricity calculator: grid tariffs for 76 Norwegian grid companies, capacity tiers, subsidy and Norgespris",
              "Self-learning heating that plans 36 hours ahead from price and weather forecast",
              "Water heater in the cheapest hours, home/away and EV charging",
              "Shadow mode: shows what it would do before it takes control"])},
     [L("Testversjon", "Test version", "https://homey.app/a/no.kristo.kienergi/test/"),
      L("Dokumentasjon", "Documentation", GH + "ki-strom/tree/main/homey")]),
    ("HOMEY · LÅS", "Yale lokal Bluetooth",
     {"nb": ("Styr Yale Doorman L3 og andre Yale- og August-låser direkte over Bluetooth fra Homey, uten sky og uten bro.",
             ["Lås og lås opp lokalt, med låsstatus, batterinivå og varsel om lavt batteri",
              "«Alltid tilkoblet» gir nesten umiddelbar låsing",
              "Kan gå via ESPHome Bluetooth-proxyer når Homey står langt fra døra",
              "Viser hvem som låste opp og hvordan"]),
      "en": ("Control Yale Doorman L3 and other Yale and August locks directly over Bluetooth from Homey, with no cloud and no bridge.",
             ["Lock and unlock locally, with lock state, battery level and low-battery alerts",
              "«Always connected» gives near-instant locking",
              "Can go through ESPHome Bluetooth proxies when Homey is far from the door",
              "Shows who unlocked and how"])},
     [L("Testversjon", "Test version", "https://homey.app/a/no.kristo.yaleble/test/"),
      L("Kildekode", "Source code", GH + "homey-yale_doorman_bluetooth")]),
    ("HOMEY · ADGANG", "UniFi dørtilgang",
     {"nb": ("Lås opp hvilken som helst dør i Homey med ansiktsgjenkjenning fra UniFi Protect, eller fingeravtrykk og NFC fra UniFi Access.",
             ["Regler per person og metode, uten Flow: dører, ukedager og når regelen er av",
              "Kan kreve at personen er hjemme",
              "Tilgangslogg, også i Home Assistant",
              "Låser ikke opp ved feil person, avviste forsøk eller utenfor tillatte tider"]),
      "en": ("Unlock any door in Homey with face recognition from UniFi Protect, or fingerprint and NFC from UniFi Access.",
             ["Rules per person and method, without Flow: doors, weekdays and when the rule is off",
              "Can require the person to be at home",
              "Access log, also in Home Assistant",
              "Never unlocks for the wrong person, rejected attempts or outside allowed times"])},
     [L("Testversjon", "Test version", "https://homey.app/a/no.kristo.unifiaccess/test/"),
      L("Kildekode", "Source code", GH + "homey-yale_doorman_bluetooth")]),
    ("HOMEY · MUSIKK", "Squeezebox for Homey",
     {"nb": ("Gi Squeezebox Radio, Boom og Touch nytt liv i smarthjemmet, via den gratis musikkserveren Lyrion Music Server.",
             ["Av/på, spill og pause, spor og volum, og hva som spilles, med albumbilde, også nettradio",
              "Presetknapper 1–6, alarmer, bass, diskant og lysstyrke",
              "Flows for sporbytte, favoritter, radiostrømmer og synkronisering av rom",
              "Finner Lyrion-serveren selv, og støtter flere servere"]),
      "en": ("Give Squeezebox Radio, Boom and Touch a new life in your smart home, through the free Lyrion Music Server.",
             ["Power, play/pause, tracks and volume, and what is playing with album art, including internet radio",
              "Preset buttons 1–6, alarms, bass, treble and display brightness",
              "Flows for track changes, favourites, radio streams and syncing rooms",
              "Finds the Lyrion server automatically and supports several servers"])},
     [L("Homey App Store", "Homey App Store", "https://homey.app/a/no.kristo.squeezebox/"),
      L("Testversjon", "Test version", "https://homey.app/a/no.kristo.squeezebox/test/"),
      L("Kildekode", "Source code", GH + "homey-squeezebox")]),
    ("HOMEY · HOME ASSISTANT", "Mac Bridge",
     {"nb": ("Styr Mac-en eller Windows-PC-en fra Homey og Home Assistant: medier, volum, strøm og statistikk, over det lokale nettverket.",
             ["Spiller nå fra Musikk og Spotify, med albumbilde",
              "Vekk, dvale, lås skjermen, restart og slå av",
              "CPU, minne, disk, batteri, og tekst-til-tale og varsler på maskinen"]),
      "en": ("Control your Mac or Windows PC from Homey and Home Assistant: media, volume, power and statistics, over your local network.",
             ["Now playing from Music and Spotify, with album art",
              "Wake, sleep, lock screen, restart and shut down",
              "CPU, memory, disk, battery, plus text-to-speech and notifications on the computer"])},
     [L("Kildekode", "Source code", GH + "homey-homeassistant-mac")]),
    ("HOMEY · ESPHOME", "ESPHome Relévifte",
     {"nb": ("Vifter med flere hastigheter på et ESP32-relékort med ESPHome, for eksempel Ultimate Fan Project, rett i Homey. Finnes automatisk, uten endringer i ESPHome.", []),
      "en": ("Multi-speed fans on an ESP32 relay board with ESPHome, such as the Ultimate Fan Project, right in Homey. Found automatically, with no ESPHome changes.", [])},
     [L("Kildekode", "Source code", GH + "homey-apps/tree/main/esphome-fan")]),
]
HA = [
    ("SKJOLD", "Skjold for Home Assistant", "Alle Skjold-enhetene som mediespillere, med kilder, equalizer, Skjold Sensor, oppdateringer og stemmestyring.",
     "All Skjold devices as media players, with sources, equalizer, Skjold Sensor, updates and voice control.", "pult-forsterker", "integration"),
    ("ENERGI", "KI Energi", "Selvlærende energi- og klimastyring for norske hjem med kapasitetsbasert nettleie. Fjernkontroll for Homey-appen, eller frittstående.",
     "Self-learning energy and climate control for Norwegian homes with capacity-based grid tariffs. A remote for the Homey app, or standalone.", "ki-strom", "integration"),
    ("ENERGI", "KI Enhetsforbruk", "Strømforbruk og kostnad per enhet, med spotpris og Norgespris, for i dag og denne måneden.",
     "Electricity use and cost per device, with spot price and Norgespris, for today and this month.", "ki-enhetsforbruk", "integration"),
    ("LYS", "KI Lys", "Lysscener per rom, laget automatisk: velg rommene, og integrasjonen gir hvert lys en rolle og lager scenene.",
     "Light scenes per room, made automatically: pick the rooms, and each light gets a role and the scenes are built for you.", "ki-lys", "integration"),
    ("LYS", "KI Utelys", "Utelys som en fotocelle, tilpasset norske sommernetter. Solhøyden avgjør, ikke klokka.",
     "Outdoor lights like a photocell, tuned for Norwegian summer nights. The sun's elevation decides, not the clock.", "ki-utelys", "integration"),
    ("HJEM", "KI Rom", "Tellere for hvert rom: hvor mange lys som er på, effekt og aktive sensorer, til dashbord og automasjoner.",
     "Counters for every room: lights on, power and active sensors, for dashboards and automations.", "ki-rom", "integration"),
    ("HJEM", "KI Nattmodus", "Én bryter setter huset i nattmodus: slår av TV og lys, tenner nattlys, låser og lukker gardiner.",
     "One switch puts the house in night mode: turns off TV and lights, turns on night lights, locks doors and closes blinds.", "ki-nattmodus", "integration"),
    ("HJEM", "KI Søvn & Vekking", "Avgjør om en person sover, og vekker med lys som fades opp til vekketid per ukedag.",
     "Works out whether a person is asleep, and wakes you with light that fades up to your wake time per weekday.", "ki-sovn", "integration"),
    ("SIKKERHET", "KI Varslinger og sikkerhet", "Varsler med oppsett i brukergrensesnittet: dør med kamerabilde, alarmer, iPhone- og Android-mottakere og testknapper.",
     "Notifications set up in the UI: door events with camera snapshots, alarms, iPhone and Android receivers and test buttons.", "ki-varslinger", "integration"),
    ("VANN", "KI Vann", "Hva går vannet til? Fordeler forbruket på dusj, toalett, oppvask, hvitevarer og utendørs, og lærer literprisen per hendelse.",
     "Where does the water go? Splits usage between shower, toilet, dishes, appliances and outdoors, and learns the litres per event.", "ki-vann", "integration"),
    ("VANN", "KI Vanning", "Forbruk, kostnad og estimat for OpenSprinkler, per sone, satt opp av seg selv.",
     "Usage, cost and estimates for OpenSprinkler, per zone, set up automatically.", "ki-vanning", "integration"),
    ("VANN", "KI Basseng", "Sirkulasjon, varme og spreder for bassenget: sparer strøm, men sørger for nok omsetning og tid til varmepumpen.",
     "Circulation, heating and dosing for a pool: saves power while keeping turnover and heat-pump time sufficient.", "ki-basseng", "integration"),
    ("HAGE", "KI Planter", "Vanningspåminnelser for planter, med ett sted per oppføring og så mange planter du vil.",
     "Watering reminders for plants, one place per entry and as many plants as you like.", "ki-planter", "integration"),
    ("HYTTE", "KI Hyttebesøk", "Hvem var på hytta, når og hvor lenge, ført automatisk til Google-kalenderen og lest tilbake som statistikk.",
     "Who was at the cabin, when and for how long, logged automatically to Google Calendar and read back as statistics.", "ki-hyttebes-k", "integration"),
]
KORT = [
    ("KORT", "KI Cards", "Alle Lovelace-kortene samlet i ett HACS-repo og én fil. Følger temaet, uten card-mod.",
     "All the Lovelace cards in one HACS repo and one file. Follows your theme, without card-mod.", "ki-cards", "plugin"),
    ("KORT", "KI Klima Strøm-kort", "Hele klima- og energisystemet fra KI Energi i ett kort: soner, timebudsjett, nettleie, varmtvann og beslutningslogg.",
     "The whole KI Energi climate and energy system in one card: zones, hourly budget, grid tariff, hot water and decision log.", "ki-klima-strom-kort", "plugin"),
    ("DASHBORD", "KI MSH", "My SmartHome v3-dashbordet for Home Assistant, med egne kort bygget for Bubble Card-popups.",
     "The My SmartHome v3 dashboard for Home Assistant, with custom cards built for Bubble Card popups.", "ki-msh", "integration"),
    ("DASHBORD", "KI Claude", "Et helt Home Assistant-dashbord som ett kort, koblet til KI-integrasjonene: hjem, strøm, klima, vanning og basseng.",
     "A complete Home Assistant dashboard as one card, wired to the KI integrations: home, energy, climate, irrigation and pool.", "ki-claude", "plugin"),
]
PROGRAMVARE = [
    ("SELVHOSTET", "Skjold Stack", "Et selvhostet homelab-dashbord med dra-og-slipp-editor, uten YAML. Én Docker-container for Unraid, TrueNAS, Portainer og Proxmox.",
     "A self-hosted homelab dashboard with a drag-and-drop editor, no YAML. One Docker container for Unraid, TrueNAS, Portainer and Proxmox.", "glass-dash", None),
]

T = {
    "nb": {"tittel": "Smarthjem – Skjold Lab", "beskr": "Apper og integrasjoner fra Skjold Lab for Homey og Home Assistant: energi, lys, låser, vanning, musikk og mer. Lokalt, uten sky.",
           "etikett": "SKJOLD LAB · APPER OG INTEGRASJONER", "h1": "Smarthjem",
           "ingress": "Skjold Lab lager apper og integrasjoner som gjør smarthjemmet enklere og smartere. De kjører lokalt hjemme hos deg, uten skytjenester eller abonnement, og koden er åpen.",
           "homey": "Homey-apper", "homey_p": "For Homey Pro. Testversjonene kan installeres av alle med lenken. App Store-lenkene virker når Athom har godkjent appen.",
           "ha": "Home Assistant-integrasjoner", "ha_p": "Installeres med HACS: trykk «Legg til i HACS», eller legg repoet til som egendefinert repo.",
           "kort": "Dashbord og kort", "prog": "Programvare",
           "hacs": "Legg til i HACS", "kilde": "Kildekode",
           "fot": "Appene og integrasjonene er uavhengige og ikke tilknyttet Athom (Homey), Nabu Casa (Home Assistant), OpenSprinkler, Yale, ASSA ABLOY, Ubiquiti (UniFi), Lyrion / LMS Community eller Logitech. Alle varemerker tilhører sine eiere. Strømkalkulatoren i KI Energi bygger på tariffer og beregningsregler fra <a href=\"https://github.com/fredrik-lindseth/Stromkalkulator\">Strømkalkulator for Home Assistant</a> av Fredrik Lindseth (MIT).",
           "url": "/smarthjem/", "andre": "/en/smart-home/"},
    "en": {"tittel": "Smart home – Skjold Lab", "beskr": "Apps and integrations from Skjold Lab for Homey and Home Assistant: energy, lighting, locks, irrigation, music and more. Local, no cloud.",
           "etikett": "SKJOLD LAB · APPS AND INTEGRATIONS", "h1": "Smart home",
           "ingress": "Skjold Lab makes apps and integrations that make the smart home simpler and smarter. They run locally in your home, with no cloud services or subscriptions, and the code is open.",
           "homey": "Homey apps", "homey_p": "For Homey Pro. Anyone with the link can install the test versions. App Store links work once Athom has approved the app.",
           "ha": "Home Assistant integrations", "ha_p": "Installed with HACS: press «Add to HACS», or add the repository as a custom repository.",
           "kort": "Dashboards and cards", "prog": "Software",
           "hacs": "Add to HACS", "kilde": "Source code",
           "fot": "The apps and integrations are independent and not affiliated with Athom (Homey), Nabu Casa (Home Assistant), OpenSprinkler, Yale, ASSA ABLOY, Ubiquiti (UniFi), Lyrion / LMS Community or Logitech. All trademarks belong to their owners. The electricity calculator in KI Energi builds on tariffs and calculation rules from <a href=\"https://github.com/fredrik-lindseth/Stromkalkulator\">Strømkalkulator for Home Assistant</a> by Fredrik Lindseth (MIT).",
           "url": "/en/smart-home/", "andre": "/smarthjem/"},
}
KAT_EN = {"ENERGI": "ENERGY", "LYS": "LIGHTING", "HJEM": "HOME", "SIKKERHET": "SECURITY", "VANN": "WATER", "HAGE": "GARDEN", "HYTTE": "CABIN",
          "KORT": "CARDS", "DASHBORD": "DASHBOARD", "SELVHOSTET": "SELF-HOSTED", "SKJOLD": "SKJOLD",
          "SKJOLD · HOMEY": "SKJOLD · HOMEY", "HOMEY · VANNING": "HOMEY · IRRIGATION", "HOMEY · LYS": "HOMEY · LIGHTING", "HOMEY · ENERGI": "HOMEY · ENERGY",
          "HOMEY · LÅS": "HOMEY · LOCKS", "HOMEY · ADGANG": "HOMEY · ACCESS", "HOMEY · MUSIKK": "HOMEY · MUSIC", "HOMEY · HOME ASSISTANT": "HOMEY · HOME ASSISTANT",
          "HOMEY · ESPHOME": "HOMEY · ESPHOME"}
NAVN_EN = {"Smart utelys": "Smart outdoor lights", "UniFi dørtilgang": "UniFi door access", "Yale lokal Bluetooth": "Yale local Bluetooth",
           "ESPHome Relévifte": "ESPHome relay fan", "KI Søvn & Vekking": "KI Sleep & Wake", "KI Varslinger og sikkerhet": "KI Notifications and security",
           "KI Enhetsforbruk": "KI Device consumption", "KI Planter": "KI Plants", "KI Hyttebesøk": "KI Cabin visits", "KI Nattmodus": "KI Night mode",
           "KI Rom": "KI Rooms", "KI Vann": "KI Water", "KI Vanning": "KI Irrigation", "KI Basseng": "KI Pool", "KI Lys": "KI Lights",
           "KI Utelys": "KI Outdoor lights", "KI Klima Strøm-kort": "KI Climate Energy card"}
e = html.escape
IMG = "/assets/img/smarthjem/"
# bilder: Homey-appene får butikkbildet sitt som banner, resten et ikon (assets/img/smarthjem/, laget fra repoene)
BANNER = {"Skjold for Homey": "skjold-homey", "OpenSprinkler for Homey": "opensprinkler", "Yale lokal Bluetooth": "yale",
          "UniFi dørtilgang": "unifi", "Squeezebox for Homey": "squeezebox", "KI Energi for Homey": "kienergi-homey",
          "ESPHome Relévifte": "esphomefan"}
IKON = {"Mac Bridge": "macbridge", "Skjold for Home Assistant": "skjold-ha", "KI Energi": "ki-strom", "KI Lys": "ki-lys",
        "KI Utelys": "ki-utelys", "KI Rom": "ki-rom", "KI Nattmodus": "ki-nattmodus", "KI Søvn & Vekking": "ki-sovn",
        "KI Varslinger og sikkerhet": "ki-varslinger", "KI Vanning": "ki-vanning", "KI Basseng": "ki-basseng",
        "KI Planter": "ki-planter", "KI Hyttebesøk": "ki-hyttebes-k", "KI Cards": "ki-cards", "KI Klima Strøm-kort": "ki-klima-strom-kort",
        "KI MSH": "ki-msh", "Skjold Stack": "glass-dash"}
# monogram (to bokstaver) og farge der repoet ikke har eget ikon
MONO = {"KI Enhetsforbruk": ("kWh", "#2d6a8f", "#173a52"), "KI Vann": ("H₂O", "#2f7fa8", "#123447"), "KI Claude": ("KI", "#8a5cf6", "#2b1d52"),
        "Smart utelys": ("", "#26315c", "#0d1226")}
UTELYS_SVG = ('<svg viewBox="0 0 960 960" width="84" height="84" aria-hidden="true"><path fill="#f4d58d" d="M480 120c-110 0-200 90-200 200 0 75 40 125 80 170 25 28 40 60 40 100h160c0-40 15-72 40-100 40-45 80-95 80-170 0-110-90-200-200-200zm-80 520v50c0 22 18 40 40 40h80c22 0 40-18 40-40v-50zM720 160a90 90 0 1 0 90 90 70 70 0 1 1-90-90zM200 700h560v40H200z"/></svg>')

CSS = """<style>
.sh-topp{padding:150px 22px 40px;text-align:center;display:flex;flex-direction:column;align-items:center}
.sh-topp .etikett{position:static;margin:0 auto}
.sh-topp h1{font-family:var(--sora);font-size:clamp(46px,8vw,96px);font-weight:600;letter-spacing:-.045em;line-height:1;margin:14px 0 0}
.sh-topp .ingress{margin:22px auto 0;max-width:680px;font-size:19px;line-height:1.5;color:var(--demp-l)}
.sh-chips{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:24px}
.sh-chip{font-family:var(--mono);font-size:11.5px;letter-spacing:.12em;padding:7px 12px;border-radius:999px;border:1px solid var(--linje);color:var(--demp-l);background:rgba(255,255,255,.02)}
.sh-plattformer{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:14px;max-width:1100px;margin:44px auto 0;padding:0 22px}
.sh-pl{position:relative;display:flex;align-items:center;gap:18px;padding:22px 24px;border-radius:var(--r);border:1px solid var(--linje);background:linear-gradient(135deg,rgba(255,255,255,.04),rgba(255,255,255,.01));text-decoration:none;color:inherit;transition:border-color .4s,transform .6s var(--ut)}
.sh-pl:hover{border-color:rgba(217,164,65,.4);transform:translateY(-3px)}
.sh-pl .tall{font-family:var(--sora);font-size:44px;font-weight:600;letter-spacing:-.04em;line-height:1;color:var(--gull)}
.sh-pl b{display:block;font-family:var(--sora);font-size:19px;font-weight:600}
.sh-pl span{font-size:14px;color:var(--demp-l)}
.sh-filter{position:sticky;top:64px;z-index:5;display:flex;gap:6px;justify-content:center;flex-wrap:wrap;padding:14px 22px;margin-top:40px;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);background:rgba(8,8,9,.6);border-top:1px solid var(--linje);border-bottom:1px solid var(--linje)}
.sh-filter button{font:inherit;font-size:14px;padding:8px 16px;border-radius:999px;border:1px solid var(--linje);background:transparent;color:var(--demp-l);cursor:pointer;transition:all .3s}
.sh-filter button[aria-pressed=true]{background:var(--gull);border-color:var(--gull);color:#111;font-weight:600}
.sh-seksjon{max-width:1240px;margin:0 auto;padding:70px 22px 10px}
.sh-seksjon h2{font-family:var(--sora);font-size:clamp(30px,4.5vw,46px);font-weight:600;letter-spacing:-.035em;margin:0}
.sh-seksjon .under{margin:10px 0 30px;max-width:720px;font-size:16px;line-height:1.55;color:var(--demp-l)}
.sh-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:16px}
.sh-grid.sma{grid-template-columns:repeat(auto-fill,minmax(min(100%,290px),1fr))}
.sh-kort{position:relative;display:flex;flex-direction:column;border-radius:20px;border:1px solid var(--linje);background:var(--kort);overflow:hidden;transition:border-color .4s,transform .6s var(--ut),box-shadow .6s}
.sh-kort:hover{border-color:rgba(217,164,65,.35);transform:translateY(-4px);box-shadow:0 24px 60px -30px rgba(0,0,0,.8)}
.sh-banner{position:relative;aspect-ratio:10/6;overflow:hidden;background:#141416}
.sh-banner img{width:100%;height:100%;object-fit:cover;display:block;transition:transform 1.2s var(--ut)}
.sh-kort:hover .sh-banner img{transform:scale(1.04)}
.sh-banner::after{content:"";position:absolute;inset:auto 0 0 0;height:55%;background:linear-gradient(to top,var(--kort),transparent)}
.sh-banner.tegnet{display:grid;place-items:center}
.sh-banner.tegnet img{width:96px;height:96px;object-fit:contain;border-radius:22px;box-shadow:0 18px 40px -14px rgba(0,0,0,.7)}
.sh-innhold{display:flex;flex-direction:column;gap:10px;padding:4px 24px 24px;flex:1}
.sh-merker{display:flex;gap:6px;flex-wrap:wrap}
.sh-merke{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;padding:4px 9px;border-radius:999px;border:1px solid var(--linje);color:var(--demp-l)}
.sh-merke.homey{color:#e9c46a;border-color:rgba(233,196,106,.35)}
.sh-merke.ha{color:#58b7f0;border-color:rgba(88,183,240,.35)}
.sh-merke.test{color:#9fd49f;border-color:rgba(159,212,159,.3)}
.sh-kort h3{font-family:var(--sora);font-size:23px;font-weight:600;letter-spacing:-.025em;line-height:1.15;margin:2px 0 0}
.sh-kort p{margin:0;font-size:15px;line-height:1.55;color:var(--demp-l)}
.sh-kort ul{margin:2px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:7px}
.sh-kort li{position:relative;padding-left:20px;font-size:14px;line-height:1.5;color:var(--demp-l)}
.sh-kort li::before{content:"";position:absolute;left:2px;top:.62em;width:7px;height:7px;border-radius:50%;background:var(--gull);opacity:.75}
.sh-knapper{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px}
.sh-knapp{display:inline-flex;align-items:center;gap:7px;font-size:14px;font-weight:500;padding:9px 15px;border-radius:999px;border:1px solid var(--linje);color:inherit;text-decoration:none;transition:all .3s}
.sh-knapp:hover{border-color:var(--gull);color:var(--gull)}
.sh-knapp.primar{background:var(--gull);border-color:var(--gull);color:#111}
.sh-knapp.primar:hover{filter:brightness(1.08);color:#111}
.sh-knapp svg{width:15px;height:15px}
.sh-rad{flex-direction:row;align-items:flex-start;gap:16px;padding:20px}
.sh-rad .sh-innhold{padding:0;gap:8px}
.sh-ikon{flex:0 0 64px;width:64px;height:64px;border-radius:16px;overflow:hidden;box-shadow:0 10px 26px -12px rgba(0,0,0,.8)}
.sh-ikon img{width:100%;height:100%;display:block}
.sh-mono{display:grid;place-items:center;font-family:var(--sora);font-weight:600;font-size:19px;color:#fff;letter-spacing:-.02em}
.sh-rad h3{font-size:19px}
.sh-rad .sh-knapp{padding:7px 13px;font-size:13px}
.sh-rad .sh-knapper{gap:6px}
.sh-rad p{font-size:14.5px}
.sh-fot{max-width:1240px;margin:0 auto;padding:60px 22px 100px}
.sh-fot p{max-width:780px;font-size:13.5px;line-height:1.65;color:var(--demp-l)}
.sh-fot a{color:var(--demp-l)}
[data-sh-skjult]{display:none!important}
@media (max-width:600px){.sh-topp{padding-top:120px}.sh-filter{top:56px}.sh-rad{padding:16px}}
</style>"""
GH_SVG = '<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'
PIL_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v12m0 0l-5-5m5 5l5-5M5 20h14"/></svg>'


def knapp(tekst, url, primar=False):
    ikon = GH_SVG if "github.com" in url else PIL_SVG
    return f'<a class="sh-knapp{" primar" if primar else ""}" href="{e(url)}">{ikon}{e(tekst)}</a>'


def bilde_ikon(navn):
    if navn in IKON:
        return f'<div class="sh-ikon"><img src="{IMG}{IKON[navn]}.webp" alt="" width="64" height="64" loading="lazy"></div>'
    t, a, b = MONO.get(navn, (navn[:2], "#444", "#222"))
    return f'<div class="sh-ikon sh-mono" style="background:linear-gradient(140deg,{a},{b})" aria-hidden="true">{e(t)}</div>'


def homey_kort(kat, navn, d, lenker, sprak, i):
    ingress, punkter = d[sprak]
    n = navn if sprak == "nb" else NAVN_EN.get(navn, navn)
    if navn in BANNER:
        banner = f'<div class="sh-banner"><img src="{IMG}{BANNER[navn]}.webp" alt="" width="500" height="350" loading="lazy"></div>'
    elif navn in IKON:
        banner = f'<div class="sh-banner tegnet" style="background:radial-gradient(circle at 50% 35%,#3a3f8f,#14152b)"><img src="{IMG}{IKON[navn]}.webp" alt="" loading="lazy"></div>'
    else:
        banner = f'<div class="sh-banner tegnet" style="background:radial-gradient(circle at 50% 30%,#2b3a73,#0b0f22)">{UTELYS_SVG}</div>'
    deler = [x for x in (kat if sprak == "nb" else KAT_EN.get(kat, kat)).split(" · ") if x not in ("HOMEY", "HOME ASSISTANT")]
    merker = '<span class="sh-merke homey">HOMEY</span>'
    if navn == "Mac Bridge":
        merker += '<span class="sh-merke ha">HOME ASSISTANT</span>'
    merker += "".join(f'<span class="sh-merke">{e(x)}</span>' for x in deler)
    if any("/test/" in u for _, _, u in lenker) and not any(u.endswith(".opensprinkler/") or u.endswith(".squeezebox/") for _, _, u in lenker):
        merker += f'<span class="sh-merke test">{"TESTVERSJON" if sprak == "nb" else "TEST VERSION"}</span>'
    ul = "".join(f"<li>{e(p)}</li>" for p in punkter[:4])
    ul = f"<ul>{ul}</ul>" if ul else ""
    kn = "".join(knapp(nb if sprak == "nb" else en, u, primar=(k == 0 and "github.com" not in u)) for k, (nb, en, u) in enumerate(lenker))
    return (f'<article class="sh-kort" data-plattform="homey{" ha" if navn == "Mac Bridge" else ""}" data-reveal="{(i % 3) * 80}">{banner}'
            f'<div class="sh-innhold"><div class="sh-merker">{merker}</div><h3>{e(n)}</h3><p>{e(ingress)}</p>{ul}'
            f'<div class="sh-knapper">{kn}</div></div></article>')


def rad_kort(kat, navn, nb, en, repo, hacs_kat, sprak, i, plattform):
    n = navn if sprak == "nb" else NAVN_EN.get(navn, navn)
    kat_t = kat if sprak == "nb" else KAT_EN.get(kat, kat)
    sti = GH + repo + ("/tree/main/custom_components/skjold" if repo == "pult-forsterker" else "")
    kn = ""
    if hacs_kat:
        kn += knapp("Legg til i HACS" if sprak == "nb" else "Add to HACS", HACS.format(repo, hacs_kat), primar=True)
    kn += knapp("Kildekode" if sprak == "nb" else "Source code", sti)
    pm = {"ha": '<span class="sh-merke ha">HOME ASSISTANT</span>', "kort": '<span class="sh-merke ha">LOVELACE</span>', "prog": '<span class="sh-merke">DOCKER</span>'}[plattform]
    return (f'<article class="sh-kort sh-rad" data-plattform="{plattform}" data-reveal="{(i % 3) * 80}">{bilde_ikon(navn)}'
            f'<div class="sh-innhold"><div class="sh-merker">{pm}<span class="sh-merke">{e(kat_t)}</span></div><h3>{e(n)}</h3>'
            f'<p>{e(nb if sprak == "nb" else en)}</p><div class="sh-knapper">{kn}</div></div></article>')


def seksjon(id_, tittel, tekst, kort, sma=False):
    under = f'<p class="under">{e(tekst)}</p>' if tekst else '<div style="height:26px"></div>'
    return (f'<section class="sh-seksjon" id="{id_}" data-seksjon="{id_}"><h2 data-reveal="0">{e(tittel)}</h2>{under}'
            f'<div class="sh-grid{" sma" if sma else ""}">{"".join(kort)}</div></section>')


FILTER_JS = """<script>
(function(){var k=document.querySelectorAll('.sh-filter button');k.forEach(function(b){b.addEventListener('click',function(){
k.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});var f=b.dataset.f;
document.querySelectorAll('.sh-kort').forEach(function(c){var p=c.dataset.plattform.split(' ');if(f==='alle'||p.indexOf(f)>=0)c.removeAttribute('data-sh-skjult');else c.setAttribute('data-sh-skjult','')});
document.querySelectorAll('[data-seksjon]').forEach(function(s){if(s.querySelector('.sh-kort:not([data-sh-skjult])'))s.removeAttribute('data-sh-skjult');else s.setAttribute('data-sh-skjult','')});
})})})();
</script>"""


def lag(sprak):
    t = T[sprak]
    mal = "programvare/index.html" if sprak == "nb" else "en/software/index.html"
    s = open(os.path.join(HER, mal), encoding="utf-8").read()
    hode, rest = s.split('<main id="hoved">', 1)
    bunn = rest.split("</main>", 1)[1]
    gammel_url = "/programvare/" if sprak == "nb" else "/en/software/"
    gammel_tittel = re.search(r"<title>(.*?)</title>", hode).group(1)
    gammel_beskr = re.search(r'<meta name="description" content="(.*?)">', hode).group(1)
    hode = hode.replace(gammel_tittel, t["tittel"]).replace(gammel_beskr, e(t["beskr"]))
    hode = hode.replace("https://skjold-lab.com/programvare/", "https://skjold-lab.com/smarthjem/").replace("https://skjold-lab.com/en/software/", "https://skjold-lab.com/en/smart-home/")
    hode = hode.replace('href="/programvare/" lang="nb"', 'href="/smarthjem/" lang="nb"').replace('href="/en/software/" lang="en"', 'href="/en/smart-home/" lang="en"')
    # menyen: «Smarthjem» er aktiv her, ikke programvare-siden malen kommer fra
    ny_lenke = '<a href="/smarthjem/">Smarthjem</a>' if sprak == "nb" else '<a href="/en/smart-home/">Smart home</a>'
    aktiv = ny_lenke.replace('">', '" aria-current="page">', 1)
    hode = hode.replace(ny_lenke, "")
    hode = re.sub(r'(<a href="' + re.escape(gammel_url) + r'") aria-current="page">([^<]+</a>)', lambda m: m.group(1) + ">" + m.group(2) + aktiv, hode, count=1)
    homey = [homey_kort(k, n, d, l, sprak, i) for i, (k, n, d, l) in enumerate(HOMEY)]
    ha = [rad_kort(*x, sprak, i, "ha") for i, x in enumerate(HA)]
    kort = [rad_kort(*x, sprak, i, "kort") for i, x in enumerate(KORT)]
    prog = [rad_kort(*x, sprak, i, "prog") for i, x in enumerate(PROGRAMVARE)]
    nb = sprak == "nb"
    pl = (f'<div class="sh-plattformer" data-reveal="120">'
          f'<a class="sh-pl" href="#homey"><div class="tall">{len(HOMEY)}</div><div><b>Homey Pro</b><span>{"apper" if nb else "apps"} · Flow · {"widgets"}</span></div></a>'
          f'<a class="sh-pl" href="#ha"><div class="tall">{len(HA)}</div><div><b>Home Assistant</b><span>{"integrasjoner via HACS" if nb else "integrations via HACS"}</span></div></a>'
          f'<a class="sh-pl" href="#kort"><div class="tall">{len(KORT)}</div><div><b>{"Dashbord og kort" if nb else "Dashboards and cards"}</b><span>Lovelace</span></div></a></div>')
    chips = "".join(f'<span class="sh-chip">{c}</span>' for c in (["LOKALT", "UTEN SKY", "ÅPEN KILDEKODE", "NORSK"] if nb else ["LOCAL", "NO CLOUD", "OPEN SOURCE", "MADE IN NORWAY"]))
    fl = [("alle", "Alle", "All"), ("homey", "Homey", "Homey"), ("ha", "Home Assistant", "Home Assistant"), ("kort", "Dashbord og kort", "Dashboards"), ("prog", "Programvare", "Software")]
    filt = '<nav class="sh-filter" aria-label="Filter">' + "".join(f'<button type="button" data-f="{f}" aria-pressed="{"true" if f == "alle" else "false"}">{e(a if nb else b_)}</button>' for f, a, b_ in fl) + "</nav>"
    main = (f'<main id="hoved">\n{CSS}\n<section class="sh-topp"><div class="etikett" data-reveal="0">{e(t["etikett"])}</div><h1 data-reveal="80">{e(t["h1"])}</h1>'
            f'<p class="ingress" data-reveal="120">{e(t["ingress"])}</p><div class="sh-chips" data-reveal="160">{chips}</div></section>\n{pl}\n{filt}\n'
            + seksjon("homey", t["homey"], t["homey_p"], homey) + "\n"
            + seksjon("ha", t["ha"], t["ha_p"], ha, sma=True) + "\n"
            + seksjon("kort", t["kort"], "", kort, sma=True) + "\n"
            + seksjon("prog", t["prog"], "", prog, sma=True) + "\n"
            + f'<section class="sh-fot"><p>{t["fot"]}</p></section>\n{FILTER_JS}\n')
    ut = os.path.join(HER, t["url"].strip("/"), "index.html")
    os.makedirs(os.path.dirname(ut), exist_ok=True)
    open(ut, "w", encoding="utf-8").write(hode + main + "</main>" + bunn)
    print("skrev", ut)


if __name__ == "__main__":
    lag("nb")
    lag("en")
