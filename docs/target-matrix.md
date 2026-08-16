# S19/S21 target matrix

This matrix separates **connector compatibility** from **firmware readiness**. Rev A.1 uses one common 18-position/16-used, 3.3 V cable interface for all rows. A board is not allowed to mine until its exact SKU/profile defines chip family, chip count, address stride, UART sequence, reset behavior, and I²C voltage/temperature control.

| Miner family / example | ASIC | Typical chips per board | Current ESP-Miner chip driver | Rev A.1 status |
|---|---|---:|---|---|
| Legacy S19 / S19 Pro revisions | BM1398 | SKU-dependent | No | Connector-compatible; new driver required |
| S19 / S19 Pro / S19j-class BM1362 revisions | BM1362 | variants include 84, 88, 108, 120, or 126 | No | Connector-compatible; new driver required; model name alone is insufficient |
| S19 XP / S19j XP | BM1366 | variants include 70, 99, or 110 | Yes | Candidate after exact-SKU profile and full-chain tests |
| S19k Pro | BM1366 | commonly 77 | Yes | Candidate after exact-SKU profile and full-chain tests |
| S21 | BM1368 | commonly 108 | Yes | Preferred first S21 target; NoPIC-aware path required |
| S21 Pro | BM1370 | commonly 65 | Yes | Candidate after exact-SKU profile and reset/voltage proof |
| S21 XP | BM1370 | commonly 91 | Yes | Candidate after exact-SKU profile and reset/voltage proof |
| S21+ | BM1370 | commonly 55 | Yes | Candidate after exact-SKU profile and reset/voltage proof |

Counts are catalog/firmware evidence, not a substitute for reading the exact hashboard label/EEPROM, confirming its ASIC ID, and confirming enumeration. The same family name can span silicon and board revisions. Hydro, immersion, repair-class, and regional variants often use different counts and are outside the first-article scope.

## Recommended bring-up order

1. **S21 / BM1368 / 108 chips** — current ESP-Miner already has the chip driver, public full-board work identifies a 108-chip chain, and the main special case is explicit: do not apply legacy GPIO-reset behavior to the NoPIC/DAC power path.
2. **S19 XP / BM1366 / exact labeled count** — current chip driver exists, but the family has multiple chain counts and board revisions.
3. **BM1370 S21 variants** — driver exists, but use a distinct profile per exact SKU/count.
4. **BM1362 and BM1398 S19 variants** — hardware connector may be used, but firmware driver work comes first.

## Profile record required in firmware

Each supported hashboard must have an immutable profile containing:

- exact model/SKU string and accepted aliases;
- ASIC chip ID and expected response length;
- exact chip count and address stride;
- reset policy: `legacy_active_low`, `no_gpio_reset`, or another proven sequence;
- initial and operating UART baud plus register sequence;
- I²C devices, addresses, and pull-up assumptions;
- voltage enable/set/readback method, if present on the board;
- temperature sensor type, location, conversion, and limits;
- conservative frequency/voltage starting point;
- fan count and minimum airflow interlock; and
- tested shutdown and recovery order.

Runtime chip-ID detection may choose a driver, but it must not invent a chip count or power/reset policy. Ambiguous or unknown SKUs remain in management/diagnostic mode.

## Evidence notes

- Current ESP-Miner's ASIC enum and drivers include BM1366, BM1368, and BM1370, but not BM1362 or BM1398.
- ESP-Miner issue #248 records an S19 XP example with 110 BM1366 chips.
- DCENT_OS's S21 silicon profile records 108 BM1368 chips, 3.125 Mbaud Bitmain operation, and a NoPIC warning against legacy GPIO reset.
- Public third-party hashboard catalogs list multiple different counts within both S19 XP and S21-derived product names; exact SKU identity is therefore a required safety input.
