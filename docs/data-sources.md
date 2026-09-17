# Data Sources & Provenance

- **Elevation (DEM):** Copernicus GLO-30 Cloud Optimized GeoTIFFs (via AWS s3 public registry). Preprocessed with Pysheds to compute Height Above Nearest Drainage (HAND).
- **Roads & Waterways:** OpenStreetMap (via OSMnx). Bounded to the study area.
- **Candidate Shelters:** Assumed manually or mapped from OpenStreetMap nodes for the purpose of the scenario.
- **Population:** Assumed scenario values assigned to origins.
- **Basemap:** OpenStreetMap tiles via MapLibre GL JS.

## Licences
- Application Code: MIT (or team's chosen license)
- OpenStreetMap data is &copy; OpenStreetMap contributors, licensed under ODbL.
- Copernicus DEM data is provided openly with Copernicus open data policy.
