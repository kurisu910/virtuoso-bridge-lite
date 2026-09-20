from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.env import set_runtime_env_file

set_runtime_env_file(r"E:\64459\Projects\virtuoso-bridge-lite\.env")
client = VirtuosoClient.from_env()
lib = "FC_OTA_0P9V_TSMC28"
cell = "tb_fc_fd_cmfb_tt"
session = client.maestro.open_session(lib, cell)
try:
    client.maestro.create_test("AC_TT", lib=lib, cell=cell, session=session)
    client.maestro.set_analysis(
        "AC_TT", "ac",
        options='(("start" "1k") ("stop" "100G") '
                '("incrType" "Logarithmic") ("stepTypeLog" "Points Per Decade") '
                '("dec" "60"))',
        session=session,
    )
    client.maestro.set_analysis("AC_TT", "tran", enable=False, session=session)
    client.maestro.add_output("VOP", "AC_TT", output_type="net", signal_name="/VOP", session=session)
    client.maestro.add_output("VON", "AC_TT", output_type="net", signal_name="/VON", session=session)
    client.maestro.add_output(
        "Adiff_dB", "AC_TT",
        expr='dB20(VF("/VOP")-VF("/VON"))', session=session,
    )
    client.maestro.setup_corner(
        "TT_27C",
        model_file="/opt/pdk/tsmc28hpcp_1p8m_5x2z/models/spectre/toplevel.scs",
        model_section="top_tt",
        session=session,
    )
    client.maestro.set_sim_option("AC_TT", '(("temp" "27"))', session=session)
    client.maestro.save_setup(lib, cell, session=session)
    print("created_maestro", lib, cell, session)
finally:
    client.maestro.close_session(session)
