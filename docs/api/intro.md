Skjold har et åpent HTTP-API på port **8765** i hjemmenettet. Det trengs ingen nøkkel, siden API-et bare kan nås lokalt. Bruk Skjold-hjem eller fjernstyring for tilgang utenfra.

**Sanntid**
- **SSE**: `GET /api/events` sender hele statusen (`data: {…}`) hver gang noe endrer seg.
- **WebSocket**: `GET /api/ws` bruker samme meldinger som Skjold Touch.
- **MQTT** (pluginen «MQTT-bro»):
  - status publiseres retained på `skjold/<vertsnavn>/state`;
  - kommandoer går til `skjold/<vertsnavn>/set` som JSON (`{"volume": 30}`, også `input`, `power`, `preset`, `transport` og `mute`), eller som en ren verdi på `…/set/<felt>`;
  - med Home Assistant-oppdagelse slått på dukker Skjold opp av seg selv.

**Eksempler**

```bash
curl http://skjold.local:8765/api/status
curl -X POST http://skjold.local:8765/api/volume -H 'content-type: application/json' -d '{"volume": 30}'
curl -N http://skjold.local:8765/api/events
```

```python
from skjold import Skjold          # sdk/python
s = Skjold("skjold.local")
s.volume(30); s.preset(1)
for st in s.events(): print(st["title"])
```

```js
import { Skjold } from "skjold";   // sdk/js
const s = new Skjold("skjold.local");
await s.power(true);
for await (const st of s.events()) console.log(st.volume);
```

```yaml
# Home Assistant – uten integrasjonen (configuration.yaml)
rest_command:
  skjold_volum:
    url: http://skjold.local:8765/api/volume
    method: POST
    content_type: application/json
    payload: '{"volume": {{ volume }}}'
sensor:
  - platform: rest
    name: Skjold volum
    resource: http://skjold.local:8765/api/status
    value_template: "{{ value_json.volume }}"
```

Plugins kan utvide API-et. Se [PLUGINS.md](https://github.com/SebastianKristo/pult-forsterker/blob/main/docs/PLUGINS.md). Simulatoren i `sdk/simulator` (`python -m skjold_sim`) svarer på det samme API-et uten maskinvare.
