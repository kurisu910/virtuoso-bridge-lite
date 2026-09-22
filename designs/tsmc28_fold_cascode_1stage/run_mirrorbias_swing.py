from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge.env import set_runtime_env_file
from virtuoso_bridge.spectre.runner import SpectreSimulator


HERE = Path(__file__).resolve().parent
set_runtime_env_file(HERE.parents[1] / ".env")
SOURCE = HERE / "mirrorbias_tt.scs"
DECK = HERE / "mirrorbias_swing.scs"
SUMMARY = HERE / "mirrorbias_swing_summary.json"


def main():
    text = SOURCE.read_text(encoding="ascii")
    text = text.replace("global 0\n", "global 0\nparameters VDIFF=0\n")
    text = text.replace("dc=450m mag=0.5 phase=0 type=dc", "dc=450m+VDIFF/2")
    text = text.replace("dc=450m mag=0.5 phase=180 type=dc", "dc=450m-VDIFF/2")
    text = text.replace("dcOp dc maxiters=200\nac ac start=1k stop=100G dec=100", "swing dc param=VDIFF start=-20m stop=20m step=50u")
    DECK.write_text(text, encoding="ascii")
    sim = SpectreSimulator.from_env(work_dir=HERE / "mirrorbias_swing_runs", output_format="psfascii", timeout=300)
    result = sim.run_simulation(DECK, {})
    if not result.ok:
        print(result.errors[:10])
        raise SystemExit(1)
    keymap = {key.lower(): key for key in result.data}
    outp = result.data[keymap["swing_outp"]]
    outn = result.data[keymap["swing_outn"]]
    diff = [p - n for p, n in zip(outp, outn)]
    payload = {
        "differential_output_min_v": min(diff),
        "differential_output_max_v": max(diff),
        "differential_output_swing_vpp": max(diff) - min(diff),
        "single_ended_outp_min_v": min(outp),
        "single_ended_outp_max_v": max(outp),
    }
    SUMMARY.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
