# Verktøy for kabinett og dokumentasjon

Alle skript kjøres fra `kabinett/tools/`. Krever Python 3 med `manifold3d`, `numpy`, `matplotlib`, `markdown`, `playwright` (pip), og Node med `playwright` + `three@0.128` (npm) for stegbildene.

| Skript | Lager | Kjør |
|---|---|---|
| `build_stl.py` | `../stl/v2_body.stl`, `v2_frontplate.stl`, `v2_lid.stl`, `v2_lid_frittstaende.stl` fra parametrene i `../scad/pultforsterker_v2.scad` (uten OpenSCAD, via manifold3d). `VARIANT=pi4` gir `*_pi4.stl` (200 × 135, Pi 4-layout), `VARIANT=pcb` gir `*_pcb.stl` (200 × 195, hovedkort + Pi 4) | `python3 build_stl.py` |
| `build_usbsw.py` | USB-switch-varianten (215 × 160 × 48, Ugreen 2 PC → 4 USB mot venstre vegg, hovedkort over Pi 4): `v2_body_usbsw.stl`, `v2_lid_usbsw.stl`, `v2_lid_frittstaende_usbsw.stl`, `v2_frontplate_usbsw.stl` og testfronten `v2_frontplate_test.stl` (0,91" OLED, 12 × 12-knapper med hette, 5 mm LED) | `python3 build_usbsw.py` |
| `make_usbsw_3d.py` | `../3d-usbsw/usbsw.json` til 3D-visningen `../3d-usbsw/index.html` | `python3 make_usbsw_3d.py` |
| `render_plan_pi4.py` | `guide_04_inni_pi4.png` – plantegning for Pi 4-varianten | `python3 render_plan_pi4.py` |
| `render_guide.py` | `guide_01_deler.png` – eksplodert 3D-visning av de tre delene | `python3 render_guide.py` (trenger STL-ene i samme mappe) |
| `render_panels.py` | `guide_02_bak.png`, `guide_03_front.png` – 2D-oppriss med nummererte hull og mål | `python3 render_panels.py` |
| `render_plan.py` | `guide_04_inni.png` – plantegning av innvendig plassering A–H | `python3 render_plan.py` |
| `render_closeups.py` | `steps/close_*.png` – lodde-/koblingsnærbilder (DAC-broer, knapp-pinner, bananplugg, KCD1/DC, Pi-header, lydvei, encoder, MOSFET) | `python3 render_closeups.py` |
| `render_steps.js` | `steps/step_01..16.png` – LEGO-aktige monteringssteg (three.js, headless Chromium) | `SCRATCH=<mappe med node_modules> node render_steps.js` |
| `build_manual_pdf.py` | `KI_Pultforsterker_Byggeveiledning.pdf` fra `docs/byggeveiledning.md` + guide-bildene | `python3 build_manual_pdf.py ../../docs/byggeveiledning.md ut.pdf` |
| `build_lego_pdf.py` | `KI_Pultforsterker_Bildeveiledning.pdf` fra `steps/` | `python3 build_lego_pdf.py` |

Stiene øverst i PDF-skriptene (`K=Path(...)`) peker på arbeidsmappen de ble laget i – juster til `kabinett/` i dette repoet.

## Endre kabinettet

Parametrene i `pultforsterker_v2.scad` (hullmål, posisjoner, stolper) brukes både av OpenSCAD og av `build_stl.py`. Endre ett sted, bygg STL på nytt, kjør renderne på nytt.
