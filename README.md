# JALREKHA - what-if flood & evacuation twin

Drag the water level: streets flood on real terrain, drowned roads drop out of the
road graph, people are re-assigned to shelters with capacity limits, and routes re-plan.

**Live demo:** https://shivam-core.github.io/jalrekha/
**API:** https://shivam-core-jalrekha-api.hf.space/health

## How it works
1. Copernicus GLO-30 DEM -> pysheds -> HAND (height above nearest drainage).
2. Water level h floods every cell with HAND <= h.
3. OpenStreetMap roads (OSMnx): a road node with HAND <= h is removed.
4. Dijkstra finds reachable shelters; min-cost-flow assigns people within capacity.
5. MapLibre GL JS shows water, cut roads, routes and shelter loads in 3-D.

## Run it again
Open the notebooks in Google Colab in order: 00 -> 05. See `notes/method.md`.

## Limitations (read before judging)
See `notes/limitations.md`. This is a planning twin, not a flood forecast.

## Data credits
See `notes/data-credits.md`. Code: MIT licence.
