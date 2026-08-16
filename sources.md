# Source and license record

Accessed 2026-08-16. Repository commits are pinned where a reviewed revision was available. Part availability, board variants, and external documentation can change; revalidate them before design release.

## Requested hardware repositories

### bitaxeNaja

- Repository: https://github.com/bitaxeorg/bitaxeNaja
- Reviewed master commit: `6d815ef05288b3079a94567eb02c4e73d85dd82d`
- License: CERN Open Hardware Licence Version 2 — Strongly Reciprocal (`CERN-OHL-S-2.0`).
- Applicable facts: ESP32-S3-WROOM-1-N16R8 conventions, native USB implementation, and buffered ASIC signals.
- Boundary: Naja is a short, dual-BM1340 chain and is not proof of signal integrity, power sequencing, or firmware behavior on a full S19/S21 hashboard.

### aditBoard

- Repository: https://github.com/skot/aditBoard
- Production v2 revision reviewed: https://github.com/skot/aditBoard/tree/1c260d8767b7821e2b2d7aa110d65c469ff71d2d
- Firmware reference: https://github.com/skot/aditboard-firmware
- No hardware license was found in the repository. Use it as interface evidence; do not copy or redistribute its KiCad artwork or custom footprints without permission.
- Applicable facts: common 2×9 / 18-position cable connector, with signal positions 1–16 and positions 17–18 NC; USB/UART/I2C/GPIO bridge topology.
- Boundary: its firmware is a bridge rather than a miner, and the exact cable connector manufacturer/part number still needs procurement verification.

### AntHat

- Repository: https://github.com/skot/AntHat
- Master revision reviewed: `5a05b5dd6bb5a9b8b767a26e3bf38c463c0e4669`
- Newer v3 branch head inspected: `24fcf0eb23e5fd2e0015a6cf52990735f914ed60`
- No hardware license was found. Redraw circuits/footprints from manufacturer documentation or obtain permission before copying source artwork.
- Applicable facts: EMC2305 fan-control concept, four 12 V four-wire fan interfaces, logical fan pin order `GND, 12V, TACH, PWM`, Molex `0353180420` / LCSC `C54909` as the 2×2 fan-connector candidate, and Molex `0455580003` / LCSC `C492365` as its input connector. The reviewed source assigns input pins 1–3 to GND and 4–6 to VIN, and uses a DMP3013SFV-based reverse-polarity stage; Rev A.1 expands that stage provisionally for the four-fan load.
- Boundary: Rev A.1 intentionally does not use AntHat's PSU section.

## Hashboard and firmware evidence

- ESP-Miner baseline: https://github.com/bitaxeorg/ESP-Miner/tree/d3dbcc51d11d33b7579baac8c5b9808a4a112790
  - License: GPL-3.0.
  - `device_config.h`: https://github.com/bitaxeorg/ESP-Miner/blob/d3dbcc51d11d33b7579baac8c5b9808a4a112790/main/device_config.h
  - The reviewed baseline exposes BM1397, BM1366, BM1368, and BM1370 ASIC drivers. It does not expose BM1362 or BM1398 drivers.
  - Its current newer-ASIC implementations and UART17/18 convention are starting points, not full-hashboard profiles.
- ESP-Miner S19 XP investigation: https://github.com/bitaxeorg/ESP-Miner/issues/248
  - Records one 110-chip BM1366 S19 XP example and useful initialization discussion. Treat it as one board variant, not a universal count.
- DCENT_OS platform notes: https://github.com/DCentralTech/DCENT_OS/blob/main/DCENT_OS_Antminer/docs/PLATFORMS.md
  - Used to associate established Antminer families with BM1398, BM1362, BM1366, BM1368, and BM1370 generations. Family labels span revisions, so exact board identity still controls.
- DCENT_OS S21 BM1368 profile: https://github.com/DCentralTech/DCENT_OS/blob/main/DCENT_OS_Antminer/dcentrald/dcentrald-silicon-profiles/src/bm1368.rs
  - Records a 108-chip, three-chain S21 profile, 3.125 Mbaud Bitmain operation, and a NoPIC warning: GPIO-resetting the chain can kill the TAS5782M DAC voltage. Rev A.1 therefore has an independent reset output-enable and keeps it disabled for S21 NoPIC.
- Third-party current model catalog: https://github.com/molepool/GMiner-Molepool-Asic-Release
  - Used only as variant/count evidence for exact-profile planning: examples include BM1366 S19 XP at 70/99/110 chips, S19k Pro at 77, BM1368 S21 at 108, and BM1370 S21 variants at 55/65/91.
  - This is not silicon-vendor documentation and does not establish a safe voltage, frequency, reset sequence, or connector rating.

## Primary component and layout sources

- Espressif ESP32-S3-WROOM-1 / WROOM-1U module datasheet: https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf
  - Module land pattern, 3.7 mm center pad and via array, antenna-end orientation, and antenna keepout used for the project-local footprint.
- Espressif ESP32-S3 PCB layout guidance: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html
  - Board-edge antenna placement, 15 mm antenna keepout, continuous USB reference plane, and 90 Ω ±10% USB differential routing.
- Microchip EMC2301/2/3/5 datasheet: https://ww1.microchip.com/downloads/aemDocuments/documents/MSLD/ProductDocuments/DataSheets/EMC2301-2-3-5-Data-Sheet-DS20006532A.pdf
  - Four-wire fan support, PWM output configuration, tach measurement, startup strap behavior, and electrical limits.
- Diodes Inc. AP64501 datasheet, DS41980 Rev. 5-2: https://www.diodes.com/datasheet/download/AP64501.pdf
  - 3.8–40 V, 5 A synchronous buck candidate for the low-current logic rail. Its SO-8EP pin map, feedback equation, soft-start recommendation, compensation network, magnetics, output capacitance, and thermal behavior control the Rev A.1 implementation.
- TI TPS22917 datasheet, SLVSDW8B: https://www.ti.com/lit/gpn/TPS22917
  - Gated pin-16 3.3 V supply with reverse-current blocking; pin 4 is CT, pin 5 is QOD, and pin 6 is switched VOUT.
- TI TMUX1511 datasheet, SCDS390B: https://www.ti.com/lit/gpn/TMUX1511
  - Four-channel bidirectional switch with powered-off protection to 3.6 V, fail-safe select inputs, and internal select pulldowns. Rev A.1 powers it from `HB_3V3`, uses two channels for SCL/SDA, and adds an external enable pulldown.
- TI SN74AXC4T774 datasheet, SCES898C: https://www.ti.com/lit/gpn/SN74AXC4T774
- TI SN74LVC1G125: https://www.ti.com/product/SN74LVC1G125
- TI TPD4E05U06 datasheet/package drawing, SLVSBO7O: https://www.ti.com/lit/gpn/TPD4E05U06
  - DQA0010A signal lands, enlarged ground lands, pin numbering, and NC pins used for the cable-ESD footprint.
- ST USBLC6-2SC6: https://www.st.com/en/protections-and-emi-filters/usblc6-2.html
- Diodes Inc. DMP3013SFV datasheet: https://www.diodes.com/assets/Datasheets/DMP3013SFV.pdf
  - PowerDI3333-8 package pins 1–3 are source, pin 4 is gate, and pins 5–8 are drain. The reverse-input topology must be checked against that physical package map and diode-mode tested before fabrication.
- onsemi BZX84C12LT1G product/datasheet: https://www.onsemi.com/products/discrete-power-modules/zener-diodes/bzx84c12l
  - The SOT-23 map is pin 1 anode, pin 2 NC, pin 3 cathode. Rev A.1 uses it from the P-FET gate to protected `FAN_12V`; the 250 mW rating and clamp current need calculation and transient verification.
- Bitmain fan overview: https://support.bitmain.com/hc/en-us/articles/4402395808409-General-knowledge-and-Recurring-problem-about-Fan
  - General evidence that S19-family fans are four-wire 12 V units; the exact fan label/datasheet controls current, connector, pulses/revolution, and speed limits.
- Molex 0455580003 sales drawing SD-45558-001: https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/455/45558/455580003_sd.pdf
  - J1 contact pitch, hole diameters, retention pegs, and circuit-1 orientation.
- Molex 0353180420 sales drawing SD-35318: https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/353/35318/353180420_sd.pdf
  - J2–J5 unequal row/column pitch, hole diameters, and circuit numbering.
- GCT USB4105 drawing: https://gct.co/files/drawings/usb4105.pdf
- KiCad 8.0.9 USB4105 footprint: https://gitlab.com/kicad/libraries/kicad-footprints/-/blob/8.0.9/Connector_USB.pretty/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.kicad_mod
  - Drawing-derived USB-C signal lands, locating pegs, shell stakes, courtyard, and board-edge datum. KiCad footprint-library material is distributed under CC BY-SA 4.0; any vendored copy remains under that license.

## JLCPCB/LCSC references

- JLCPCB KiCad BOM/CPL export guide: https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad
- JLCPCB BOM/CPL matching guidance: https://jlcpcb.com/help/article/common-bom-and-cpl-matching-issues-and-explanations
- Candidate LCSC pages:
  - ESP32-S3-WROOM-1-N16R8: https://www.lcsc.com/product-detail/C2913202.html
  - AP64501SP-13: https://www.lcsc.com/product-detail/C2071517.html
  - EMC2305-1-AP-TR: https://www.lcsc.com/product-detail/C621415.html
  - TMUX1511PWR: https://www.lcsc.com/product-image/C2866750.html
  - BZX84C12LT1G: https://www.lcsc.com/product-detail/C82475.html
  - USBLC6-2SC6: https://www.lcsc.com/product-detail/C7519.html
  - TPS22917DBVR: https://www.lcsc.com/product-detail/C2681320.html

These are sourcing candidates, not a frozen AVL. Confirm package, lifecycle, stock, JLC basic/extended status, substitutions, voltage ratings, and thermal limits at quotation time. Provisional TVS, connectors, power diodes, magnetics, fan-current protection, and reset-buffer ordering codes intentionally remain TBD in the engineering BOM.

## Clean-room and licensing boundary

This package records public interface facts and new engineering decisions. It intentionally contains no copied KiCad schematic, PCB, Gerber, or custom footprint file from the unlicensed aditBoard or AntHat repositories. If a later implementation copies CERN-OHL-S-2.0-covered Naja hardware or incorporates GPL-3.0-covered ESP-Miner code, distribute the required corresponding source and notices under those licenses.
