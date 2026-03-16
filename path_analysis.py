"""
path_analysis.py — Phân tích đường đi từ Start → End
  • Liệt kê tất cả path
  • Tính tổng chi phí mỗi path
  • Phân bổ nhân sự trên mỗi path
  • Danh mục thiết bị cần thiết
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

TYPE_NAME = {1: "Event", 2: "Task", 3: "Gateway XOR", 4: "Gateway OR"}


# ── Core: tìm tất cả đường đi S→E (không đi qua cycle) ──────────────────────
def find_all_paths(nodes: list, edges: list) -> list[list]:
    """Tìm tất cả đường đi từ node type=1 đầu tiên đến node type=1 cuối cùng."""
    adj: dict = {n["id"]: [] for n in nodes}
    for src, tgt in edges:
        if src in adj:
            adj[src].append(tgt)

    # Start = Event node đầu tiên, End = Event node cuối cùng
    event_nodes = [n["id"] for n in nodes if n["type"] == 1]
    if len(event_nodes) < 2:
        return []
    start_id = event_nodes[0]
    end_id   = event_nodes[-1]

    all_paths = []
    MAX_PATHS = 50  # Giới hạn để tránh bùng nổ tổ hợp

    def dfs(current, path, visited):
        if len(all_paths) >= MAX_PATHS:
            return
        if current == end_id:
            all_paths.append(list(path))
            return
        for nb in adj.get(current, []):
            if nb not in visited:
                visited.add(nb)
                path.append(nb)
                dfs(nb, path, visited)
                path.pop()
                visited.discard(nb)

    dfs(start_id, [start_id], {start_id})
    return all_paths


def _build_node_map(nodes: list) -> dict:
    return {n["id"]: n for n in nodes}


def _path_label(path: list, node_map: dict) -> str:
    return " → ".join(node_map[nid]["label"] for nid in path if nid in node_map)


def _path_cost(path: list, node_map: dict) -> int:
    return sum(int(node_map[nid].get("node_cost") or 0) for nid in path if nid in node_map)


def _path_people(path: list, node_map: dict) -> list[dict]:
    people = []
    seen   = set()
    for nid in path:
        n = node_map.get(nid, {})
        assignee = n.get("assignee") or ""
        dept     = n.get("department") or ""
        if assignee and assignee not in seen:
            seen.add(assignee)
            people.append({"Phụ trách": assignee, "Phòng ban": dept,
                           "Task": n.get("label", "")})
    return people


def _path_equipment(path: list, node_map: dict) -> list[str]:
    equipment = []
    seen      = set()
    for nid in path:
        n    = node_map.get(nid, {})
        equip_str = n.get("equipment") or ""
        for eq in equip_str.split(";"):
            eq = eq.strip()
            if eq and eq not in seen:
                seen.add(eq)
                equipment.append(eq)
    return equipment


# ── Render ────────────────────────────────────────────────────────────────────
def render_path_analysis(graph_data: dict) -> dict:
    nodes    = graph_data["nodes"]
    edges    = graph_data["edges"]
    node_map = _build_node_map(nodes)

    st.subheader("🗺️ Phân tích đường đi (Path Analysis)")

    paths = find_all_paths(nodes, edges)

    if not paths:
        st.warning("Không tìm được đường đi nào từ Start → End. Kiểm tra lại cấu trúc đồ thị.")
        return {"paths": []}

    # ── Tổng quan ─────────────────────────────────────────────────────────────
    path_costs = [_path_cost(p, node_map) for p in paths]
    min_cost   = min(path_costs)
    max_cost   = max(path_costs)
    cheapest_idx = path_costs.index(min_cost)

    p1, p2, p3 = st.columns(3)
    p1.metric("📍 Số đường đi",       len(paths))
    p2.metric("💰 Chi phí thấp nhất", f"{min_cost:,}đ")
    p3.metric("💸 Chi phí cao nhất",  f"{max_cost:,}đ")

    if min_cost < max_cost:
        saving = max_cost - min_cost
        st.info(f"💡 Chọn **Path {cheapest_idx + 1}** tiết kiệm được **{saving:,}đ** so với đường đắt nhất.")

    # ── Bar chart chi phí các path ────────────────────────────────────────────
    st.markdown("**Chi phí từng đường đi:**")
    path_labels = [f"Path {i+1}" for i in range(len(paths))]
    colors      = ["#ef4444" if c == max_cost else
                   "#22c55e" if c == min_cost else
                   "#4f8ef7" for c in path_costs]

    fig = go.Figure(go.Bar(
        x=path_labels, y=path_costs,
        marker_color=colors,
        text=[f"{c:,}đ" for c in path_costs],
        textposition="outside",
    ))
    fig.update_layout(
        plot_bgcolor="#0f1117", paper_bgcolor="#0f1117", font_color="#e0e0e0",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#2a2a3a", title="VNĐ"),
        margin=dict(t=30, b=20, l=20, r=20), height=280,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Chi tiết từng path ────────────────────────────────────────────────────
    st.markdown("**Chi tiết từng đường đi:**")

    result_paths = []
    for i, path in enumerate(paths):
        cost      = path_costs[i]
        label_str = _path_label(path, node_map)
        people    = _path_people(path, node_map)
        equipment = _path_equipment(path, node_map)

        badge = ""
        if cost == min_cost and len(paths) > 1:
            badge = " 🏆 Rẻ nhất"
        elif cost == max_cost and len(paths) > 1:
            badge = " ⚠️ Đắt nhất"

        with st.expander(f"Path {i+1}{badge}:  {label_str}  —  {cost:,}đ", expanded=(i == cheapest_idx)):

            col_info, col_cost = st.columns([3, 1])
            with col_info:
                st.markdown(f"**Đường đi:** `{label_str}`")
            with col_cost:
                st.metric("Tổng chi phí", f"{cost:,}đ")

            tab_people, tab_equip, tab_nodes = st.tabs(["👥 Nhân sự", "🔧 Thiết bị", "📋 Nodes"])

            with tab_people:
                if people:
                    st.dataframe(pd.DataFrame(people), use_container_width=True, hide_index=True)
                else:
                    st.info("Không có thông tin nhân sự trên đường đi này.")

            with tab_equip:
                if equipment:
                    eq_df = pd.DataFrame({"STT": range(1, len(equipment)+1), "Thiết bị / Công cụ": equipment})
                    st.dataframe(eq_df, use_container_width=True, hide_index=True)
                else:
                    st.info("Không có thông tin thiết bị.")

            with tab_nodes:
                node_details = []
                for nid in path:
                    n = node_map.get(nid, {})
                    node_details.append({
                        "ID":        nid,
                        "Tên":       n.get("label", ""),
                        "Loại":      TYPE_NAME.get(n.get("type", 0), "?"),
                        "Phụ trách": n.get("assignee") or "—",
                        "Phòng ban": n.get("department") or "—",
                        "Chi phí":   f"{int(n.get('node_cost') or 0):,}đ",
                    })
                st.dataframe(pd.DataFrame(node_details), use_container_width=True, hide_index=True)

        result_paths.append({
            "path_id":  i + 1,
            "label":    label_str,
            "node_ids": path,
            "cost":     cost,
            "people":   people,
            "equipment": equipment,
        })

    return {"paths": result_paths, "min_cost": min_cost, "max_cost": max_cost}
