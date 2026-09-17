import json
import rasterio
from pathlib import Path
import math

def prepare_scenarios(network_path, locations_path, hand_path, out_dir):
    with open(network_path) as f:
        network = json.load(f)
    with open(locations_path) as f:
        locations = json.load(f)
        
    levels = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    
    hazards = {
        "levels": levels,
        "scenarios": {}
    }
    
    print(f"Reading {hand_path}...")
    with rasterio.open(hand_path) as src:
        hand = src.read(1)
        transform = src.transform
        bounds = src.bounds
        nodata = src.nodata
        
        def get_hand_at(lon, lat):
            # Check if out of bounds
            if not (bounds.left <= lon <= bounds.right and bounds.bottom <= lat <= bounds.top):
                return None
            row, col = src.index(lon, lat)
            if 0 <= row < hand.shape[0] and 0 <= col < hand.shape[1]:
                val = hand[row, col]
                if nodata is not None and val == nodata:
                    return None
                return float(val)
            return None

        for h in levels:
            unavailable_edges = []
            unknown_edges = []
            
            for edge in network["edges"]:
                # simple sampling at u and v
                u_node = network["nodes"][edge["u"]]
                v_node = network["nodes"][edge["v"]]
                
                h_u = get_hand_at(u_node["lon"], u_node["lat"])
                h_v = get_hand_at(v_node["lon"], v_node["lat"])
                
                if h_u is None or h_v is None:
                    unknown_edges.append(edge["id"])
                else:
                    # if hand is less than or equal to level, it's flooded
                    # h == 0.0 means normal river level. roads shouldn't be flooded at 0.0 unless they are physically in the river.
                    if h == 0.0:
                        if h_u == 0.0 or h_v == 0.0:
                            pass # We might not close roads at 0.0 to keep baseline intact
                    else:
                        if h_u <= h or h_v <= h:
                            unavailable_edges.append(edge["id"])

            hazards["scenarios"][str(h)] = {
                "overlay_url": f"/data/water/level_{h}.png",
                "image_coordinates": [
                    [bounds.left, bounds.top],
                    [bounds.right, bounds.top],
                    [bounds.right, bounds.bottom],
                    [bounds.left, bounds.bottom]
                ],
                "unavailable_edge_ids": unavailable_edges,
                "unknown_edge_ids": unknown_edges
            }
            
    out_path = Path(out_dir) / "hazards.json"
    with open(out_path, 'w') as f:
        json.dump(hazards, f)
    print(f"Saved hazards to {out_path}")
    
    manifest = {
        "version": "1.0",
        "dataset_version": "v1-demo",
        "bounds": {
            "west": bounds.left,
            "south": bounds.bottom,
            "east": bounds.right,
            "north": bounds.top
        },
        "levels": levels,
        "crs": "EPSG:4326"
    }
    manifest_path = Path(out_dir) / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f)
    print(f"Saved manifest to {manifest_path}")

if __name__ == "__main__":
    out_dir = Path("data/processed")
    prepare_scenarios(
        out_dir / "network.json",
        out_dir / "locations.json",
        Path("data/raw") / "hand.tif",
        out_dir
    )
