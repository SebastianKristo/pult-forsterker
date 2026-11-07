// Laget av taster.py – ikke rediger for hånd.
// hette: [id, form, x, n (fra nesen), bredde, høyde, ikon, farge] · bryter: [id, x, n]
DPAD_R = 14.0;
VIPPE_D = 11.0;
PCB_N0 = 79.5;
// variant «kort»: 14 brytere, 10 hetter, L = 193.0
HETTER_KORT = [
  ["av", "rund", 7.50, 83.00, 7.00, 7.00, "av", "mork"],
  ["dpad", "ring", 27.50, 100.00, 39.00, 17.00, "pil", "gull"],
  ["ok", "ok", 27.50, 100.00, 15.00, 15.00, "OK", "mork"],
  ["hjem", "rund", 17.50, 124.70, 8.00, 8.00, "skjold", "gull"],
  ["meny", "rund", 37.00, 124.70, 8.00, 8.00, "meny", "mork"],
  ["tilbake", "rund", 17.50, 135.70, 8.00, 8.00, "tilbake", "mork"],
  ["avslutt", "rund", 37.00, 135.70, 8.00, 8.00, "avslutt", "mork"],
  ["spill_pause", "rund", 17.50, 150.50, 16.00, 16.00, "spill_pause", "mork"],
  ["demp", "rund", 17.50, 169.50, 16.00, 16.00, "demp", "mork"],
  ["vol", "vippe", 37.00, 160.00, 17.00, 35.00, "vol", "mork"]
];
BRYTERE_KORT = [
  ["av", 7.50, 83.00],
  ["opp", 27.50, 86.00],
  ["ned", 27.50, 114.00],
  ["venstre", 13.50, 100.00],
  ["hoyre", 41.50, 100.00],
  ["ok", 27.50, 100.00],
  ["hjem", 17.50, 124.70],
  ["meny", 37.00, 124.70],
  ["tilbake", 17.50, 135.70],
  ["avslutt", 37.00, 135.70],
  ["spill_pause", 17.50, 150.50],
  ["demp", 17.50, 169.50],
  ["vol_opp", 37.00, 149.00],
  ["vol_ned", 37.00, 171.00]
];
PCB_N1_KORT = 177.30;
L_KORT = 193.0;
// variant «full»: 30 brytere, 26 hetter, L = 236.0
HETTER_FULL = [
  ["av", "rund", 7.50, 83.00, 7.00, 7.00, "av", "mork"],
  ["dpad", "ring", 27.50, 100.00, 39.00, 17.00, "pil", "gull"],
  ["ok", "ok", 27.50, 100.00, 15.00, 15.00, "OK", "mork"],
  ["hjem", "rund", 17.50, 124.70, 8.00, 8.00, "skjold", "gull"],
  ["meny", "rund", 37.00, 124.70, 8.00, 8.00, "meny", "mork"],
  ["tilbake", "rund", 17.50, 135.70, 8.00, 8.00, "tilbake", "mork"],
  ["avslutt", "rund", 37.00, 135.70, 8.00, 8.00, "avslutt", "mork"],
  ["spill_pause", "rund", 17.50, 150.50, 16.00, 16.00, "spill_pause", "mork"],
  ["demp", "rund", 17.50, 169.50, 16.00, 16.00, "demp", "mork"],
  ["vol", "vippe", 37.00, 160.00, 17.00, 35.00, "vol", "mork"],
  ["tall_1", "pille", 13.50, 184.25, 11.60, 6.00, "1", "mork"],
  ["tall_2", "pille", 27.50, 184.25, 11.60, 6.00, "2", "mork"],
  ["tall_3", "pille", 41.50, 184.25, 11.60, 6.00, "3", "mork"],
  ["tall_4", "pille", 13.50, 192.65, 11.60, 6.00, "4", "mork"],
  ["tall_5", "pille", 27.50, 192.65, 11.60, 6.00, "5", "mork"],
  ["tall_6", "pille", 41.50, 192.65, 11.60, 6.00, "6", "mork"],
  ["tall_7", "pille", 13.50, 201.05, 11.60, 6.00, "7", "mork"],
  ["tall_8", "pille", 27.50, 201.05, 11.60, 6.00, "8", "mork"],
  ["tall_9", "pille", 41.50, 201.05, 11.60, 6.00, "9", "mork"],
  ["strek", "pille", 13.50, 209.45, 11.60, 6.00, "strek", "mork"],
  ["tall_0", "pille", 27.50, 209.45, 11.60, 6.00, "0", "mork"],
  ["enter", "pille", 41.50, 209.45, 11.60, 6.00, "enter", "mork"],
  ["lys", "pille", 9.50, 219.05, 9.60, 6.00, "lys", "lys"],
  ["stikk", "pille", 21.50, 219.05, 9.60, 6.00, "stikk", "lys"],
  ["minus", "pille", 33.50, 219.05, 9.60, 6.00, "minus", "lys"],
  ["pluss", "pille", 45.50, 219.05, 9.60, 6.00, "pluss", "lys"]
];
BRYTERE_FULL = [
  ["av", 7.50, 83.00],
  ["opp", 27.50, 86.00],
  ["ned", 27.50, 114.00],
  ["venstre", 13.50, 100.00],
  ["hoyre", 41.50, 100.00],
  ["ok", 27.50, 100.00],
  ["hjem", 17.50, 124.70],
  ["meny", 37.00, 124.70],
  ["tilbake", 17.50, 135.70],
  ["avslutt", 37.00, 135.70],
  ["spill_pause", 17.50, 150.50],
  ["demp", 17.50, 169.50],
  ["vol_opp", 37.00, 149.00],
  ["vol_ned", 37.00, 171.00],
  ["tall_1", 13.50, 184.25],
  ["tall_2", 27.50, 184.25],
  ["tall_3", 41.50, 184.25],
  ["tall_4", 13.50, 192.65],
  ["tall_5", 27.50, 192.65],
  ["tall_6", 41.50, 192.65],
  ["tall_7", 13.50, 201.05],
  ["tall_8", 27.50, 201.05],
  ["tall_9", 41.50, 201.05],
  ["strek", 13.50, 209.45],
  ["tall_0", 27.50, 209.45],
  ["enter", 41.50, 209.45],
  ["lys", 9.50, 219.05],
  ["stikk", 21.50, 219.05],
  ["minus", 33.50, 219.05],
  ["pluss", 45.50, 219.05]
];
PCB_N1_FULL = 225.35;
L_FULL = 236.0;
