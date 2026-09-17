# Method
- HAND: fill pits -> fill depressions -> resolve flats -> D8 flow direction -> flow accumulation
-> drainage mask (accumulation > threshold, plus OSM rivers burned in) -> compute_hand.
- Inundation(h) = all cells with HAND <= h. Depth = h - HAND.
- Road cut: a road node whose HAND <= h is removed; every edge touching it is "cut".
- Neighbourhoods: 1 km grid cells. People at risk = population x share of the cell under water.
- Start node: nearest dry road node inside the cell. None -> "isolated" (boat/helicopter zone).
- Routing: Dijkstra on travel time, max 45 minutes, up to 8 nearest shelters per cell.
- Assignment: min-cost-flow (networkx). Shelter capacity is a hard limit; people who do not fit
go to an OVERFLOW node and are reported as "no shelter space".
- Naive plan (for comparison): everyone goes to the nearest shelter, ignoring capacity.
- River forecast: Open-Meteo Flood API (GloFAS). Level = 8 m x (Q - median) / (max - median),
clipped to 0-8 m. This is a demo heuristic, NOT a calibrated rating curve.
