from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.env import set_runtime_env_file
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_create_pin_at_instance_term as pin_at,
    schematic_label_instance_term as label_term,
)
from virtuoso_bridge.virtuoso.schematic.params import set_instance_params
from virtuoso_bridge.virtuoso.symbol import (
    symbol_create_instance_label,
    symbol_create_logical_label,
    symbol_create_pin,
    symbol_create_rect,
    symbol_create_selection_box,
    symbol_set_term_order,
)


ENV = Path(r"E:\64459\Projects\virtuoso-bridge-lite\.env")
LIB = "FC_OTA_0P9V_TSMC28"
LIB_PATH = "/home/leon/cadence_work/FC_OTA_0P9V_TSMC28"
OTA = "fc_fd_cmfb"
TB = "tb_fc_fd_cmfb_tt"
PDK = "tsmcN28"

set_runtime_env_file(ENV)


def mos(sch, name, cell, x, y):
    sch.add(inst(PDK, cell, "symbol", name, x, y, "R0"))


def labels(sch, name, mapping):
    for term, net in mapping.items():
        sch.add(label_term(name, term, net, extension_length=0.35, justification="lowerCenter"))


def create_symbol(client: VirtuosoClient):
    pins = [
        ("VINP", -3.0, 2.0, "input", -1.8, 2.0, "centerLeft"),
        ("VINN", -3.0, 1.2, "input", -1.8, 1.2, "centerLeft"),
        ("VCMREF", -3.0, 0.2, "input", -1.8, 0.2, "centerLeft"),
        ("VBNT", -3.0, -0.6, "input", -1.8, -0.6, "centerLeft"),
        ("VBPT", -3.0, -1.2, "input", -1.8, -1.2, "centerLeft"),
        ("VBPF", -3.0, -1.8, "input", -1.8, -1.8, "centerLeft"),
        ("VBNC", -3.0, -2.4, "input", -1.8, -2.4, "centerLeft"),
        ("VOP", 3.0, 1.2, "output", 1.8, 1.2, "centerRight"),
        ("VON", 3.0, -1.2, "output", 1.8, -1.2, "centerRight"),
        ("VDD", 0.0, 3.5, "inputOutput", 0.0, 2.7, "centerCenter"),
        ("VSS", 0.0, -3.5, "inputOutput", 0.0, -2.7, "centerCenter"),
    ]
    with client.symbol.create(LIB, OTA) as symbol:
        symbol.add(symbol_create_rect("device", "drawing", -2.5, -3.0, 2.5, 3.0))
        for name, x, y, direction, lx, ly, just in pins:
            symbol.add(symbol_create_pin(name, x, y, direction=direction,
                                         label_x=lx, label_y=ly, label_justification=just))
        symbol.add(symbol_create_instance_label(-2.3, 3.25))
        symbol.add(symbol_create_logical_label(0.0, 0.0))
        symbol.add(symbol_create_selection_box(-3.0, -3.5, 3.0, 3.5))
        symbol.add(symbol_set_term_order([p[0] for p in pins]))


def create_ota(client: VirtuosoClient):
    with client.schematic.create(LIB, OTA) as sch:
        # Main NMOS-input folded-cascode core.
        mos(sch, "MNIP", "nch_mac", 4.0, 4.0)
        mos(sch, "MNIN", "nch_mac", 7.0, 4.0)
        mos(sch, "MNTAIL", "nch_mac", 5.5, 1.0)
        mos(sch, "MPTOPP", "pch_mac", 1.5, 7.0)
        mos(sch, "MPTOPN", "pch_mac", 9.5, 7.0)
        mos(sch, "MPFOLDP", "pch_mac", 1.5, 4.5)
        mos(sch, "MPFOLDN", "pch_mac", 9.5, 4.5)
        mos(sch, "MNCASP", "nch_mac", 1.5, 2.0)
        mos(sch, "MNCASN", "nch_mac", 9.5, 2.0)
        mos(sch, "MNSINKP", "nch_mac", 1.5, -0.5)
        mos(sch, "MNSINKN", "nch_mac", 9.5, -0.5)

        labels(sch, "MNIP", {"D": "XP", "G": "VINP", "S": "NTAIL", "B": "VSS"})
        labels(sch, "MNIN", {"D": "XN", "G": "VINN", "S": "NTAIL", "B": "VSS"})
        labels(sch, "MNTAIL", {"D": "NTAIL", "G": "VBNT", "S": "VSS", "B": "VSS"})
        labels(sch, "MPTOPP", {"D": "XP", "G": "VBPT", "S": "VDD", "B": "VDD"})
        labels(sch, "MPTOPN", {"D": "XN", "G": "VBPT", "S": "VDD", "B": "VDD"})
        labels(sch, "MPFOLDP", {"D": "VOP", "G": "VBPF", "S": "XP", "B": "VDD"})
        labels(sch, "MPFOLDN", {"D": "VON", "G": "VBPF", "S": "XN", "B": "VDD"})
        labels(sch, "MNCASP", {"D": "VOP", "G": "VBNC", "S": "NSINKP", "B": "VSS"})
        labels(sch, "MNCASN", {"D": "VON", "G": "VBNC", "S": "NSINKN", "B": "VSS"})
        labels(sch, "MNSINKP", {"D": "NSINKP", "G": "VBNCM", "S": "VSS", "B": "VSS"})
        labels(sch, "MNSINKN", {"D": "NSINKN", "G": "VBNCM", "S": "VSS", "B": "VSS"})

        # Continuous-time CMFB: passive averaging and a differential error amplifier.
        sch.add(inst("analogLib", "res", "symbol", "RCMP", 12.0, 6.0, "R90"))
        sch.add(inst("analogLib", "res", "symbol", "RCMN", 15.0, 6.0, "R90"))
        sch.add(inst("analogLib", "cap", "symbol", "CCMS", 13.5, 3.5, "R0"))
        sch.add(inst("analogLib", "cap", "symbol", "CCMCOMP", 17.5, 3.5, "R0"))
        labels(sch, "RCMP", {"PLUS": "VOP", "MINUS": "VCMS"})
        labels(sch, "RCMN", {"PLUS": "VON", "MINUS": "VCMS"})
        labels(sch, "CCMS", {"PLUS": "VCMS", "MINUS": "VSS"})
        labels(sch, "CCMCOMP", {"PLUS": "VBNCM", "MINUS": "VSS"})

        mos(sch, "MNCM_S", "nch_mac", 12.0, 1.5)
        mos(sch, "MNCM_R", "nch_mac", 15.0, 1.5)
        mos(sch, "MNCM_T", "nch_mac", 13.5, -0.5)
        mos(sch, "MPCM_D", "pch_mac", 12.0, 4.5)
        mos(sch, "MPCM_O", "pch_mac", 15.0, 4.5)
        labels(sch, "MNCM_S", {"D": "NCM1", "G": "VCMS", "S": "NCMTAIL", "B": "VSS"})
        labels(sch, "MNCM_R", {"D": "VBNCM", "G": "VCMREF", "S": "NCMTAIL", "B": "VSS"})
        labels(sch, "MNCM_T", {"D": "NCMTAIL", "G": "VBNT", "S": "VSS", "B": "VSS"})
        labels(sch, "MPCM_D", {"D": "NCM1", "G": "NCM1", "S": "VDD", "B": "VDD"})
        labels(sch, "MPCM_O", {"D": "VBNCM", "G": "NCM1", "S": "VDD", "B": "VDD"})

        # External interface pins. Bias generation is intentionally outside this first-pass OTA cell.
        for dev, term, name, direction in (
            ("MNIP", "G", "VINP", "input"), ("MNIN", "G", "VINN", "input"),
            ("MPFOLDP", "D", "VOP", "output"), ("MPFOLDN", "D", "VON", "output"),
            ("MPTOPP", "S", "VDD", "inputOutput"), ("MNTAIL", "S", "VSS", "inputOutput"),
            ("MNCM_R", "G", "VCMREF", "input"), ("MNTAIL", "G", "VBNT", "input"),
            ("MPTOPP", "G", "VBPT", "input"), ("MPFOLDP", "G", "VBPF", "input"),
            ("MNCASP", "G", "VBNC", "input"),
        ):
            sch.add(pin_at(dev, term, name, direction=direction))

    client.open_window(LIB, OTA, view="schematic")
    sizes = {
        "MNIP": ("36u", "60n", "24"), "MNIN": ("36u", "60n", "24"),
        "MNTAIL": ("18u", "90n", "24"),
        "MPTOPP": ("40u", "120n", "20"), "MPTOPN": ("40u", "120n", "20"),
        "MPFOLDP": ("24u", "240n", "24"), "MPFOLDN": ("24u", "240n", "24"),
        "MNCASP": ("24u", "180n", "16"), "MNCASN": ("24u", "180n", "16"),
        "MNSINKP": ("24u", "180n", "16"), "MNSINKN": ("24u", "180n", "16"),
        "MNCM_S": ("2u", "90n", "8"), "MNCM_R": ("2u", "90n", "8"),
        "MNCM_T": ("2u", "90n", "8"),
        "MPCM_D": ("4u", "90n", "8"), "MPCM_O": ("4u", "90n", "8"),
    }
    for name, (w, l, nf) in sizes.items():
        set_instance_params(client, name, w=w, l=l, nf=nf, strict=True)
    set_instance_params(client, "RCMP", r="10Meg", strict=True)
    set_instance_params(client, "RCMN", r="10Meg", strict=True)
    set_instance_params(client, "CCMS", c="20f", strict=True)
    set_instance_params(client, "CCMCOMP", c="200f", strict=True)
    create_symbol(client)


def create_tb(client: VirtuosoClient):
    with client.schematic.create(LIB, TB) as sch:
        sch.add(inst(LIB, OTA, "symbol", "DUT", 7.0, 3.0, "R0"))
        source_specs = [
            ("VDD0", "VDD", "0.9", "", ""),
            ("VINP0", "VINP", "0.45", "0.5", "0"),
            ("VINN0", "VINN", "0.45", "0.5", "180"),
            ("VCMR0", "VCMREF", "0.45", "", ""),
            ("VBNT0", "VBNT", "0.55", "", ""),
            ("VBPT0", "VBPT", "0.43", "", ""),
            ("VBPF0", "VBPF", "0.25", "", ""),
            ("VBNC0", "VBNC", "0.60", "", ""),
        ]
        for i, (name, net, _, _, _) in enumerate(source_specs):
            sch.add(inst("analogLib", "vdc", "symbol", name, float(i) * 1.5, -2.0, "R0"))
            labels(sch, name, {"PLUS": net, "MINUS": "0"})
        sch.add(inst("analogLib", "gnd", "symbol", "GND0", 5.0, -4.0, "R0"))
        labels(sch, "GND0", {"gnd!": "0"})
        sch.add(inst("analogLib", "cap", "symbol", "CLOADP", 12.0, 2.0, "R0"))
        sch.add(inst("analogLib", "cap", "symbol", "CLOADN", 14.0, 2.0, "R0"))
        labels(sch, "CLOADP", {"PLUS": "VOP", "MINUS": "0"})
        labels(sch, "CLOADN", {"PLUS": "VON", "MINUS": "0"})
        for pin in ("VDD", "VSS", "VINP", "VINN", "VOP", "VON", "VCMREF", "VBNT", "VBPT", "VBPF", "VBNC"):
            labels(sch, "DUT", {pin: "0" if pin == "VSS" else pin})

    client.open_window(LIB, TB, view="schematic")
    for name, _, vdc, acm, acp in source_specs:
        kwargs = {"vdc": vdc}
        if acm:
            kwargs.update(acm=acm, acp=acp)
        set_instance_params(client, name, param_filters=None, **kwargs)
    set_instance_params(client, "CLOADP", c="50f", strict=True)
    set_instance_params(client, "CLOADN", c="50f", strict=True)


def main():
    client = VirtuosoClient.from_env()
    if LIB not in client.library.list():
        info = client.library.create(LIB, LIB_PATH, technology_library=PDK)
        print("created_library", info)
    else:
        print("using_library", client.library.get(LIB))
    create_ota(client)
    create_tb(client)
    ota_data = client.schematic.read(LIB, OTA, include_positions=True, param_filters=None)
    tb_data = client.schematic.read(LIB, TB, include_positions=True, param_filters=None)
    report = {
        "library": LIB,
        "path": client.library.get(LIB).path,
        "technology": client.library.get(LIB).technology_library,
        "ota_instances": len(ota_data.get("instances", [])),
        "ota_pins": ota_data.get("pins", []),
        "tb_instances": len(tb_data.get("instances", [])),
        "views": client.execute_skill(f'ddGetObj("{LIB}" "{OTA}")~>views~>name').output,
    }
    out = Path(r"E:\64459\VirtuosoDesigns\folded_cascode\virtuoso_creation_report.json")
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    client.open_window(LIB, OTA, view="schematic")


if __name__ == "__main__":
    main()
