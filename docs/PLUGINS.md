# Plugins for Skjold

Skjold kan utvides med plugins fra **Plugins → Butikk** i web-appen. Et plugin er en mappe med en `plugin.json` og
eventuelt en Python-fil. Det installeres i `/var/lib/skjold/plugins/<id>/`.

## plugin.json

```json
{
  "id": "hvit-stoy",
  "navn": "Hvit støy-generator",
  "versjon": "1.0.0",
  "forfatter": "Skjold",
  "beskrivelse": "Lager hvit, rosa eller brun støy.",
  "ikon": "waves",
  "kategori": "Verktøy",
  "minSkjold": "0.1.0",
  "tillatelser": ["audio"],
  "events": ["play", "test"],
  "settings": {
    "farge": {"type": "select", "navn": "Type støy", "valg": ["hvit", "rosa", "brun"], "default": "rosa"}
  },
  "entry": "main.py"
}
```

| Felt | Betydning |
|---|---|
| `id` | Små bokstaver, tall og bindestrek. Samme som mappenavnet. |
| `versjon` | `1.2.3`. Butikken tilbyr oppdatering når katalogen har en høyere versjon. |
| `kategori` | `Musikk`, `Radio og podkast`, `Verktøy`, `Hjem` eller `Moro`. |
| `minSkjold` | Laveste Skjold-versjon pluginet virker på. |
| `tillatelser` | `http` (nett), `audio` (spille, kunngjøre, volum), `settings` (egne innstillinger), `schedule` (kjøre på klokkeslett). |
| `events` | Hendelser pluginet svarer på: `before_news` (rett før Morgennyheter), `tick` (tidsplan), `test` (knappen «Prøv»), eller egne navn. |
| `schedule` | `[{"time": "08:00", "days": [0,1,2,3,4], "event": "tick"}]`. `"$tid"` henter klokkeslettet fra innstillingen `tid`. Krever `schedule`. |
| `settings` | Skjema for innstillinger. Typer: `string`, `number`, `select` (med `valg`), `time`, `password`, `boolean`. |
| `entry` | `main.py` (Python) eller en `.json`/`.yaml`-fil med deklarative ferdigheter. `plugin.json` betyr at ferdighetene står i `skills` i samme fil. |

## Python-plugins

```python
def register(api):
    def hei(data):
        api.toast("Hei fra pluginet", "undertekst")      # alle
        api.play("https://…/strøm.mp3", "Tittel")        # krever audio
        api.announce("https://…/lyd.mp3")                # krever audio – spilles oppå det som spiller
        api.volume(15)                                     # krever audio
        tekst = api.http_get("https://api.met.no/…")      # krever http
        return "ferdig"
    api.on("test", hei)
```

`api.settings` er brukerens innstillinger, og `api.tmpdir()` gir en mappe pluginet kan skrive i.

**Sandkasse:** Pluginet kjøres i en egen Python-prosess (`python3 -I`) for hver hendelse, med tidsgrense på 10 sekunder,
256 MB minne, 8 s CPU og 32 MB filstørrelse. Uten `http` er nettverket sperret. Pluginet kan ikke styre Skjold direkte: det
returnerer handlinger, og daemonen fjerner dem pluginet ikke har tillatelse til.

## Deklarative ferdigheter

Uten Python, rett i `plugin.json` (eller i en egen `.json`/`.yaml`):

```json
"entry": "plugin.json",
"skills": [
  {"when": {"event": "tick", "time": "$tid"}, "do": [{"toast": "Dagens låt"}, {"navidrome_random": true}]}
]
```

Handlinger: `toast`, `play` (+ `title`), `announce`, `volume`, `navidrome_random`.

## Katalog og installasjon

Butikken leser `plugins/index.json` fra main-grenen på GitHub. Hver fil har en sha256-sjekksum, og installasjonen avbrytes
hvis en fil ikke stemmer. Etter endring i et plugin i `plugins/`, kjør:

```bash
python3 plugins/build_index.py
```

Du kan også installere fra en adresse (en `.zip` med `plugin.json`, eller adressen til en `plugin.json`) eller laste opp
en `.zip`. Oppgi sha256 for å sjekke pakken. Installer bare plugins du stoler på.

API-et: `GET /api/store`, `GET /api/store/catalog`, `POST /api/store` med `{install}`, `{url, sha256}`, `{remove}`,
`{id, settings}` eller `{id, run}`. Opplasting med multipart (`file`, `sha256`).

## Eksempler i repoet

- `plugins/vaer-for-nyheter` – viser været fra MET Norge før Morgennyhetene (Python, `http`).
- `plugins/hvit-stoy` – lager og spiller hvit/rosa/brun støy (Python, `audio`).
- `plugins/dagens-lat` – tilfeldig låt fra Navidrome hver morgen (deklarativ, `audio` + `schedule`).

---

## English summary

A Skjold plugin is a folder with `plugin.json` (id, navn = name, versjon = version, forfatter = author, beskrivelse =
description, ikon, kategori, minSkjold, tillatelser = permissions [`http`, `audio`, `settings`, `schedule`], a settings
schema and `entry`). The entry is either a Python module exposing `register(api)` or declarative `skills` in JSON/YAML.
Plugins are installed into `/var/lib/skjold/plugins/<id>/`. Python plugins run in a separate, isolated interpreter per
event with a 10 s timeout and resource limits; network access is blocked unless `http` is granted, and the daemon drops
any returned action the plugin lacks permission for. The catalog is `plugins/index.json` in this repository (every file
carries a sha256 checksum, regenerate it with `python3 plugins/build_index.py`). Plugins can also be installed from a URL
or an uploaded zip. Install, update and remove them in the web app under Plugins → Butikk.

## Utenfra: API og SDK

Vil du styre Skjold fra et annet system i stedet for å kjøre kode på den? Bruk det lokale API-et: [docs/api/openapi.yaml](api/openapi.yaml) (vises på [/utvikler/](https://skjold-lab.com/utvikler/)). Det finnes også SDK-er for Python og JS, og en simulator i [sdk/](../sdk/README.md).
