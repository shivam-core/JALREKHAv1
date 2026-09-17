import networkx as nx

def allocate_shelters(network, locations, hazard_scenario, closed_edge_ids, shelter_overrides):
    # 1. Build the graph for current scenario
    G = nx.DiGraph()
    
    # Filter unavailable edges from hazard and user overrides
    unavailable = set(hazard_scenario.get("unavailable_edge_ids", []))
    unavailable.update(closed_edge_ids)
    
    edge_geom_map = {}
    for edge in network["edges"]:
        edge_geom_map[edge["id"]] = edge["geometry"]
        if edge["id"] not in unavailable:
            G.add_edge(edge["u"], edge["v"], weight=edge["travel_seconds"], id=edge["id"])
            
    # Apply shelter overrides
    shelters = []
    for s in locations["shelters"]:
        s_copy = s.copy()
        if s["id"] in shelter_overrides:
            s_copy.update(shelter_overrides[s["id"]])
        s_copy["usable"] = s_copy.get("open", False) # Simplify for now
        shelters.append(s_copy)

    origins = locations["origins"]
    
    # 2. Compute shortest paths from all origins to all open shelters
    cutoff = 2700
    allocations = []
    baseline_alloc = []
    paths_info = {}
    
    for o in origins:
        paths_info[o["id"]] = {}
        try:
            lengths, paths = nx.single_source_dijkstra(G, o["node"], cutoff=cutoff, weight="weight")
            for s in shelters:
                if s["usable"] and s["node"] in lengths:
                    # Construct edge path
                    path_nodes = paths[s["node"]]
                    edge_ids = []
                    geom_path = []
                    for i in range(len(path_nodes) - 1):
                        edge_data = G.get_edge_data(path_nodes[i], path_nodes[i+1])
                        edge_id = edge_data["id"]
                        edge_ids.append(edge_id)
                        geom = edge_geom_map.get(edge_id)
                        if geom:
                            geom_path.extend(geom)
                        
                    paths_info[o["id"]][s["id"]] = {
                        "cost": lengths[s["node"]],
                        "edge_ids": edge_ids,
                        "geometry": geom_path if geom_path else None
                    }
        except nx.NodeNotFound:
            pass
            
    # Baseline Allocation
    s_caps = {s["id"]: s["capacity"] for s in shelters if s["usable"]}
    for o in origins:
        o_pop = o["assumed_population"]
        # Find nearest
        nearest = sorted([
            (paths_info[o["id"]][s["id"]]["cost"], s["id"]) 
            for s in shelters if s["id"] in paths_info[o["id"]] and s_caps.get(s["id"], 0) > 0
        ])
        
        remaining = o_pop
        for cost, s_id in nearest:
            if remaining <= 0:
                break
            cap = s_caps[s_id]
            if cap > 0:
                alloc = min(remaining, cap)
                baseline_alloc.append({
                    "origin_id": o["id"],
                    "shelter_id": s_id,
                    "people": alloc,
                    "travel_seconds": cost,
                    "edge_ids": paths_info[o["id"]][s_id]["edge_ids"],
                    "geometry": paths_info[o["id"]][s_id]["geometry"]
                })
                s_caps[s_id] -= alloc
                remaining -= alloc
                
    # Optimization Allocation (Max flow min cost)
    # Build bipartite flow network
    # Source -> Origins (cap = pop, cost = 0)
    # Origins -> Shelters (cap = inf, cost = travel_time)
    # Shelters -> Sink (cap = shelter_cap, cost = 0)
    
    F = nx.DiGraph()
    F.add_node("SOURCE")
    F.add_node("SINK")
    
    for o in origins:
        F.add_edge("SOURCE", f"O_{o['id']}", capacity=o["assumed_population"], weight=0)
    
    for s in shelters:
        if s["usable"]:
            cap = s["capacity"]
            F.add_edge(f"S_{s['id']}", "SINK", capacity=cap, weight=0)
            
    for o_id, s_paths in paths_info.items():
        for s_id, p in s_paths.items():
            F.add_edge(f"O_{o_id}", f"S_{s_id}", capacity=999999, weight=int(p["cost"]))
            
    try:
        flow_dict = nx.max_flow_min_cost(F, "SOURCE", "SINK", capacity="capacity", weight="weight")
        for o_id in paths_info:
            o_node = f"O_{o_id}"
            if o_node in flow_dict:
                for s_node, flow in flow_dict[o_node].items():
                    if flow > 0 and s_node.startswith("S_"):
                        s_id = s_node[2:]
                        allocations.append({
                            "origin_id": o_id,
                            "shelter_id": s_id,
                            "people": flow,
                            "travel_seconds": paths_info[o_id][s_id]["cost"],
                            "edge_ids": paths_info[o_id][s_id]["edge_ids"],
                            "geometry": paths_info[o_id][s_id]["geometry"]
                        })
    except nx.NetworkXUnfeasible:
        # If no flow possible, allocations remain empty
        pass
        
    def summarize(allocs):
        allocated = sum(a["people"] for a in allocs)
        unserved = sum(o["assumed_population"] for o in origins) - allocated
        # We simplify isolated vs capacity unserved
        isolated = 0
        cap_unserved = unserved
        return {
            "population": sum(o["assumed_population"] for o in origins),
            "allocated": allocated,
            "isolated": isolated,
            "capacity_unserved": cap_unserved,
            "unknown_or_unavailable_origin": 0
        }
        
    return {
        "allocations": allocations,
        "totals": summarize(allocations),
        "baseline": {
            "allocations": baseline_alloc,
            "totals": summarize(baseline_alloc)
        }
    }
