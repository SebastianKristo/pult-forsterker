// Laget av taster.py – ikke rediger for hånd.
// hette: [id, form, x, n (fra nesen), bredde, høyde, ikon, farge] · bryter: [id, x, n]
DPAD_R = 12.0;
VIPPE_D = 9.5;
PCB_N0 = 79.5;
// variant «kort»: 15 brytere, 11 hetter, L = 180.0
HETTER_KORT = [
  ["av", "rund", 13.50, 83.00, 7.00, 7.00, "av", "mork"],
  ["hjem", "rund", 27.50, 83.00, 7.60, 7.60, "skjold", "gull"],
  ["meny", "rund", 41.50, 83.00, 7.00, 7.00, "meny", "mork"],
  ["dpad", "ring", 27.50, 106.00, 32.00, 14.60, "pil", "gull"],
  ["ok", "ok", 27.50, 106.00, 12.60, 12.60, "OK", "mork"],
  ["tilbake", "rund", 13.50, 129.00, 8.00, 8.00, "tilbake", "mork"],
  ["guide", "rund", 27.50, 129.00, 8.00, 8.00, "guide", "mork"],
  ["avslutt", "rund", 41.50, 129.00, 8.00, 8.00, "avslutt", "mork"],
  ["spill_pause", "rund", 19.00, 143.50, 12.50, 12.50, "spill_pause", "mork"],
  ["demp", "rund", 19.00, 158.50, 12.50, 12.50, "demp", "mork"],
  ["vol", "vippe", 37.50, 151.00, 13.00, 30.00, "vol", "mork"]
];
BRYTERE_KORT = [
  ["av", 13.50, 83.00],
  ["hjem", 27.50, 83.00],
  ["meny", 41.50, 83.00],
  ["opp", 27.50, 94.00],
  ["ned", 27.50, 118.00],
  ["venstre", 15.50, 106.00],
  ["hoyre", 39.50, 106.00],
  ["ok", 27.50, 106.00],
  ["tilbake", 13.50, 129.00],
  ["guide", 27.50, 129.00],
  ["avslutt", 41.50, 129.00],
  ["spill_pause", 19.00, 143.50],
  ["demp", 19.00, 158.50],
  ["vol_opp", 37.50, 141.50],
  ["vol_ned", 37.50, 160.50]
];
PCB_N1_KORT = 166.80;
L_KORT = 180.0;
// variant «full»: 31 brytere, 27 hetter, L = 223.0
HETTER_FULL = [
  ["av", "rund", 13.50, 83.00, 7.00, 7.00, "av", "mork"],
  ["hjem", "rund", 27.50, 83.00, 7.60, 7.60, "skjold", "gull"],
  ["meny", "rund", 41.50, 83.00, 7.00, 7.00, "meny", "mork"],
  ["dpad", "ring", 27.50, 106.00, 32.00, 14.60, "pil", "gull"],
  ["ok", "ok", 27.50, 106.00, 12.60, 12.60, "OK", "mork"],
  ["tilbake", "rund", 13.50, 129.00, 8.00, 8.00, "tilbake", "mork"],
  ["guide", "rund", 27.50, 129.00, 8.00, 8.00, "guide", "mork"],
  ["avslutt", "rund", 41.50, 129.00, 8.00, 8.00, "avslutt", "mork"],
  ["spill_pause", "rund", 19.00, 143.50, 12.50, 12.50, "spill_pause", "mork"],
  ["demp", "rund", 19.00, 158.50, 12.50, 12.50, "demp", "mork"],
  ["vol", "vippe", 37.50, 151.00, 13.00, 30.00, "vol", "mork"],
  ["tall_1", "pille", 13.50, 171.50, 11.60, 6.00, "1", "mork"],
  ["tall_2", "pille", 27.50, 171.50, 11.60, 6.00, "2", "mork"],
  ["tall_3", "pille", 41.50, 171.50, 11.60, 6.00, "3", "mork"],
  ["tall_4", "pille", 13.50, 179.90, 11.60, 6.00, "4", "mork"],
  ["tall_5", "pille", 27.50, 179.90, 11.60, 6.00, "5", "mork"],
  ["tall_6", "pille", 41.50, 179.90, 11.60, 6.00, "6", "mork"],
  ["tall_7", "pille", 13.50, 188.30, 11.60, 6.00, "7", "mork"],
  ["tall_8", "pille", 27.50, 188.30, 11.60, 6.00, "8", "mork"],
  ["tall_9", "pille", 41.50, 188.30, 11.60, 6.00, "9", "mork"],
  ["strek", "pille", 13.50, 196.70, 11.60, 6.00, "strek", "mork"],
  ["tall_0", "pille", 27.50, 196.70, 11.60, 6.00, "0", "mork"],
  ["enter", "pille", 41.50, 196.70, 11.60, 6.00, "enter", "mork"],
  ["lys", "pille", 9.50, 206.30, 9.60, 6.00, "lys", "lys"],
  ["stikk", "pille", 21.50, 206.30, 9.60, 6.00, "stikk", "lys"],
  ["minus", "pille", 33.50, 206.30, 9.60, 6.00, "minus", "lys"],
  ["pluss", "pille", 45.50, 206.30, 9.60, 6.00, "pluss", "lys"]
];
BRYTERE_FULL = [
  ["av", 13.50, 83.00],
  ["hjem", 27.50, 83.00],
  ["meny", 41.50, 83.00],
  ["opp", 27.50, 94.00],
  ["ned", 27.50, 118.00],
  ["venstre", 15.50, 106.00],
  ["hoyre", 39.50, 106.00],
  ["ok", 27.50, 106.00],
  ["tilbake", 13.50, 129.00],
  ["guide", 27.50, 129.00],
  ["avslutt", 41.50, 129.00],
  ["spill_pause", 19.00, 143.50],
  ["demp", 19.00, 158.50],
  ["vol_opp", 37.50, 141.50],
  ["vol_ned", 37.50, 160.50],
  ["tall_1", 13.50, 171.50],
  ["tall_2", 27.50, 171.50],
  ["tall_3", 41.50, 171.50],
  ["tall_4", 13.50, 179.90],
  ["tall_5", 27.50, 179.90],
  ["tall_6", 41.50, 179.90],
  ["tall_7", 13.50, 188.30],
  ["tall_8", 27.50, 188.30],
  ["tall_9", 41.50, 188.30],
  ["strek", 13.50, 196.70],
  ["tall_0", 27.50, 196.70],
  ["enter", 41.50, 196.70],
  ["lys", 9.50, 206.30],
  ["stikk", 21.50, 206.30],
  ["minus", 33.50, 206.30],
  ["pluss", 45.50, 206.30]
];
PCB_N1_FULL = 212.60;
L_FULL = 223.0;
