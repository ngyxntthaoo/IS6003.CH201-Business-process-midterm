"""
stats.py — Thống kê quy trình: đếm node theo loại, bar chart, pie chart
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

TYPE_COLOR = {1: "#00e5ff", 2: "#4f8ef7", 3: "#f59e0b", 4: "#a855f7"}
TYPE_NAME  = {1: "Event", 2: "Task", 3: "Gateway XOR", 4: "Gateway OR"}


def render_statistics(graph_data: dict):
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    counts = {}
    for n in nodes:
        t    = n["type"]
        name = TYPE_NAME.get(t, f"Unknown({t})")
        counts[name] = counts.get(name, 0) + 1

    type_key = {nm: t for t, nm in TYPE_NAME.items()}
    df = pd.DataFrame([
        {"Loại node": k, "Số lượng": v, "Màu": TYPE_COLOR.get(type_key.get(k, 0), "#888")}
        for k, v in counts.items()
    ])

    total_nodes    = len(nodes)
    total_edges    = len(edges)
    total_tasks    = counts.get("Task", 0)
    total_gateways = counts.get("Gateway XOR", 0) + counts.get("Gateway OR", 0)

    # KPI
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🔵 Tổng số Node",    total_nodes)
    k2.metric("➡️ Tổng số Edge",    total_edges)
    k3.metric("📋 Task nodes",      total_tasks,    help="Số bước thực thi")
    k4.metric("🔀 Gateway nodes",   total_gateways, help="Số điểm rẽ nhánh")

    st.markdown("")
    col_bar, col_pie = st.columns(2)

    with col_bar:
        st.markdown("**Biểu đồ cột — Số lượng theo loại node**")
        fig = go.Figure(go.Bar(
            x=df["Loại node"], y=df["Số lượng"],
            marker_color=df["Màu"].tolist(),
            text=df["Số lượng"], textposition="outside", width=0.5,
        ))
        fig.update_layout(
            plot_bgcolor="#0f1117", paper_bgcolor="#0f1117", font_color="#e0e0e0",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#2a2a3a", dtick=1),
            margin=dict(t=20, b=20, l=20, r=20), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_pie:
        st.markdown("**Biểu đồ tròn — Tỉ trọng loại node**")
        fig = go.Figure(go.Pie(
            labels=df["Loại node"], values=df["Số lượng"],
            marker=dict(colors=df["Màu"].tolist(), line=dict(color="#0f1117", width=2)),
            textinfo="label+percent", textfont_size=13, hole=0.35,
        ))
        fig.update_layout(
            plot_bgcolor="#0f1117", paper_bgcolor="#0f1117", font_color="#e0e0e0",
            margin=dict(t=20, b=20, l=20, r=20), height=300, showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Nhận xét tự động
    if total_nodes > 0:
        task_pct = total_tasks / total_nodes * 100
        gw_pct   = total_gateways / total_nodes * 100
        remarks  = []
        if task_pct >= 50:
            remarks.append(f"✅ Quy trình **tập trung thực thi** — Task chiếm {task_pct:.0f}% tổng node.")
        if gw_pct >= 30:
            remarks.append(f"⚠️ Quy trình có **nhiều điểm rẽ nhánh** — Gateway chiếm {gw_pct:.0f}%, cần kiểm soát luồng.")
        if total_edges > total_nodes:
            remarks.append(f"🔁 Số edge ({total_edges}) > số node ({total_nodes}) — có thể tồn tại vòng lặp hoặc hợp lưu.")
        if not remarks:
            remarks.append("ℹ️ Quy trình cân bằng giữa các loại node.")
        for r in remarks:
            st.markdown(r)

    return {
        "total_nodes": total_nodes, "total_edges": total_edges,
        "total_tasks": total_tasks, "total_gateways": total_gateways,
        "counts": counts,
    }
