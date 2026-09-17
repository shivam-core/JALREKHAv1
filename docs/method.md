# Method

JALREKHA evaluates disaster scenarios by examining the intersection of an assumed localized flood state and an open road network, and routing impacted populations to limited shelter capacity.

## Hydrology (HAND)
Height Above Nearest Drainage (HAND) normalizes local topography against the river network. 
1. The DEM is pit-filled, depressions are resolved.
2. Flow directions and accumulations are calculated.
3. The main river network is extracted based on a cell accumulation threshold.
4. Vertical distance to the nearest drainage is calculated for each cell.
5. In scenarios, a specific water level (e.g. 1.5m) is applied. Any cell with HAND <= 1.5m is classified as flooded.

## Graph & Allocations
1. The road network is imported as a directed graph. Edge traversal times are derived from speed limits.
2. Edges that intersect flooded cells are marked as unavailable in the graph.
3. The optimizer runs a Max-Flow Min-Cost algorithm (bipartite matching) to allocate assumed populations at predefined origins to candidate shelters up to their stated capacity, minimizing overall travel time.
