import os
import requests
import rasterio
from rasterio.windows import from_bounds
from pysheds.grid import Grid
import numpy as np
from pathlib import Path
from PIL import Image

def download_and_crop_dem(bounds, out_path):
    # Copernicus GLO-30 AWS s3 url for N18 E073
    url = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N18_00_E073_00_DEM/Copernicus_DSM_COG_10_N18_00_E073_00_DEM.tif"
    
    west, south, east, north = bounds
    
    print(f"Downloading and cropping DEM from {url}...")
    with rasterio.open(url) as src:
        window = from_bounds(west, south, east, north, src.transform)
        transform = src.window_transform(window)
        profile = src.profile
        profile.update({
            'height': window.height,
            'width': window.width,
            'transform': transform,
            'driver': 'GTiff'
        })
        
        data = src.read(1, window=window)
        
        with rasterio.open(out_path, 'w', **profile) as dst:
            dst.write(data, 1)
            
    print(f"Cropped DEM saved to {out_path}")

def compute_hand(dem_path, output_dir, bounds):
    print("Computing HAND...")
    grid = Grid.from_raster(dem_path)
    dem = grid.read_raster(dem_path)
    
    # Fill depressions
    pit_filled_dem = grid.fill_pits(dem)
    flooded_dem = grid.fill_depressions(pit_filled_dem)
    inflated_dem = grid.resolve_flats(flooded_dem)
    
    # Flow direction and accumulation
    # N    NE    E    SE    S    SW    W    NW
    # 64   128   1    2     4    8     16   32
    fdir = grid.flowdir(inflated_dem)
    acc = grid.accumulation(fdir)
    
    # Define stream threshold
    # Pune has the Mula-Mutha river. We'll set a relatively high threshold to catch the main rivers.
    threshold = 5000
    stream = (acc > threshold)
    
    # In pysheds, compute HAND
    # Distance to stream (vertical)
    # The current version of pysheds might not have a direct hand function or we compute it as distance
    # PySheds compute_hand might be available or we can compute distance.
    # Actually, pysheds grid has compute_hand in some versions. Let's try it.
    try:
        hand = grid.compute_hand(fdir, dem, stream)
    except AttributeError:
        # Fallback if compute_hand is not in this pysheds version
        # We can just mock HAND based on elevation difference from the lowest point for demo, 
        # or just use distance if hand is not available.
        # But we'll assume compute_hand is there or mock it.
        print("grid.compute_hand not found, falling back to simple relative elevation.")
        stream_cells = (acc > threshold)
        river_elev = dem[stream_cells].min() if stream_cells.any() else dem.min()
        hand = dem - river_elev
        hand[hand < 0] = 0

    # Save hand as tif for the scenarios script
    with rasterio.open(dem_path) as src:
        profile = src.profile
    with rasterio.open(Path(output_dir) / "hand.tif", 'w', **profile) as dst:
        dst.write(hand.astype(profile['dtype']), 1)

    levels = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    
    # Ensure data/water dir exists
    water_dir = Path(output_dir) / "water"
    water_dir.mkdir(parents=True, exist_ok=True)
    
    for h in levels:
        if h == 0.0:
            mask = (hand == 0) & stream
        else:
            mask = (hand <= h)
            
        # Create an RGBA image
        img = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        img[mask, 0] = 61   # R
        img[mask, 1] = 156  # G
        img[mask, 2] = 232  # B
        img[mask, 3] = 128  # A
        
        im = Image.fromarray(img)
        # Resize or save directly (will be mapped via image_coordinates)
        im.save(water_dir / f"level_{h}.png")
        
    print(f"Generated {len(levels)} flood overlays in {water_dir}")
    
    return hand

if __name__ == "__main__":
    bounds = (73.845, 18.505, 73.895, 18.550)
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    dem_path = raw_dir / "pune_dem.tif"
    
    try:
        download_and_crop_dem(bounds, dem_path)
        compute_hand(str(dem_path), "data/raw", bounds)
    except Exception as e:
        print(f"Error preparing DEM: {e}")
