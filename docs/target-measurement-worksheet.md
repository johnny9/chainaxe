# Target identification and measurement worksheet

Complete one copy for every supported hashboard profile before moving Rev A.1 from schematic entry to fabrication release. Cable fit is common across the target family; ASIC protocol, count, reset policy, voltage-control path, and fast baud are not.

## Identification

| Field | Record |
|---|---|
| Miner SKU (for example S19 XP or S21) | |
| Hashboard label / assembly number | |
| Hashboard PCB revision | |
| ASIC marking and counted quantity | |
| PIC / NoPIC architecture | |
| Original control-board model/revision | |
| Data-cable part / photographs | |
| Profile name and firmware revision tested | |
| Fan manufacturer and MPN | |
| Fan rated voltage/current | |
| Fan connector family/keying | |

Attach clear photographs of the hashboard label, both sides of J10, both ends of the data cable, original-controller connector, and fan plug/socket. Record any factory firmware or EEPROM identity that distinguishes otherwise similar boards.

## Unpowered continuity

Record the connector view used: `mating face / solder side / PCB top / PCB bottom`.

| Position | Expected function | Continuity / observation | Confidence |
|---:|---|---|---|
| 1 | GND | | |
| 2 | GND | | |
| 3 | SDA | | |
| 4 | SCL | | |
| 5 | PLUG | | |
| 6 | A2 | | |
| 7 | A1 | | |
| 8 | A0 | | |
| 9 | GND | | |
| 10 | GND | | |
| 11 | TXD | | |
| 12 | RXD | | |
| 13 | GND | | |
| 14 | GND | | |
| 15 | RESET | | |
| 16 | 3V3 | | |
| 17 | NC | | |
| 18 | NC | | |

Confirm that the exact cable uses a 2×9 shell with positions 17 and 18 unused. Do not substitute a 2×8 connector or omit its keying simply because only 16 positions carry signals.

## Original-controller capture

Only perform powered measurements if equipped to work safely around high-current DC equipment. Keep the hashboard in its original cooling arrangement. Use a ground-referenced differential or isolated measurement method appropriate to the power system; never assume an oscilloscope earth clip can be attached to an arbitrary node.

| Signal | Idle voltage | Active min/max | Source/pull-up side | Timing / notes |
|---|---:|---:|---|---|
| Pin 16 / 3V3 | | | | Startup and shutdown sequence |
| TXD | | | | Initial baud and operational baud |
| RXD | | | | Return-data polarity and timing |
| RESET | | | | Driven, high-impedance, or never touched? |
| PLUG | | | | Inserted/removed levels |
| SDA | | | | Pull-up value/rail if measurable |
| SCL | | | | Frequency and clock stretching |
| A0/A1/A2 | | | | Static strap or sampled function |

Save logic-analyzer captures from cold power-on through ASIC enumeration, including all local-voltage-controller or EEPROM transactions. Record both the conservative bring-up baud and the final operational baud.

### Reset policy gate

| Question | Result |
|---|---|
| May this exact profile drive RESET? | |
| Required polarity and pulse timing | |
| Required state while pin 16 is off | |
| Evidence/source | |
| Firmware unit/integration test name | |

For the S21 BM1368 NoPIC profile, the required result is **controller must never enable or drive RESET**. Verify this electrically across boot, normal mining, software restart, watchdog reset, and every injected fault.

## Hashboard-local voltage and shutdown

Rev A.1 does not communicate with or switch the external PSU. Characterize the hashboard-local control path without treating it as a guaranteed hard disconnect.

| Item | Record |
|---|---|
| Voltage-control device/address | |
| Safe initial command/voltage | |
| Enable/ramp sequence | |
| Telemetry/status available | |
| Local voltage-off/shutdown command | |
| Verified outcome if command succeeds | |
| Failure indication and timeout | |
| Required external power-removal procedure | |

If the local shutdown path fails, Rev A.1 can stop work, disable cable I/O as the profile permits, and run fans at full speed, but it cannot remove hashboard core input power. The test plan must include a safe external disconnect procedure.

## Fan and supply characterization

J1 is an exact regulated 12 V high-current fan input. J6 is a separate 12–15 V low-current logic input. Do not characterize a 15 V fan operating point.

| Fan | Running A at 100% | Startup peak A / duration | Stall behavior | Tach pulses/rev | Minimum reliable PWM/RPM |
|---|---:|---:|---|---:|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |

| Power test | Input voltage | Input current | Result / temperatures |
|---|---:|---:|---|
| J1, four-fan simultaneous start | 12.0 V | | |
| J1, worst continuous fan load | 12.0 V | | |
| J6 minimum | 12.0 V | | |
| J6 maximum | 15.0 V | | |
| USB-only logic | 5.0 V | | |
| JP1 closed, verified 12 V J1 | 12.0 V | | |

Use the largest measured simultaneous-start value, connector derating, cable ampacity, ambient-temperature margin, and PCB thermography to set the fuse and copper requirement. Verify each unpowered input remains free of backfeed in every J1/J6/USB/JP1 combination.
