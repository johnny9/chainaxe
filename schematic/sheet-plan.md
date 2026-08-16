# KiCad schematic-entry plan — Rev A.1

Create a hierarchical KiCad project with the following sheets. Rev A.1 is a direct S19/S21-family hashboard and four-fan controller; it has no PSU communication or PSU-enable interface.

## Sheet 1 — root / connectors

- J1 regulated 12 V high-current fan input (`FAN_12V`); this rail must not exceed the connected fans' rating.
- J6 low-current 12–15 V controller input (`VIN_LOGIC_12_15`).
- JP1 optional fan-rail-to-logic-input feed, fitted only when J1 is a verified regulated 12 V source.
- J2–J5 AntHat-style four-wire 12 V fan headers, silk-labeled `G / 12 / T / P`.
- J10 common Bitmain 2×9, 18-position hashboard data connector; positions 1–16 active and 17–18 NC.
- J30 USB-C for native USB and optional logic power.
- Hierarchical pins for each functional sheet.
- Four mounting holes, fiducials, and a labeled test-point table.

## Sheet 2 — power

- Three-source logic-input OR: J6 through D1, the JP1-qualified J1 feed through D2, and USB VBUS through D3.
- AP64501 3.3 V buck and complete compensation/feedback cell.
- J1 `FAN_12V_RAW` through two provisional parallel Q5/Q6 high-side P-channel reverse-polarity FETs, with gate resistor and 12 V Zener clamp, then D4 on the protected `FAN_12V` bus. Recalculate FET count and copper from measured current.
- J6 series D1 reverse-block/OR diode and a bidirectional D5 TVS appropriate to 12–15 V. Do not join the high-current fan path to the logic-input path except at the explicit JP1/D2 option.
- U5 TPS22917, populated, switches controller 3.3 V to `HB_3V3` and J10 pin 16.
- Rail-monitor divider, RC filter, and labeled test points.
- Copper/fusing note: J1 and J2–J5 carry fan current; J6, JP1, and the OR diodes carry controller current only.

## Sheet 3 — ESP32-S3

- ESP32-S3-WROOM-1-N16R8.
- Native USB protection and source-series resistors.
- EN RC/reset button and GPIO0 boot button.
- Debug UART/test pads; GPIO5 and GPIO6 reserved as labeled expansion/test pads.
- Local bulk and high-frequency decoupling.
- Explicit no-connects and antenna keepout note.

## Sheet 4 — hashboard interface

- U6 SN74AXC4T774-class 3.3 V-to-3.3 V gated interface for UART TX, UART RX, and PLUG.
- U7 TMUX1511PWR powered-off-protected switch, supplied by switched `HB_3V3`; use channels 1 and 2 for SCL/SDA, tie both selects to `HB_I2C_EN`, ground unused selects, and leave unused signal pins NC.
- 4.7 kΩ pull-ups on controller SCL/SDA to always-on `3V3`, and separate 4.7 kΩ cable-side pull-ups to switched `HB_3V3`.
- U12 independent SN74LVC1G125-class reset buffer: GPIO1 is reset data and GPIO4 is active-low output enable.
- 10 kΩ pullup on `HB_RESET_OE_N`; no fixed connector-side reset pulldown. Provide mutually exclusive optional bias pads and leave them DNP.
- DNP/open `RESET_ENABLE_LINK` between U12 and the cable-side 33 Ω position. The default S21-safe assembly leaves this physical path open; populate 33 Ω only for a validated legacy-reset target.
- Large schematic warning: the S21 BM1368 NoPIC profile must leave the link open and never enable or toggle U12.
- A0/A1/A2 default-low resistors and mutually exclusive high straps to switched `HB_3V3` only; never to always-on `3V3`.
- Connector-side ESD arrays and 33 Ω source-series options.
- Safe-state pulls on U5 enable, U6 OE, U7 enable, and U12 OE.

## Sheet 5 — fan controller

- EMC2305 with exposed pad, decoupling, 22 kΩ `CLK`, and 33 kΩ `ADDR_SEL` straps.
- SN74LVC126-class buffer disabled by `FAN_ARM` at reset, with 100 kΩ pulldowns on all four `EMC_PWM` inputs, followed by four 2N7002 open-drain PWM sinks.
- No controller-side PWM pull-up rail; supported AntHat-style four-wire fans must provide their own compatible PWM pull-ups.
- Four 36 kΩ tach pull-ups to 3.3 V.
- ALERT pull-up and test points.
- `FAN_ARM` hardware pulldown, four buffer-input pulldowns, and individual MOSFET gate pulldowns.
- Optional RC/ESD footprints at external fan signal lines; populate only after signal-integrity review.

## Sheet 6 — expansion / test

- Labeled GPIO5/GPIO6 expansion pads with ground and 3.3 V nearby.
- Programming/debug access and test points for all rails and external signals.
- Profile/assembly-variant identification pads.
- No PSU connector, PSU control net, or PSU communications circuitry.

## ERC conventions

- Name every voltage domain: `FAN_12V`, `VIN_LOGIC_12_15`, `USB_VBUS`, `LOGIC_IN`, `3V3`, and `HB_3V3`.
- Use net ties only where a documented single-point connection is required; do not silence ERC with generic power flags.
- Mark DNP alternatives with assembly variants and mutually exclusive population groups.
- Add a note beside every external connector specifying the drawing view and pin-1 indicator.
- Include source URL, datasheet revision, and footprint-drawing revision as symbol/footprint properties for critical parts.
