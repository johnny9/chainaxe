# PCB floorplan and routing brief

## Board and stack-up

- Outline: 100.0 × 70.0 mm, 1.6 mm finished thickness.
- Four copper layers: L1 signals/power, L2 uninterrupted GND, L3 quiet logic power with fan-rail exclusions, and L4 signals/power.
- Copper: request 2 oz outer layers if supported by the selected JLC four-layer stack; 1 oz inner layers is acceptable. Recalculate fan-current temperature rise after the stack is fixed.
- Finish: ENIG is preferred for the EMC2305 exposed-pad QFN and prototype rework; lead-free HASL is acceptable after assembly-yield review.
- Prototype rules: begin at 0.15/0.15 mm track/space and 0.30 mm finished drill in a 0.60 mm via, unless the selected JLC capability is more conservative.
- Mounting: four M3 holes at (4,4), (96,4), (4,66), and (96,66) mm. Set plated/NPTH and copper clearance to the enclosure/chassis strategy.

The intended component placement is recorded in `pcb/placement.csv` and illustrated in `pcb/floorplan.svg`.

## Functional zones

| Zone | Approximate area | Rules |
|---|---|---|
| Four fan connectors and FAN_12V bus | y = 0–16 mm | Short, wide L1/L4 pours; dense stitching; no sensitive traces |
| J1 regulated 12 V fan input | x = 82–100, y = 10–32 mm | High-current connector, Q5/Q6 reverse-polarity FETs, and TVS coordinated with the upstream external fuse; multiple current-transfer vias and thermal copper |
| Fan controller and safe sinks | x = 42–72, y = 17–32 mm | Quiet tach reference; PWM NMOS devices close to fan fan-out |
| Logic buck | x = 74–96, y = 24–40 mm | Tight switch loop; keep SW copper small and away from antenna |
| Hashboard connector/interface | x = 0–38, y = 22–52 mm | J10 at edge; ESD first; gated 3.3 V, UART/I²C and independent RESET |
| J6 logic input and expansion | x = 0–40, y = 54–68 mm | Low-current 12–15 V input; separated from cable I/O; no PSU interface |
| ESP and USB | x = 62–100, y = 42–70 mm | Module antenna at bottom edge; 15 mm keepout |

## Placement order

1. Fix J1, J2–J6, J10, and J30 from manufacturer drawings and real mating plugs.
2. Put TVS/ESD devices between every external cable connector and the first active device.
3. Place AP64501, inductor, input/output capacitors, bootstrap, and feedback as one compact datasheet-derived cell. Keep FB away from SW.
4. Keep the protected J6 path, USB path, and optional JP1/diode fan-to-logic path distinct until the logic-power OR node.
5. Place EMC2305 and its decoupler between the fan signal routes but outside the fan motor-current return path.
6. Place U5, U6, U7, and U12 behind J10 protection. Keep U12 RESET output-enable independent from U6 UART enable.
7. Place the ESP32-S3 module at the bottom edge with the antenna projecting over or immediately adjacent to the edge.
8. Route USB first, then UART/RESET, I²C/tach, service nets, and finally fan power. Review return current in startup, stall, and fault states.

## Critical routing constraints

### USB and ESP antenna

- Solve D+/D− for 90 Ω differential, ±10%, using the selected JLC stack-up rather than a hard-coded width.
- Match D+/D− within 0.5 mm, use the same via count, avoid stubs, and maintain continuous L2 GND.
- Put ESD next to J30 and the 22–33 Ω resistors next to the ESP.
- Keep the module antenna at the board edge. No copper, planes, vias, traces, components, fasteners, cables, or enclosure metal within its 15 mm keepout.
- Do not route the fan bus, J6 input, or buck switch node behind the antenna.

### Hashboard signals

- Route TX/RX as single-ended 3.3 V CMOS, not as a differential pair.
- Keep TX/RX/RESET short and over solid ground. Put each 33 Ω source/damping resistor next to its driver/translator.
- Route RESET from U12 independently; do not merge its enable with the UART translator enable.
- Keep hashboard I²C together over ground and away from fan PWM edges.
- Put U5/TPS22917 close to J10 pin 16 and provide a local HB_3V3 test point.
- Stitch ground beside J10 pins 1, 2, 9, 10, 13, and 14 and beside protection-array returns.
- Leave pins 17 and 18 copper-free except for labeled no-connect pads.

### Fan motor power

- J1 accepts regulated 12 V only. J6 is the 12–15 V logic input; do not merge their upstream nets.
- Reserve at least a 12–14 mm board-edge band for FAN_12V and ground distribution.
- Use both outer layers and via stitching at 1.5–2.0 mm pitch around current-transfer necks, with multiple via rows at J1 and each fan branch.
- Treat every connector pad, reverse-polarity FET, neck, pour, and layer transition as part of the board current path, and include the upstream external fuse and wiring in the system review. A wide pour cannot rescue an undersized terminal or hot FET.
- Calculate simultaneous startup/stall current and temperature rise from the actual AntHat fans. The provisional design target is 12 A total, not a guaranteed rating.
- Route tach and PWM alongside quiet ground and never through a motor-return bottleneck.

### Logic power

- Keep the protected `FAN_12V`→JP1/D2, J6→D1, and USB→D3 paths visually and electrically separable before `LOGIC_IN`.
- JP1 must be inaccessible to accidental closure or carry an unmistakable `12V ONLY` silkscreen warning.
- Choose OR devices for reverse isolation across all unpowered-source combinations. Verify USB cannot backfeed J1/J6 and 12–15 V cannot reach VBUS.
- Minimize the buck high-di/dt loop: input ceramic → U3 VIN/PGND → switch → U3 PGND → input ceramic.
- Keep SW only large enough to connect U3 and L1. Place output capacitors immediately after L1 and route FB from the output-capacitor sense point away from SW.

## Suggested net classes

| Class | Nets | Start rule | Finalization |
|---|---|---|---|
| USB_DIFF | USB_DP, USB_DN | Solver-derived width/spacing | JLC stack and impedance review |
| FAN_PWR | FAN_12V, FAN_GND | L1/L4 pours | IPC-2152 plus prototype thermography |
| LOGIC_INPUT | VIN_LOGIC_12_15, LOGIC_IN | ≥0.75 mm where practical | OR-device/regulator current and surge analysis |
| LOGIC_PWR | 3V3, HB_3V3 | ≥0.50 mm where practical | Regulator/load-current calculation |
| HB_UART | HB_TX, HB_RX, HB_RESET | 0.20–0.25 mm | Scope edge quality at each profile baud |
| I2C_TACH | SDA/SCL/tach/alert | 0.20–0.25 mm | Rise-time check with final cable and pull-ups |
| GPIO | Remaining digital | 0.20 mm | Standard DRC |

## Assembly notes for JLCPCB

- Keep manufacturer MPN and LCSC code in separate fields. Footprint compatibility alone does not approve a substitute.
- Use explicit `DNP` fields for the optional fan pull-up rail, profile straps, and JP1; do not rely on omitted BOM rows.
- High-current and shrouded THT connectors may need hand installation or JLC wave/selective solder service.
- Inspect every rotation and side in JLC's assembly preview. Right-angle and bottom-inserted THT connectors need manual orientation review.
- Add labeled test pads for FAN_12V, VIN_LOGIC_12_15, LOGIC_IN, USB_VBUS, 3V3, HB_3V3, both I²C buses, TX, RX, RESET, RESET_OE_N, PLUG, and all tach/PWM channels.

## Fault-containment boundary

Rev A.1 has no PSU connection, so it cannot guarantee removal of the hashboard core supply. On a fault it can stop work submission, request the profile's hashboard-local voltage-off command when supported, disable cable interfaces, keep RESET behavior profile-safe, and release every fan PWM input for full speed. If local shutdown does not succeed, external removal of hashboard power is required. Placement, labels, and documentation must not imply a hard power-cut function that the PCB does not contain.
