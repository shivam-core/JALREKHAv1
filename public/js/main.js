// Basic frontend to hit the API
document.addEventListener('DOMContentLoaded', async () => {
    console.log("JALREKHA app init");
    
    const statusMsg = document.getElementById('status-message');
    const levelSlider = document.getElementById('water-level');
    const levelDisplay = document.getElementById('level-display');
    const resetBtn = document.getElementById('btn-reset');
    const exportBtn = document.getElementById('btn-export');
    const methodsBtn = document.getElementById('btn-methods');

    let map = null;
    let currentScenario = null;
    let baseMapLoaded = false;
    
    // Custom state
    let customLevel = 0.0;
    
    initMap();

    // Fetch meta
    try {
        statusMsg.innerText = "Connecting to API...";
        const health = await fetch('/api/health').then(r => r.json());
        
        statusMsg.innerText = "Loading scenario...";
        await fetchScenario(0.0);
    } catch (e) {
        console.error("API Error", e);
        statusMsg.innerText = "Error: Could not connect to API.";
    }

    levelSlider.addEventListener('input', (e) => {
        levelDisplay.innerText = e.target.value;
    });

    levelSlider.addEventListener('change', async (e) => {
        const val = parseFloat(e.target.value);
        customLevel = val;
        await fetchScenario(val);
    });

    async function fetchScenario(h) {
        statusMsg.innerText = `Updating scenario to ${h}m...`;
        try {
            const scenario = await fetch(`/api/scenario?h=${h}`).then(r => r.json());
            currentScenario = scenario;
            updateMetrics(scenario.totals);
            updateMap(scenario);
            statusMsg.innerText = "Ready.";
        } catch (err) {
            console.error(err);
            statusMsg.innerText = "Error fetching scenario.";
        }
    }

    function updateMetrics(totals) {
        if(!totals) return;
        document.getElementById('stat-pop').innerText = totals.population;
        document.getElementById('stat-alloc').innerText = totals.allocated;
        document.getElementById('stat-unalloc').innerText = totals.isolated + totals.capacity_unserved;
        document.getElementById('stat-cap').innerText = (totals.allocated + totals.capacity_unserved) || '-'; 
    }

    function initMap() {
        map = new maplibregl.Map({
            container: 'map',
            style: {
                'version': 8,
                'sources': {
                    'osm': {
                        'type': 'raster',
                        'tiles': [
                            'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'
                        ],
                        'tileSize': 256,
                        'attribution': '&copy; OpenStreetMap Contributors'
                    }
                },
                'layers': [
                    {
                        'id': 'osm-tiles',
                        'type': 'raster',
                        'source': 'osm',
                        'minzoom': 0,
                        'maxzoom': 19
                    }
                ]
            },
            center: [73.87, 18.53],
            zoom: 13
        });

        map.on('load', () => {
            baseMapLoaded = true;
            if (currentScenario) {
                updateMap(currentScenario);
            }
        });
    }

    function updateMap(scenario) {
        if (!baseMapLoaded || !map) return;

        // 1. Update Water Overlay
        const hazard = scenario.hazard;
        if (hazard) {
            const sourceId = 'water-source';
            const layerId = 'water-layer';
            if (map.getSource(sourceId)) {
                map.getSource(sourceId).updateImage({
                    url: hazard.overlay_url,
                    coordinates: hazard.image_coordinates
                });
            } else {
                map.addSource(sourceId, {
                    'type': 'image',
                    'url': hazard.overlay_url,
                    'coordinates': hazard.image_coordinates
                });
                map.addLayer({
                    'id': layerId,
                    'type': 'raster',
                    'source': sourceId,
                    'paint': {
                        'raster-opacity': 0.6
                    }
                });
            }
        }
        
        // 2. Plot Allocations
        const allocSourceId = 'alloc-source';
        const allocLayerId = 'alloc-layer';
        
        let features = [];
        if (scenario.allocations) {
            scenario.allocations.forEach(a => {
                if (a.geometry && a.geometry.length > 0) {
                    features.push({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": a.geometry
                        },
                        "properties": {
                            "people": a.people,
                            "travel": a.travel_seconds
                        }
                    });
                }
            });
        }
        
        const geojson = {
            "type": "FeatureCollection",
            "features": features
        };
        
        if (map.getSource(allocSourceId)) {
            map.getSource(allocSourceId).setData(geojson);
        } else {
            map.addSource(allocSourceId, {
                'type': 'geojson',
                'data': geojson
            });
            map.addLayer({
                'id': allocLayerId,
                'type': 'line',
                'source': allocSourceId,
                'layout': {
                    'line-join': 'round',
                    'line-cap': 'round'
                },
                'paint': {
                    'line-color': '#55D6BE',
                    'line-width': 4
                }
            });
        }
        
        // 3. Nodes (Origins / Shelters)
        const nodeSourceId = 'node-source';
        const nodeLayerId = 'node-layer';
        let nFeatures = [];
        if (scenario.origins) {
            scenario.origins.forEach(o => {
                nFeatures.push({
                    "type": "Feature",
                    "geometry": { "type": "Point", "coordinates": [o.lon, o.lat] },
                    "properties": { "type": "origin", "id": o.id }
                });
            });
        }
        if (scenario.shelters) {
            scenario.shelters.forEach(s => {
                nFeatures.push({
                    "type": "Feature",
                    "geometry": { "type": "Point", "coordinates": [s.lon, s.lat] },
                    "properties": { "type": "shelter", "id": s.id, "open": s.usable }
                });
            });
        }
        const nodeGeojson = {
            "type": "FeatureCollection",
            "features": nFeatures
        };
        if (map.getSource(nodeSourceId)) {
            map.getSource(nodeSourceId).setData(nodeGeojson);
        } else {
            map.addSource(nodeSourceId, {
                'type': 'geojson',
                'data': nodeGeojson
            });
            map.addLayer({
                'id': nodeLayerId,
                'type': 'circle',
                'source': nodeSourceId,
                'paint': {
                    'circle-radius': 6,
                    'circle-color': [
                        'match',
                        ['get', 'type'],
                        'origin', '#B5C2CA',
                        'shelter', '#74C991',
                        '#ccc'
                    ],
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#111B24'
                }
            });
        }
    }
});
