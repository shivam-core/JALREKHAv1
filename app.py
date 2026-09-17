from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Optional
import json

from engine.load import load_all_data, get_data
from engine.allocate import allocate_shelters

app = FastAPI(title="JALREKHAv1 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"

@app.on_event("startup")
def startup_event():
    try:
        load_all_data(DATA_DIR)
    except FileNotFoundError:
        print("Data files not found. Run prep scripts.")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/meta")
def get_meta():
    d = get_data()
    return d.get("manifest", {
        "bounds": {"west": 73.845, "south": 18.505, "east": 73.895, "north": 18.550},
        "levels": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        "data_version": "v1-demo"
    })

class ScenarioRequest(BaseModel):
    level_m: float = 0.0
    closed_edge_ids: List[str] = []
    shelter_overrides: Dict[str, dict] = {}

def compute_scenario(req: ScenarioRequest):
    d = get_data()
    if not d.get("network"):
        raise HTTPException(status_code=503, detail="Data not loaded")
        
    level_str = str(float(req.level_m))
    hazards = d["hazards"].get("scenarios", {})
    if level_str not in hazards:
        # Default to 0.0 or closest if needed, but for now raise
        if "0.0" in hazards:
            level_str = "0.0"
        else:
            raise HTTPException(status_code=400, detail="Invalid level")
            
    hazard_scenario = hazards[level_str]
    
    alloc_result = allocate_shelters(
        d["network"], 
        d["locations"], 
        hazard_scenario, 
        req.closed_edge_ids, 
        req.shelter_overrides
    )
    
    # Calculate deltas
    b_alloc = alloc_result["baseline"]["totals"]["allocated"]
    o_alloc = alloc_result["totals"]["allocated"]
    
    b_cost = sum(a["travel_seconds"] * a["people"] for a in alloc_result["baseline"]["allocations"])
    o_cost = sum(a["travel_seconds"] * a["people"] for a in alloc_result["allocations"])
    
    # We populate the response
    res = {
        "schema_version": "1.0",
        "dataset_version": d["manifest"].get("dataset_version", "v1"),
        "scenario_id": f"custom",
        "input": req.dict(),
        "hazard": hazard_scenario,
        "origins": d["locations"]["origins"],
        "shelters": d["locations"]["shelters"],
        "allocations": alloc_result["allocations"],
        "totals": alloc_result["totals"],
        "baseline": alloc_result["baseline"],
        "comparison": {
            "allocated_delta": o_alloc - b_alloc,
            "travel_time_delta": o_cost - b_cost,
            "interpretation": "Computed from graph."
        },
        "assumptions": ["Scenario computed dynamically"]
    }
    return res

@app.get("/api/scenario")
def default_scenario(h: float = 0.0):
    req = ScenarioRequest(level_m=h)
    return compute_scenario(req)

@app.post("/api/scenario")
def custom_scenario(payload: ScenarioRequest):
    return compute_scenario(payload)

