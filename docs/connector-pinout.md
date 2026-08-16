# Connector pinout and cable rules

All connector drawings and silkscreen must identify the **mating-face view**. A bottom-mounted or right-angle connector can mirror what the designer sees in KiCad. Verify orientation, keying, and pin 1 with continuity testing before applying power.

## J10 — common Bitmain hashboard data cable

Rev A.1 uses the common 2×9, 2.00 mm, 18-position Bitmain data connector. The electrical interface occupies positions 1–16; positions 17 and 18 remain no-connect. This preserves the cable form used by the target S19/S21 families even though it is often informally called a “16-pin” interface.

Proposed connector: right-angle female `PM200-2-09-W-4.3` / LCSC `C3012192`, pending a real-cable fit check and a manufacturer-drawing footprint audit.

| Pin | Net | Rev A.1 treatment | Direction at controller |
|---:|---|---|---|
| 1 | GND | Cable ground | — |
| 2 | GND | Cable ground | — |
| 3 | HB_SDA | TMUX1511 powered-off-protected switch; cable pull-up to `HB_3V3` | Bidirectional |
| 4 | HB_SCL | TMUX1511 powered-off-protected switch; cable pull-up to `HB_3V3` | Bidirectional |
| 5 | HB_PLUG | SN74AXC4T774 channel, ESD protected | Input |
| 6 | HB_A2 | 4.7 kΩ default low; mutually exclusive option to switched `HB_3V3` | Static strap |
| 7 | HB_A1 | 4.7 kΩ default low; mutually exclusive option to switched `HB_3V3` | Static strap |
| 8 | HB_A0 | 4.7 kΩ default low; mutually exclusive option to switched `HB_3V3` | Static strap |
| 9 | GND | Cable ground | — |
| 10 | GND | Cable ground | — |
| 11 | HB_TX | SN74AXC4T774 channel + 33 Ω source resistor | Output to hashboard |
| 12 | HB_RX | SN74AXC4T774 channel + 33 Ω damping resistor | Input from hashboard |
| 13 | GND | Cable ground | — |
| 14 | GND | Cable ground | — |
| 15 | HB_RESET | Independent tri-state reset buffer through `RESET_ENABLE_LINK` | Physical link DNP/open for default S21-safe assembly; fit 33 Ω only for a validated legacy-reset profile |
| 16 | HB_3V3 | Controller-supplied 3.3 V through U5/TPS22917 | Power output |
| 17 | NC | No connection | — |
| 18 | NC | No connection | — |

U5, the UART/PLUG translator, and the I²C switch are populated in Rev A.1. Their enables default inactive so an unconfigured ESP cannot drive the cable. The reset path has a separate output-enable signal from the normal UART enable; a profile may use UART and I²C while leaving RESET electrically high-impedance.

### Reset rule

RESET is not a universal startup primitive. The selected hashboard profile owns its polarity, level, timing, and whether it may be driven at all. In particular, the S21 BM1368 NoPIC assembly leaves `RESET_ENABLE_LINK` open and its firmware must **never enable the controller reset buffer**. A firmware update or fault handler must not bypass this rule.

### Cable validation

1. With both systems unpowered, trace cable pin 1 to ground and establish the mating-face orientation.
2. Confirm that positions 17 and 18 are unused on the exact board and cable.
3. Record the exact miner model, hashboard assembly/revision, ASIC type/count, and original-controller startup capture.
4. Power Rev A.1 with the hashboard's core rail off for the first interface test. Confirm 3.3 V at pin 16 and high-impedance UART/I²C/RESET before enabling one interface at a time.
5. Do not connect an unprofiled or unknown hashboard merely because the cable fits.

## J2–J5 — AntHat-style 12 V four-wire fans

Use the AntHat 2×2 candidate, Molex `0353180420` / LCSC `C54909`, and match the actual fan harness before releasing the footprint. Redraw it from Molex's current drawing rather than copying AntHat's custom combo footprint. Print the electrical order beside every connector as `G 12 T P`; do not rely on wire color.

| Pin | Signal | Notes |
|---:|---|---|
| 1 | GND | High-current motor return |
| 2 | FAN_12V | Exact regulated 12 V motor rail from J1 |
| 3 | TACHn | Open-collector/open-drain tach; pulled to 3.3 V |
| 4 | PWMn | External 2N7002 open-drain control; hardware default released for full speed |

Connector views in fan documentation can show these functions in the opposite visual order. Treat that as an orientation issue, not permission to swap functions. Validate pin 1, keying, power polarity, tach pulses/revolution, and PWM behavior on the actual AntHat fan before mating it to Rev A.1.

## J1 — regulated 12 V fan input

J1 is the high-current fan input. It must receive a regulated **12 V** supply suitable for the measured simultaneous startup/stall current of all four fans. Do not feed J1 with 15 V.

Proposed connector: Molex `0455580003` / LCSC `C492365`, using a datasheet-derived 2×3 THT footprint with three contacts paralleled per rail. AntHat uses this part for its input, but Rev A.1 restricts it to regulated 12 V fan power.

| Pins | Net |
|---|---|
| 1, 2, 3 | GND |
| 4, 5, 6 | FAN_12V_RAW |

This polarity follows the reviewed AntHat source. `FAN_12V_RAW` passes through the Q5/Q6 reverse-polarity stage before it becomes the protected `FAN_12V` bus. Do not reuse AntHat's custom footprint: generate a fresh footprint from the connector manufacturer's current drawing, print it 1:1, and perform a real-part fit check.

## J6 — 12–15 V logic input

J6 is a separate, low-current input for the controller buck regulator.

| Pin | Net | Notes |
|---:|---|---|
| 1 | VIN_LOGIC_12_15 | 12–15 V DC input, protected before the logic-power OR |
| 2 | GND | Logic return |

JP1 and its series diode provide an optional `FAN_12V → LOGIC_IN` feed. Close JP1 only when J1 is known to be a regulated 12 V source. The controller may instead be powered from J6 or USB. The OR network must prevent any source from backfeeding USB, J6, or the fan rail.

## J30 — USB-C device/debug

USB 2.0 device-only receptacle:

- CC1 and CC2: separate 5.1 kΩ pull-downs to GND.
- D+/D−: USBLC6-2SC6-class low-capacitance ESD, then matched 22–33 Ω series resistors near the ESP.
- VBUS: logic-power OR input and VBUS sense only; never connected directly to J1 or J6.
- Schematic-owned contacts: A4/A9/B4/B9 = `USB_VBUS`; A1/A12/B1/B12 = `GND`; A5/B5 = CC1/CC2; A6/B6 = D+; A7/B7 = D−; A8/B8 = NC; all four conductive shell stakes share pad number S1 = `USB_SHIELD`, matching the official KiCad/GCT footprint.
- The project-local USB4105-GF-A footprint vendors the official KiCad 8.0.9/GCT drawing-derived geometry, including every duplicated contact, four through-hole shell stakes, and two locating pegs; a real-part first-article fit check remains mandatory.
- USB-only power must leave fan sinks released, HB_3V3 off, UART/I²C disabled, and RESET high-impedance.
- Shield: configurable chassis/ground treatment; initial 1 MΩ ∥ 1 nF option plus a short ESD return, subject to enclosure strategy.
