import os
import osmnx as ox
import networkx as nx
import json
from pathlib import Path

def prepare_roads(bounds, out_path, locations_path):
    west, south, east, north = bounds
    print("Downloading OSM road network...")
    
    # Download drive network
    G = ox.graph_from_bbox(bbox=(west, south, east, north), network_type='drive', simplify=True)
    
    # Ensure it is a directed graph and calculate speeds/times
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    
    network = {
        "nodes": {},
        "edges": []
    }
    
    # Save nodes
    for node, data in G.nodes(data=True):
        network["nodes"][str(node)] = {
            "lon": data["x"],
            "lat": data["y"]
        }
        
    # Save edges
    for u, v, key, data in G.edges(keys=True, data=True):
        edge_id = f"{u}_{v}_{key}"
        travel_time = data.get("travel_time", 60.0) # default 60s if missing
        geom = None
        if "geometry" in data:
            geom = [[lon, lat] for lon, lat in data["geometry"].coords]
        
        network["edges"].append({
            "id": edge_id,
            "u": str(u),
            "v": str(v),
            "travel_seconds": travel_time,
            "geometry": geom
        })
        
    with open(out_path, 'w') as f:
        json.dump(network, f)
    print(f"Saved road network to {out_path}")
    
    # Prepare mock origins and shelters mapped to nodes in this graph
    nodes_list = list(G.nodes())
    # Take a few nodes for origins and shelters
    origins = []
    shelters = []
    
    if len(nodes_list) > 10:
        for i in range(6):
            origins.append({
                "id": f"origin-{i+1}",
                "node": str(nodes_list[i]),
                "assumed_population": 100,
                "lat": G.nodes[nodes_list[i]]["y"],
                "lon": G.nodes[nodes_list[i]]["x"]
            })
        for i in range(6, 11):
            shelters.append({
                "id": f"shelter-{i-5}",
                "node": str(nodes_list[i]),
                "capacity": 150,
                "open": (i < 10), # One shelter closed by default
                "lat": G.nodes[nodes_list[i]]["y"],
                "lon": G.nodes[nodes_list[i]]["x"]
            })
            
    locations = {
        "origins": origins,
        "shelters": shelters
    }
    with open(locations_path, 'w') as f:
        json.dump(locations, f)
    print(f"Saved locations to {locations_path}")

if __name__ == "__main__":
    bounds = (73.845, 18.505, 73.895, 18.550)
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    prepare_roads(bounds, out_dir / "network.json", out_dir / "locations.json")
