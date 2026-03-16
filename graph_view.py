"""
graph_view.py — Render đồ thị pyvis với highlight cycle
"""
from pyvis.network import Network

TYPE_COLOR = {1: "#00e5ff", 2: "#4f8ef7", 3: "#f59e0b", 4: "#a855f7"}
TYPE_SHAPE = {1: "ellipse", 2: "box", 3: "diamond", 4: "diamond"}
TYPE_NAME  = {1: "Event", 2: "Task", 3: "Gateway XOR", 4: "Gateway OR"}
FONT_COLOR = {1: "#0f1117", 2: "#ffffff", 3: "#0f1117", 4: "#0f1117"}


def generate_graph_html(graph_data: dict, graph_name: str,
                        cycle_node_ids: set = None,
                        cycle_edge_pairs: set = None) -> str:
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]
    cycle_node_ids   = cycle_node_ids   or set()
    cycle_edge_pairs = cycle_edge_pairs or set()

    # Adjacency cho hover info
    adj: dict = {n["id"]: [] for n in nodes}
    for src, tgt in edges:
        if src in adj:
            adj[src].append(tgt)
    node_label = {n["id"]: n["label"] for n in nodes}

    net = Network(
        height="860px", width="100%",
        bgcolor="#0f1117", font_color="#e0e0e0",
        directed=True, cdn_resources="remote",
    )
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": { "gravitationalConstant": -80, "springLength": 160, "springConstant": 0.05 },
        "stabilization": { "iterations": 250 }
      },
      "interaction": { "hover": true, "dragNodes": true, "tooltipDelay": 0, "navigationButtons": false },
      "edges": {
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.8 } },
        "smooth": { "type": "curvedCW", "roundness": 0.15 },
        "color": { "color": "#444", "highlight": "#00e5ff", "hover": "#00e5ff" },
        "width": 2, "selectionWidth": 3
      },
      "nodes": { "borderWidth": 2, "borderWidthSelected": 3,
                 "shadow": { "enabled": true, "size": 10, "x": 2, "y": 2 } }
    }
    """)

    for n in nodes:
        t = n["type"]
        in_cycle = n["id"] in cycle_node_ids
        neighbors = adj.get(n["id"], [])
        neighbor_labels = ", ".join(node_label.get(nb, str(nb)) for nb in neighbors) or "—"
        node_color   = "#ef4444" if in_cycle else TYPE_COLOR[t]
        border_color = "#ff0000" if in_cycle else TYPE_COLOR[t]

        # Extra info cho hover panel
        assignee  = n.get("assignee", "") or "—"
        dept      = n.get("department", "") or "—"
        cost      = n.get("node_cost", 0) or 0
        cost_str  = f"{int(cost):,}đ" if cost else "—"

        meta = f'__node__|{n["id"]}|{n["label"]}|{TYPE_NAME[t]}|{node_color}|{neighbor_labels}|{assignee}|{dept}|{cost_str}'

        net.add_node(
            n["id"], label=n["label"],
            color={"background": node_color, "border": border_color,
                   "highlight": {"background": "#fff", "border": border_color},
                   "hover":     {"background": "#fff", "border": border_color}},
            shape=TYPE_SHAPE[t], size=34, title=meta,
            font={"size": 15, "bold": True,
                  "color": "#ffffff" if in_cycle else FONT_COLOR[t]},
        )

    for src, tgt in edges:
        in_ce = (src, tgt) in cycle_edge_pairs
        net.add_edge(src, tgt, width=3 if in_ce else 2,
                     color={"color": "#ef4444" if in_ce else "#444",
                            "highlight": "#ef4444" if in_ce else "#00e5ff"})

    html = net.generate_html()

    # Legend badges
    used_types = sorted({n["type"] for n in nodes})
    legend_items = "".join([
        f'<span style="background:{TYPE_COLOR[t]};color:{FONT_COLOR[t]};'
        f'padding:5px 13px;border-radius:20px;font-size:12px;font-weight:700;'
        f'margin:3px;display:inline-block">{TYPE_NAME[t]}</span>'
        for t in used_types
    ])
    if cycle_node_ids:
        legend_items += '<span style="background:#ef4444;color:#fff;padding:5px 13px;border-radius:20px;font-size:12px;font-weight:700;margin:3px;display:inline-block">🔴 Trong Cycle</span>'

    inject = f"""
<style>
  body {{ margin:0; padding:0; background:#0f1117; overflow:hidden; position:relative; }}
  html {{ width:100%; height:100%; }}
  .card {{ border:none !important; background:transparent !important; width:100% !important; margin:0 !important; padding:0 !important; border-radius:0 !important; }}
  .card-body {{ padding:0 !important; }}
  #mynetwork {{ width:100% !important; height:860px !important; }}
  #mynetwork canvas {{ width:100% !important; }}
  .vis-tooltip {{ display:none !important; }}

  #node-panel {{
    position:absolute; top:18px; right:18px; z-index:1000; width:340px;
    background:rgba(20,22,34,0.97); border:1px solid rgba(255,255,255,0.12);
    border-radius:16px; padding:24px 26px; font-family:'Segoe UI',sans-serif;
    color:#e0e0e0; box-shadow:0 12px 48px rgba(0,0,0,0.6);
    backdrop-filter:blur(12px); transition:opacity .2s ease; opacity:0; pointer-events:none;
  }}
  #node-panel.visible {{ opacity:1; }}
  #np-badge {{ display:inline-block; padding:5px 16px; border-radius:20px; font-size:13px; font-weight:700; margin-bottom:14px; }}
  #np-label {{ font-size:26px; font-weight:800; margin-bottom:4px; color:#fff; }}
  #np-id    {{ font-size:13px; color:#888; margin-bottom:16px; }}
  .np-row   {{ display:flex; justify-content:space-between; font-size:14px; padding:9px 0; border-bottom:1px solid rgba(255,255,255,0.06); }}
  .np-row:last-child {{ border-bottom:none; }}
  .np-key {{ color:#888; }}
  .np-val {{ color:#e0e0e0; font-weight:600; text-align:right; max-width:180px; word-break:break-word; }}

  #legend {{
    position:absolute; top:16px; left:16px; z-index:999;
    background:rgba(20,22,34,0.93); border:1px solid rgba(255,255,255,0.1);
    padding:10px 14px; border-radius:10px; font-family:'Segoe UI',sans-serif; max-width:360px;
  }}
  #legend-title {{ font-weight:700; margin-bottom:8px; font-size:12px; color:#aaa; letter-spacing:.5px; text-transform:uppercase; }}
  #hint {{
    position:absolute; top:16px; left:50%; transform:translateX(-50%);
    font-size:11px; color:#aaa; z-index:999; background:rgba(20,22,34,0.8);
    padding:4px 14px; border-radius:20px; font-family:'Segoe UI',sans-serif; white-space:nowrap;
  }}
</style>

<div id="node-panel">
  <div id="np-badge">Event</div>
  <div id="np-label">Node</div>
  <div id="np-id">ID: —</div>
  <div class="np-row"><span class="np-key">Loại</span><span class="np-val" id="np-type">—</span></div>
  <div class="np-row"><span class="np-key">Phụ trách</span><span class="np-val" id="np-assignee">—</span></div>
  <div class="np-row"><span class="np-key">Phòng ban</span><span class="np-val" id="np-dept">—</span></div>
  <div class="np-row"><span class="np-key">Chi phí node</span><span class="np-val" id="np-cost">—</span></div>
  <div class="np-row"><span class="np-key">Out-edges →</span><span class="np-val" id="np-neighbors">—</span></div>
  <div class="np-row"><span class="np-key">In / Out degree</span><span class="np-val" id="np-degree">—</span></div>
</div>

<div id="legend">
  <div id="legend-title">🗺 {graph_name}</div>
  {legend_items}
</div>
<div id="hint">Hover node để xem thông tin &nbsp;•&nbsp; Kéo để ghim &nbsp;•&nbsp; Nhấp đúp để bỏ ghim</div>

<script>
  setTimeout(function() {{
    var nodeMeta = {{}};
    network.body.data.nodes.get().forEach(function(n) {{
      if (n.title && n.title.startsWith('__node__|')) {{
        var p = n.title.split('|');
        nodeMeta[n.id] = {{ id:p[1], label:p[2], typeName:p[3], color:p[4],
                            neighbors:p[5], assignee:p[6], dept:p[7], cost:p[8] }};
        network.body.data.nodes.update({{ id:n.id, title:'' }});
      }}
    }});
    var inDeg = {{}};
    network.body.data.edges.get().forEach(function(e) {{ inDeg[e.to]=(inDeg[e.to]||0)+1; }});

    var panel = document.getElementById('node-panel');
    function showPanel(nodeId) {{
      var m = nodeMeta[nodeId]; if (!m) return;
      var outDeg = (m.neighbors==='—' ? 0 : m.neighbors.split(',').length);
      document.getElementById('np-badge').textContent = m.typeName;
      document.getElementById('np-badge').style.background = m.color;
      document.getElementById('np-badge').style.color = '#0f1117';
      document.getElementById('np-label').textContent    = m.label;
      document.getElementById('np-id').textContent       = 'Node ID: ' + m.id;
      document.getElementById('np-type').textContent     = m.typeName;
      document.getElementById('np-assignee').textContent = m.assignee;
      document.getElementById('np-dept').textContent     = m.dept;
      document.getElementById('np-cost').textContent     = m.cost;
      document.getElementById('np-neighbors').textContent = m.neighbors;
      document.getElementById('np-degree').textContent   = (inDeg[parseInt(m.id)]||0) + ' in / ' + outDeg + ' out';
      panel.classList.add('visible');
    }}
    function hidePanel() {{ panel.classList.remove('visible'); }}

    network.on('hoverNode',    function(p) {{ showPanel(p.node); }});
    network.on('blurNode',     function()  {{ hidePanel(); }});
    network.on('selectNode',   function(p) {{ if(p.nodes.length) showPanel(p.nodes[0]); }});
    network.on('deselectNode', function()  {{ hidePanel(); }});

    network.on("dragEnd", function(p) {{
      p.nodes.forEach(function(id) {{
        var pos = network.getPositions([id]);
        network.body.data.nodes.update({{ id:id, x:pos[id].x, y:pos[id].y, fixed:{{x:true,y:true}} }});
      }});
    }});
    network.on("doubleClick", function(p) {{
      p.nodes.forEach(function(id) {{
        network.body.data.nodes.update({{ id:id, fixed:{{x:false,y:false}} }});
      }});
    }});
  }}, 700);

  setTimeout(function() {{
    var w = document.body.clientWidth;
    network.setSize(w+'px', '860px');
    network.redraw(); network.fit();
  }}, 900);

  window.addEventListener('resize', function() {{
    network.setSize(document.body.clientWidth+'px', '860px');
    network.redraw();
  }});
</script>
"""
    return html.replace("</body>", inject + "</body>")
