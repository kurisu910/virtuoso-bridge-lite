from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

from virtuoso_bridge.env import set_runtime_env_file
from virtuoso_bridge.spectre.runner import SpectreSimulator


SOURCE = Path(__file__).with_name("tune_mirror_bias.py")
spec = importlib.util.spec_from_file_location("mirror", SOURCE)
mirror = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mirror)

ROOT = Path(r"E:\64459\VirtuosoDesigns\folded_cascode")
OUT = ROOT / "pvt_mirror_runs"
SUMMARY = ROOT / "pvt_mirror_summary.json"
CSV = ROOT / "pvt_mirror_summary.csv"
set_runtime_env_file(Path(r"E:\64459\Projects\virtuoso-bridge-lite\.env"))

MODEL = "/opt/pdk/tsmc28hpcp_1p8m_5x2z/models/spectre/cln28hpcp_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs"
CORNERS = {
    "TT": "ttmacro_mos_moscap",
    "SS": "ssmacro_mos_moscap",
    "FF": "ffmacro_mos_moscap",
    "SF": "sfmacro_mos_moscap",
    "FS": "fsmacro_mos_moscap",
}
VDDS = (0.81, 0.90, 0.99)
TEMPS = (-40, 27, 125)
FINAL = {
    "W_NREF": "180n",
    "W_NPMSINK": "180n",
    "W_NFOLDSINK": "468n",
    "W_PCAS": "250n",
    "CZ": "45f",
}


def deck_for(corner: str, vdd: float, temp: int) -> str:
    deck = mirror.make_deck(FINAL)
    deck = deck.replace(
        'include "/opt/pdk/tsmc28hpcp_1p8m_5x2z/models/spectre/toplevel.scs" section=top_tt',
        f'include "{MODEL}" section={CORNERS[corner]}',
    )
    deck = deck.replace("parameters VDDVAL=0.9 VCMVAL=0.45", f"parameters VDDVAL={vdd:g} VCMVAL=VDDVAL/2")
    deck = deck.replace("dcOp dc", f"simulatorOptions options temp={temp}\ndcOp dc")
    return deck


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    points = []
    tasks = []
    for corner in CORNERS:
        for vdd in VDDS:
            for temp in TEMPS:
                tag = f"{corner}_v{int(round(vdd * 100)):02d}_t{'m' if temp < 0 else 'p'}{abs(temp)}"
                path = OUT / f"fc_mirror_{tag}.scs"
                path.write_text(deck_for(corner, vdd, temp), encoding="ascii")
                points.append((corner, vdd, temp, tag))
                tasks.append((path, {}))

    sim = SpectreSimulator.from_env(
        spectre_args=[], work_dir=OUT / "results", output_format="psfascii", timeout=420
    )
    results = sim.run_parallel(tasks, max_workers=3)
    rows = []
    for (corner, vdd, temp, tag), result in zip(points, results):
        row = {
            "tag": tag,
            "corner": corner,
            "vdd_v": vdd,
            "temp_c": temp,
            "ok": result.ok,
            **mirror.metrics(result),
        }
        row["meets_gain_55db"] = bool(row.get("gain_db", -1e9) >= 55.0)
        row["meets_gbw_5g"] = bool((row.get("ugf_hz") or 0.0) >= 5e9)
        row["meets_pm_60deg"] = bool(row.get("phase_margin_deg", -1e9) >= 60.0)
        row["meets_all"] = row["ok"] and row["meets_gain_55db"] and row["meets_gbw_5g"] and row["meets_pm_60deg"]
        if result.errors:
            row["errors"] = result.errors[:3]
        rows.append(row)

    SUMMARY.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    fields = sorted({key for row in rows for key in row if key != "errors"})
    with CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: v for k, v in row.items() if k != "errors"} for row in rows)

    good = sum(1 for row in rows if row["meets_all"])
    valid = [row for row in rows if row["ok"] and "gain_db" in row]
    print(f"PVT_RESULT completed={len(valid)}/{len(rows)} meets_all={good}/{len(rows)}")
    if valid:
        for metric in ("gain_db", "ugf_hz", "phase_margin_deg"):
            worst = min(valid, key=lambda row: row[metric])
            best = max(valid, key=lambda row: row[metric])
            print(f"PVT_RANGE {metric} min={worst[metric]}@{worst['tag']} max={best[metric]}@{best['tag']}")
    for row in rows:
        print("PVT_POINT", json.dumps(row, default=str))
    return 0 if len(valid) == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
