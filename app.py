"""
app.py — Orchestrator chính, gọi các module riêng biệt
"""
import streamlit as st
import pandas as pd
import os

from graph_view    import generate_graph_html, TYPE_NAME, TYPE_COLOR
from stats         import render_statistics
from cycle         import get_cycle_sets, render_cycle_analysis
from path_analysis import render_path_analysis
from report        import render_export
from bpmn_export   import render_bpmn_export

# ── Cấu hình trang ────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Business Process Visualizer", page_icon="📊")

st.markdown("""
<style>
  .main .block-container { padding-top:2rem !important; padding-left:1rem !important;
                           padding-right:1rem !important; max-width:100% !important; }
  .element-container:has(iframe) { width:100% !important; }
  iframe { width:100% !important; min-width:100% !important; }
  #MainMenu, footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
DATA_DIR      = os.path.join(os.path.dirname(__file__), "data")
NODES_CSV     = os.path.join(DATA_DIR, "nodes.csv")
EDGES_CSV     = os.path.join(DATA_DIR, "edges.csv")
TMPL_DIR      = os.path.join(DATA_DIR, "templates")

TEMPLATES = {
    "Accounting/Finance — 10 quy trình": {
        "nodes": os.path.join(TMPL_DIR, "accounting_nodes.csv"),
        "edges": os.path.join(TMPL_DIR, "accounting_edges.csv"),
    },
}


# ── Data loading ──────────────────────────────────────────────────────────────
def _parse_df(nodes_df, edges_df) -> dict:
    db = {}
    for graph_name in nodes_df["graph"].unique():
        n_rows = nodes_df[nodes_df["graph"] == graph_name].copy()
        e_rows = edges_df[edges_df["graph"] == graph_name]
        for col in ["assignee","department","equipment","lane","pool"]:
            if col in n_rows.columns:
                n_rows[col] = n_rows[col].fillna("")
        for col in ["headcount","node_cost"]:
            if col in n_rows.columns:
                n_rows[col] = pd.to_numeric(n_rows[col], errors="coerce").fillna(0)
        db[graph_name] = {
            "nodes": n_rows.to_dict("records"),
            "edges": list(zip(e_rows["source"], e_rows["target"])),
        }
    return db


@st.cache_data
def load_data():
    return _parse_df(pd.read_csv(NODES_CSV), pd.read_csv(EDGES_CSV))


@st.cache_data
def load_template(tmpl_name: str) -> dict:
    t = TEMPLATES[tmpl_name]
    return _parse_df(pd.read_csv(t["nodes"]), pd.read_csv(t["edges"]))


def validate_data(db: dict) -> list[str]:
    warnings = []
    for gname, data in db.items():
        node_ids = {n["id"] for n in data["nodes"]}
        for src, tgt in data["edges"]:
            if src not in node_ids:
                warnings.append(f"[{gname}] Edge ({src}→{tgt}): node {src} không tồn tại.")
            if tgt not in node_ids:
                warnings.append(f"[{gname}] Edge ({src}→{tgt}): node {tgt} không tồn tại.")
    return warnings


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar(db: dict, selected: str) -> dict | None:
    st.sidebar.header("📂 Dữ liệu")
    nodes_file = st.sidebar.file_uploader("nodes.csv", type="csv", key="nodes_up")
    edges_file = st.sidebar.file_uploader("edges.csv", type="csv", key="edges_up")

    uploaded_db = None
    if nodes_file and edges_file:
        try:
            ndf = pd.read_csv(nodes_file)
            edf = pd.read_csv(edges_file)
            req_n = {"id","label","type","graph"}
            req_e = {"source","target","graph"}
            if not req_n.issubset(ndf.columns):
                st.sidebar.error(f"nodes.csv thiếu cột: {req_n - set(ndf.columns)}")
            elif not req_e.issubset(edf.columns):
                st.sidebar.error(f"edges.csv thiếu cột: {req_e - set(edf.columns)}")
            else:
                uploaded_db = {}
                for gname in ndf["graph"].unique():
                    nr = ndf[ndf["graph"]==gname].copy()
                    er = edf[edf["graph"]==gname]
                    for col in ["assignee","department","equipment"]:
                        if col in nr.columns: nr[col] = nr[col].fillna("")
                    for col in ["headcount","node_cost"]:
                        if col in nr.columns: nr[col] = pd.to_numeric(nr[col], errors="coerce").fillna(0)
                    uploaded_db[gname] = {
                        "nodes": nr.to_dict("records"),
                        "edges": list(zip(er["source"], er["target"])),
                    }
                st.sidebar.success(f"✅ Đã tải {len(uploaded_db)} đồ thị.")
        except Exception as e:
            st.sidebar.error(f"Lỗi: {e}")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Thông tin đồ thị")
    data = db[selected]
    st.sidebar.metric("Số node", len(data["nodes"]))
    st.sidebar.metric("Số cạnh (edge)", len(data["edges"]))
    type_counts = {}
    for n in data["nodes"]:
        t = TYPE_NAME.get(n["type"], f"?({n['type']})")
        type_counts[t] = type_counts.get(t, 0) + 1
    st.sidebar.markdown("**Phân loại node:**")
    for t, cnt in type_counts.items():
        st.sidebar.write(f"- {t}: {cnt}")
    st.sidebar.markdown("---")
    st.sidebar.caption("📁 Nguồn: `data/nodes.csv` & `data/edges.csv`")
    return uploaded_db


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.title("📊 Business Process Graph Visualizer")

    # ── Chọn nguồn dữ liệu ───────────────────────────────────────────────────
    src_col, tmpl_col = st.columns([1, 2])
    with src_col:
        data_source = st.radio("Nguồn dữ liệu:", ["CSV mặc định", "Template có sẵn"],
                               horizontal=True)
    with tmpl_col:
        if data_source == "Template có sẵn":
            tmpl_choice = st.selectbox("Chọn template:", list(TEMPLATES.keys()))

    # ── Load dữ liệu ─────────────────────────────────────────────────────────
    if data_source == "Template có sẵn":
        db = load_template(tmpl_choice)
        st.success(f"✅ Đã tải template: **{tmpl_choice}** — {len(db)} quy trình")
    else:
        db = load_data()

    graph_names = list(db.keys())
    selected    = st.selectbox("Chọn quy trình:", graph_names)

    # Sidebar
    uploaded_db = render_sidebar(db, selected)
    if uploaded_db:
        db = uploaded_db
        if selected not in db:
            selected = list(db.keys())[0]

    warnings = validate_data(db)
    if warnings:
        with st.expander("⚠️ Cảnh báo dữ liệu", expanded=True):
            for w in warnings: st.warning(w)

    graph_data = db[selected]

    # ── Detect cycles ─────────────────────────────────────────────────────────
    cycle_node_ids, cycle_edge_pairs, cycles = get_cycle_sets(
        graph_data["nodes"], graph_data["edges"]
    )

    # ── Graph ─────────────────────────────────────────────────────────────────
    import streamlit.components.v1 as components
    with st.spinner("Đang tạo đồ thị..."):
        html_graph = generate_graph_html(
            graph_data, selected,
            cycle_node_ids=cycle_node_ids,
            cycle_edge_pairs=cycle_edge_pairs,
        )
    components.html(html_graph, height=880, scrolling=False)

    # ── Tabs phân tích ────────────────────────────────────────────────────────
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Thống kê quy trình",
        "🔁 Tìm chu trình",
        "🗺️ Phân tích đường đi",
        "📐 Xuất BPMN",
        "📤 Xuất báo cáo Excel",
    ])

    with tab1:
        stats = render_statistics(graph_data)

    with tab2:
        cycle_result = render_cycle_analysis(graph_data, cycles, cycle_node_ids)

    with tab3:
        path_result = render_path_analysis(graph_data)

    with tab4:
        render_bpmn_export(graph_data, selected)

    with tab5:
        # stats/path_result cần được tính trước — dùng giá trị từ tab1/tab3
        # Tính lại nếu chưa có (người dùng nhảy thẳng vào tab5)
        if "stats" not in dir():
            stats = render_statistics.__wrapped__(graph_data) if hasattr(render_statistics,"__wrapped__") else {}
        if "path_result" not in dir():
            path_result = {"paths": []}
        render_export(selected, graph_data, stats, cycles, path_result)

    # ── Dữ liệu thô ───────────────────────────────────────────────────────────
    with st.expander("🔍 Xem dữ liệu thô"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Nodes")
            st.dataframe(
                pd.DataFrame(graph_data["nodes"]).assign(
                    type_name=lambda df: df["type"].map(TYPE_NAME)
                ), use_container_width=True,
            )
        with col2:
            st.subheader("Edges")
            st.dataframe(
                pd.DataFrame(graph_data["edges"], columns=["source","target"]),
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
