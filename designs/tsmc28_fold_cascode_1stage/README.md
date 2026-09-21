# TSMC28 `fold_cascode_1stage` tuning handoff

## Design location

- Virtuoso library: `FC_OTA_0P9V_TSMC28`
- Active cell: `fold_cascode_1stage/schematic`
- Baseline backup: `fold_cascode_1stage_baseline_20260921/schematic`
- Local simulation root: `E:\64459\VirtuosoDesigns\folded_cascode_1stage`
- Generated tuning scripts: `C:\Users\64459\Documents\Codex\2026-09-20\https-github-com-arcadia-1-virtuoso\work`

## Version currently saved in Virtuoso

The saved OA schematic remains the verified 0.9 V / 50 fF version. The later
1.0 V experiments were simulation-only and were not written back.

Changed instances:

| Instance | Parameters |
|---|---|
| M2, M3 | W=144 um, L=60 nm, fingers=96 |
| M4 | W=216 um, L=90 nm, fingers=288 |
| M9, M10 | W=32 um, L=210 nm, fingers=16 |
| E0 | ideal CMFB gain=50 |

TT results at VDD=0.9 V and 50 fF per output:

- Differential DC gain: 51.84 dB
- Unity-gain bandwidth: 8.23 GHz
- Differential output swing: 1.577 Vpp
- Balanced output common mode: 447.7 mV
- Supply current: 2.093 mA
- Phase margin: 28.7 degrees

The result was re-run without a nodeset and converged to the same operating
point. At 100 fF, the best stable sweep was about 51.3 dB / 6.30 GHz, so the
6.5 GHz requirement required reducing the load to 50 fF.

## Bounded 1.0 V investigation

Raising VDD to 1.0 V provided enough gain and speed but did not solve the
non-dominant-pole limitation:

- High-speed point: 56.36 dB / 9.93 GHz / 22.6 degree PM.
- Low-current point: 54.87 dB / 6.97 GHz / 39.3 degree PM.
- Folded-node capacitive compensation: 54.87 dB / 6.46 GHz / 44.6 degree PM.
- Best series-RC attempt above 6.5 GHz: 54.87 dB / 6.70 GHz / 45.6 degree PM.
- Larger compensation reached about 51 degrees PM only after UGBW fell below
  6.0 GHz.

Conclusion: the present single-stage topology could not simultaneously meet
gain >= 50 dB, UGBW >= 6.5 GHz, and PM >= 60 degrees in the bounded sweep.
No 1.0 V experimental parameters were applied to the OA schematic.

The selected 1.0 V experimental point was subsequently saved as a separate
OA cell, without changing the 0.9 V cell:

- Cell: `fold_cascode_1stage_1v_pm45p6/schematic`
- M2/M3: W=27 um, L=60 nm, fingers=18
- M4: W=108 um, L=90 nm, fingers=144
- M5/M6: W=18 um, L=180 nm, fingers=18
- M9/M10: W=32 um, L=210 nm, fingers=16
- Differential compensation: 2 kohm in series with 8 fF on each side
- Stable folded-node names in the saved schematic: `FOLDP` is the M3-drain /
  M5-source node, and `FOLDN` is the M2-drain / M6-source node. The
  compensation capacitors terminate on `FOLDP` and `FOLDN`; Cadence-generated
  `netXXX` names must not be used because they change when a cell is copied.
- Recorded TT result: 54.87 dB / 6.70 GHz / 45.6 degree PM at 1.0 V and
  50 fF per output

This cell records the best bounded 1.0 V experiment; it does not meet the
60-degree phase-margin goal.

## Recommended continuation

Use the folded-cascode as the first stage and investigate a lightweight,
high-bandwidth fully differential second stage with a dedicated second-stage
CMFB loop. Use Miller/Ahuja compensation with a nulling element, and validate
the differential loop and common-mode loop separately before running PVT.

For work from another computer, connect to this Windows host as a Codex SSH
host (preferably through a VPN/mesh network), then open the saved project
`E:\64459\Projects\virtuoso-bridge-lite`. The bridge on this host can continue
to control the VMware-hosted Virtuoso through its existing SSH setup.
