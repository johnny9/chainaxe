# BOM usage — ChainAxe Rev A.1

`chainaxe-reva-bom.csv` is the engineering BOM for the S19/S21-oriented controller. It deliberately retains TBD, DNP, `SELECT_BEFORE_RELEASE`, and `STOP_ORDER` rows so unknown connector, power, and protection choices cannot be mistaken for released production data. Rev A.1 contains no PSU connector or PSU-control circuitry.

`chainaxe-reva-engineering-bom.xlsx` is the review-friendly workbook. It contains a status summary, the complete engineering BOM, and the current JLC upload table. The CSV files remain the source for automation and JLCPCB import.

`jlcpcb-bom-template.csv` demonstrates JLCPCB's four useful upload columns for fitted SMT candidates whose current LCSC codes are recorded. Its designators and footprint strings are synchronized to the frozen Rev A.1 schematic, but it is **not upload-ready**: all provisional choices and quote-time availability still need review, and the file must be regenerated with the final PCB/CPL revision.

The template intentionally excludes DNP parts, bare-PCB test points, external parts, hand-installed connectors, exact-part TBDs, and every `STOP_ORDER` item. In particular, J30 is excluded until its vendored manufacturer-drawing footprint is verified by 1:1 print and real-part fit; SW1/SW2 are excluded because the prior MPN/LCSC pairing was not verified against the schematic footprint.

Status and population meanings:

- `EXACT_CANDIDATE`: the MPN/LCSC pairing is specific enough for schematic entry, but still requires quote-time identity, package, lifecycle, and stock checks.
- `PROVISIONAL`: a useful candidate whose electrical, thermal, footprint, or sourcing details still require validation.
- `TBD`: do not freeze the part, footprint, or purchase choice.
- `SELECT_BEFORE_RELEASE`: the function is required, but the exact part/value must be selected before fabrication release.
- `STOP_ORDER`: a known hard blocker; no fabrication or assembly upload is permitted until the row's note is resolved.
- `DNP`: footprint retained but unpopulated in the default Rev A.1 variant.
- `HAND_INSTALL`: not assumed to be available in JLC's standard SMT assembly flow.
- `PCB_FEATURE`: a schematic/PCB reference such as a bare-copper test pad, not a purchased or placed component.

Power-variant rule: J1 is a regulated 12 V high-current fan input. J6 is a low-current 12–15 V logic input. JP1 may be fitted only when J1 is verified to be regulated 12 V; it feeds the controller through D2 and does not make J1 tolerant of 15 V fans.

Before a JLC order:

1. Re-open every LCSC page and verify manufacturer, exact MPN, package, lifecycle, and stock.
2. Revalidate the J1 `0455580003` and J2–J5 `0353180420` candidates, then freeze J1, J2–J5, J6, and J10 from current manufacturer drawings and real mating-part fit checks.
3. Select and thermally validate Q5/Q6, D4/D5, AP64501 compensation/magnetics, input/output ceramics, bulk capacitors, and the external fan fuse from calculated and measured loads.
4. Export BOM and position/CPL files directly from the same annotated KiCad revision used for Gerbers.
5. Exclude every DNP row from the upload BOM while retaining DNP markings and assembly variants in source.
6. Inspect substitutions, rotations, board side, exposed pads, and pin 1 in JLC's assembly preview.
7. Hand-fit J1, J2–J5, J6, J10, and JP1 on the first articles unless an explicit THT assembly quote has been accepted.

U5, U6, and U7 are populated on Rev A.1 because J10 pin 16 and all signal domains are controller-side 3.3 V. U12 is a separate, normally disabled reset driver. Its 10 kΩ GPIO4 enable pull-up is mandatory. The series RESET link is DNP/open in the default S21-safe assembly and may be fitted with 33 Ω only for a validated legacy-reset target.
