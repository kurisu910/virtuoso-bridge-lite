from __future__ import annotations

import importlib.util
import json
import math
import re
from pathlib import Path

from virtuoso_bridge.env import set_runtime_env_file
from virtuoso_bridge.spectre.runner import SpectreSimulator


SOURCE = Path(__file__).with_name("optimize_fc.py")
spec = importlib.util.spec_from_file_location("fcbase", SOURCE)
fcbase = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fcbase)

ROOT = Path(r"E:\64459\VirtuosoDesigns\folded_cascode")
set_runtime_env_file(Path(r"E:\64459\Projects\virtuoso-bridge-lite\.env"))

IDEAL_BIASES = r'''VCMREF (vcmref 0) vsource dc=VCMVAL
VBNTAIL (vbntail 0) vsource dc=VBNTVAL
VBPTOP (vbptop 0) vsource dc=VBPTVAL
VBPFOLD (vbpfold 0) vsource dc=VBPFVAL
VBNCAS (vbncas 0) vsource dc=VBNCVAL'''

MIRROR_BIASES = r'''// IDC establishes the only absolute reference current.
IREFSRC (vdd vbntail) isource dc=IREF
XMNREF (vbntail vbntail 0 0) nch_mac w=W_NREF l=L_NREF nf=NF_NREF

// Complementary PMOS bias generated from the NMOS reference mirror.
XMPREF (vbptop vbptop vdd vdd) pch_mac w=W_PREF l=L_PREF nf=NF_PREF
XMN_PREF_SINK (vbptop vbntail 0 0) nch_mac w=W_NPMSINK l=L_NPMSINK nf=NF_NPMSINK

// Replica of the PMOS top/folded stack.  The folded device is diode connected.
XMPTOP_REF (xfold_ref vbptop vdd vdd) pch_mac w=W_PTOPR l=L_PTOPR nf=NF_PTOPR
XMPFOLD_REF (vbpfold vbpfold xfold_ref vdd) pch_mac w=W_FOLDR l=L_FOLDR nf=NF_FOLDR
XMN_FOLD_SINK (vbpfold vbntail 0 0) nch_mac w=W_NFOLDSINK l=L_NFOLDSINK nf=NF_NFOLDSINK

// Low-current two-NMOS replica stack for the NMOS cascode gate.
XMP_NCAS_SOURCE (vbncas vbptop vdd vdd) pch_mac w=W_PCAS l=L_PCAS nf=NF_PCAS
XMN_CAS_DIODE (vbncas vbncas ncas_mid 0) nch_mac w=W_NCASR l=L_NCASR nf=NF_NCASR
XMN_CAS_BOTTOM (ncas_mid ncas_mid 0 0) nch_mac w=W_NCASB l=L_NCASB nf=NF_NCASB

// Common-mode reference is a PMOS mirror feeding a diode-connected NMOS.
XMP_VCM_SOURCE (vcmref vbptop vdd vdd) pch_mac w=W_PCM l=L_PCM nf=NF_PCM
XMN_VCM_DIODE (vcmref vcmref 0 0) nch_mac w=W_NCMR l=L_NCMR nf=NF_NCMR'''

BIAS_PARAMETERS = r'''parameters IREF=20u
parameters W_NREF=250n L_NREF=90n NF_NREF=1
parameters W_PREF=1.6u L_PREF=120n NF_PREF=1
parameters W_NPMSINK=250n L_NPMSINK=90n NF_NPMSINK=1
parameters W_PTOPR=2u L_PTOPR=120n NF_PTOPR=1
parameters W_FOLDR=1u L_FOLDR=240n NF_FOLDR=1
parameters W_NFOLDSINK=650n L_NFOLDSINK=180n NF_NFOLDSINK=1
parameters W_PCAS=2u L_PCAS=120n NF_PCAS=1
parameters W_NCASR=40u L_NCASR=180n NF_NCASR=20
parameters W_NCASB=40u L_NCASB=180n NF_NCASB=20
parameters W_PCM=2u L_PCM=120n NF_PCM=1
parameters W_NCMR=1.5u L_NCMR=90n NF_NCMR=1'''


def make_deck(changes: dict[str, str]) -> str:
    deck = fcbase.DECK.replace(
        "parameters VDDVAL=0.9 VCMVAL=0.45 VBNTVAL=0.5825 VBPTVAL=0.41375 VBPFVAL=0.25 VBNCVAL=0.60",
        "parameters VDDVAL=0.9 VCMVAL=0.45\n" + BIAS_PARAMETERS,
    )
    deck = deck.replace(IDEAL_BIASES, MIRROR_BIASES)
    deck = deck.replace(
        "save VOP VON VCMS VBNCM XP XN NTAIL NSINKP NSINKN",
        "save VOP VON VCMS VBNCM XP XN NTAIL NSINKP NSINKN VBNTail VBPTOP VBPFOLD VBNCAS VCMREF NCAS_MID",
    )
    for name, value in changes.items():
        deck, count = re.subn(rf"(?m)(\b{name}=)([^\s]+)", rf"\g<1>{value}", deck, count=1)
        if count != 1:
            raise RuntimeError(f"parameter not found: {name}")
    return deck


def metrics(result):
    row = {}
    for node in ("vbntail", "vbptop", "vbpfold", "vbncas", "vcmref", "vop", "von", "vbncm", "ncas_mid"):
        key = f"dc_{node}"
        if key in result.data:
            row[node] = float(result.data[key])
    if not result.ok or "ac_freq" not in result.data:
        return row
    freq = result.data["ac_freq"]
    gain = [a - b for a, b in zip(result.data["ac_vop"], result.data["ac_von"])]
    mag = [abs(v) for v in gain]
    ugf = fcbase.interpolate_unity(freq, mag)
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
    p_ugf = fcbase.interpolate_at(freq, phase, ugf) if ugf else None
    row.update(
        gain_db=20 * math.log10(max(mag[0], 1e-30)),
        ugf_hz=ugf,
        phase_margin_deg=180 + p_ugf if p_ugf is not None else None,
        idd_a=-float(result.data["dc_VDD:p"]),
    )
    return row


def main():
    candidates = {
        "base2": {},
        "nref240": {"W_NREF": "240n", "W_NPMSINK": "240n", "W_NFOLDSINK": "624n"},
        "nref220": {"W_NREF": "220n", "W_NPMSINK": "220n", "W_NFOLDSINK": "572n"},
        "nref180_c45": {"W_NREF": "180n", "W_NPMSINK": "180n", "W_NFOLDSINK": "468n", "CZ": "45f"},
        "nref150_c50": {"W_NREF": "150n", "W_NPMSINK": "150n", "W_NFOLDSINK": "390n", "CZ": "50f"},
        "pcas250": {"W_PCAS": "250n"},
        "pcas500": {"W_PCAS": "500n"},
        "pcas1u": {"W_PCAS": "1u"},
    }
    sim = SpectreSimulator.from_env(
        spectre_args=[], work_dir=ROOT / "mirror_bias_runs", output_format="psfascii", timeout=300
    )
    rows = []
    for name, changes in candidates.items():
        path = ROOT / f"mirror_{name}.scs"
        path.write_text(make_deck(changes), encoding="ascii")
        result = sim.run_simulation(path, {})
        row = {"name": name, "ok": result.ok, **changes, **metrics(result)}
        if result.errors:
            row["errors"] = result.errors[:4]
        rows.append(row)
        print("RESULT", json.dumps(row, default=str))
    (ROOT / "mirror_bias_tuning_summary.json").write_text(
        json.dumps(rows, indent=2, default=str), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
