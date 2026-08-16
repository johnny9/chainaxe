# Rev A.1 design-review and release checklist

Any unchecked item in **Stop-order gates** blocks Gerber/CPL release.

## Stop-order gates

- [ ] At least one initial profile is frozen with exact miner SKU, hashboard assembly/revision, ASIC type/count, PIC/NoPIC architecture, and captured factory startup sequence.
- [ ] J10 is a common keyed 2×9, 18-position cable connector; positions 1–16 match the documented map and 17/18 are confirmed NC.
- [ ] TX, RX, PLUG, SDA, SCL, pin-16 3.3 V, and profile-specific RESET behavior are verified on the exact target.
- [ ] S21 BM1368 NoPIC assembly leaves `RESET_ENABLE_LINK` open, and its profile is also proven never to enable the independent RESET buffer in boot, operation, watchdog, update, restart, and fault paths.
- [ ] Initial and operational UART baud, ASIC enumeration count, voltage-control path, telemetry, and local shutdown command are established per supported profile.
- [ ] Exact AntHat-style fan MPN, connector/key orientation, 12 V current, startup/stall current, tach pulses/revolution, and safe minimum RPM are recorded.
- [ ] J1 is labeled and protected for exact regulated 12 V fan power; J6 is labeled and protected for 12–15 V logic power.
- [ ] J1 pins 1–3 are GND and 4–6 are `FAN_12V_RAW`, matching the reviewed AntHat source and the final mating-face drawing.
- [ ] Q5/Q6 reverse-polarity FET count, SOA, current sharing, Rds(on), copper, and thermals pass measured simultaneous fan startup/stall current.
- [ ] JP1 cannot connect J1 to logic without an explicit `12V ONLY` assembly choice, and every J1/J6/USB combination is reverse-isolated.
- [ ] System-level safety review accepts that this revision cannot hard-remove hashboard core power and documents the external disconnect procedure.

## Schematic review

- [ ] Every external cable line has an intentional default state and connector-side ESD decision.
- [ ] U5/TPS22917 is populated; source/sink direction, reverse current, rise time, QOD choice, and pin-16 load are checked.
- [ ] U6/SN74AXC4T774 is populated; channel directions, `/OE` polarity, Ioff/partial-power behavior, and maximum profile baud are checked.
- [ ] U7/TMUX1511 is populated from `HB_3V3`; its exact TSSOP-14 pin map, powered-off isolation, two used channels, grounded unused selects, 100 nF decoupling, pull-ups, and enable sequencing are checked.
- [ ] Hashboard I²C rise time, low-level sink current, bus capacitance, and overshoot are measured at 100 kHz and the intended operating rate; `HB_I2C_EN` is low before every `HB_3V3` ramp.
- [ ] U12 RESET buffer has an enable independent of U6 and defaults high-impedance with an ESP reset or unpowered.
- [ ] No fixed pull-up/pull-down on HB_RESET can violate an S21 NoPIC profile; any optional bias is visibly DNP/profile-specific.
- [ ] Every A0/A1/A2 high strap connects only to switched `HB_3V3`; the corresponding low/high population pair cannot be fitted incorrectly.
- [ ] The default S21-safe DNP RESET link provides a firmware-independent open circuit during ESP bootloader, brownout, crash, update, and USB-only operation.
- [ ] J10 pins 17 and 18 are electrically NC.
- [ ] AP64501 feedback, inductor, input/output capacitance after DC bias, transient response, loss, and thermal rise are calculated over J6 = 12–15 V.
- [ ] Logic-source OR cannot backfeed USB, J1, or J6; USB-only power leaves fan sinks released, HB_3V3 off, UART/I²C disabled, and RESET high-impedance.
- [ ] JP1 and its diode are rated for the logic load and not treated as a way to operate 12 V fans from 15 V.
- [ ] EMC2305 address and hardware 100%-speed startup decode are checked against the current datasheet.
- [ ] Fan-driver polarity is traced end-to-end: command → EMC output → buffer → NMOS → fan PWM input.
- [ ] `FAN_ARM` defaults inactive and cannot assert before verified 100% command/readback.
- [ ] `EMC_PWM1..4` each have a populated 100 kΩ pulldown at U8, and the early-arm fault case is bench-tested to keep fan PWM released/full speed.
- [ ] Every supported fan is proven to provide a compatible internal PWM pull-up and to request full speed when the controller sink is released; Rev A.1 has no external PWM pull-up rail.
- [ ] ESP strapping pins 0/3/45/46 are not used for operational safety outputs.
- [ ] No PSU-control connector, enable circuit, bus, GPIO assignment, or misleading power-cut label remains.
- [ ] ERC has no unexplained power, unconnected, or conflicting-driver warnings.

## PCB / mechanical review

- [ ] Manufacturer drawings are used for every high-current and cable connector footprint.
- [ ] 1:1 paper fit and real mating-connector fit are complete for J1, J2–J6, J10, and J30.
- [ ] J30's drawing-derived USB4105-GF-A footprint is verified by 1:1 print and real-part fit, including every VBUS/GND contact, through-hole shell stake, locating peg, board-edge datum, and pin-1 orientation.
- [ ] J10 mating-face pin 1, 2×9 keying, and no-connect positions 17/18 match the cable.
- [ ] Fan pin 1 and `G 12 T P` functions are visible after assembly and match the AntHat-style harness.
- [ ] `FAN 12V ONLY` and `LOGIC 12–15V` are distinct, legible labels; JP1 carries a `CLOSE ONLY WITH 12V J1` warning.
- [ ] Selected JLC four-layer stack is entered in KiCad and USB is solved for 90 Ω differential, ±10%.
- [ ] L2 is continuous ground under USB, UART, I²C, tach, ESP, and buck control routes.
- [ ] ESP antenna is outside/at the chassis boundary with 15 mm copper/component/metal/cable keepout, or U1 is changed to a validated external-antenna module.
- [ ] Fan-current path is reviewed from the upstream external fuse/wiring through J1 contacts, Q5/Q6, pad, neck, pour, via field, and each branch connector.
- [ ] IPC-2152/current-density analysis uses measured simultaneous startup/stall current and selected copper weight.
- [ ] Prototype thermography confirms connector, fuse, pour, and via-field temperature rise at worst case.
- [ ] Buck hot loop and SW node are compact; FB is quiet; exposed-pad thermal vias and paste windows are reviewed.
- [ ] J1, J6, USB, fan, and hashboard ESD/TVS returns reach connector ground without crossing sensitive logic returns.
- [ ] U12 and its 33 Ω RESET resistor are routed independently from UART enable and placed close to the J10 interface.
- [ ] DRC passes final JLC rules; there is no silkscreen over pads and solder-mask slivers meet the chosen process.

## BOM / JLC assembly review

- [ ] Every LCSC code is reopened at quote time and matched to manufacturer, exact MPN, package, lifecycle, and stock.
- [ ] Basic/extended/THT handling and minimum quantities are accepted.
- [ ] DNP and hand-install lists agree across schematic, BOM, CPL, assembly drawing, and README.
- [ ] U5, U6, U7, U12, their default-enable resistors, and connector-side protection are fitted in the intended Rev A.1 variant.
- [ ] JP1 is open by default and assembly notes prevent automatic solder bridging.
- [ ] CPL rotation/side and pin 1 are inspected in JLC's assembly preview for every fitted part.
- [ ] QFN exposed-pad and THT paste openings are inspected; no accidental open-hole paste remains.
- [ ] A five-board first article is ordered and reviewed before volume assembly.

## Bring-up / DVT

- [ ] Bare-board continuity and isolation pass between FAN_12V, VIN_LOGIC_12_15, LOGIC_IN, USB_VBUS, 3V3, and HB_3V3.
- [ ] Current-limited USB-only, J6 = 12 V, J6 = 15 V, and J1 = 12 V power-ups pass before J10/fans are installed.
- [ ] No test applies more than 12 V to J1 or the fan connectors.
- [ ] Hardware defaults are measured before firmware: fan PWM sinks released, HB_3V3 off, UART/I²C disabled, RESET high-impedance, and JP1 open.
- [ ] Four fans start at full speed before `FAN_ARM`; every unplug/stall produces the expected fault.
- [ ] Hashboard cable is first tested with core power disabled and all interface outputs disabled.
- [ ] Each released profile enumerates its configured ASIC count on 100 cold starts and has clean readback at its final baud.
- [ ] S19 XP/S19k-class BM1366, S21 BM1368, and BM1370-family testing is tracked as separate profiles rather than inferred from connector compatibility.
- [ ] Fault injection stops work, attempts verified local shutdown when supported, disables cable I/O as permitted, preserves profile-safe RESET behavior, and releases fans to full speed.
- [ ] A failed local shutdown test explicitly demonstrates and documents the required external hashboard power removal.
- [ ] A 24-hour conservative mining soak passes before frequency/voltage exploration for each released profile.
