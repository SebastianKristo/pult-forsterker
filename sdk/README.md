# Skjold utvikler-SDK

| Mappe | Hva |
|---|---|
| [`../docs/api/openapi.yaml`](../docs/api/openapi.yaml) | OpenAPI 3.1 for hele det lokale API-et. Generert fra rutene med `python3 docs/api/gen_openapi.py`. Dokumentasjonen finnes på [skjold.smarthjemexperten.no/utvikler/](https://skjold.smarthjemexperten.no/utvikler/). |
| [`python/`](python) | `skjold` for Python 3.9+. Bruker bare standardbiblioteket. |
| [`js/`](js) | `skjold` for JavaScript (ESM, `fetch`). Fungerer i Node 18+ og nettlesere, med TypeScript-typer. |
| [`simulator/`](simulator) | `python -m skjold_sim`: en falsk Skjold med samme API, falske låter og flere rom. Krever ingen maskinvare. |

Plugins som kjører *på* Skjold, er beskrevet i [docs/PLUGINS.md](../docs/PLUGINS.md).

## Kom i gang

```bash
pip install aiohttp
cd sdk/simulator && python -m skjold_sim --rom 2          # Stue på :8765, Kjøkken på :8766
```

```python
import sys; sys.path.insert(0, "sdk/python")
from skjold import Skjold
s = Skjold("127.0.0.1")
s.power(True); s.volume(30); s.preset(1)
for st in s.events():
    print(st["artist"], "–", st["title"])
```

```js
import { Skjold } from "./sdk/js/index.js";
const s = new Skjold("127.0.0.1");
await s.transport("next");
for await (const st of s.events()) console.log(st.title);
```

## Tester

```bash
python -m pytest sdk/tests
```

```bash
cd sdk/js && npm test
```
