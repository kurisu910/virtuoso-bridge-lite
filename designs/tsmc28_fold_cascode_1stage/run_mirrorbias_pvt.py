from __future__ import annotations

import json
import math
import os
from pathlib import Path

from virtuoso_bridge.env import set_runtime_env_file
from virtuoso_bridge.spectre.runner import SpectreSimulator


HERE = Path(__file__).resolve().parent
set_runtime_env_file(HERE.parents[1] / ".env")
SOURCE = HERE / "mirrorbias_tt.scs"
SUMMARY = HERE / "mirrorbias_pvt_summary.json"


def crossing(freq, mag):
    for i in range(1, len(freq)):
        if mag[i - 1] >= 1 >= mag[i]:
            x0, x1 = math.log10(freq[i - 1]), math.log10(freq[i])
            y0, y1 = math.log10(mag[i - 1]), math.log10(mag[i])
            return 10 ** (x0 - y0 * (x1 - x0) / (y1 - y0))


def interp(freq, values, target):
    for i in range(1, len(freq)):
        if freq[i - 1] <= target <= freq[i]:
            x0, x1 = math.log10(freq[i - 1]), math.log10(freq[i])
            t = (math.log10(target) - x0) / (x1 - x0)
            return values[i - 1] + t * (values[i] - values[i - 1])


def metrics(result):
    km = {k.lower(): k for k in result.data}
    freq = result.data["ac_freq"]
    diff = [p - n for p, n in zip(result.data[km["ac_outp"]], result.data[km["ac_outn"]])]
    mag = [abs(x) for x in diff]
    ugf = crossing(freq, mag)
    phase, prev = [], None
    for value in diff:
        a = math.degrees(math.atan2(value.imag, value.real))
        if prev is not None:
            while a - prev > 180: a -= 360
            while a - prev < -180: a += 360
        phase.append(a); prev = a
    p = interp(freq, phase, ugf)
    pm = next((x for x in (180 + p, -180 + p) if 0 <= x <= 180), None)
    outp = float(result.data[km["dc_outp"]])
    outn = float(result.data[km["dc_outn"]])
    return {
        "gain_db": 20 * math.log10(mag[0]),
        "ugf_hz": ugf,
        "phase_margin_deg": pm,
        "output_common_mode_v": 0.5 * (outp + outn),
    }


def main():
    base = SOURCE.read_text(encoding="ascii")
    sim = SpectreSimulator.from_env(work_dir=HERE / "mirrorbias_pvt_runs", output_format="psfascii", timeout=300)
    rows = []
    top_include = 'include "/opt/pdk/tsmc28hpcp_1p8m_5x2z/models/spectre/toplevel.scs" section=top_tt'
    embedded = "/opt/pdk/tsmc28hpcp_1p8m_5x2z/models/spectre/cln28hpcp_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.scs"
    corners = tuple(x.strip().lower() for x in os.environ.get("MIRRORBIAS_CORNERS", "tt,ff,ss,fs,sf").split(",") if x.strip())
    for corner in corners:
        deck = HERE / f"mirrorbias_{corner}.scs"
        text = base if corner == "tt" else base.replace(
            top_include,
            f'include "{embedded}" section={corner}macro_mos_moscap',
        )
        deck.write_text(text, encoding="ascii")
        result = sim.run_simulation(deck, {})
        row = {"corner": corner.upper(), "ok": result.ok}
        if result.ok:
            row.update(metrics(result))
            row["meets_core_specs"] = row["gain_db"] >= 50 and row["ugf_hz"] >= 6.5e9 and row["phase_margin_deg"] >= 60
        else:
            row["errors"] = result.errors[:4]
        rows.append(row)
        print("PVT", json.dumps(row))
    SUMMARY.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
