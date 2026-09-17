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
    
    // Check health
    try {
        statusMsg.innerText = "Connecting to API...";
        const health = await fetch('/api/health').then(r => r.json());
        console.log("Health:", health);
        
        statusMsg.innerText = "Loading scenario...";
        const scenario = await fetch('/api/scenario?h=0.0').then(r => r.json());
        console.log("Scenario 0.0:", scenario);
        
        updateMetrics(scenario.totals);
        statusMsg.innerText = "Ready. (Synthetic Demo)";
        
        initMap();
    } catch (e) {
        console.error("API Error", e);
        statusMsg.innerText = "Error: Could not connect to API.";
    }

    levelSlider.addEventListener('input', (e) => {
        levelDisplay.innerText = e.target.value;
    });

    levelSlider.addEventListener('change', async (e) => {
        const val = parseFloat(e.target.value);
        statusMsg.innerText = `Updating scenario to ${val}m...`;
        try {
            const scenario = await fetch(`/api/scenario?h=${val}`).then(r => r.json());
            updateMetrics(scenario.totals);
            statusMsg.innerText = "Ready.";
        } catch (err) {
            statusMsg.innerText = "Error fetching scenario.";
        }
    });

    function updateMetrics(totals) {
        document.getElementById('stat-pop').innerText = totals.population;
        document.getElementById('stat-alloc').innerText = totals.allocated;
        document.getElementById('stat-unalloc').innerText = totals.isolated + totals.capacity_unserved;
        // Just placeholder for capacity
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
    }
});
