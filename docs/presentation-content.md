# Presentation Content

**Slide: Problem/User**
- **User:** Disaster planning coordinator.
- **Problem:** When flood conditions change, road closures affect access to limited shelter capacity. Need an intelligent system to optimize resource allocation.
- **AI-05 Alignment:** Develop an intelligent system for optimizing resource allocation in healthcare, education, or disaster management.

**Slide: Proposed Solution**
- **JALREKHA:** A what-if planning simulator.
- Integrates terrain analysis, graph algorithms, and constrained allocation.
- Allows dynamic toggling of flood water levels and road closures to instantly see impacts on route availability and shelter capacity.

**Slide: Architecture**
- **Frontend:** HTML, CSS, JavaScript with MapLibre GL JS (Hosted as static assets on Vercel).
- **Backend:** FastAPI with NetworkX for optimization (Hosted as Vercel Python Function).
- **Data Prep:** Python (Rasterio, PySheds, OSMnx) locally preparing static JSONs and PNG overlays to ensure the cloud function is extremely fast.

**Slide: Real vs Assumed Data**
- **Real:** Copernicus GLO-30 DEM and OpenStreetMap road networks.
- **Assumed:** Population counts at origins, shelter capacities, and relative water level scenarios.

**Slide: Algorithms & Baseline**
- **Algorithm:** Max-Flow Min-Cost optimization prioritizing maximum people sheltered, then minimizing total travel time.
- **Baseline:** Nearest-available-shelter allocation. JALREKHA matches or outperforms baseline in capacity-constrained scenarios.

**Slide: Limitations & Future Validation**
- Water levels are relative to HAND, not operational forecasts.
- Optimization uses individuals, not family units.
- Future work: Incorporate live flood gauges, demographic groupings, and specific vehicle capacities.

**Slide: Team & AI Disclosure**
- **Team:** Team Advantage
- **AI Tools Used:** Antigravity, GitHub Copilot.
