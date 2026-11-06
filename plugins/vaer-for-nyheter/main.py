"""Værmelding før nyheter – henter locationforecast/compact fra api.met.no."""
import json

SYMBOL = {"clearsky": "klarvær", "fair": "lettskyet", "partlycloudy": "delvis skyet", "cloudy": "skyet", "fog": "tåke",
          "rain": "regn", "lightrain": "lett regn", "heavyrain": "kraftig regn", "rainshowers": "regnbyger",
          "snow": "snø", "lightsnow": "lett snø", "sleet": "sludd"}


def describe(forecast, sted):
    ts = forecast["properties"]["timeseries"]
    now = ts[0]["data"]
    temp = now["instant"]["details"]["air_temperature"]
    nxt = now.get("next_6_hours") or now.get("next_1_hours") or {}
    sym = (nxt.get("summary") or {}).get("symbol_code", "").split("_")[0]
    rain = (nxt.get("details") or {}).get("precipitation_amount")
    temps = [t["data"]["instant"]["details"]["air_temperature"] for t in ts[:12]]
    txt = f"{sted}: {round(temp)} grader, {SYMBOL.get(sym, sym or 'ukjent vær')}"
    sub = f"Mellom {round(min(temps))} og {round(max(temps))} grader neste 12 timer" + (f", {rain} mm nedbør" if rain else "")
    return txt, sub


def register(api):
    def weather(_data):
        s = api.settings
        url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={float(s.get('lat', 59.91)):.2f}&lon={float(s.get('lon', 10.75)):.2f}"
        txt, sub = describe(json.loads(api.http_get(url)), s.get("sted") or "Her")
        api.toast(txt, sub)
        return txt
    api.on("before_news", weather)
    api.on("test", weather)
