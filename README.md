# JALREKHA: What-If Flood & Evacuation Digital Twin

<div align="center">
  <img src="docs/data/water/water_5.0.png" alt="JALREKHA Architecture" width="100%" />
</div>

**JALREKHA** is a high-performance, interactive digital twin designed for dynamic flood modeling and optimized evacuation routing. Built to handle catastrophic scenarios where static mapping fails, JALREKHA computes mathematical network failures on the fly—rendering flooded topographies, identifying isolated populations, and optimizing shelter capacities in real-time.

---

## 🚀 Key Features

* **Dynamic Network Shattering:** As flood levels rise, inundated road segments are mathematically pruned from the routing graph, dynamically isolating neighborhoods into boat/helicopter rescue zones.
* **Algorithmic Evacuation Planning:** Replaces naive "closest shelter" routing with a directed **Min-Cost Flow algorithm**, ensuring strict shelter capacity constraints and preventing overcrowding.
* **Serverless 60FPS WebGL:** Pre-computes massive geospatial models into ultra-lightweight JSON arrays and RGBA Alpha-channel PNGs, enabling instantaneous 3D rendering via MapLibre GL JS on the edge.
* **Live River Forecasting:** Integrates directly with the Open-Meteo Flood API (GloFAS), fetching 7-day river discharge forecasts and automatically shifting the engine's predictive scenario to match.

---

## 🏗 System Architecture

The project is structured as a full-stack algorithmic pipeline consisting of a data preprocessing engine, a REST API, and a WebGL frontend.

### 1. Geospatial Data Pipeline (`engine/`)
The foundation of JALREKHA is its ability to translate raw satellite data into a lightweight routing schema.
- **Topographical Modeling (HAND):** We ingest **Copernicus GLO-30 DEM** (Digital Elevation Model) from AWS Open Data. Using `pysheds`, we perform depression filling, resolve topological flats, calculate D8 flow directions, and compute **HAND** (Height Above Nearest Drainage) without requiring heavy, time-consuming 2D hydrodynamic models.
- **Infrastructure Ingestion:** Drivable networks and building footprints (schools, hospitals, community centers) are extracted dynamically via `OSMnx` and mapped into optimized adjacency matrices.

### 2. Optimization Engine (`engine/scenario.py`)
At the core of the system is the evacuation router. For a given flood level $h$:
- **Graph Pruning:** Any node where $HAND \le h$ is removed. 
- **Min-Cost Flow Routing:** The surviving topology is loaded into a `NetworkX` directed graph. Grid cells act as supply nodes, while shelters act as demand sinks with strict capacities. 
- **Overflow Penalty:** Populations unable to reach a shelter—either due to severed roads or full capacities—are routed to a virtual `OVERFLOW` sink with a massive cost penalty, allowing the system to flag critical rescue zones.

### 3. Serverless Edge API & Client (`backend/` & `docs/`)
- **FastAPI Backend:** Serves the algorithm dynamically. Generates caching layers for computed routes and streams pre-rendered water-depth PNGs to the client.
- **MapLibre GL Frontend:** A vanilla JS, zero-dependency client that drapes OpenStreetMap and our routing vectors over a 3D terrain mesh.

---

## 🛠 Installation & Local Development

This project uses modern Python packaging.

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or standard `pip`

### Setup
```bash
# 1. Clone the repository
git clone https://github.com/your-username/JALREKHAv1.git
cd JALREKHAv1

# 2. Set up the virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the Data Pipeline
To pre-compute all HAND models, build the optimized graphs, and generate the static JSON scenarios for the UI:
```bash
python run_pipeline.py
```
*(Note: Ensure your `config.json` bounding box and target city are configured correctly).*

### Running the Vercel API Locally
```bash
cd backend
uvicorn app:app --reload --port 7860
```
Navigate to `http://localhost:7860/health` to verify the API status.

---

## 📊 Limitations & Considerations

While highly sophisticated, JALREKHA is a *planning twin* and not a hydrodynamically calibrated flood forecast:
- **Surface Topology Limitations:** The Copernicus DEM is a surface model. Extremely dense urban canopies or heavy structural layouts may artificially raise elevation profiles.
- **Bathtub Indexing:** HAND assumes uniform water distribution across a plane. It does not calculate complex fluid dynamics like backwater effects or drain-capacity overflows.
- **Capacity Proxies:** Default shelter capacities are heuristic assumptions (e.g., Schools = 300, Hospitals = 100) and must be calibrated with municipal data for production deployment.

## 📄 License & Credits

- **Codebase License:** MIT License.
- **Copernicus DEM GLO-30:** © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018.
- **Infrastructure Data:** © OpenStreetMap contributors, ODbL.
- **River Discharge Forecast:** Weather data by Open-Meteo.com (CC BY 4.0), GloFAS / Copernicus EMS.

> **AI Disclosure:** Portions of this project’s architecture implementation and boilerplate code generation were accelerated using AI assistance to ensure rapid prototyping and optimization during the development lifecycle. 
