from __future__ import annotations

import json
import math
import os
from pathlib import Path

from virtuoso_bridge.env import set_runtime_env_file
from virtuoso_bridge.spectre.runner import SpectreSimulator


HERE = Path(__file__).resolve().parent
ENV = HERE.parents[1] / ".env"
OA_NETLIST = HERE / "mirrorbias_si_netlist.scs"
DECK = HERE / "mirrorbias_tt.scs"
SUMMARY = HERE / "mirrorbias_tt_summary.json"
COMP_C = os.environ.get("MIRRORBIAS_COMP_C", "122f")
set_runtime_env_file(ENV)


def unity_crossing(freq, mag):
    for i in range(1, len(freq)):
        if mag[i - 1] >= 1.0 >= mag[i]:
            x0, x1 = math.log10(freq[i - 1]), math.log10(freq[i])
            y0, y1 = math.log10(mag[i - 1]), math.log10(mag[i])
            return 10 ** (x0 - y0 * (x1 - x0) / (y1 - y0))
    return None


def interp_log_x(freq, values, target):
    for i in range(1, len(freq)):
        if freq[i - 1] <= target <= freq[i]:
            x0, x1 = math.log10(freq[i - 1]), math.log10(freq[i])
            t = (math.log10(target) - x0) / (x1 - x0)
            return values[i - 1] + t * (values[i] - values[i - 1])
    return None


def build_deck():
    circuit = OA_NETLIST.read_text(encoding="utf-8")
    circuit = circuit.replace("CCN2 (NZN VON) capacitor c=80f", f"CCN2 (NZN VON) capacitor c={COMP_C}")
    circuit = circuit.replace("CCP2 (NZP VOP) capacitor c=80f", f"CCP2 (NZP VOP) capacitor c={COMP_C}")
    header = '''simulator lang=spectre
global 0
include "/opt/pdk/tsmc28hpcp_1p8m_5x2z/models/spectre/toplevel.scs" section=top_tt

VDD (VDDA VDDS) vsource dc=1.0
VSS (VDDS 0) vsource dc=0
VIP_SRC (VIP VDDS) vsource dc=450m mag=0.5 phase=0 type=dc
VIN_SRC (VIN VDDS) vsource dc=450m mag=0.5 phase=180 type=dc

'''
    footer = '''
dcOp dc maxiters=200
ac ac start=1k stop=100G dec=100
save OUTP OUTN VOP VON VBIAS2 VBP2 VCM2 VDDA VDDS VDD:p
saveOptions options save=selected
'''
    DECK.write_text(header + circuit + footer, encoding="ascii")


def main():
    build_deck()
    sim = SpectreSimulator.from_env(
        work_dir=HERE / "mirrorbias_runs",
        output_format="psfascii",
        timeout=300,
    )
    result = sim.run_simulation(DECK, {})
    if not result.ok:
        print("ERRORS", result.errors[:10])
        print("WARNINGS", result.warnings[:10])
        raise SystemExit(1)
    keymap = {key.lower(): key for key in result.data}
    def data(name):
        return result.data[keymap[name.lower()]]
    freq = result.data["ac_freq"]
    diff = [p - n for p, n in zip(data("ac_outp"), data("ac_outn"))]
    mag = [abs(x) for x in diff]
    gain_db = 20 * math.log10(max(mag[0], 1e-30))
    ugf = unity_crossing(freq, mag)
    phase = []
    previous = None
    for value in diff:
        angle = math.degrees(math.atan2(value.imag, value.real))
        if previous is not None:
            while angle - previous > 180:
                angle -= 360
            while angle - previous < -180:
                angle += 360
        phase.append(angle)
        previous = angle
    phase_at_ugf = interp_log_x(freq, phase, ugf) if ugf else None
    # Normalize the transfer sign so phase margin is measured around -180 deg.
    candidates = [180 + phase_at_ugf, -180 + phase_at_ugf] if phase_at_ugf is not None else []
    pm = next((x for x in candidates if 0 <= x <= 180), None)
    dc = {k: float(v) for k, v in result.data.items() if k.lower().startswith("dc_") and not isinstance(v, (list, tuple))}
    dcmap = {key.lower(): value for key, value in dc.items()}
    out_cm = 0.5 * (dcmap["dc_outp"] + dcmap["dc_outn"])
    summary = {
        "cell": "fold_cascode_2stage_1v_mirrorbias_tt",
        "corner": "TT",
        "vdd_v": 1.0,
        "load_per_output_f": 50,
        "compensation_cap_f": COMP_C,
        "gain_db": gain_db,
        "ugf_hz": ugf,
        "phase_at_ugf_deg": phase_at_ugf,
        "phase_margin_deg": pm,
        "output_common_mode_v": out_cm,
        "vbias2_v": dcmap.get("dc_vbias2"),
        "vbp2_v": dcmap.get("dc_vbp2"),
        "supply_current_a": -dcmap.get("dc_vdd:p", 0.0),
        "dc": dc,
        "output_dir": result.metadata.get("output_dir"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
