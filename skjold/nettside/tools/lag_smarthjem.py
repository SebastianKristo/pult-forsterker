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
LENKE = 'style="display:inline-flex;align-items:center;gap:6px;font-size:14.5px;color:var(--gull);text-decoration:none;margin-right:16px"'


def flis(kat, navn, ingress, punkter, lenker, sprak, d):
    k = kat if sprak == "nb" else KAT_EN.get(kat, kat)
    n = navn if sprak == "nb" else NAVN_EN.get(navn, navn)
    ul = "".join(f"<li>{e(p)}</li>" for p in punkter)
    ul = f'<ul style="margin:4px 0 0;padding-left:18px;font-size:14.5px;line-height:1.55;color:var(--demp-l)">{ul}</ul>' if ul else ""
    ln = "".join(f'<a {LENKE} href="{e(u)}">{e(nb if sprak == "nb" else en)} ›</a>' for nb, en, u in lenker)
    return (f'<div class="flis" data-reveal="{d}"><div class="k">{e(k)}</div><h3 class="h" style="font-size:22px">{e(n)}</h3>'
            f'<p class="p">{e(ingress)}</p>{ul}<div style="margin-top:auto;padding-top:10px">{ln}</div></div>')


def seksjon(tittel, tekst, fliser, lys=False):
    p = f'<p style="margin:8px 0 26px;max-width:720px;font-size:16.5px;line-height:1.55;color:var(--demp-l)">{e(tekst)}</p>' if tekst else '<div style="height:22px"></div>'
    return (f'<section class="seksjon{" lys" if lys else ""}" style="padding-top:60px;padding-bottom:60px"><div class="innhold">'
            f'<h2 class="h2" data-reveal="0">{e(tittel)}</h2>{p}<div class="fliser">{"".join(fliser)}</div></div></section>')


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
    homey = [flis(k, n, d[sprak][0], d[sprak][1], l, sprak, (i % 3) * 80) for i, (k, n, d, l) in enumerate(HOMEY)]
    def ha_fliser(liste):
        ut = []
        for i, (k, n, nb, en, repo, kat) in enumerate(liste):
            lenker = []
            if kat:
                lenker.append(("Legg til i HACS", "Add to HACS", HACS.format(repo, kat)))
            sti = GH + repo + ("/tree/main/custom_components/skjold" if repo == "pult-forsterker" else "")
            lenker.append(("Kildekode", "Source code", sti))
            ut.append(flis(k, n, nb if sprak == "nb" else en, [], lenker, sprak, (i % 3) * 80))
        return ut
    main = (f'<main id="hoved">\n<section class="side-topp"><div class="etikett" data-reveal="0">{e(t["etikett"])}</div><h1 data-reveal="80">{e(t["h1"])}</h1>'
            f'<p style="margin:20px auto 0;max-width:680px;font-size:19px;line-height:1.5;color:var(--demp-l)">{e(t["ingress"])}</p></section>\n'
            + seksjon(t["homey"], t["homey_p"], homey) + "\n"
            + seksjon(t["ha"], t["ha_p"], ha_fliser(HA), lys=True) + "\n"
            + seksjon(t["kort"], "", ha_fliser(KORT)) + "\n"
            + seksjon(t["prog"], "", ha_fliser(PROGRAMVARE), lys=True) + "\n"
            + f'<section class="seksjon" style="padding-top:30px;padding-bottom:80px"><div class="innhold"><p style="max-width:760px;font-size:14px;line-height:1.6;color:var(--demp-l)">{t["fot"]}</p></div></section>\n')
    ut = os.path.join(HER, t["url"].strip("/"), "index.html")
    os.makedirs(os.path.dirname(ut), exist_ok=True)
    open(ut, "w", encoding="utf-8").write(hode + main + "</main>" + bunn)
    print("skrev", ut)


if __name__ == "__main__":
    lag("nb")
    lag("en")
