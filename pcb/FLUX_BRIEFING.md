# Project briefing for Flux AI – KI Pultforsterker rev B (main board)

You are reviewing a finished, routed 2-layer board that is about to be ordered from JLCPCB (PCBA on top side).
Thank you for the previous review: your findings on **U4 PCM5102A pins 10/18** and **U7 FE1.1s footprint** were correct
and are fixed (plus a third one we then found ourselves on U8). Please read this whole brief before you start.

## 1. What the device is

A desk amplifier ("pultforsterker", product name *Skjold S1*) in a metal enclosure under a desk:

- **Raspberry Pi 4** (mounted under the board, 40-pin ribbon cable to J5) runs all audio: AirPlay 2, Bluetooth, Spotify Connect,
  internet radio, USB audio gadget, mixing and DSP (CamillaDSP), plus Home Assistant/Homey integration.
- **This board** does everything else: 24 V input and protection, 5 V/5 A buck for the Pi, I2S DAC, two digitised AUX inputs,
  analog volume (PGA2311), 2 × 50 W class-D amplifier (TPA3116D2), headphone amp, a USB KVM-style switch (2 PCs → 4 USB-A ports),
  front-panel buttons/encoder/LED rings/display, a "smart relay" that cuts power to the amplifier section in standby,
  and an over-temperature guard (NTC on the heatsink).

## 2. Files (KiCad 7)

| File | What |
|---|---|
| `ki_pultforsterker_main.kicad_pcb` | The routed board (180 × 100 mm, 2 layers, 1.6 mm). **This is the source of truth.** |
| `ki_pultforsterker_main.kicad_sch` + `ki_pultforsterker.kicad_sym` + `sym-lib-table` | Schematic **generated from the board**: every part as a symbol, connections as global labels with the board's net names (no drawn wires). Verified pin-for-pin against the PCB: 865 pads, 188 nets, 0 differences. 8 custom symbols (TPA3116D2DAD, PCM1808, PGA2311, LM2662, TS3USB221, PCM2900C, USB-C 16P, RPi 40-pin). |
| `build_board.py` | Python script that generates the whole board (parts, netlist `net(...)`, placement, fixed power tracks). Human-readable netlist. |
| `netlist.json`, `bom.csv` | Netlist and full BOM (value, footprint, LCSC code per reference). |
| `produksjon/` | Gerber zip, JLCPCB BOM + CPL (SMD only), THT hand-solder list, DRC report, renders, `skjema.pdf`. |
| `README.md` | Full design description in Norwegian (blocks, GPIO map, connectors, protection, known compromises). |
| `GRANSKNING_REV_B.md` | All review findings so far and what was fixed. |

The board was placed by script and auto-routed with Freerouting; GND is both routed and poured (zones on both layers). Power paths
(24 V, 5 V) are hand-laid locked tracks ("power spine").

## 3. Power tree

```
DC 19–24 V ─ KCD1 switch (off-board) ─ J1 ─ F1 5 A slow (Littelfuse 111 clips) ─ Q11 AOD409 P-MOSFET (reverse-polarity, D5 12 V zener + R79 on gate)
   └ VIN24 ─ D1 SMBJ28A TVS ─ C1/C110 680–1000 µF/35 V
        ├ K1 relay (SRD-05VDC, NO) ─ 24V_AMP ─ C40/C41 220 µF ─ U6 TPA3116D2 PVCC/AVCC
        └ U1 TPS54560 buck (400 kHz, L1 10 µH, 3 × 47 µF, 33k/6.2k → 5.06 V, EN 330k/49.9k → UVLO ≈ 9 V)
             └ 5V (always on): Pi (J6 + J5 pins 2/4), USB hub U7 + mux U8, MCP23017, relay coil, PGA2311 (VD+, and VA+ via FB1, VA− via LM2662 U3),
                TPA6132A2 headphone amp, U2 AMS1117 → 3V3 (DAC, ADC digital, oscillator, MCP, OLED/TFT logic)
                └ Q8 AO3401 (from GPIO 27 via Q7) → 5V_SW: LED rings, PCM1808 VCC (analog), U9 AMS1117 → 3V3_SW (TFT backlight only)
        F2 2 A polyfuse → 5V_USB → J15–J18 USB-A
```

**Design rule we care about:** nothing that is always powered may drive into an unpowered chip (that is why the DAC, ADC digital side,
MCP23017, PGA2311 and the displays' logic are on always-on rails, and only LED rings, ADC analog and backlight are switched).

## 4. Signal paths

- **Audio:** Pi I2S (Pi is I2S *slave*) → U4 PCM5102A DAC (SCK = GND, internal PLL) → 100 Ω/2.2 nF → 10 µF → U5 PGA2311 (±5 V, bit-banged
  from GPIO 0/1/16, fixed level, muted in standby) → (a) U6 TPA3116D2 BD mode, 26 dB, 400 kHz, LC filter L2–L5 10 µH / C49–C52 680 nF +
  RC snubbers → J2/J3; (b) U13 TPA6132A2 (+6 dB, EN from MCP GPA6) → J23 front 3.5 mm jack.
- **AUX 1:** J4 → divider → U10 PCM1808 ADC, I2S **master** 256 fs from X1 12.288 MHz → Pi I2S in (GPIO 20).
- **AUX 2:** J20 → divider → U11 PCM2900C USB codec (Y2 12 MHz), bus-powered from a Pi USB-A port via J19.
- **USB switch:** J11/J12 USB-C (PC1/PC2, CC 5.1 k pull-downs, USBLC6 ESD) → U8 TS3USB221 2:1 mux (S from MCP GPB4, OE = GND) →
  U7 FE1.1s 4-port hub (Y1 12 MHz, self-powered, BUSJ = high) → J15–J18 USB-A (USBLC6 each). The Pi is **not** on this hub.
- **Control:** U12 MCP23017 at I2C 0x20 (INTA → GPIO 14): GPA0–4 buttons, GPA5 jack detect, GPA6 HP enable, GPB0–3 LED-ring low-side
  FETs, GPB4 USB mux select, GPB5 over-temperature (NTC → R81/C112 → U14 74LVC1G14 Schmitt → GPB5). Encoder on GPIO 23/24/25,
  TPA3116 SDZ on GPIO 22, DAC XSMT on GPIO 26, relay on GPIO 27. Full GPIO map in README.

## 5. What has been verified (and how)

- **KiCad DRC:** 0 unconnected, 0 clearance, 0 hole-to-hole (rule set to 0.5 mm for JLCPCB), 0 edge errors. Remaining items are only
  silkscreen, 6 courtyard overlaps (pads ≥ 0.2 mm apart), 4 "starved thermal" on THT GND pads, 2 tiny dangling stubs, and 199
  `lib_footprint_issues` (footprints are embedded, no library nick).
- **Measured directly in the Gerbers** (independent script, X2 net attributes): all 189 nets continuous, no hole touching two nets,
  min hole-to-hole 0.508 mm, no via-in-pad, min copper clearance 0.143 mm, copper-to-edge ≥ 0.57 mm, paste on every SMD pad except
  R18 (DNP) and U6 exposed pad (TPA3116D2 **DAD** = PowerPAD on top, no paste by design).
- **Pin-by-pin against manufacturer datasheets:** U1, U3, U4, U5, U6, U7, U8, U10, U11, U12, U13, Q11, D6–D11, J11/J12, J15–J18, J5,
  diodes and electrolytic polarity – all OK after the fixes below. Package width/pitch checked against the LCSC "Package" field of the
  ordered part code.
- **BOM/CPL:** every line has an in-stock JLCPCB code (31 Oct 2026), one line per code, rotations checked visually in JLCPCB's preview.

## 6. Fixes made after your review (all routed and re-verified)

| Ref | Problem | Fix |
|---|---|---|
| U4 PCM5102A | pin 10 (DEMP) and 18 (LDOO) swapped – LDOO was grounded | pin 18 → C19 (DAC_LDOO), pin 10 → GND |
| U7 FE1.1s (C9359, SSOP-28 150 mil) | footprint was 5.3 mm / 0.65 mm | `Package_SO:SSOP-28_3.9x9.9mm_P0.635mm` |
| U8 TS3USB221RSER | footprint was onsemi UQFN-10 1.4 × 1.8 / 0.4 mm | `Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm` (RSE0010A) |
| U1 TPS54560DDA | ST HSOP footprint, small thermal pad | `Package_SO:Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm` |
| U5 PGA2311 | VA+/VA− were on switched 5V_SW while VD+ always on | whole PGA2311 on always-on 5 V |
| Buck output | 5.28 V (above 5.25 V limits) | 33k/6.2k → 5.06 V |

## 7. What we would like from you

Please review for **anything that would make the assembled board fail, damage parts, or be unsafe**, in this order:

1. Remaining **pin-number or footprint mismatches** – especially the parts we could not verify against a datasheet:
   **X1** JGHC O3212288153350 (C437124, 3225 4-pin oscillator – which pin is OE/ST, GND, OUT, VDD? Board: pads 1 and 4 = 3V3,
   2 = GND, 3 = OUT), **Y1/Y2** C9002 YXC X322512MSB4SI (board: pads 1/3 = crystal, 2/4 = GND), **K1** Songle SRD-05VDC-SL-C vs the
   KiCad SANYOU SRD footprint (board: 1 COM = 24V_AMP, 3 NO = VIN24, 2/5 coil), **U2/U9** AMS1117 SOT-223 (1 GND, 2/tab OUT, 3 IN),
   **U14** SN74LVC1G14DBVR, **Q2–Q10** AO3400A/AO3401A (1 G, 2 S, 3 D).
2. **Electrical design errors** in the circuits (bias, enable/reset levels, missing pull-ups, absolute-max violations, rails that can
   back-feed). Known open questions: TPS54560 compensation (R6 13 k / C6 3.3 nF / C7 47 pF) – is it stable with 10 µH + 3 × 47 µF
   ceramics at 5.06 V/400 kHz? Crystal load caps for FE1.1s (has internal caps) and PCM2900C (C87/C88 22 pF). PCM2900C D+ pull-up
   1.5 k to VCCCI.
3. **Layout risks** that DRC does not catch: thermal (TPA3116 has heatsink on top; U1 buck), current capacity (speaker tracks are
   0.4–0.5 mm on short stretches – we will order **2 oz copper**), buck hot loop (U1/C2/C3/D2/L1), USB D+/D− routing.

**Please do not** redesign, re-place or re-route anything, and do not change part choices unless something is actually wrong.
For each finding give: reference + pin, what the board has, what the datasheet says (with link/page), consequence, and severity
(CRITICAL = do not order / SHOULD FIX / INFO). If you are guessing rather than reading a datasheet, say so.

## 8. Known and accepted compromises (no need to report)

Single shared GND plane (analog/USB/class-D); USB not impedance-controlled (short traces, 2 layers); AMS1117 with 10 µF ceramic
output; no fiducials; THT parts (connectors, relay, fuse clips, C1/C110, USB-A) are hand-soldered and not in the CPL; the enclosure
(separate project) has its own list of mechanical conflicts that is being handled elsewhere.
