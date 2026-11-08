"""Koblingsskjema (nettetiketter) og pinnetabell for hovedkortet, laget fra kretser.py.

Det finnes ikke noe tegnet skjema: kretser.py er kilden. Dette skriptet tegner hver komponent som en boks med
pinnene og nettet på hver pinne (som et skjema der alle forbindelser går med nettetiketter), gruppert etter funksjon.
Samme nettnavn = samme ledning.

  skjema.pdf      én side per funksjonsblokk (A4 liggende)
  pinner.csv      ESP32-S3-pinnene: modulpinne, GPIO, nett, funksjon

Bruk:  python3 hovedkort/lag_skjema.py"""
import csv
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import kretser  # noqa: E402

K = {r: (fp, v, p) for r, fp, v, side, x, n, rot, p in kretser.KOMP}
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
f_tit, f_hode, f_pin, f_lite = ImageFont.truetype(FB, 34), ImageFont.truetype(FB, 19), ImageFont.truetype(FM, 16), ImageFont.truetype(F, 15)
SB, SH = 1754, 1240   # A4 liggende, 150 dpi

FUNKSJON = {
    "IR_TX": "IR-sender (→ Q4)", "IR_RX": "IR-mottaker VS1838B", "VIB_SW": "vibrasjonsbryter (vekking, ext1)",
    "TCA_INT": "INT fra 3 × TCA9555 (vekking, ext0)", "SKJ_PA": "3V3_SW av/på (Q2, lav = på)", "MOTOR": "vibrasjonsmotor (→ Q5)",
    "CHRG": "TP4056 CHRG (lav = lader)", "SDA": "I²C SDA (TCA9555)", "SCL": "I²C SCL (TCA9555)",
    "T_SDA": "I²C SDA berøring (3V3_SW)", "T_SCL": "I²C SCL berøring (3V3_SW)", "T_INT": "berøring INT", "T_RST": "berøring RST",
    "LCD_MOSI": "skjerm SPI MOSI", "LCD_SCK": "skjerm SPI SCK", "LCD_DC": "skjerm DC", "LCD_RES": "skjerm RES",
    "LCD_BL": "baklys PWM (→ Q3)", "USB_DN": "USB D−", "USB_DP": "USB D+", "BOOT": "BOOT-knapp (strappinne)",
    "VBAT_ADC": "batterispenning (1 M / 1 M)", "U0TXD": "UART TX (testpunkt)", "U0RXD": "UART RX (testpunkt)",
    "EN": "reset (10 kΩ / 1 µF, RESET-knapp)", "3V3": "forsyning", "GND": "jord",
}
BLOKKER = [
    ("1  ESP32-S3-WROOM-1 med reset og BOOT", ["U1", "C1", "C2", "R1", "C3", "SW44", "SW45", "R2"]),
    ("2  USB-C, ESD, lader, lastdeling, LDO og batteri", ["J1", "R3", "R4", "U2", "C14", "C15", "U3", "R5", "C4", "C5", "R6",
                                                         "D1", "Q1", "R7", "R8", "U4", "C6", "C7", "R9", "R10", "C8", "J2"]),
    ("3  Skjerm, berøring, skjermstrøm og baklys", ["J3", "J4", "Q2", "R11", "C9", "Q3", "R12", "R13", "R14", "R24", "R25", "R18"]),
    ("4  TCA9555 og I²C", ["U5", "U6", "U7", "C10", "C11", "C12", "R15", "R16", "R17"]),
    ("5  IR, motor, vibrasjonsbryter og testpunkter", ["J5", "Q4", "R19", "R20", "C13", "Q5", "R21", "R22", "D2", "TP1", "TP2",
                                                      "TP3", "TP4", "R23"] + [f"TP{i}" for i in range(5, 16)]),
]


def sorter(p):
    return (0, int(p)) if p.isdigit() else (1, p)


def kort(d, x, y, ref, bredde):
    fp, v, p = K[ref]
    pins = sorted(p, key=sorter)
    h = 34 + 22 * len(pins)
    d.rectangle([x, y, x + bredde, y + h], outline=(30, 30, 30), width=2)
    d.rectangle([x, y, x + bredde, y + 30], fill=(232, 236, 242))
    d.text((x + 8, y + 5), f"{ref}  {v}", font=f_hode, fill=(0, 0, 0))
    for i, q in enumerate(pins):
        yy = y + 36 + 22 * i
        n = p[q]
        farge = (170, 30, 30) if n in kretser_forsyning else (20, 60, 150) if n.startswith("K_") else (0, 0, 0)
        d.text((x + 8, yy), f"{q:>4}", font=f_pin, fill=(90, 90, 90))
        d.line([x + 56, yy + 9, x + 80, yy + 9], fill=(120, 120, 120), width=2)
        d.text((x + 86, yy), n, font=f_pin, fill=farge)
    return h


kretser_forsyning = {"GND", "3V3", "3V3_SW", "VSYS", "VBAT", "VBUS"}


def side(tittel, refs, nr, av):
    im = Image.new("RGB", (SB, SH), "white")
    d = ImageDraw.Draw(im)
    d.text((60, 40), tittel, font=f_tit, fill=(0, 0, 0))
    d.text((60, 88), "Skjold Fjernkontroll – hovedkort · laget av lag_skjema.py fra kretser.py · samme nettnavn = samme ledning · "
           "rødt = forsyning, blått = taster", font=f_lite, fill=(80, 80, 80))
    d.text((SB - 200, SH - 50), f"side {nr} av {av}", font=f_lite, fill=(80, 80, 80))
    x, y, kol_b, toppy, kol = 60, 130, 250, 130, 0
    for r in refs:
        bredde = 330 if len(K[r][2]) > 12 else kol_b
        h = 34 + 22 * len(K[r][2])
        if y + h > SH - 70:
            x += kol + 30
            y, kol = toppy, 0
        kol = max(kol, bredde)
        if r == "U1" or h > SH - 200:   # lange pinnelister i to kolonner
            pins = sorted(K[r][2], key=sorter)
            halv = (len(pins) + 1) // 2
            for del_ in (pins[:halv], pins[halv:]):
                sub = {q: K[r][2][q] for q in del_}
                K["_"] = (K[r][0], K[r][1], sub)
                kort(d, x, y, "_", 330)
                d.rectangle([x + 2, y + 2, x + 328, y + 29], fill=(232, 236, 242))
                d.text((x + 8, y + 5), f"{r}  {K[r][1]}", font=f_hode, fill=(0, 0, 0))
                x += 360
            y, kol = toppy, 0
            x -= 30
            continue
        y += kort(d, x, y, r, bredde) + 24
    if nr == 4:
        d.text((x + kol_b + 60, toppy), "Tastene SW1–SW43 (oppsiden): hver mellom sitt K_-nett og GND.\n"
               "Adresser: U5 0x20, U6 0x21, U7 0x22.\nU7 P11–P15 er ledige (intern pull-up).", font=f_lite, fill=(0, 0, 0))
    return im


def main():
    sider = [side(t, r, i + 1, len(BLOKKER)) for i, (t, r) in enumerate(BLOKKER)]
    pdf = os.path.join(HER, "skjema.pdf")
    sider[0].save(pdf, save_all=True, append_images=sider[1:], resolution=150)
    sider[0].save(os.path.join(HER, "skjema_esp.png"))
    rader = [("modulpinne", "GPIO", "nett", "funksjon")]
    for p in sorted(kretser.ESP, key=sorter):
        n = kretser.ESP[p]
        g = kretser.GPIO.get(n, "")
        rader.append((p, f"GPIO{g}" if g != "" else "", n or "(åpen)", FUNKSJON.get(n, "")))
    with open(os.path.join(HER, "pinner.csv"), "w", newline="") as f:
        csv.writer(f).writerows(rader)
    print("skrev skjema.pdf,", len(sider), "sider, og pinner.csv,", len(rader) - 1, "pinner")


if __name__ == "__main__":
    main()
