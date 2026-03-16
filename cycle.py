"""
cycle.py — Phát hiện chu trình (Cycle Detection) bằng DFS
"""
import streamlit as st
import pandas as pd

TYPE_NAME = {1: "Event", 2: "Task", 3: "Gateway XOR", 4: "Gateway OR"}


def find_cycles(nodes: list, edges: list) -> list[list]:
    """DFS tìm tất cả chu trình trong đồ thị có hướng."""
    adj: dict = {n["id"]: [] for n in nodes}
    for src, tgt in edges:
        if src in adj:
            adj[src].append(tgt)

    all_cycles = []
    visited    = set()
    rec_stack  = []
    in_stack   = set()

    def dfs(node):
        visited.add(node)
        rec_stack.append(node)
        in_stack.add(node)
        for nb in adj.get(node, []):
            if nb not in visited:
                dfs(nb)
            elif nb in in_stack:
                idx   = rec_stack.index(nb)
                cycle = rec_stack[idx:]
                norm  = tuple(sorted(cycle))
                if norm not in {tuple(sorted(c)) for c in all_cycles}:
                    all_cycles.append(list(cycle))
        rec_stack.pop()
        in_stack.discard(node)

    import sys
    sys.setrecursionlimit(10000)
    for n in nodes:
        if n["id"] not in visited:
            dfs(n["id"])
    return all_cycles


def get_cycle_sets(nodes: list, edges: list):
    """Trả về (cycle_node_ids, cycle_edge_pairs, cycles) để dùng ở nhiều nơi."""
    cycles           = find_cycles(nodes, edges)
    cycle_node_ids   = set()
    cycle_edge_pairs = set()
    for cycle in cycles:
        cycle_node_ids.update(cycle)
        for i in range(len(cycle)):
            cycle_edge_pairs.add((cycle[i], cycle[(i + 1) % len(cycle)]))
    return cycle_node_ids, cycle_edge_pairs, cycles


def render_cycle_analysis(graph_data: dict, cycles: list, cycle_node_ids: set) -> dict:
    nodes      = graph_data["nodes"]
    edges      = graph_data["edges"]
    node_label = {n["id"]: n["label"] for n in nodes}

    st.subheader("🔁 Tìm chu trình (Cycle Detection)")

    if not cycles:
        st.success("✅ **Không phát hiện chu trình.** Quy trình chạy tuyến tính, không có vòng lặp vô tận.")
        c1, c2 = st.columns(2)
        c1.metric("Số chu trình", 0)
        c2.metric("Node bị ảnh hưởng", 0)
        return {"cycles": [], "affected_nodes": 0}

    affected_nodes = len(cycle_node_ids)
    affected_pct   = affected_nodes / len(nodes) * 100 if nodes else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("⚠️ Số chu trình",         len(cycles))
    c2.metric("🔴 Node bị ảnh hưởng",    affected_nodes, help="Node nằm trong ≥1 chu trình")
    c3.metric("📊 % node trong cycle",   f"{affected_pct:.0f}%")

    st.error(f"**Phát hiện {len(cycles)} chu trình!** Quy trình có thể bị lặp vô tận nếu thiếu điều kiện thoát.")

    for i, cycle in enumerate(cycles, 1):
        labels     = [node_label.get(nid, str(nid)) for nid in cycle]
        path_str   = " → ".join(labels) + f" → **{labels[0]}**"
        node_types = [TYPE_NAME.get(
            next((n["type"] for n in nodes if n["id"] == nid), 0), "?") for nid in cycle]

        with st.expander(f"Chu trình {i}: {' → '.join(labels)} → {labels[0]}", expanded=True):
            st.markdown(f"🔄 **Đường đi:** {path_str}")
            st.markdown(f"📏 **Độ dài:** {len(cycle)} node")
            cycle_df = pd.DataFrame([{
                "Node ID": nid,
                "Tên":     node_label.get(nid, str(nid)),
                "Loại":    TYPE_NAME.get(next((n["type"] for n in nodes if n["id"] == nid), 0), "?"),
            } for nid in cycle])
            st.dataframe(cycle_df, use_container_width=True, hide_index=True)
            if any("Gateway" in t for t in node_types):
                st.warning("🔀 Chu trình đi qua **Gateway** — kiểm tra điều kiện thoát.")
            else:
                st.warning("📋 Chu trình chỉ gồm **Task** — thiếu Gateway để thoát vòng lặp!")

    return {"cycles": cycles, "affected_nodes": affected_nodes}
