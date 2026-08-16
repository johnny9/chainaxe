# ChainAxe agent instructions

ChainAxe is safety-relevant, pre-prototype open hardware. Do not describe the design, BOM, Gerbers, or firmware as production-ready unless every applicable gate in `design-review-checklist.md` is closed with evidence.

## Required checks

- Run `python3 scripts/validate_design.py .` after changing KiCad, CSV, or connector files.
- Run KiCad ERC and DRC after any electrical or PCB change when KiCad is available. Do not suppress a warning without a written reason.
- Keep schematic, PCB, engineering BOM, JLC table, and connector documentation synchronized.
- Treat manufacturer footprints, JLC/LCSC availability, USB impedance, high-current copper, and thermal calculations as release-time checks, not assumptions.

## Fixed Rev A.1 boundaries

- J10 is 2×9 / 18 positions. Pins 1–16 follow `docs/connector-pinout.md`; pins 17–18 are NC.
- J1 is regulated 12 V fan power. J6 is low-current 12–15 V logic power. Do not join them except through the deliberate, normally open 12 V-only JP1 path.
- Four fan connectors use `GND, 12V, TACH, PWM` and must default to full speed when the controller is unpowered or not armed.
- Rev A.1 has no PSU communication, PSU-enable output, or guaranteed hard cutoff for hashboard core power.
- RESET has an independent, normally disabled buffer. The default S21-safe assembly leaves the series RESET link open/DNP, and S21 BM1368 NoPIC firmware must also never enable or drive the buffer.
- A0/A1/A2 high straps may connect only to switched `HB_3V3`, never always-on `3V3`.

## Source hygiene

Use `sources.md` for reviewed evidence and pin source revisions. Do not copy KiCad artwork from aditBoard or AntHat without a license or explicit permission. Preserve CERN-OHL-S-2.0 notices for covered ChainAxe hardware and keep any GPL firmware work in its proper licensing boundary.
