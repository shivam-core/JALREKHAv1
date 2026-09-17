"""Step 2: OpenStreetMap roads, shelters and rivers -> small CSV/JSON tables."""
import json
import math
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from scipy.spatial import cKDTree
import osmnx as ox

# Assumed shelter capacities (people). These are ASSUMPTIONS - say so on the slide.
CAPACITY = {"school": 300, "college": 500, "university": 800,
            "hospital": 100, "community_centre": 200}

def download_roads(bbox):
    """bbox = (west, south, east, north). Returns a drivable road graph with travel times."""
    G = ox.graph_from_bbox(bbox=bbox, network_type="drive", simplify=True)
    G = ox.add_edge_speeds(G)         # fills missing speeds from road type
    G = ox.add_edge_travel_times(G)   # seconds per edge
    return G

def download_features(bbox, tags):
    """Return a GeoDataFrame of OSM features, or an empty one if nothing is found."""
    try:
        return ox.features_from_bbox(bbox=bbox, tags=tags)
    except Exception as e:  # osmnx raises InsufficientResponseError when empty
        print("No features for", tags, "->", type(e).__name__)
        import geopandas as gpd
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

def download_shelters(bbox):
    gdf = download_features(bbox, {"amenity": list(CAPACITY.keys())})
    if gdf.empty:
        return pd.DataFrame(columns=["name", "kind", "lon", "lat", "capacity"])
    
    pts = gdf.geometry.representative_point()
    df = pd.DataFrame({
        "name": gdf.get("name", pd.Series(index=gdf.index, dtype=object)).fillna("Unnamed"),
        "kind": gdf["amenity"].values,
        "lon": pts.x.values, "lat": pts.y.values,
    })
    df["capacity"] = df["kind"].map(CAPACITY).fillna(200).astype(int)
    return df.reset_index(drop=True)

def download_river_lines(bbox):
    gdf = download_features(bbox, {"waterway": ["river", "stream", "drain"]})
    if gdf.empty:
        return []
    return [g for g in gdf.geometry if g.geom_type in ("LineString", "MultiLineString")]

def _xy(lons, lats, lat0):
    """Degrees -> approximate metres (good enough inside one city)."""
    k = 111_320.0
    return np.column_stack([np.asarray(lons) * k * math.cos(math.radians(lat0)),
                            np.asarray(lats) * k])

def sample_hand(hand_path, lons, lats):
    with rasterio.open(hand_path) as r:
        vals = np.array([v[0] for v in r.sample(zip(lons, lats))], dtype="float32")
        b = r.bounds
        outside = (np.asarray(lons) < b.left) | (np.asarray(lons) > b.right) | \
                  (np.asarray(lats) < b.bottom) | (np.asarray(lats) > b.top)
        vals[outside | ~np.isfinite(vals)] = 999.0
        return vals

def build_tables(G, shelters, hand_path, bbox, out_dir, cell_km=1.0, people_per_node=25):
    """Write nodes.csv, edges.csv, shelters.csv, origins.json, meta.json into out_dir."""
    west, south, east, north = bbox
    lat0 = (south + north) / 2
    
    # --- nodes ---
    nodes = pd.DataFrame([(n, d["x"], d["y"]) for n, d in G.nodes(data=True)],
                         columns=["id", "lon", "lat"])
    nodes["hand"] = sample_hand(hand_path, nodes.lon, nodes.lat)
    tree = cKDTree(_xy(nodes.lon, nodes.lat, lat0))
    
    # --- edges (undirected, keep fastest parallel edge) ---
    rows = [(min(u, v), max(u, v), float(d.get("travel_time", 60.0)))
            for u, v, d in G.edges(data=True) if u != v]
    edges = (pd.DataFrame(rows, columns=["u", "v", "travel_time"])
             .groupby(["u", "v"], as_index=False)["travel_time"].min())
             
    # --- shelters: snap to nearest road node ---
    shelters = shelters.copy().reset_index(drop=True)
    if len(shelters):
        _, idx = tree.query(_xy(shelters.lon, shelters.lat, lat0))
        shelters["node"] = nodes.id.values[idx]
        shelters["hand"] = sample_hand(hand_path, shelters.lon, shelters.lat)
        shelters.insert(0, "id", [f"S{i}" for i in range(len(shelters))])
        
    # --- origins: one per grid cell that contains road nodes ---
    step_lat = cell_km / 111.32
    step_lon = cell_km / (111.32 * math.cos(math.radians(lat0)))
    
    col = ((nodes.lon - west) // step_lon).astype(int)
    row = ((nodes.lat - south) // step_lat).astype(int)
    
    origins = []
    with rasterio.open(hand_path) as r:
        for (ci, ri), grp in nodes.groupby([col, row]):
            cw, cs = west + ci * step_lon, south + ri * step_lat
            ce, cn = cw + step_lon, cs + step_lat
            win = from_bounds(cw, cs, ce, cn, transform=r.transform)
            px = r.read(1, window=win, boundless=True, fill_value=999.0).ravel()
            px = px[np.isfinite(px)]
            if px.size == 0:
                continue
                
            clon, clat = grp.lon.mean(), grp.lat.mean()
            d = np.hypot(*(_xy(grp.lon, grp.lat, lat0) - _xy([clon], [clat], lat0)[0]).T)
            cand = grp.id.values[np.argsort(d)][:60]
            
            origins.append({
                "id": f"O{ci}_{ri}", "lon": round(float(clon), 5), "lat": round(float(clat), 5),
                "population": int(people_per_node * len(grp)),
                "candidates": [int(c) for c in cand],
                "hand_pct": [round(float(v), 2) for v in np.percentile(px, range(101))],
            })
            
    with rasterio.open(hand_path) as r:
        b = r.bounds
        meta = {"bbox": list(bbox), "raster_bounds": [b.left, b.bottom, b.right, b.top],
                "cell_km": cell_km, "people_per_node": people_per_node,
                "n_nodes": len(nodes), "n_edges": len(edges), "n_shelters": len(shelters),
                "n_origins": len(origins)}
                
    nodes.to_csv(f"{out_dir}/nodes.csv", index=False)
    edges.to_csv(f"{out_dir}/edges.csv", index=False)
    shelters.to_csv(f"{out_dir}/shelters.csv", index=False)
    json.dump(origins, open(f"{out_dir}/origins.json", "w"))
    json.dump(meta, open(f"{out_dir}/meta.json", "w"), indent=2)
    return meta
