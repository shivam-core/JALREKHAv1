"""Step 1: DEM -> HAND (Height Above Nearest Drainage)."""
import math
import numpy as np
import rasterio
from rasterio.merge import merge
from scipy.ndimage import distance_transform_edt
from rasterio.windows import from_bounds
from rasterio.features import rasterize
# pysheds 0.5 still calls np.in1d, which newer NumPy (2.4+) removed. Small compatibility shim:
if not hasattr(np, "in1d"):
    np.in1d = lambda ar1, ar2, **kw: np.isin(np.asarray(ar1).ravel(), ar2, **kw)

from pysheds.grid import Grid  # noqa: E402
from pysheds.sview import Raster  # noqa: E402

DIRMAP = (64, 128, 1, 2, 4, 8, 16, 32)

def dem_tile_urls(bounds):
    """Copernicus GLO-30 tile URLs (AWS Open Data, no account) covering (west, south, east, north)."""
    west, south, east, north = bounds
    urls = []
    for lat in range(math.floor(south), math.floor(north - 1e-9) + 1):
        for lon in range(math.floor(west), math.floor(east - 1e-9) + 1):
            ns = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00"
            ew = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00"
            name = f"Copernicus_DSM_COG_10_{ns}_{ew}_DEM"
            urls.append(f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif")
    return urls

def crop_dem(sources, bounds, out_path):
    """Read only the window we need from one or more DEM tiles and save one local GeoTIFF."""
    datasets = [rasterio.open(s) for s in sources]
    try:
        data, transform = merge(datasets, bounds=bounds, nodata=-9999)
        profile = datasets[0].profile.copy()
        gaps = data[0] == -9999          # e.g. a 1-pixel strip at a tile edge
        if gaps.any():                   # fill each gap with its nearest real elevation
            idx = distance_transform_edt(gaps, return_distances=False, return_indices=True)
            data[0] = data[0][tuple(idx)]
    finally:
        for d in datasets:
            d.close()
    
    profile.update(driver="GTiff", height=data.shape[1], width=data.shape[2], count=1, nodata=None,
                   transform=transform, compress="deflate", tiled=False)
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data[0], 1)
    return data.shape[1:]

def compute_hand(dem_path, stream_threshold=2000, river_lines=None):
    """Return (hand_array, acc_array, streams_mask, transform, crs).
    
    stream_threshold: number of upstream cells needed to call a cell 'drainage'.
    river_lines: optional list of shapely lines (OSM rivers) burned into the mask.
    """
    grid = Grid.from_raster(dem_path)
    dem = grid.read_raster(dem_path)
    pit_filled = grid.fill_pits(dem)
    flooded = grid.fill_depressions(pit_filled)
    inflated = grid.resolve_flats(flooded)
    
    fdir = grid.flowdir(inflated, dirmap=DIRMAP)
    acc = grid.accumulation(fdir, dirmap=DIRMAP)
    
    streams = np.asarray(acc) > stream_threshold
    
    if river_lines:
        burned = rasterize([(g, 1) for g in river_lines], out_shape=streams.shape,
                           transform=dem.affine, fill=0, dtype="uint8").astype(bool)
        streams = streams | burned
        
    mask = Raster(streams.astype(bool), viewfinder=acc.viewfinder)  # pysheds wants a Raster
    
    hand = grid.compute_hand(fdir, inflated, mask, dirmap=DIRMAP)
    hand = np.asarray(hand, dtype="float32")
    hand[~np.isfinite(hand)] = 999.0  # cells that never reach a drain: never flood
    hand[hand < 0] = 0.0
    
    return hand, np.asarray(acc), streams, dem.affine, dem.crs

def save_cropped(array, transform, crs, bounds, out_path):
    """Crop an array (same grid as the DEM) to the study bbox and save as GeoTIFF."""
    h, w = array.shape
    tmp = rasterio.io.MemoryFile()
    with tmp.open(driver="GTiff", height=h, width=w, count=1, dtype="float32",
                  crs=crs, transform=transform) as ds:
        ds.write(array.astype("float32"), 1)
        win = from_bounds(*bounds, transform=transform).round_offsets().round_lengths()
        out = ds.read(1, window=win)
        out_tf = ds.window_transform(win)
        
    with rasterio.open(out_path, "w", driver="GTiff", height=out.shape[0], width=out.shape[1],
                       count=1, dtype="float32", crs=crs, transform=out_tf,
                       compress="deflate") as dst:
        dst.write(out, 1)
        
    return out.shape
