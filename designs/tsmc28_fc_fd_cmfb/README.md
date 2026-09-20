# TSMC28 0.9 V NMOS-input fully differential folded-cascode OTA

This directory records the first-pass TT design created in the user's Cadence IC6.1.8 environment.

## Virtuoso database

- Library: `FC_OTA_0P9V_TSMC28`
- Remote path: `/home/leon/cadence_work/FC_OTA_0P9V_TSMC28`
- Technology library: `tsmcN28`
- OTA: `fc_fd_cmfb/schematic` and `fc_fd_cmfb/symbol`
- Testbench and ADE state: `tb_fc_fd_cmfb_tt/schematic` and `tb_fc_fd_cmfb_tt/maestro`
- Devices: `tsmcN28/nch_mac`, `tsmcN28/pch_mac`, `analogLib/res`, and `analogLib/cap`

## Verified TT result

Spectre 18.1, `top_tt`, 27 C, VDD = 0.9 V, input/output common mode target = 0.45 V, and 50 fF load on each differential output:

| Metric | Result |
|---|---:|
| Differential DC gain | 58.94 dB |
| Differential unity-gain bandwidth | 5.436 GHz |
| Differential phase margin estimate | 30.49 deg |
| Output common mode | 0.4457 V |
| Supply current | 0.7465 mA |
| Power | 0.6718 mW |

The requested gain and GBW targets are met at TT. This is an initial schematic result, not a sign-off design: phase margin needs further compensation work, bias voltages are external pins, and PVT/Monte-Carlo/noise/slew/output-swing/post-layout checks have not yet been completed.

## External biases

| Pin | Voltage |
|---|---:|
| `VBNT` | 0.55 V |
| `VBPT` | 0.43 V |
| `VBPF` | 0.25 V |
| `VBNC` | 0.60 V |
| `VCMREF` | 0.45 V |

The continuous-time CMFB uses two 10 Mohm averaging resistors, a 20 fF sense-node capacitor, a transistor error amplifier, and a 200 fF compensation capacitor.

## Reproduction

`fc_fd_cmfb_tt_final.scs` is the standalone Spectre deck used for the measurements. `final_summary.json` contains the machine-readable result. `create_fc_virtuoso.py` recreates the library cells through virtuoso-bridge, and `setup_fc_maestro.py` recreates the TT ADE/Maestro setup.
