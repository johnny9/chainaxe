# ChainAxe KiCad project

This directory contains the editable Rev A.1 KiCad baseline.

## Files

- `chainaxe.kicad_pro` — KiCad project settings and provisional net classes.
- `chainaxe.kicad_sch` — annotated preliminary schematic.
- `chainaxe.kicad_pcb` — 100 × 70 mm unrouted placement baseline.
- `chainaxe.kicad_dru` — conservative prototype rules.
- `pin-net-audit.csv` — exhaustive expected/actual connection contract for every schematic pin.
- `symbols/ChainAxe.kicad_sym` and `sym-lib-table` — project-local custom symbols.
- `ChainAxe.pretty/` and `fp-lib-table` — nine pinned project-local manufacturer-derived/audited footprints.

Open `chainaxe.kicad_pro` in KiCad 9. KiCad may update generated metadata when the project is first saved; review that diff before committing it.

The source package is structurally checked by `scripts/validate_design.py`. The exhaustive `pin-net-audit.csv` contract is independently checked against physical symbol-pin endpoints by `scripts/validate_schematic_pinmap.py`; that validator explicitly converts KiCad library Y-up coordinates to schematic Y-down coordinates. `scripts/validate_pcb_geometry.py` checks different-net pad intersections, NPTH/copper conflicts, body/courtyard collisions, and undocumented edge overhangs. All three are dependency-free CI checks. This build environment does not include `kicad-cli`, so a local KiCad 9 ERC/DRC run remains mandatory before any fabrication export; none of the source validators replaces it.

Fan startup is hardware-defined: R105 holds `FAN_ARM` low, while R106–R109 hold the four EMC2305 PWM inputs to U8 low. This keeps the open-drain fan sinks released (the supported-fan full-speed-safe state) even if firmware asserts `FAN_ARM` before configuring the EMC2305. J30's audit enumerates every USB4105-GF-A signal/power contact; its A9/B9 VBUS and A12/B12 ground contacts are stacked on their shared logical nets. The official footprint numbers all four conductive shell stakes as `S1`, so one audited `S1` pin owns that common shell net.

C112 is the populated 100 nF USBLC6 VBUS bypass and must sit directly beside U9 pins 5/2. C3, the optional 220 µF 3V3 bulk footprint, is native DNP until AP64501 loop and load-transient validation proves an appropriate bulk value.

## Design status

This is an engineering-entry design, not an order-ready board. The schematic and PCB capture the intended architecture, safe startup states, connector map, and major candidate parts. The following remain release blockers:

- real-mating-part fit and keyed circuit-view checks for J1, J2–J6, J10, and USB-C; J6's exact connector/part remains a stop-order choice;
- fan current, inrush, reverse-polarity FET, connector, copper, and thermal calculations;
- AP64501 feedback, compensation, inductor, capacitance, and thermal verification;
- ESD/TVS clamping analysis and final ordering codes;
- exact first hashboard SKU/profile, including RESET policy and local voltage-off behavior;
- KiCad ERC, PCB synchronization, routing, stack-up impedance calculation, and DRC; and
- JLCPCB assembly preview, BOM/CPL reconciliation, and first-article review.

Do not generate production Gerbers from this baseline without closing the stop-order gates in `../../design-review-checklist.md`.

## PCB intent

The PCB is intentionally unrouted. The fan-current band stays at the top/right edge, the J10 interface lane stays at the left edge, and the ESP32-S3 antenna faces the bottom board edge with a 15 mm keepout. The `USB_90OHM_PLACEHOLDER` and `FAN_POWER_PROVISIONAL` net classes are reminders, not validated geometries.
