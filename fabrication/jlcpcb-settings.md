# JLCPCB-oriented fabrication and assembly settings — Rev A.1

This file records the intended production path; it is not an authorization to order an unreviewed board.

## PCB quote

| Setting | Starting choice | Release note |
|---|---|---|
| Layers | 4 | L2 solid GND; L3 quiet power |
| Size | 100 × 70 mm | Confirm final outline and connector overhang |
| Thickness | 1.6 mm | Match connector/mechanical design |
| Outer copper | 2 oz preferred | Confirm available JLC stack and impedance service |
| Inner copper | 1 oz | Recheck returned stack-up |
| Material | Standard FR-4, Tg ≥135 °C | Consider higher Tg after thermal testing |
| Surface finish | ENIG preferred | QFN/prototype yield; lead-free HASL is an alternate |
| Solder mask | Any high-contrast color | Green usually offers best process latitude |
| Impedance | 90 Ω differential USB | Use JLC's calculator with chosen stack |
| Via | 0.60/0.30 mm starting point | Use smaller only where required |
| Edge routing | Standard | No castellations or controlled-depth features planned |
| Electrical test | Flying probe | Required |

## Assembly quote

- SMT top-side assembly is the default.
- Hand-install or obtain a separate THT quote for J1, J2–J5, J6, J10, and JP1 until part availability, orientation, and mechanical fit are proven.
- Panel fiducials are JLC-managed; retain three local board fiducials away from edge copper and tall connectors.
- Use windowed paste apertures on the EMC2305 and AP64501 exposed pads; target roughly 50–70% paste coverage per package/application guidance and review the generated stencil.
- Keep DNP parts explicit in KiCad variants and exclude them from the uploaded BOM/CPL.
- Keep `RESET_ENABLE_LINK` DNP/open in the default S21-safe assembly. A legacy-reset BOM variant may populate 33 Ω only after the exact profile is validated.
- Do not place a common copper link between J1 `FAN_12V` and J6 `VIN_LOGIC_12_15`; the only permitted option is JP1 followed by D2 into `LOGIC_IN`.

## Required export set

1. Gerber X2 or standard Gerbers for all copper, mask, silk, and Edge.Cuts.
2. Excellon plated/non-plated drill files.
3. Fabrication drawing with stack, thickness, copper, finish, controlled impedance, and tolerances.
4. Assembly drawing showing every connector mating direction, pin 1, J10 positions 17/18 NC, and fan labels `G / 12 / T / P`.
5. BOM with `Comment`, `Designator`, `Footprint`, and exact `LCSC Part #`.
6. CPL/position file from the same final KiCad board, in millimetres, with side and rotation.
7. Read-me identifying every DNP, selection-required, and hand-installed component.

JLC's current KiCad guidance expects BOM and centroid/CPL files generated from the PCB project. Use `bom/jlcpcb-bom-template.csv` only as a column/example seed; never upload its planning references as production data.

## Quote-time checks

- Every LCSC code resolves to the intended manufacturer and exact MPN, not merely a compatible-looking package.
- No unavailable part silently substitutes a different electrical rating.
- JLC preview pin 1, rotation, and board side match the assembly drawing.
- USB connector shell/anchors and all QFN/exposed pads render correctly.
- No paste appears in THT holes unless the selected assembly process explicitly calls for pin-in-paste.
- Board outline, mounting holes, antenna keepout, and connector overhang match the mechanical print.
- J1, Q5/Q6, and J2–J5 are rated and thermally checked from measured simultaneous fan startup/stall current at regulated 12 V; J6 and D1 are rated for controller inrush at 15 V.
- D4/D5 standoff, clamp voltage, pulse energy, and coordination with the upstream protection are documented.
- U5/U6/U7/U12 directions, enables, safe pulls, and 3.3 V domains match the schematic review checklist; U7 is TMUX1511PWR/TSSOP-14, not PCA9306.
