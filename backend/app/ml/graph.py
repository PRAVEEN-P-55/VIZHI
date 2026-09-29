"""Cross-complaint fraud network graph (GNN-lite via NetworkX).

Builds a graph where nodes are mule accounts, complaints, and banks, and edges are
shared attributes (mule<->complaint linkage, complaint<->bank). Connected components
are surfaced as candidate fraud syndicates.
"""
from __future__ import annotations

import json

import networkx as nx

from .data import load_all


def build_graph(max_mules: int = 120, state: str | None = None) -> dict:
    """Return a renderable subgraph + detected syndicate components.

    Limits to the top mule accounts by amount so the D3 force graph stays legible.
    """
    data = load_all()
    mules = data["mules"].sort_values("total_amount_received", ascending=False).head(max_mules)
    complaints = data["complaints"].set_index("complaint_id")
    if state:
        complaints = complaints[complaints["state"] == state]

    G = nx.Graph()
    for m in mules.itertuples():
        try:
            links = json.loads(m.linked_complaint_ids)
        except Exception:
            links = []
        links = [cid for cid in links[:25] if cid in complaints.index]
        if not links:
            continue
        mid = f"mule:{m.mule_account_id[:8]}"
        G.add_node(mid, kind="mule", label=f"Mule {m.mule_account_id[:6]}",
                   bank=m.bank_name, amount=float(m.total_amount_received),
                   flagged=bool(m.flagged))
        bank_node = f"bank:{m.bank_name}"
        G.add_node(bank_node, kind="bank", label=m.bank_name)
        G.add_edge(mid, bank_node, kind="registered_at")
        for cid in links:
            cnode = f"cmp:{cid}"
            district = complaints.loc[cid, "district"]
            G.add_node(cnode, kind="complaint", label=cid, district=str(district))
            G.add_edge(mid, cnode, kind="linked_complaint")

    # Banks are context nodes, not evidence that every account at the same bank is
    # part of one syndicate. Detect components only through complaint linkages.
    evidence_graph = nx.Graph(
        (u, v) for u, v, d in G.edges(data=True) if d.get("kind") == "linked_complaint"
    )
    components = [c for c in nx.connected_components(evidence_graph) if len(c) >= 3]
    components.sort(key=len, reverse=True)
    comp_map = {}
    syndicates = []
    for i, comp in enumerate(components):
        for n in comp:
            comp_map[n] = i
        mule_ct = sum(1 for n in comp if G.nodes[n]["kind"] == "mule")
        cmp_ct = sum(1 for n in comp if G.nodes[n]["kind"] == "complaint")
        syndicates.append({
            "syndicate_id": i,
            "size": len(comp),
            "mule_accounts": mule_ct,
            "complaints": cmp_ct,
        })

    nodes = [
        {"id": n, "component": comp_map.get(n, -1), **{k: v for k, v in d.items()}}
        for n, d in G.nodes(data=True)
    ]
    edges = [{"source": u, "target": v, "kind": d.get("kind")} for u, v, d in G.edges(data=True)]
    return {
        "nodes": nodes,
        "edges": edges,
        "syndicates": syndicates[:20],
        "stats": {"node_count": G.number_of_nodes(), "edge_count": G.number_of_edges(),
                  "component_count": len(components)},
    }
