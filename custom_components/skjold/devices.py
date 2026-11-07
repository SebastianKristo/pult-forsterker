"""Rene hjelpere (uten Home Assistant-import, så de kan testes alene) for enhetsprofiler:
hovedenheten (S1, Node, Touch, Core) og tilbehøret Skjold Røst, Skjold Kassett og Skjold Hjul."""
from __future__ import annotations

# status["product"] → modellnavn, og board → maskinvareutgave (vises som «Maskinvare» i Home Assistant)
MODELS = {"s1": "Skjold S1", "node": "Skjold Node", "core": "Skjold Core", "touch": "Skjold Touch"}
BOARD_LABELS = {"s1f": "rev F", "main": "rev B", "kit": "Kit", "modules": "Moduler", "node": "Node", "touch": "Touch",
                "core": "Core"}
ACCESSORY_MODELS = {"rost": "Skjold Røst", "kassett": "Skjold Kassett", "hjul": "Skjold Hjul"}
ICONS = {"s1": "mdi:amplifier", "node": "mdi:speaker-wireless", "core": "mdi:raspberry-pi", "touch": "mdi:tablet-dashboard",
         "rost": "mdi:speaker", "kassett": "mdi:cassette", "hjul": "mdi:knob"}


def main_model(data: dict | None, product: str) -> tuple[str, str, str | None]:
    """(modellnavn, model_id, maskinvare) for hovedenheten, f.eks. («Skjold S1», «s1-s1f», «rev F»)."""
    d = data or {}
    board = str(d.get("board") or "")
    model = MODELS.get(product, "Skjold")
    if product == "s1" and board == "s1f":
        model = "Skjold S1 rev F"
    return model, f"{product}-{board}" if board else product, (BOARD_LABELS.get(board, board) or None)


def rost_devices(res: dict | None) -> list[dict]:
    """GET /api/rost → Røst-høyttalere: [{id, name, connected, power, playing, volume, synced, ip}]."""
    out = []
    for m in (res or {}).get("minis") or []:
        if isinstance(m, dict) and m.get("id"):
            out.append({"id": str(m["id"]).lower(), "name": str(m.get("name") or "Skjold Røst"),
                        "connected": bool(m.get("connected")), "power": bool(m.get("power")), "playing": bool(m.get("playing")),
                        "volume": m.get("volume"), "synced": bool(m.get("synced")), "ip": str(m.get("ip") or "")})
    return out


def kassett_state(nfc: dict | None, spoler: dict | None) -> dict | None:
    """GET /api/nfc (+ /api/nfc/spoler) → én Kassett-enhet per Skjold, eller None når ingen spiller er i bruk."""
    if not isinstance(nfc, dict) or "cards" not in nfc:
        return None
    cards = [c for c in nfc.get("cards") or [] if isinstance(c, dict) and c.get("uid")]
    last = nfc.get("last") or {}
    if not cards and not last.get("uid"):
        return None   # ingen Kassett-spiller har vært i bruk
    active = str(nfc.get("active") or "")
    by_uid = {c["uid"]: c for c in cards}
    return {
        "cards": [{"uid": c["uid"], "navn": str(c.get("navn") or c["uid"])} for c in cards],
        "active_uid": active, "active": (by_uid.get(active) or {}).get("navn") if active else None,
        "last": last.get("navn") or None, "last_t": last.get("t") or None,
        "spoler": None if not isinstance(spoler, dict) else bool(spoler.get("på", True)),
        "kilde": _KILDE.get(((by_uid.get(active) or {}).get("losning") or {}).get("kilde"), "") if active else "",
        "paret": str(nfc.get("paret") or ""),
        "ventende": len(nfc.get("ventende") or []),
    }


_KILDE = {"navidrome": "Navidrome", "ytmusic": "YouTube Music", "ma": "Music Assistant"}


def card_option_names(cards: list[dict]) -> list[str]:
    """Unike visningsnavn for kassettene (like navn får uid-suffiks)."""
    seen: dict[str, int] = {}
    for c in cards:
        seen[c["navn"]] = seen.get(c["navn"], 0) + 1
    return [c["navn"] if seen[c["navn"]] == 1 else f"{c['navn']} ({c['uid'][-4:]})" for c in cards]


def hjul_devices(cfg: dict | None) -> list[dict]:
    """GET /api/hjul → [{id, name, battery, last, room, rooms}] for hjul som har meldt seg."""
    c = cfg or {}
    rooms = [str(r) for r in c.get("rom") or []]
    out = []
    for dev, e in (c.get("enheter") or {}).items():
        if not isinstance(e, dict):
            continue
        out.append({"id": str(dev), "name": str(e.get("navn") or "Skjold Hjul"), "battery": e.get("batteri"),
                    "last": e.get("sist"), "room": str(e.get("rom") or (rooms[0] if rooms else "")), "rooms": rooms})
    return sorted(out, key=lambda d: d["name"].lower())
