"""
bpmn_export.py — Chuyển đổi graph → BPMN 2.0 XML + SVG
"""
import math
import xml.etree.ElementTree as ET
from xml.dom import minidom

TYPE_NAME = {1: "Event", 2: "Task", 3: "Gateway XOR", 4: "Gateway OR"}

# ── Layout constants ──────────────────────────────────────────────────────────
NODE_W, NODE_H   = 120, 60
EVENT_R          = 30          # radius của event circle
GW_SIZE          = 50          # diamond half-size
H_GAP, V_GAP     = 180, 120   # khoảng cách ngang / dọc
LANE_H           = 200         # chiều cao mỗi lane
POOL_HEADER_W    = 40
LANE_HEADER_W    = 100
MARGIN           = 60

# Màu sắc SVG
COLOR = {
    "Event":       ("#00E5FF", "#0f1117"),
    "Task":        ("#4F8EF7", "#ffffff"),
    "Gateway XOR": ("#F59E0B", "#0f1117"),
    "Gateway OR":  ("#A855F7", "#0f1117"),
}
LANE_COLORS = ["#EFF6FF","#F0FDF4","#FEF9C3","#FDF4FF","#FFF7ED","#F0FDFA"]


# ══════════════════════════════════════════════════════════════════════════════
# 1. Layout engine — tính toán vị trí x,y cho mỗi node
# ══════════════════════════════════════════════════════════════════════════════
def _compute_layout(nodes: list, edges: list) -> dict:
    """
    Topological sort → gán cột (x) theo thứ tự duyệt, hàng (y) theo lane.
    Trả về dict: node_id → (x, y, width, height)
    """
    # Build adjacency
    adj   = {n["id"]: [] for n in nodes}
    in_deg= {n["id"]: 0  for n in nodes}
    for src, tgt in edges:
        if src in adj and tgt in in_deg:
            adj[src].append(tgt)
            in_deg[tgt] += 1

    # Topological BFS (Kahn)
    from collections import deque
    queue = deque([nid for nid, d in in_deg.items() if d == 0])
    order = []
    col   = {}  # node_id → column index
    while queue:
        nid = queue.popleft()
        order.append(nid)
        col[nid] = col.get(nid, 0)
        for nb in adj[nid]:
            col[nb] = max(col.get(nb, 0), col[nid] + 1)
            in_deg[nb] -= 1
            if in_deg[nb] == 0:
                queue.append(nb)

    # Assign remaining (cycle nodes) to max col + 1
    max_col = max(col.values()) if col else 0
    for n in nodes:
        if n["id"] not in col:
            max_col += 1
            col[n["id"]] = max_col

    # Group nodes by lane
    lanes_order = []
    lane_nodes  = {}
    for n in nodes:
        lane = n.get("lane") or "Default"
        if lane not in lane_nodes:
            lane_nodes[lane] = []
            lanes_order.append(lane)
        lane_nodes[lane].append(n["id"])

    # Compute y for each lane
    lane_y = {}
    y_cursor = MARGIN + LANE_HEADER_W
    for lane in lanes_order:
        lane_y[lane] = y_cursor
        y_cursor += LANE_H

    # Count nodes per col per lane for vertical centering
    pos = {}
    for n in nodes:
        lane  = n.get("lane") or "Default"
        c     = col[n["id"]]
        t     = n.get("type", 2)
        ly    = lane_y[lane]

        x = MARGIN + POOL_HEADER_W + LANE_HEADER_W + c * (NODE_W + H_GAP)
        y = ly + LANE_H // 2 - NODE_H // 2  # vertically center in lane

        if t == 1:    # Event — circle
            w, h = EVENT_R*2, EVENT_R*2
        elif t in (3, 4):  # Gateway — diamond
            w, h = GW_SIZE*2, GW_SIZE*2
        else:          # Task — rectangle
            w, h = NODE_W, NODE_H

        pos[n["id"]] = {"x": x, "y": y, "w": w, "h": h,
                        "cx": x + w//2, "cy": y + h//2}

    return pos, lanes_order, lane_nodes, lane_y, y_cursor


# ══════════════════════════════════════════════════════════════════════════════
# 2. BPMN 2.0 XML export
# ══════════════════════════════════════════════════════════════════════════════
def graph_to_bpmn_xml(nodes: list, edges: list,
                       process_name: str = "Process",
                       pool_name: str    = "Pool") -> str:
    """
    Tạo BPMN 2.0 XML chuẩn — mở được trong Camunda Modeler / draw.io / Bizagi.
    """
    pos, lanes_order, lane_nodes, lane_y, total_h = _compute_layout(nodes, edges)
    node_map  = {n["id"]: n for n in nodes}
    edge_label= {}  # sẽ dùng sau khi thêm label vào edges

    # ── Namespaces ────────────────────────────────────────────────────────────
    NS = {
        "bpmn":  "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "bpmndi":"http://www.omg.org/spec/BPMN/20100524/DI",
        "dc":    "http://www.omg.org/spec/DD/20100524/DC",
        "di":    "http://www.omg.org/spec/DD/20100524/DI",
        "xsi":   "http://www.w3.org/2001/XMLSchema-instance",
    }
    for prefix, uri in NS.items():
        ET.register_namespace(prefix, uri)

    root = ET.Element("bpmn:definitions",
        attrib={
            "xmlns:bpmn":  NS["bpmn"],
            "xmlns:bpmndi":NS["bpmndi"],
            "xmlns:dc":    NS["dc"],
            "xmlns:di":    NS["di"],
            "targetNamespace": "http://bpmn.io/schema/bpmn",
            "id": "Definitions_1",
        })

    proc_id  = "Process_1"
    process  = ET.SubElement(root, "bpmn:process",
                              attrib={"id": proc_id, "name": process_name,
                                      "isExecutable": "false"})

    # ── Lane Set ──────────────────────────────────────────────────────────────
    lane_set = ET.SubElement(process, "bpmn:laneSet", attrib={"id": "LaneSet_1"})
    for lane_name in lanes_order:
        lane_el = ET.SubElement(lane_set, "bpmn:lane",
                                attrib={"id": f"Lane_{lane_name.replace(' ','_')}",
                                        "name": lane_name})
        for nid in lane_nodes[lane_name]:
            ET.SubElement(lane_el, "bpmn:flowNodeRef").text = f"Node_{nid}_{proc_id}"

    # ── Flow nodes ────────────────────────────────────────────────────────────
    event_nodes = [n["id"] for n in nodes if n["type"] == 1]
    start_id    = event_nodes[0]  if event_nodes else None

    for n in nodes:
        t   = n["type"]
        nid = f"Node_{n['id']}_{proc_id}"
        if t == 1:
            tag = "bpmn:startEvent" if n["id"] == start_id else "bpmn:endEvent"
        elif t == 2:
            tag = "bpmn:task"
        elif t == 3:
            tag = "bpmn:exclusiveGateway"
        else:
            tag = "bpmn:inclusiveGateway"
        ET.SubElement(process, tag, attrib={"id": nid, "name": n.get("label", "")})

    # ── Sequence flows ────────────────────────────────────────────────────────
    for i, (src, tgt) in enumerate(edges):
        ET.SubElement(process, "bpmn:sequenceFlow",
                      attrib={"id":        f"Flow_{i+1}_{proc_id}",
                              "sourceRef": f"Node_{src}_{proc_id}",
                              "targetRef": f"Node_{tgt}_{proc_id}"})

    # ── BPMNDiagram ───────────────────────────────────────────────────────────
    diagram    = ET.SubElement(root,    "bpmndi:BPMNDiagram", attrib={"id": "Diagram_1"})
    bpmn_plane = ET.SubElement(diagram, "bpmndi:BPMNPlane",
                               attrib={"id": "Plane_1", "bpmnElement": proc_id})

    # Pool shape
    total_cols = max(p["x"] + p["w"] for p in pos.values()) + MARGIN if pos else 800
    pool_w     = total_cols + MARGIN
    pool_shape = ET.SubElement(bpmn_plane, "bpmndi:BPMNShape",
                               attrib={"id": "Pool_shape", "bpmnElement": proc_id,
                                       "isHorizontal": "true"})
    pool_shape.append(_dc_bounds(MARGIN, MARGIN, pool_w, total_h - MARGIN, NS))

    # Lane shapes
    for lane_name in lanes_order:
        ly    = lane_y[lane_name]
        shape = ET.SubElement(bpmn_plane, "bpmndi:BPMNShape",
                              attrib={"id":          f"Lane_{lane_name.replace(' ','_')}_shape",
                                      "bpmnElement": f"Lane_{lane_name.replace(' ','_')}",
                                      "isHorizontal":"true"})
        shape.append(_dc_bounds(MARGIN + POOL_HEADER_W, ly, pool_w - POOL_HEADER_W, LANE_H, NS))

    # Node shapes
    for n in nodes:
        p    = pos[n["id"]]
        nid  = f"Node_{n['id']}_{proc_id}"
        shape= ET.SubElement(bpmn_plane, "bpmndi:BPMNShape",
                             attrib={"id": f"{nid}_shape", "bpmnElement": nid})
        if n["type"] in (3, 4):
            shape.set("isMarkerVisible", "true")
        shape.append(_dc_bounds(p["x"], p["y"], p["w"], p["h"], NS))
        lbl = ET.SubElement(shape, "bpmndi:BPMNLabel")
        lbl.append(_dc_bounds(p["x"]-10, p["y"]+p["h"]+2, p["w"]+20, 14, NS))

    # Edge waypoints
    for i, (src, tgt) in enumerate(edges):
        sf_id   = f"Flow_{i+1}_{proc_id}"
        ps, pt  = pos[src], pos[tgt]
        edge_el = ET.SubElement(bpmn_plane, "bpmndi:BPMNEdge",
                                attrib={"id": f"{sf_id}_di", "bpmnElement": sf_id})
        _add_waypoint(edge_el, ps["cx"], ps["cy"], NS)
        _add_waypoint(edge_el, pt["cx"], pt["cy"], NS)

    raw = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(raw)
    return dom.toprettyxml(indent="  ", encoding=None)


def _dc_bounds(x, y, w, h, NS):
    return ET.Element("dc:Bounds",
                      attrib={"x": str(int(x)), "y": str(int(y)),
                              "width": str(int(w)), "height": str(int(h))})

def _add_waypoint(parent, x, y, NS):
    ET.SubElement(parent, "di:waypoint",
                  attrib={"x": str(int(x)), "y": str(int(y))})


# ══════════════════════════════════════════════════════════════════════════════
# 3. SVG export
# ══════════════════════════════════════════════════════════════════════════════
def graph_to_svg(nodes: list, edges: list,
                 process_name: str = "Process") -> str:
    pos, lanes_order, lane_nodes, lane_y, total_h = _compute_layout(nodes, edges)
    node_map = {n["id"]: n for n in nodes}

    total_w = max(p["x"] + p["w"] for p in pos.values()) + MARGIN * 2 if pos else 800
    svg_h   = total_h + MARGIN

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{svg_h}" '
        f'style="font-family:Arial,sans-serif;background:#f8fafc">',
        '<defs>',
        '  <marker id="arrow" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">',
        '    <polygon points="0 0, 10 3.5, 0 7" fill="#94A3B8"/>',
        '  </marker>',
        '  <filter id="shadow"><feDropShadow dx="2" dy="2" stdDeviation="2" flood-opacity="0.15"/></filter>',
        '</defs>',
    ]

    # Pool border
    lines.append(f'<rect x="{MARGIN}" y="{MARGIN}" width="{total_w-MARGIN*2}" '
                 f'height="{svg_h-MARGIN*2}" rx="8" fill="white" '
                 f'stroke="#1E3A5F" stroke-width="2"/>')

    # Pool header
    lines.append(f'<rect x="{MARGIN}" y="{MARGIN}" width="{POOL_HEADER_W}" '
                 f'height="{svg_h-MARGIN*2}" fill="#1E3A5F" rx="8"/>')
    lines.append(f'<text x="{MARGIN + POOL_HEADER_W//2}" y="{MARGIN + (svg_h-MARGIN*2)//2}" '
                 f'fill="white" font-size="13" font-weight="bold" text-anchor="middle" '
                 f'transform="rotate(-90,{MARGIN+POOL_HEADER_W//2},{MARGIN+(svg_h-MARGIN*2)//2})">'
                 f'{process_name}</text>')

    # Lanes
    for i, lane_name in enumerate(lanes_order):
        ly  = lane_y[lane_name]
        bg  = LANE_COLORS[i % len(LANE_COLORS)]
        lx  = MARGIN + POOL_HEADER_W
        lw  = total_w - MARGIN * 2 - POOL_HEADER_W

        lines.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{LANE_H}" '
                     f'fill="{bg}" stroke="#CBD5E1" stroke-width="1"/>')
        # Lane header
        lines.append(f'<rect x="{lx}" y="{ly}" width="{LANE_HEADER_W}" height="{LANE_H}" '
                     f'fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>')
        lines.append(f'<text x="{lx + LANE_HEADER_W//2}" y="{ly + LANE_H//2}" '
                     f'fill="#334155" font-size="11" font-weight="bold" text-anchor="middle" '
                     f'transform="rotate(-90,{lx+LANE_HEADER_W//2},{ly+LANE_H//2})">'
                     f'{lane_name}</text>')

    # Edges (draw first so nodes are on top)
    for src, tgt in edges:
        if src not in pos or tgt not in pos:
            continue
        ps, pt = pos[src], pos[tgt]
        x1, y1 = ps["cx"], ps["cy"]
        x2, y2 = pt["cx"], pt["cy"]

        # Simple orthogonal routing
        if abs(y1 - y2) < 5:  # same lane → horizontal
            lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                         f'stroke="#94A3B8" stroke-width="1.5" '
                         f'marker-end="url(#arrow)"/>')
        else:  # cross-lane → elbow
            mx = (x1 + x2) // 2
            lines.append(f'<polyline points="{x1},{y1} {mx},{y1} {mx},{y2} {x2},{y2}" '
                         f'fill="none" stroke="#94A3B8" stroke-width="1.5" '
                         f'marker-end="url(#arrow)"/>')

    # Nodes
    for n in nodes:
        p    = pos[n["id"]]
        t    = n.get("type", 2)
        lbl  = n.get("label", "")
        name = TYPE_NAME.get(t, "Task")
        fill, tc = COLOR.get(name, ("#4F8EF7", "#fff"))
        x, y, w, h, cx, cy = p["x"], p["y"], p["w"], p["h"], p["cx"], p["cy"]

        if t == 1:  # Event — circle
            lines.append(f'<circle cx="{cx}" cy="{cy}" r="{EVENT_R}" '
                         f'fill="{fill}" stroke="{fill}" stroke-width="3" filter="url(#shadow)"/>')
            if n["id"] == [nn["id"] for nn in nodes if nn["type"]==1][0]:
                lines.append(f'<circle cx="{cx}" cy="{cy}" r="{EVENT_R-6}" '
                             f'fill="none" stroke="{tc}" stroke-width="2"/>')
            else:
                lines.append(f'<circle cx="{cx}" cy="{cy}" r="{EVENT_R-6}" '
                             f'fill="{tc}" opacity="0.25"/>')

        elif t in (3, 4):  # Gateway — diamond
            pts = f"{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}"
            lines.append(f'<polygon points="{pts}" fill="{fill}" stroke="white" '
                         f'stroke-width="2" filter="url(#shadow)"/>')
            sym = "✕" if t == 3 else "+"
            lines.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" '
                         f'font-size="16" font-weight="bold" fill="{tc}">{sym}</text>')

        else:  # Task — rounded rect
            lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                         f'fill="{fill}" stroke="white" stroke-width="1.5" filter="url(#shadow)"/>')

        # Label
        words   = lbl.split()
        chunks  = []
        line_w  = ""
        for word in words:
            test = (line_w + " " + word).strip()
            if len(test) > 14 and line_w:
                chunks.append(line_w)
                line_w = word
            else:
                line_w = test
        if line_w:
            chunks.append(line_w)
        chunks = chunks[:3]

        label_y = cy - (len(chunks)-1) * 7
        for li, chunk in enumerate(chunks):
            lines.append(f'<text x="{cx}" y="{label_y + li*14}" text-anchor="middle" '
                         f'font-size="10" font-weight="bold" fill="{tc}">{chunk}</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Streamlit UI
# ══════════════════════════════════════════════════════════════════════════════
def render_bpmn_export(graph_data: dict, graph_name: str):
    import streamlit as st

    nodes = graph_data["nodes"]
    edges_raw = graph_data["edges"]

    # edges có thể là list of tuple (src,tgt) hoặc list of tuple (src,tgt,label)
    edges = [(e[0], e[1]) for e in edges_raw]

    st.subheader("📐 Xuất BPMN")
    st.markdown(
        "Chuyển đổi graph sang **BPMN 2.0 XML** (mở bằng Camunda / draw.io) "
        "và **SVG** (xem trực tiếp / in ấn)."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Tạo BPMN XML", type="primary", use_container_width=True):
            with st.spinner("Đang tạo BPMN XML..."):
                xml_str = graph_to_bpmn_xml(nodes, edges, graph_name)
            fname = graph_name.replace(" ","_").replace("—","").replace("/","") + ".bpmn"
            st.download_button(
                "📥 Tải BPMN XML (.bpmn)",
                data=xml_str.encode("utf-8"),
                file_name=fname,
                mime="application/xml",
                use_container_width=True,
            )
            with st.expander("Xem XML", expanded=False):
                st.code(xml_str[:3000] + ("\n..." if len(xml_str) > 3000 else ""), language="xml")

    with col2:
        if st.button("🎨 Tạo SVG", type="primary", use_container_width=True):
            with st.spinner("Đang tạo SVG..."):
                svg_str = graph_to_svg(nodes, edges, graph_name)
            fname_svg = graph_name.replace(" ","_").replace("—","").replace("/","") + ".svg"
            st.download_button(
                "📥 Tải SVG",
                data=svg_str.encode("utf-8"),
                file_name=fname_svg,
                mime="image/svg+xml",
                use_container_width=True,
            )
            st.markdown("**Preview SVG:**")
            st.components.v1.html(svg_str, height=500, scrolling=True)

    st.markdown("---")
    st.caption(
        "💡 **Hướng dẫn mở BPMN XML:**  "
        "draw.io → File → Import → chọn file .bpmn  |  "
        "Camunda Modeler → Open file .bpmn"
    )
