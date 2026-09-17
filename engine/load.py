import json
from pathlib import Path

# In-memory storage of processed data
data = {
    "network": {},
    "locations": {},
    "hazards": {},
    "manifest": {}
}

def load_all_data(data_dir: Path):
    with open(data_dir / "network.json") as f:
        data["network"] = json.load(f)
    with open(data_dir / "locations.json") as f:
        data["locations"] = json.load(f)
    with open(data_dir / "hazards.json") as f:
        data["hazards"] = json.load(f)
    with open(data_dir / "manifest.json") as f:
        data["manifest"] = json.load(f)

def get_data():
    return data
