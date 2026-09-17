"""JALREKHA API - live scenarios for any water level (runs on Hugging Face Spaces)."""
import os
import sys
from functools import lru_cache
from pathlib import Path
import io

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))          # on the Space: engine/ sits next to app.py
sys.path.insert(0, str(HERE.parent))   # in the repo: engine/ sits one level up
from engine.scenario import Engine     # noqa: E402

DATA_DIR = os.getenv("DATA_DIR") or (
    str(HERE / "data") if (HERE / "data").exists() else str(HERE.parent / "data" / "processed"))

app = FastAPI(title="JALREKHA API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

engine = Engine(DATA_DIR)
HAND = np.load(f"{DATA_DIR}/hand.npy")

def water_rgba(hand, h):  # same colours as engine/render.py (kept here so rasterio is not needed)
    depth = h - hand
    rgba = np.zeros(hand.shape + (4,), dtype="uint8")
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 30, 144, 255
    rgba[..., 3] = np.where(depth >= 0, np.clip(90 + depth * 40, 90, 220), 0).astype("uint8")
    return Image.fromarray(rgba, "RGBA")

@lru_cache(maxsize=128)
def cached(level_tenths: int):
    return engine.run(level_tenths / 10)

@app.get("/health")
def health():
    return {"status": "ok", "nodes": len(engine.nodes), "shelters": len(engine.shelters)}

@app.get("/meta")
def meta():
    return engine.meta

@app.get("/scenario")
def scenario(h: float):
    if not 0 <= h <= 15:
        raise HTTPException(400, "h must be between 0 and 15 metres")
    return cached(int(round(h * 10)))

@lru_cache(maxsize=64)
def water_bytes(level_tenths: int):
    buf = io.BytesIO()
    water_rgba(HAND, level_tenths / 10).save(buf, format="PNG", optimize=True)
    return buf.getvalue()

@app.get("/water")
def water(h: float):
    if not 0 <= h <= 15:
        raise HTTPException(400, "h must be between 0 and 15 metres")
    return Response(water_bytes(int(round(h * 10))), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"})
