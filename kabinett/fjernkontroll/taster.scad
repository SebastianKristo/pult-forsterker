// Laget av taster.py – ikke rediger for hånd.
// hette: [id, form, x, n (fra nesen), bredde, høyde, ikon, farge] · bryter: [id, x, n]
DPAD_R = 12.0;
VIPPE_D = 9.0;
PCB_N0 = 79.5;
// variant «kort»: 17 brytere, 13 hetter, L = 177.0
HETTER_KORT = [
  ["tilbake", "rund", 7.60, 83.00, 6.60, 6.60, "tilbake", "mork"],
  ["avslutt", "rund", 47.40, 83.00, 6.60, 6.60, "avslutt", "mork"],
  ["dpad", "ring", 27.50, 96.00, 32.00, 14.60, "pil", "gull"],
  ["ok", "ok", 27.50, 96.00, 12.60, 12.60, "OK", "mork"],
  ["vol", "vippe", 27.50, 129.50, 11.50, 28.00, "vol", "mork"],
  ["demp", "rund", 12.50, 129.50, 9.00, 9.00, "demp", "mork"],
  ["guide", "rund", 42.50, 129.50, 9.00, 9.00, "guide", "mork"],
  ["av", "rund", 13.50, 150.00, 7.00, 7.00, "av", "mork"],
  ["hjem", "rund", 27.50, 150.00, 7.60, 7.60, "skjold", "gull"],
  ["meny", "rund", 41.50, 150.00, 7.00, 7.00, "meny", "mork"],
  ["spol_tilbake", "pille", 12.00, 160.00, 12.00, 7.20, "spol_tilbake", "mork"],
  ["spill_pause", "pille", 27.50, 160.00, 12.00, 7.20, "spill_pause", "mork"],
  ["spol_frem", "pille", 43.00, 160.00, 12.00, 7.20, "spol_frem", "mork"]
];
BRYTERE_KORT = [
  ["tilbake", 7.60, 83.00],
  ["avslutt", 47.40, 83.00],
  ["opp", 27.50, 84.00],
  ["ned", 27.50, 108.00],
  ["venstre", 15.50, 96.00],
  ["hoyre", 39.50, 96.00],
  ["ok", 27.50, 96.00],
  ["vol_opp", 27.50, 120.50],
  ["vol_ned", 27.50, 138.50],
  ["demp", 12.50, 129.50],
  ["guide", 42.50, 129.50],
  ["av", 13.50, 150.00],
  ["hjem", 27.50, 150.00],
  ["meny", 41.50, 150.00],
  ["spol_tilbake", 12.00, 160.00],
  ["spill_pause", 27.50, 160.00],
  ["spol_frem", 43.00, 160.00]
];
PCB_N1_KORT = 166.30;
L_KORT = 177.0;
// variant «full»: 33 brytere, 29 hetter, L = 220.0
HETTER_FULL = [
  ["tilbake", "rund", 7.60, 83.00, 6.60, 6.60, "tilbake", "mork"],
  ["avslutt", "rund", 47.40, 83.00, 6.60, 6.60, "avslutt", "mork"],
  ["dpad", "ring", 27.50, 96.00, 32.00, 14.60, "pil", "gull"],
  ["ok", "ok", 27.50, 96.00, 12.60, 12.60, "OK", "mork"],
  ["vol", "vippe", 27.50, 129.50, 11.50, 28.00, "vol", "mork"],
  ["demp", "rund", 12.50, 129.50, 9.00, 9.00, "demp", "mork"],
  ["guide", "rund", 42.50, 129.50, 9.00, 9.00, "guide", "mork"],
  ["av", "rund", 13.50, 150.00, 7.00, 7.00, "av", "mork"],
  ["hjem", "rund", 27.50, 150.00, 7.60, 7.60, "skjold", "gull"],
  ["meny", "rund", 41.50, 150.00, 7.00, 7.00, "meny", "mork"],
  ["spol_tilbake", "pille", 12.00, 160.00, 12.00, 7.20, "spol_tilbake", "mork"],
  ["spill_pause", "pille", 27.50, 160.00, 12.00, 7.20, "spill_pause", "mork"],
  ["spol_frem", "pille", 43.00, 160.00, 12.00, 7.20, "spol_frem", "mork"],
  ["tall_1", "pille", 13.50, 169.00, 11.60, 6.00, "1", "mork"],
  ["tall_2", "pille", 27.50, 169.00, 11.60, 6.00, "2", "mork"],
  ["tall_3", "pille", 41.50, 169.00, 11.60, 6.00, "3", "mork"],
  ["tall_4", "pille", 13.50, 177.40, 11.60, 6.00, "4", "mork"],
  ["tall_5", "pille", 27.50, 177.40, 11.60, 6.00, "5", "mork"],
  ["tall_6", "pille", 41.50, 177.40, 11.60, 6.00, "6", "mork"],
  ["tall_7", "pille", 13.50, 185.80, 11.60, 6.00, "7", "mork"],
  ["tall_8", "pille", 27.50, 185.80, 11.60, 6.00, "8", "mork"],
  ["tall_9", "pille", 41.50, 185.80, 11.60, 6.00, "9", "mork"],
  ["strek", "pille", 13.50, 194.20, 11.60, 6.00, "strek", "mork"],
  ["tall_0", "pille", 27.50, 194.20, 11.60, 6.00, "0", "mork"],
  ["enter", "pille", 41.50, 194.20, 11.60, 6.00, "enter", "mork"],
  ["lys", "pille", 9.50, 203.80, 9.60, 6.00, "lys", "lys"],
  ["stikk", "pille", 21.50, 203.80, 9.60, 6.00, "stikk", "lys"],
  ["minus", "pille", 33.50, 203.80, 9.60, 6.00, "minus", "lys"],
  ["pluss", "pille", 45.50, 203.80, 9.60, 6.00, "pluss", "lys"]
];
BRYTERE_FULL = [
  ["tilbake", 7.60, 83.00],
  ["avslutt", 47.40, 83.00],
  ["opp", 27.50, 84.00],
  ["ned", 27.50, 108.00],
  ["venstre", 15.50, 96.00],
  ["hoyre", 39.50, 96.00],
  ["ok", 27.50, 96.00],
  ["vol_opp", 27.50, 120.50],
  ["vol_ned", 27.50, 138.50],
  ["demp", 12.50, 129.50],
  ["guide", 42.50, 129.50],
  ["av", 13.50, 150.00],
  ["hjem", 27.50, 150.00],
  ["meny", 41.50, 150.00],
  ["spol_tilbake", 12.00, 160.00],
  ["spill_pause", 27.50, 160.00],
  ["spol_frem", 43.00, 160.00],
  ["tall_1", 13.50, 169.00],
  ["tall_2", 27.50, 169.00],
  ["tall_3", 41.50, 169.00],
  ["tall_4", 13.50, 177.40],
  ["tall_5", 27.50, 177.40],
  ["tall_6", 41.50, 177.40],
  ["tall_7", 13.50, 185.80],
  ["tall_8", 27.50, 185.80],
  ["tall_9", 41.50, 185.80],
  ["strek", 13.50, 194.20],
  ["tall_0", 27.50, 194.20],
  ["enter", 41.50, 194.20],
  ["lys", 9.50, 203.80],
  ["stikk", 21.50, 203.80],
  ["minus", 33.50, 203.80],
  ["pluss", 45.50, 203.80]
];
PCB_N1_FULL = 210.10;
L_FULL = 220.0;
