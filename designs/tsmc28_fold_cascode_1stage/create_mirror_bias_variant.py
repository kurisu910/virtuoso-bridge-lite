from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient, decode_skill_output
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_label_instance_term as label_term,
)
from virtuoso_bridge.virtuoso.schematic.params import set_instance_params


LIB = "FC_OTA_0P9V_TSMC28"
SOURCE = "fold_cascode_2stage_1v_tt"
TARGET = "fold_cascode_2stage_1v_mirrorbias_tt"
REPORT = Path(__file__).with_name("mirror_bias_variant_readback.json")


def copy_source(client: VirtuosoClient) -> None:
    result = client.execute_skill(
        f'''let((src dst wins)
  wins = setof(w hiGetWindowList()
    w~>cellView && w~>cellView~>libName == "{LIB}" &&
    w~>cellView~>cellName == "{TARGET}" && w~>cellView~>viewName == "schematic")
  foreach(w wins
    dbSave(w~>cellView)
    hiCloseWindow(w))
  src = dbOpenCellViewByType("{LIB}" "{SOURCE}" "schematic" "" "r")
  unless(src error("Cannot open source schematic"))
  dst = dbCopyCellView(src "{LIB}" "{TARGET}" "schematic" nil nil t)
  dbClose(src)
  unless(dst error("dbCopyCellView failed"))
  schCheck(dst)
  dbSave(dst)
  dbClose(dst)
  "copied")'''
    )
    decoded = decode_skill_output(result.output)
    print(decoded)
    if decoded != "copied":
        raise RuntimeError(f"Copy did not complete: {decoded!r}")


def delete_fixed_voltage_source(client: VirtuosoClient) -> None:
    result = client.execute_skill(
        f'''let((cv old)
  cv = dbOpenCellViewByType("{LIB}" "{TARGET}" "schematic" "" "a")
  unless(cv error("Cannot open target schematic"))
  old = car(setof(x cv~>instances x~>name == "VBIAS22"))
  when(old dbDeleteObject(old))
  schCheck(cv)
  dbSave(cv)
  dbClose(cv)
  "fixed voltage source removed")'''
    )
    print(decode_skill_output(result.output))


def add_mirror_reference(client: VirtuosoClient) -> None:
    with client.schematic.modify(LIB, TARGET) as sch:
        sch.add(inst("tsmcN28", "pch_mac", "symbol", "MP2REF", 18.0, 2.0, "R0"))
        sch.add(label_term("MP2REF", "D", "VBIAS2"))
        sch.add(label_term("MP2REF", "G", "VBIAS2"))
        sch.add(label_term("MP2REF", "S", "VDDA"))
        sch.add(label_term("MP2REF", "B", "VDDA"))

        sch.add(inst("analogLib", "idc", "symbol", "IREF2", 21.0, 0.0, "R0"))
        sch.add(label_term("IREF2", "PLUS", "VBIAS2"))
        sch.add(label_term("IREF2", "MINUS", "VDDS"))

    client.open_window(LIB, TARGET, view="schematic")
    # Match the first-stage sink devices to the 180 nm reference devices while
    # preserving their old W/L ratio (32u / 210n = 27.43u / 180n).
    for name in ("M9", "M10"):
        set_instance_params(client, name, w="27.43u", l="180n", nf="16", strict=True)
    # A 1:10 PMOS mirror: 250 uA reference gives roughly 2.5 mA per output branch.
    set_instance_params(client, "MP2REF", w="4u", l="120n", nf="2", strict=True)
    set_instance_params(client, "IREF2", idc="250u", strict=True)
    set_instance_params(client, "CCN2", c="122f", strict=True)
    set_instance_params(client, "CCP2", c="122f", strict=True)


def verify(client: VirtuosoClient) -> None:
    data = client.schematic.read(LIB, TARGET, include_positions=True, param_filters=None)
    wanted = {"M9", "M10", "M15", "M16", "MP2P", "MP2N", "MP2REF", "IREF2", "ECM2"}
    selected_raw = {
        item["name"]: {
            "cell": item.get("cell"),
            "params": item.get("params", {}),
            "terms": item.get("terms", {}),
        }
        for item in data.get("instances", [])
        if item.get("name") in wanted
    }
    selected = {
        name: {
            "cell": item["cell"],
            "params": {key: item["params"][key] for key in ("w", "l", "fingers", "idc", "egain") if key in item["params"]},
            "terms": item["terms"],
        }
        for name, item in selected_raw.items()
    }
    names = {item.get("name") for item in data.get("instances", [])}
    checks = {
        "fixed_vbias_removed": "VBIAS22" not in names,
        "mirror_reference_present": {"MP2REF", "IREF2"}.issubset(names),
        "m9_m10_l_180n": all(selected[n]["params"].get("l", "").startswith("180") for n in ("M9", "M10")),
        "reference_supply_nets": selected["MP2REF"]["terms"].get("S") == "VDDA" and selected["IREF2"]["terms"].get("MINUS") == "VDDS",
    }
    payload = {"library": LIB, "source_backup": SOURCE, "target": TARGET, "checks": checks, "instances": selected}
    REPORT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    if not all(checks.values()):
        raise RuntimeError(f"Readback verification failed: {checks}")


def main() -> None:
    client = VirtuosoClient.local(port=65426, timeout=90)
    copy_source(client)
    delete_fixed_voltage_source(client)
    add_mirror_reference(client)
    verify(client)
    client.open_window(LIB, TARGET, view="schematic")


if __name__ == "__main__":
    main()
