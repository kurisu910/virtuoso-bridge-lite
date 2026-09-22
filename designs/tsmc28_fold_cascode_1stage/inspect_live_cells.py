from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


LIB = "FC_OTA_0P9V_TSMC28"
CELLS = ("fold_cascode_2stage_1v_mirrorbias_tt",)


def main() -> None:
    client = VirtuosoClient.local(port=65426, timeout=60)
    for cell in CELLS:
        data = client.schematic.read(
            LIB,
            cell,
            include_positions=True,
        )
        print(f"\n=== {cell} ===")
        for inst in sorted(data["instances"], key=lambda item: item["name"]):
            params = inst.get("params", {})
            keep = {key: params[key] for key in ("w", "l", "fingers", "m", "idc", "vdc", "egain", "r", "c", "expr") if key in params}
            print(f"{inst['name']:9s} {inst['cell']:12s} params={keep} terms={inst.get('terms', {})}")


if __name__ == "__main__":
    main()
