import json
import os
import numpy as np

from engine.hand import dem_tile_urls, crop_dem, compute_hand, save_cropped
from engine.graph_prep import download_roads, download_shelters, build_tables
from engine.render import save_hand_npy, export_all
from engine.scenario import Engine

if __name__ == "__main__":
    config = json.load(open("config.json"))
    bbox = config["bbox"]
    
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    hand_path = "data/processed/hand.tif"
    
    print("Step 1: DEM & HAND")
    if not os.path.exists("data/raw/dem.tif"):
        urls = dem_tile_urls(bbox)
        crop_dem(urls, bbox, "data/raw/dem.tif")
    if not os.path.exists(hand_path):
        hand, acc, streams, tf, crs = compute_hand("data/raw/dem.tif")
        save_cropped(hand, tf, crs, bbox, hand_path)
        
    print("Step 2: Roads & Shelters")
    if not os.path.exists("data/processed/meta.json"):
        G = download_roads(bbox)
        sh = download_shelters(bbox)
        build_tables(G, sh, hand_path, bbox, "data/processed", cell_km=config["cell_km"], people_per_node=config["people_per_node"])
        
    print("Step 3 & 4: Render & Export")
    if not os.path.exists("data/processed/hand.npy"):
        save_hand_npy(hand_path, "data/processed/hand.npy")
        
    eng = Engine("data/processed")
    levels = np.arange(0, 8.1, 0.5)
    export_all(eng, hand_path, "docs/data", levels)
    print("Done!")
