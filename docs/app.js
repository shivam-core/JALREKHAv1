const CFG = window.JALREKHA_CONFIG;
const $ = (id) => document.getElementById(id);
let map, meta, lastResult = null, plan = "opt";

// ---------- data loading (API first, static files as fallback) ----------
async function fetchJSON(url, timeoutMs = 10000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { signal: ctrl.signal });
    if (!r.ok) throw new Error(r.status + " " + url);
    return await r.json();
  } finally { clearTimeout(t); }
}

async function loadScenario(h) {
  const name = h.toFixed(1);
  if (CFG.API_URL) {
    try {
      const data = await fetchJSON(`${CFG.API_URL}/scenario?h=${name}`);
      setSource(true);
      return { data, waterUrl: `${CFG.API_URL}/water?h=${name}` };
    } catch (e) { console.warn("API failed, using static files", e); }
  }
  setSource(false);
  const snapped = (Math.round(h * 2) / 2).toFixed(1);  // static files exist every 0.5 m
  return { data: await fetchJSON(`data/levels/level_${snapped}.json`),
           waterUrl: `data/water/water_${snapped}.png` };
}

function setSource(live) {
  $("source").textContent = live ? "live API" : "static data";
  $("source").className = "badge" + (live ? " live" : "");
}

// ---------- GeoJSON builders ----------
const fc = (features) => ({ type: "FeatureCollection", features });

const cutGeo = (d) => fc(d.cut_roads.map((c) => ({ type: "Feature", properties: {},
  geometry: { type: "LineString", coordinates: c } })));

const routeGeo = (d) => fc(d.routes.map((r) => ({ type: "Feature",
  properties: { people: r.people, minutes: r.minutes, shelter: r.shelter },
  geometry: { type: "LineString", coordinates: r.path } })));

const originGeo = (d) => fc(d.origins.map((o) => ({ type: "Feature",
  properties: { people: o.people, status: o.status },
  geometry: { type: "Point", coordinates: [o.lon, o.lat] } })));

const shelterGeo = (d) => fc(d.shelters.map((s) => ({ type: "Feature",
  properties: { ...s, pct: plan === "opt" ? s.pct_opt : s.pct_naive,
                load: plan === "opt" ? s.load_opt : s.load_naive },
  geometry: { type: "Point", coordinates: [s.lon, s.lat] } })));

// ---------- map setup ----------
function addTerrain() {
  if (!CFG.TERRAIN) return;
  const tiles = ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"];
  map.addSource("dem", { type: "raster-dem", tiles, tileSize: 256, encoding: "terrarium", maxzoom: 14 });
  map.addSource("dem-hs", { type: "raster-dem", tiles, tileSize: 256, encoding: "terrarium", maxzoom: 14 });
  map.addLayer({ id: "hillshade", type: "hillshade", source: "dem-hs",
                 paint: { "hillshade-exaggeration": 0.5 } });
  map.setTerrain({ source: "dem", exaggeration: CFG.TERRAIN_EXAGGERATION });
}

function addLayers() {
  const [w, s, e, n] = meta.water_bounds;
  map.addSource("water", { type: "image", url: "data/water/water_0.0.png",
                           coordinates: [[w, n], [e, n], [e, s], [w, s]] });
  map.addLayer({ id: "water", type: "raster", source: "water",
                 paint: { "raster-opacity": 0.85, "raster-fade-duration": 0 } });
                 
  for (const id of ["cut", "routes", "origins", "shelters"]) map.addSource(id, { type: "geojson", data: fc([]) });
  
  map.addLayer({ id: "cut", type: "line", source: "cut",
                 paint: { "line-color": "#ff4d4d", "line-width": 2, "line-dasharray": [2, 1.5] } });
                 
  map.addLayer({ id: "routes", type: "line", source: "routes", layout: { "line-cap": "round" },
                 paint: { "line-color": "#ffd33d", "line-opacity": 0.9,
                          "line-width": ["interpolate", ["linear"], ["get", "people"], 0, 1.5, 1000, 6] } });
                          
  map.addLayer({ id: "origins", type: "circle", source: "origins",
                 paint: { "circle-radius": 5, "circle-stroke-width": 1, "circle-stroke-color": "#000",
                          "circle-color": ["match", ["get", "status"], "ok", "#ff9f1c",
                                           "isolated", "#e040fb", "#ff4d4d"] } });
                                           
  map.addLayer({ id: "shelters", type: "circle", source: "shelters",
                 paint: { "circle-radius": ["interpolate", ["linear"], ["get", "capacity"], 100, 6, 800, 14],
                          "circle-stroke-width": 2, "circle-stroke-color": "#fff",
                          "circle-color": ["case", ["!", ["get", "usable"]], "#6e7681",
                                           [">", ["get", "pct"], 100], "#ff4d4d",
                                           [">", ["get", "pct"], 80], "#f0b429", "#2ea043"] } });

  map.on("click", "shelters", (ev) => {
    const p = ev.features[0].properties;
    new maplibregl.Popup().setLngLat(ev.lngLat).setHTML(
      `<b>${p.name}</b> (${p.kind})<br>${p.usable === true || p.usable === "true" ? "" : "<b>FLOODED - unusable</b><br>"}` +
      `Load: ${p.load} / ${p.capacity} people (${p.pct}%)`).addTo(map);
  });
  
  map.on("click", "routes", (ev) => {
    const p = ev.features[0].properties;
    new maplibregl.Popup().setLngLat(ev.lngLat)
      .setHTML(`${p.people} people → ${p.shelter}<br>${p.minutes} min by road`).addTo(map);
  });
}

// ---------- update everything for a level ----------
async function setLevel(h) {
  $("loading").style.display = "block";
  try {
    const { data, waterUrl } = await loadScenario(h);
    lastResult = data;
    const [w, s, e, n] = meta.water_bounds;
    map.getSource("water").updateImage({ url: waterUrl, coordinates: [[w, n], [e, n], [e, s], [w, s]] });
    map.getSource("cut").setData(cutGeo(data));
    map.getSource("routes").setData(routeGeo(data));
    map.getSource("origins").setData(originGeo(data));
    map.getSource("shelters").setData(shelterGeo(data));
    updatePanel(data);
  } catch (e) {
    $("alert").textContent = "Could not load this level: " + e.message;
  } finally { $("loading").style.display = "none"; }
}

function updatePanel(d) {
  const t = d.totals, fmt = (x) => x.toLocaleString("en-IN");
  $("levelText").textContent = d.level.toFixed(1);
  $("sRisk").textContent = fmt(t.people_at_risk);
  $("sAssigned").textContent = fmt(t.assigned);
  $("sUnassigned").textContent = fmt(t.unassigned);
  $("sIsolated").textContent = fmt(t.isolated);
  $("sCut").textContent = fmt(t.roads_cut);
  $("sShelters").textContent = fmt(t.shelters_usable);
  
  const over = d.shelters.filter((s) => s.usable && (plan === "opt" ? s.pct_opt : s.pct_naive) > 100).length;
  const msgs = [];
  if (t.isolated > 0) msgs.push(`${fmt(t.isolated)} people have no dry road out → boat / helicopter zone`);
  if (over > 0) msgs.push(`${over} shelter(s) over capacity`);
  $("alert").textContent = msgs.join(" · ");
}

// ---------- river forecast (Open-Meteo Flood API, GloFAS) ----------
function levelFromDischarge(q) {
  const d = meta.discharge;
  if (!d || d.q_max <= d.q_median) return 0;
  const lvl = CFG.MAX_LEVEL * (q - d.q_median) / (d.q_max - d.q_median);
  return Math.min(CFG.MAX_LEVEL, Math.max(0, Math.round(lvl * 2) / 2));
}

async function loadForecast() {
  const p = CFG.RIVER_POINT;
  const url = `https://flood-api.open-meteo.com/v1/flood?latitude=${p.lat}&longitude=${p.lon}` +
              `&daily=river_discharge&forecast_days=7`;
  try {
    const j = await fetchJSON(url);
    const box = $("forecast"); box.innerHTML = "";
    j.daily.time.forEach((day, i) => {
      const q = j.daily.river_discharge[i], lvl = levelFromDischarge(q);
      const el = document.createElement("div");
      el.className = "day";
      el.innerHTML = `${day.slice(5)}<br>${Math.round(q)} m³/s<br><b>${lvl.toFixed(1)} m</b>`;
      el.onclick = () => { $("slider").value = lvl; setLevel(lvl); };
      box.appendChild(el);
    });
    const maxLvl = Math.max(...j.daily.river_discharge.map(levelFromDischarge));
    $("slider").value = maxLvl; setLevel(maxLvl);
  } catch (e) {
    $("forecast").textContent = "Forecast unavailable (offline?) - use the slider.";
  }
}

// ---------- start ----------
async function init() {
  meta = await fetchJSON("data/meta.json");
  const [w, s, e, n] = meta.water_bounds;
  map = new maplibregl.Map({ container: "map", style: CFG.BASEMAP,
    center: [(w + e) / 2, (s + n) / 2], zoom: 12.3, pitch: 55, bearing: -15, maxPitch: 80 });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
  
  map.on("load", async () => {
    try { addTerrain(); } catch (e) { console.warn("terrain off", e); }
    addLayers();
    $("slider").max = CFG.MAX_LEVEL;
    if (CFG.API_URL) $("slider").step = 0.1;
    await setLevel(0);
  });
  
  let timer;
  $("slider").addEventListener("input", (ev) => {
    const h = parseFloat(ev.target.value);
    $("levelText").textContent = h.toFixed(1);
    clearTimeout(timer); timer = setTimeout(() => setLevel(h), 120); // debounce
  });
  
  document.querySelectorAll("input[name=plan]").forEach((r) => r.addEventListener("change", (ev) => {
    plan = ev.target.value;
    if (lastResult) { map.getSource("shelters").setData(shelterGeo(lastResult)); updatePanel(lastResult); }
  }));
  
  $("showWater").addEventListener("change", (ev) => {
    const v = ev.target.checked ? "visible" : "none";
    ["water", "cut"].forEach((id) => map.setLayoutProperty(id, "visibility", v));
  });
  
  $("forecastBtn").addEventListener("click", loadForecast);
}

init();
