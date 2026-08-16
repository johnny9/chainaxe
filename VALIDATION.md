# ChainAxe Rev A.1 validation snapshot

Date: 2026-08-16  
Status: **engineering prototype source; not a fabrication release**

This snapshot records the checks completed on the editable Rev A.1 source package. It does not authorize a JLCPCB order. The PCB is an intentionally unrouted placement baseline, and this environment does not provide KiCad's native ERC/DRC engine.

## Frozen source hashes

| Artifact | SHA-256 |
|---|---|
| `hardware/chainaxe/chainaxe.kicad_sch` | `c5ab1864315fee64124293f3780d8cc0bd6a481a3dc5e6ae20863bb70655ee61` |
| `hardware/chainaxe/chainaxe.kicad_pcb` | `e64937dc008cee42d53eb6474ec83e666f1a017f1b23b2938610d4655da5476a` |
| `hardware/chainaxe/pin-net-audit.csv` | `3e5f585fd3cf63d26aacb7d06084e4bf2c83de7438b81604c77df4c8e84450b7` |
| `scripts/validate_design.py` | `23e28567653a3e3bc9b8564604b43d3168ab291ee4b6c4cabaad711a4172bd78` |
| `scripts/validate_schematic_pinmap.py` | `246a12f9523711c40cad49b799edd80e29d786da46209838f14d99f81bdfad1f` |
| `scripts/validate_pcb_geometry.py` | `b10e061550c6aa2a80219b5b2b5de76439abe2f889b878b28a4df8e11e710376` |
| `.github/workflows/validate.yml` | `011e3e9b5feaeeae38f4f8b436cb7bbba3678cdee81c814a9c122856ec3bae94` |
| `bom/chainaxe-reva-bom.csv` | `c9a18b48a104538682deb578c80180f2284badda386fc0c7006a98370211bd91` |
| `bom/chainaxe-reva-engineering-bom.xlsx` | `8c8304a6ca015c11219aeed9a3fada36858aaf338fe034fea6cb3433f42a05b4` |

The source was renamed from its working title to ChainAxe, including the KiCad project, project-local library nicknames, BOM files, and documentation. This changed textual source hashes but did not change references, pins, nets, labels, NC markers, component placement, or DNP state. All validators were rerun after the rename.

## Automated checks

Run from the repository root:

```text
python3 scripts/validate_design.py .
python3 scripts/validate_schematic_pinmap.py .
python3 scripts/validate_pcb_geometry.py .
```

Recorded results:

- Design consistency: 267 CSV designators, 6 CSV files, 26 documented connector pins, 159 schematic/BOM footprint matches, 159 schematic/PCB footprint matches, 59 audited PCB connector pads, 163 PCB references, 9 project-local footprint files, 427 schematic labels, and zero errors or warnings.
- Schematic pin map: 159 components, 475 pins, 427 labels, 41 legitimate NC markers, zero expected/actual net mismatches, and zero cross-component endpoint collisions.
- PCB placement geometry: 163 footprints, 495 copper pads, 9 NPTH/mechanical holes, and zero different-net pad, NPTH/copper, component-body/courtyard, or undocumented edge-overhang findings.
- Population state: 13 native DNP components agree between schematic, PCB, and BOM; the S21-safe RESET series link remains open/DNP.
- Engineering BOM: 65 grouped rows and quantity 160, representing all 159 schematic components plus one required external fan fuse. The JLC seed contains 24 fitted-SMT rows; 28 engineering-BOM rows still have a TBD/blank LCSC code.
- Python byte-code compilation of all three validators passed.

These source checks are intentionally independent of KiCad, so they can run in GitHub Actions. They do **not** perform electrical rules, routed-board design rules, field solving, thermal analysis, or physical mating-part verification.

## Explicitly not completed

- KiCad ERC and DRC: not run because `kicad-cli` is unavailable in this environment.
- Routing: zero copper track segments, arcs, and routing vias; net classes are placement/routing intent only.
- JLC stack-up and USB impedance solution: not selected or calculated.
- Gerbers, drill files, CPL/centroid, assembly drawings, and fabrication ZIP: not generated.
- Fan-current copper sizing, Q5/Q6 SOA/current sharing, connector temperature rise, and thermography: not completed.
- AP64501 loop, transient, magnetics, effective ceramic capacitance, and thermal validation: not completed; optional C3 remains DNP.
- Real-part 1:1 fit, mating orientation, keying, and cable continuity for J1, J2–J6, J10, and J30: not completed.
- Exact first hashboard SKU/profile and real Antminer fan MPN validation: not completed.
- Hashboard/fan first article, fault injection, and mining soak: not completed.

## Release rule

Do not generate or order fabrication data until every applicable stop-order item in `design-review-checklist.md` is closed with evidence, native KiCad ERC/DRC passes, the board is routed against the selected JLCPCB process, BOM and CPL are regenerated from that exact source revision, and a five-board first article is reviewed.
