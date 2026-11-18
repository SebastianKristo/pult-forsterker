"""Tilbehør som egne enheter i Home Assistant: Skjold Røst (høyttaler i Lyrion), Skjold Kassett (NFC-kassettspiller)
og Skjold Hjul (fjernkontroll). Alle er koblet til Skjold-enheten de hører til (via_device).

Enhetene lages når integrasjonen lastes. Ny Røst eller nytt Hjul dukker opp etter at integrasjonen er lastet på nytt."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .entity import _NAMES
from .devices import ACCESSORY_MODELS, card_option_names, hjul_devices, kassett_state, rost_devices, sensor_devices, stav_devices


def _uid(c) -> str:
    return c.entry.unique_id or c.entry.entry_id


class _Acc(CoordinatorEntity):
    """Felles for tilbehør: egen enhet, koblet til Skjold-enheten."""
    _attr_has_entity_name = True

    def __init__(self, c, kind: str, dev_id: str, dev_name: str, key: str, name: str) -> None:
        super().__init__(c)
        self._dev = dev_id
        self._attr_unique_id = f"{_uid(c)}_{kind}_{dev_id}_{key}"
        self._attr_translation_key = f"{kind}_{key}"   # navn og ikon fra translations/*.json og icons.json
        self._fallback_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{_uid(c)}_{kind}_{dev_id}")},
            name=dev_name, manufacturer=MANUFACTURER, model=ACCESSORY_MODELS[kind], via_device=(DOMAIN, _uid(c)),
        )


    @property
    def name(self):
        """Navnet fra oversettelsene (også når Home Assistant ikke har lastet dem, som i KiAmpEntity)."""
        plat = "switch" if isinstance(self, SwitchEntity) else "number" if isinstance(self, NumberEntity) else \
            "select" if isinstance(self, SelectEntity) else "binary_sensor" if isinstance(self, BinarySensorEntity) else "sensor"
        lang = "nb" if str(getattr(getattr(self.hass, "config", None), "language", "") or "").startswith(("nb", "no", "nn")) else "en"
        for lg in (lang, "en"):
            n = _NAMES.get(lg, {}).get(plat, {}).get(self._attr_translation_key, {}).get("name")
            if n:
                return n
        return self._fallback_name


# ---------- Skjold Røst ----------
def _rost(c, mid):
    return next((m for m in rost_devices(c.extras.get("rost")) if m["id"] == mid), None)


class RostPower(_Acc, SwitchEntity):

    def __init__(self, c, m) -> None:
        super().__init__(c, "rost", m["id"], m["name"], "power", "Strøm")

    @property
    def available(self) -> bool:
        m = _rost(self.coordinator, self._dev)
        return bool(m and m["connected"])

    @property
    def is_on(self) -> bool:
        return bool((_rost(self.coordinator, self._dev) or {}).get("power"))

    async def _act(self, action, value=None):
        self.coordinator.extras["rost"] = await self.coordinator.api.rost_act(self._dev, action, value)
        self.async_write_ha_state()

    async def async_turn_on(self, **kw) -> None:
        await self._act("power", True)

    async def async_turn_off(self, **kw) -> None:
        await self._act("power", False)


class RostSynced(RostPower):
    """Spiller sammen med rommet (synkgruppe i Lyrion)."""

    def __init__(self, c, m) -> None:
        _Acc.__init__(self, c, "rost", m["id"], m["name"], "synced", "Spill med rommet")

    @property
    def is_on(self) -> bool:
        return bool((_rost(self.coordinator, self._dev) or {}).get("synced"))

    async def async_turn_on(self, **kw) -> None:
        await self._act("sync")

    async def async_turn_off(self, **kw) -> None:
        await self._act("unsync")


class RostVolume(_Acc, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, c, m) -> None:
        super().__init__(c, "rost", m["id"], m["name"], "volume", "Volum")

    @property
    def available(self) -> bool:
        m = _rost(self.coordinator, self._dev)
        return bool(m and m["connected"])

    @property
    def native_value(self):
        return (_rost(self.coordinator, self._dev) or {}).get("volume")

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.extras["rost"] = await self.coordinator.api.rost_act(self._dev, "volume", int(value))
        self.async_write_ha_state()


class RostPlaying(_Acc, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, c, m) -> None:
        super().__init__(c, "rost", m["id"], m["name"], "playing", "Spiller")

    @property
    def is_on(self) -> bool:
        return bool((_rost(self.coordinator, self._dev) or {}).get("playing"))


class RostConnected(RostPlaying):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, c, m) -> None:
        _Acc.__init__(self, c, "rost", m["id"], m["name"], "connected", "Tilkoblet")

    @property
    def is_on(self) -> bool:
        return bool((_rost(self.coordinator, self._dev) or {}).get("connected"))


# ---------- Skjold Kassett ----------
def _kas(c):
    return kassett_state(c.extras.get("nfc"), c.extras.get("spoler")) or {"cards": [], "active": None, "last": None, "spoler": None}


class KassettConnected(_Acc, BinarySensorEntity):
    """Har kassettspilleren (ESP32) kontakt med denne Skjold-en?"""
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, c) -> None:
        super().__init__(c, "kassett", "spiller", "Skjold Kassett", "connected", "Tilkoblet")

    @property
    def is_on(self) -> bool:
        return bool(_kas(self.coordinator).get("tilkoblet"))

    @property
    def extra_state_attributes(self):
        return {"ip": _kas(self.coordinator).get("spiller_ip") or None}


class KassettTag(_Acc, SensorEntity):
    """UID-en til den siste NFC-brikken spilleren leste (nyttig når du kobler nye kassetter)."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, c) -> None:
        super().__init__(c, "kassett", "spiller", "Skjold Kassett", "tag", "Siste brikke")

    @property
    def native_value(self):
        return _kas(self.coordinator).get("siste_brikke") or None


class KassettActive(_Acc, SensorEntity):

    def __init__(self, c) -> None:
        super().__init__(c, "kassett", "spiller", "Skjold Kassett", "active", "Kassett i spilleren")

    @property
    def native_value(self):
        return _kas(self.coordinator)["active"] or "Ingen"

    @property
    def extra_state_attributes(self):
        k = _kas(self.coordinator)
        return {"kilde": k.get("kilde") or None, "spilles_paa": k.get("paret") or "denne", "ventende_album": k.get("ventende", 0),
                "mest_spilt": k.get("mest_spilt")}


class KassettLast(_Acc, SensorEntity):

    def __init__(self, c) -> None:
        super().__init__(c, "kassett", "spiller", "Skjold Kassett", "last", "Sist innsatt")

    @property
    def native_value(self):
        return _kas(self.coordinator)["last"]

    @property
    def extra_state_attributes(self):
        t = _kas(self.coordinator).get("last_t")
        return {"tid": datetime.fromtimestamp(t, timezone.utc).isoformat()} if t else {}


class KassettVentende(_Acc, SensorEntity):
    """Antall delte kassetter fra venner som venter på en NFC-brikke."""
    _attr_native_unit_of_measurement = "kassetter"

    def __init__(self, c) -> None:
        super().__init__(c, "kassett", "spiller", "Skjold Kassett", "shared_pending", "Ventende delte kassetter")

    @property
    def native_value(self):
        return _kas(self.coordinator).get("ventende_delte", 0)

    @property
    def extra_state_attributes(self):
        return {"ventende_totalt": _kas(self.coordinator).get("ventende", 0)}


class KassettPlay(_Acc, SelectEntity):
    """Velg en kassett = spill den, som om den ble satt i spilleren."""

    def __init__(self, c) -> None:
        super().__init__(c, "kassett", "spiller", "Skjold Kassett", "play", "Spill kassett")

    @property
    def options(self) -> list[str]:
        return card_option_names(_kas(self.coordinator)["cards"]) or ["Ingen kassetter"]

    @property
    def current_option(self):
        k = _kas(self.coordinator)
        names = card_option_names(k["cards"])
        return next((n for n, card in zip(names, k["cards"]) if card["uid"] == k.get("active_uid")), None)

    async def async_select_option(self, option: str) -> None:
        k = _kas(self.coordinator)
        card = next((card for n, card in zip(card_option_names(k["cards"]), k["cards"]) if n == option), None)
        if card:
            await self.coordinator.api.nfc_scan(card["uid"])
            await self.coordinator.refresh_extras()
            self.async_write_ha_state()


class KassettSpoler(_Acc, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, c) -> None:
        super().__init__(c, "kassett", "spiller", "Skjold Kassett", "spoler", "Spoler i vinduet")

    @property
    def is_on(self):
        return _kas(self.coordinator)["spoler"]

    async def async_turn_on(self, **kw) -> None:
        self.coordinator.extras["spoler"] = await self.coordinator.api.set_spoler(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kw) -> None:
        self.coordinator.extras["spoler"] = await self.coordinator.api.set_spoler(False)
        self.async_write_ha_state()


# ---------- Skjold Hjul ----------
def _hjul(c, dev):
    return next((h for h in hjul_devices(c.extras.get("hjul")) if h["id"] == dev), None)


class HjulBattery(_Acc, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, c, h) -> None:
        super().__init__(c, "hjul", h["id"], h["name"], "battery", "Batteri")

    @property
    def native_value(self):
        return (_hjul(self.coordinator, self._dev) or {}).get("battery")


class HjulLastUsed(_Acc, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, c, h) -> None:
        super().__init__(c, "hjul", h["id"], h["name"], "last", "Sist brukt")

    @property
    def native_value(self):
        t = (_hjul(self.coordinator, self._dev) or {}).get("last")
        return datetime.fromtimestamp(t, timezone.utc) if t else None


class HjulRoom(_Acc, SelectEntity):

    def __init__(self, c, h) -> None:
        super().__init__(c, "hjul", h["id"], h["name"], "room", "Rom")

    @property
    def options(self) -> list[str]:
        return (_hjul(self.coordinator, self._dev) or {}).get("rooms") or ["Dette rommet"]

    @property
    def current_option(self):
        return (_hjul(self.coordinator, self._dev) or {}).get("room")

    async def async_select_option(self, option: str) -> None:
        self.coordinator.extras["hjul"] = await self.coordinator.api.set_hjul_room(self._dev, option)
        self.async_write_ha_state()


# ---------- Skjold Stav (fjernkontrollen) ----------
def _stav(c, dev):
    return next((h for h in stav_devices(c.extras.get("stav")) if h["id"] == dev), None)


class StavBattery(_Acc, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, c, h) -> None:
        super().__init__(c, "stav", h["id"], h["name"], "battery", "Batteri")

    @property
    def native_value(self):
        return (_stav(self.coordinator, self._dev) or {}).get("battery")


class StavLastKey(_Acc, SensorEntity):
    def __init__(self, c, h) -> None:
        super().__init__(c, "stav", h["id"], h["name"], "key", "Siste tast")

    @property
    def native_value(self):
        return (_stav(self.coordinator, self._dev) or {}).get("key")


class StavLastUsed(_Acc, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, c, h) -> None:
        super().__init__(c, "stav", h["id"], h["name"], "last", "Sist hørt fra")

    @property
    def native_value(self):
        t = (_stav(self.coordinator, self._dev) or {}).get("last")
        return datetime.fromtimestamp(t, timezone.utc) if t else None


class StavCharging(_Acc, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, c, h) -> None:
        super().__init__(c, "stav", h["id"], h["name"], "charging", "Lader")

    @property
    def is_on(self):
        return (_stav(self.coordinator, self._dev) or {}).get("charging")


class StavConnected(_Acc, BinarySensorEntity):
    """Hørt fra det siste kvarteret (Staven sover mellom trykk og melder seg hvert 5. minutt når den er våken)."""
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, c, h) -> None:
        super().__init__(c, "stav", h["id"], h["name"], "connected", "Tilkoblet")

    @property
    def is_on(self):
        return bool((_stav(self.coordinator, self._dev) or {}).get("connected"))


# ---------- Skjold Sensor (romsensoren, esphome/skjold-sensor*.yaml) ----------
# (navn i ESPHome, nøkkel, device_class, enhet, state_class, diagnostikk)
SENSOR_VERDIER = [
    ("Temperatur", "temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", False),
    ("Luftfuktighet", "humidity", SensorDeviceClass.HUMIDITY, PERCENTAGE, "measurement", False),
    ("Lys", "illuminance", SensorDeviceClass.ILLUMINANCE, "lx", "measurement", False),
    ("Duggpunkt", "dew_point", SensorDeviceClass.TEMPERATURE, "°C", "measurement", False),
    ("Føles som", "feels_like", SensorDeviceClass.TEMPERATURE, "°C", "measurement", False),
    ("Absolutt fuktighet", "abs_humidity", None, "g/m³", "measurement", False),
    ("Komfort", "comfort", None, None, None, False),
    ("Lysnivå", "light_level", None, None, None, False),
    ("Bevegelser", "motion_count", None, None, "total_increasing", False),
    ("Minutter siden bevegelse", "minutes_since_motion", SensorDeviceClass.DURATION, "min", "measurement", False),
    ("Wi-Fi-signal", "wifi", SensorDeviceClass.SIGNAL_STRENGTH, "dBm", "measurement", True),
    ("Oppetid", "uptime", SensorDeviceClass.DURATION, "s", None, True),
    ("IP-adresse", "ip", None, None, None, True),
    ("MAC-adresse", "mac", None, None, None, True),
    ("Wi-Fi-nett", "ssid", None, None, None, True),
    ("Tilgangspunkt", "bssid", None, None, None, True),
    ("ESPHome-versjon", "esphome_version", None, None, None, True),
    ("Brikketemperatur", "chip_temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", True),
]
# Innstillinger (number): navn i ESPHome, nøkkel, min, maks, steg, enhet
SENSOR_TALL = [
    ("Oppdateringsintervall", "update_interval", 5, 600, 5, "s"),
    ("Bevegelse av etter", "motion_cooldown", 1, 600, 1, "s"),
    ("Tilstedeværelse av etter", "presence_timeout", 1, 240, 1, "min"),
]
SENSOR_BINAERE = [
    ("Bevegelse", "motion", BinarySensorDeviceClass.MOTION),
    ("Tilstedeværelse", "presence", BinarySensorDeviceClass.OCCUPANCY),
    ("Mørkt", "dark", None),
    ("Høy fuktighet", "high_humidity", BinarySensorDeviceClass.MOISTURE),
]


def _sens(c, dev):
    return next((h for h in sensor_devices(c.extras.get("sensorer")) if h["id"] == dev), None)


class _SensorVerdi(_Acc):
    def __init__(self, c, h, esp_navn: str, key: str) -> None:
        super().__init__(c, "sensor", h["id"], h["name"], key, esp_navn)
        self._esp = esp_navn.lower()

    def _v(self):
        h = _sens(self.coordinator, self._dev) or {}
        return h.get("values", {}).get(self._esp)

    @property
    def available(self) -> bool:
        h = _sens(self.coordinator, self._dev)
        return bool(super().available and h and self._esp in h["values"])


class SkjoldSensorVerdi(_SensorVerdi, SensorEntity):
    def __init__(self, c, h, spec) -> None:
        navn, key, dc, enhet, sc, diag = spec
        super().__init__(c, h, navn, key)
        self._attr_device_class = dc
        self._attr_native_unit_of_measurement = enhet
        self._attr_state_class = sc
        if diag:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        v = self._v()
        return None if isinstance(v, bool) else v


class SkjoldSensorTall(_SensorVerdi, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, c, h, spec) -> None:
        navn, key, lo, hi, steg, enhet = spec
        super().__init__(c, h, navn, key)
        self._navn = navn
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = lo, hi, steg
        self._attr_native_unit_of_measurement = enhet

    @property
    def native_value(self):
        v = self._v()
        return None if isinstance(v, bool) or v is None else float(v)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.extras["sensorer"] = await self.coordinator.api.sensor_sett(self._dev, self._navn, value)
        self.async_write_ha_state()


class SkjoldSensorLed(_SensorVerdi, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, c, h) -> None:
        super().__init__(c, h, "Status-LED", "status_led")

    @property
    def is_on(self):
        v = self._v()
        return None if v is None else bool(v)

    async def _sett(self, on: bool) -> None:
        self.coordinator.extras["sensorer"] = await self.coordinator.api.sensor_sett(self._dev, "Status-LED", on)
        self.async_write_ha_state()

    async def async_turn_on(self, **kw) -> None:
        await self._sett(True)

    async def async_turn_off(self, **kw) -> None:
        await self._sett(False)


class SkjoldSensorBinaer(_SensorVerdi, BinarySensorEntity):
    def __init__(self, c, h, spec) -> None:
        navn, key, dc = spec
        super().__init__(c, h, navn, key)
        self._attr_device_class = dc

    @property
    def is_on(self):
        v = self._v()
        return None if v is None else bool(v)


class SkjoldSensorTilkoblet(_Acc, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, c, h) -> None:
        super().__init__(c, "sensor", h["id"], h["name"], "connected", "Tilkoblet")

    @property
    def is_on(self):
        return bool((_sens(self.coordinator, self._dev) or {}).get("connected"))


def entities(c, platform: str) -> list:
    """Tilbehørsentitetene for én plattform (kalles fra switch.py, number.py, sensor.py, select.py, binary_sensor.py)."""
    out: list = []
    minis = rost_devices(c.extras.get("rost"))
    kas = kassett_state(c.extras.get("nfc"), c.extras.get("spoler"))
    hjul = hjul_devices(c.extras.get("hjul"))
    staver = stav_devices(c.extras.get("stav"))
    sensorer = sensor_devices(c.extras.get("sensorer"))
    if platform == "switch":
        out += [x for m in minis for x in (RostPower(c, m), RostSynced(c, m))]
        if kas and kas["spoler"] is not None:
            out.append(KassettSpoler(c))
        out += [SkjoldSensorLed(c, h) for h in sensorer]
    elif platform == "number":
        out += [RostVolume(c, m) for m in minis]
        out += [SkjoldSensorTall(c, h, sp) for h in sensorer for sp in SENSOR_TALL]
    elif platform == "binary_sensor":
        out += [x for m in minis for x in (RostPlaying(c, m), RostConnected(c, m))]
        if kas:
            out.append(KassettConnected(c))
        out += [x for h in staver for x in (StavCharging(c, h), StavConnected(c, h))]
        out += [x for h in sensorer for x in [SkjoldSensorTilkoblet(c, h)] + [SkjoldSensorBinaer(c, h, sp) for sp in SENSOR_BINAERE]]
    elif platform == "sensor":
        if kas:
            out += [KassettActive(c), KassettLast(c), KassettVentende(c), KassettTag(c)]
        out += [x for h in hjul for x in (HjulBattery(c, h), HjulLastUsed(c, h))]
        out += [x for h in staver for x in (StavBattery(c, h), StavLastKey(c, h), StavLastUsed(c, h))]
        out += [SkjoldSensorVerdi(c, h, sp) for h in sensorer for sp in SENSOR_VERDIER]
    elif platform == "select":
        if kas:
            out.append(KassettPlay(c))
        out += [HjulRoom(c, h) for h in hjul]
    return out
