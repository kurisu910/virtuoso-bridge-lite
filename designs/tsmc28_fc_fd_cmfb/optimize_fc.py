from __future__ import annotations

import json
import math
from pathlib import Path

from virtuoso_bridge.env import set_runtime_env_file
from virtuoso_bridge.spectre.runner import SpectreSimulator


ENV = Path(r"E:\64459\Projects\virtuoso-bridge-lite\.env")
ROOT = Path(r"E:\64459\VirtuosoDesigns\folded_cascode")
NETLIST = ROOT / "fc_fd_cmfb_tt_final.scs"
SUMMARY = ROOT / "final_summary.json"
set_runtime_env_file(ENV)


DECK = r'''simulator lang=spectre
global 0
include "/opt/pdk/tsmc28hpcp_1p8m_5x2z/models/spectre/toplevel.scs" section=top_tt

parameters VDDVAL=0.9 VCMVAL=0.45 VBNTVAL=0.5825 VBPTVAL=0.41375 VBPFVAL=0.25 VBNCVAL=0.60
parameters W_IN=36u L_IN=60n NF_IN=24
parameters W_TAIL=18u L_TAIL=90n NF_TAIL=24
parameters W_PTOP=40u L_PTOP=120n NF_PTOP=20
parameters W_FOLD=24u L_FOLD=240n NF_FOLD=24
parameters W_NCAS=24u L_NCAS=180n NF_NCAS=16
parameters W_NSINK=24u L_NSINK=180n NF_NSINK=16
parameters W_CM=2u L_CM=90n NF_CM=8
parameters W_CMLOAD=4u L_CMLOAD=90n NF_CMLOAD=8
parameters W_CMTAIL=2u L_CMTAIL=90n NF_CMTAIL=8
parameters CL=50f RCM=10Meg CCM=200f RZ=1k CZ=40f

VDD (vdd 0) vsource dc=VDDVAL
VINP (vinp 0) vsource dc=VCMVAL mag=0.5 phase=0 type=dc
VINN (vinn 0) vsource dc=VCMVAL mag=0.5 phase=180 type=dc
VCMREF (vcmref 0) vsource dc=VCMVAL
VBNTAIL (vbntail 0) vsource dc=VBNTVAL
VBPTOP (vbptop 0) vsource dc=VBPTVAL
VBPFOLD (vbpfold 0) vsource dc=VBPFVAL
VBNCAS (vbncas 0) vsource dc=VBNCVAL

// NMOS input pair and tail source
XMNIP (xp vinp ntail 0) nch_mac w=W_IN l=L_IN nf=NF_IN
XMNIN (xn vinn ntail 0) nch_mac w=W_IN l=L_IN nf=NF_IN
XMNTAIL (ntail vbntail 0 0) nch_mac w=W_TAIL l=L_TAIL nf=NF_TAIL

// PMOS top sources and PMOS folding common-gate devices
XMPTOPP (xp vbptop vdd vdd) pch_mac w=W_PTOP l=L_PTOP nf=NF_PTOP
XMPTOPN (xn vbptop vdd vdd) pch_mac w=W_PTOP l=L_PTOP nf=NF_PTOP
XMPFOLDP (vop vbpfold xp vdd) pch_mac w=W_FOLD l=L_FOLD nf=NF_FOLD
XMPFOLDN (von vbpfold xn vdd) pch_mac w=W_FOLD l=L_FOLD nf=NF_FOLD

// NMOS cascoded output sinks; CMFB controls the lower devices
XMNCASP (vop vbncas nsinkp 0) nch_mac w=W_NCAS l=L_NCAS nf=NF_NCAS
XMNCASN (von vbncas nsinkn 0) nch_mac w=W_NCAS l=L_NCAS nf=NF_NCAS
XMNSINKP (nsinkp vbncm 0 0) nch_mac w=W_NSINK l=L_NSINK nf=NF_NSINK
XMNSINKN (nsinkn vbncm 0 0) nch_mac w=W_NSINK l=L_NSINK nf=NF_NSINK

// Continuous-time CMFB: passive output averaging + NMOS error pair
RCMP (vop vcms) resistor r=RCM
RCMN (von vcms) resistor r=RCM
CCMS (vcms 0) capacitor c=20f
XMNCM_S (ncm1 vcms ncmtail 0) nch_mac w=W_CM l=L_CM nf=NF_CM
XMNCM_R (vbncm vcmref ncmtail 0) nch_mac w=W_CM l=L_CM nf=NF_CM
XMNCM_T (ncmtail vbntail 0 0) nch_mac w=W_CMTAIL l=L_CMTAIL nf=NF_CMTAIL
XMPCM_D (ncm1 ncm1 vdd vdd) pch_mac w=W_CMLOAD l=L_CMLOAD nf=NF_CMLOAD
XMPCM_O (vbncm ncm1 vdd vdd) pch_mac w=W_CMLOAD l=L_CMLOAD nf=NF_CMLOAD
CCMCOMP (vbncm 0) capacitor c=CCM

CLOADP (vop 0) capacitor c=CL
CLOADN (von 0) capacitor c=CL
RLEAD (vop vlead) resistor r=RZ
CLEAD (vlead von) capacitor c=CZ

dcOp dc
ac ac start=1k stop=100G dec=60
save VOP VON VCMS VBNCM XP XN NTAIL NSINKP NSINKN
saveOptions options save=selected
'''


def interpolate_unity(freq, mag):
    for i in range(1, len(freq)):
        if mag[i - 1] >= 1.0 and mag[i] <= 1.0:
            x0, x1 = math.log10(freq[i - 1]), math.log10(freq[i])
            y0, y1 = math.log10(mag[i - 1]), math.log10(mag[i])
            return 10 ** (x0 + (0.0 - y0) * (x1 - x0) / (y1 - y0))
    return None


def interpolate_at(freq, values, target):
    for i in range(1, len(freq)):
        if freq[i - 1] <= target <= freq[i]:
            x0, x1 = math.log10(freq[i - 1]), math.log10(freq[i])
            t = (math.log10(target) - x0) / (x1 - x0)
            return values[i - 1] + t * (values[i] - values[i - 1])
    return None


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    NETLIST.write_text(DECK, encoding="ascii")
    sim = SpectreSimulator.from_env(
        spectre_args=[],
        work_dir=ROOT / "runs",
        output_format="psfascii",
        timeout=300,
    )
    result = sim.run_simulation(NETLIST, {})
    print("status", result.status.value)
    if result.errors:
        print("errors", result.errors[:8])
    print("keys", sorted(result.data))
    if not result.ok:
        return 1

    freq = result.data.get("ac_freq", [])
    vop = result.data.get("ac_vop", [])
    von = result.data.get("ac_von", [])
    if len(freq) == 0 or len(vop) == 0 or len(von) == 0:
        print("missing AC vectors")
        return 2
    gain = [a - b for a, b in zip(vop, von)]
    print("first_ac", freq[0], vop[0], von[0], gain[0])
    mag = [abs(x) for x in gain]
    gain_db = 20 * math.log10(max(mag[0], 1e-30))
    ugf = interpolate_unity(freq, mag)
    phase = []
    previous = None
    for value in (-x for x in gain):
        angle = math.degrees(math.atan2(value.imag, value.real))
        if previous is not None:
            while angle - previous > 180:
                angle -= 360
            while angle - previous < -180:
                angle += 360
        phase.append(angle)
        previous = angle
    phase_at_ugf = interpolate_at(freq, phase, ugf) if ugf else None
    summary = {
        "gain_db": gain_db,
        "ugf_hz": ugf,
        "phase_at_ugf_deg": phase_at_ugf,
        "phase_margin_deg": 180 + phase_at_ugf if phase_at_ugf is not None else None,
        "load_per_output_f": 50,
        "vdd_v": 0.9,
        "supply_current_a": -float(result.data["dc_VDD:p"]),
        "power_w": 0.9 * -float(result.data["dc_VDD:p"]),
        "dc": {k: v for k, v in result.data.items() if k.startswith("dc_")},
        "signals": sorted(result.data),
        "output_dir": result.metadata.get("output_dir"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
