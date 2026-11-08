"""Lag et enkelt skjermbilde for OLED-en på Skjold Røst (128 × 64, hvit på svart) til renderne: render/oled.png.

squeezelite-esp32 viser kanal/låt, artist og volum på skjermen. Bildet er en enkel etterligning av det, tegnet med
skarpe piksler (ingen kantutjevning), så det ser ut som en ekte 128 × 64-skjerm når det legges inn i bildene."""
import os

from PIL import Image, ImageDraw, ImageFont

HER = os.path.dirname(os.path.abspath(__file__))
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def main():
    im = Image.new("1", (128, 64), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    small, big = ImageFont.truetype(F, 9), ImageFont.truetype(FB, 15)
    d.text((0, -1), "FAVORITT 3", font=small, fill=1)
    d.text((128, -1), "18:42", font=small, fill=1, anchor="ra")
    d.text((0, 12), "NRK P3", font=big, fill=1)
    d.text((0, 31), "Ofenbach – Dance Th", font=small, fill=1)
    # volum: høyttalersymbol og stolpe
    d.polygon([(0, 52), (3, 52), (7, 48), (7, 60), (3, 56), (0, 56)], fill=1)
    d.rectangle([12, 52, 105, 56], outline=1)
    d.rectangle([12, 52, 12 + int(93 * 0.34), 56], fill=1)
    d.text((128, 48), "34", font=small, fill=1, anchor="ra")
    im.convert("RGB").save(os.path.join(HER, "render", "oled.png"))
    print("skrev render/oled.png")


if __name__ == "__main__":
    main()
