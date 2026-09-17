from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

app = FastAPI(title="JALREKHAv1 API")

# Setup CORS for development, though relative paths will be used in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/meta")
def get_meta():
    return {
        "bounds": {"west": 73.845, "south": 18.505, "east": 73.895, "north": 18.550},
        "levels_m": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        "data_version": "v1-demo"
    }

@app.get("/api/scenario")
def default_scenario(h: float = 0.0):
    # Synthetic fixture for now
    return {
        "schema_version": "1.0",
        "dataset_version": "v1-demo",
        "scenario_id": f"default_{h}",
        "input": {"level_m": h, "closed_edge_ids": [], "shelter_overrides": {}},
        "hazard": {
            "overlay_url": f"/data/water/level_{h}.png",
            "image_coordinates": [[73.845, 18.550], [73.895, 18.550], [73.895, 18.505], [73.845, 18.505]],
            "unavailable_edge_ids": [],
            "unknown_edge_ids": []
        },
        "origins": [
            {"id": "origin-1", "assumed_population": 100, "status": "usable", "allocated": 100, "unmet": 0}
        ],
        "shelters": [
            {"id": "shelter-1", "open": True, "usable": True, "capacity": 200, "allocated": 100, "remaining": 100}
        ],
        "allocations": [
            {"origin_id": "origin-1", "shelter_id": "shelter-1", "people": 100, "travel_seconds": 600, "edge_ids": ["edge-1"], "geometry": None}
        ],
        "totals": {
            "population": 100,
            "allocated": 100,
            "isolated": 0,
            "capacity_unserved": 0,
            "unknown_or_unavailable_origin": 0
        },
        "baseline": {
            "allocations": [
                {"origin_id": "origin-1", "shelter_id": "shelter-1", "people": 100, "travel_seconds": 600, "edge_ids": ["edge-1"], "geometry": None}
            ],
            "totals": {
                "population": 100,
                "allocated": 100,
                "isolated": 0,
                "capacity_unserved": 0,
                "unknown_or_unavailable_origin": 0
            }
        },
        "comparison": {
            "allocated_delta": 0,
            "travel_time_delta": 0,
            "interpretation": "Baseline and optimised are identical."
        },
        "assumptions": ["Synthetic data for health check"]
    }

@app.post("/api/scenario")
def custom_scenario(payload: dict):
    h = payload.get("level_m", 0.0)
    return default_scenario(h)
