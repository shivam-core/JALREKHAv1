"""Step 4: pre-render water images and scenario JSON for every level (for the website)."""
import json
import os
import numpy as np
import rasterio
from PIL import Image

def level_name(h):
    return f"{h:.1f}"

def water_rgba(hand, h):
    """HAND array + water level -> RGBA image (deeper water = more opaque blue)."""
    depth = h - hand
    wet = depth >= 0
    rgba = np.zeros(hand.shape + (4,), dtype="uint8")
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 30, 144, 255
    rgba[..., 3] = np.where(wet, np.clip(90 + depth * 40, 90, 220), 0).astype("uint8")
    return Image.fromarray(rgba, "RGBA")

def water_png(hand_path, h, out_path):
    with rasterio.open(hand_path) as r:
        hand = r.read(1)
        b = r.bounds
        water_rgba(hand, h).save(out_path, optimize=True)
        return [b.left, b.bottom, b.right, b.top]

def save_hand_npy(hand_path, out_path):
    """Compact copy of HAND for the backend (no rasterio needed there)."""
    with rasterio.open(hand_path) as r:
        np.save(out_path, r.read(1).astype("float32"))

def export_all(engine, hand_path, site_data_dir, levels, extra=None):
    os.makedirs(f"{site_data_dir}/levels", exist_ok=True)
    os.makedirs(f"{site_data_dir}/water", exist_ok=True)
    
    summary = []
    for h in levels:
        name = level_name(h)
        bounds = water_png(hand_path, h, f"{site_data_dir}/water/water_{name}.png")
        result = engine.run(h)
        
        with open(f"{site_data_dir}/levels/level_{name}.json", "w") as f:
            json.dump(result, f, separators=(",", ":"))
            
        summary.append({"level": h, **result["totals"]})
        print(f"h={name} m ->", result["totals"])
        
    meta = {**engine.meta, "levels": [level_name(h) for h in levels],
            "water_bounds": bounds, "summary": summary, **(extra or {})}
            
    with open(f"{site_data_dir}/meta.json", "w") as f:
        json.dump(meta, f, indent=1)
        
    return meta
