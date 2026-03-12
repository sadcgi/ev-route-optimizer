/* ── EV Route Optimiser – Frontend ─────────────────────────────────────────── */

'use strict';

// ── Map initialisation ───────────────────────────────────────────────────────

const map = L.map('map', {
  center: [54.0, -2.5],
  zoom: 6,
  zoomControl: true,
});

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
    '&copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

// Layer groups so we can clear them between routes
const layerRoute    = L.layerGroup().addTo(map);
const layerMarkers  = L.layerGroup().addTo(map);
const layerNearby   = L.layerGroup().addTo(map);
const layerAll      = L.layerGroup().addTo(map);   // background stations

// State
let allStationsLoaded = false;

// ── Vehicle range hints ──────────────────────────────────────────────────────

const VEHICLE_HINTS = [
  { max: 100,  label: 'Short city hop' },
  { max: 160,  label: 'Renault Zoe / Vauxhall Corsa-e ≈ 150 km' },
  { max: 230,  label: 'Nissan Leaf 40 kWh ≈ 200 km' },
  { max: 280,  label: 'VW ID.3 Pro ≈ 260 km' },
  { max: 340,  label: 'Tesla Model 3 Long Range ≈ 300 km' },
  { max: 420,  label: 'Tesla Model S / Mercedes EQS ≈ 380 km' },
  { max: 520,  label: 'Tesla Model S Plaid ≈ 500 km' },
  { max: Infinity, label: 'Exceptional range – long-haul capable' },
];

function vehicleHint(km) {
  return VEHICLE_HINTS.find(v => km <= v.max)?.label ?? '';
}

// ── Range slider ─────────────────────────────────────────────────────────────

const rangeSlider  = document.getElementById('range-slider');
const rangeDisplay = document.getElementById('range-display');
const sliderFill   = document.getElementById('slider-fill');
const vehicleHintEl= document.getElementById('vehicle-hint');

function updateSlider() {
  const min = +rangeSlider.min;
  const max = +rangeSlider.max;
  const val = +rangeSlider.value;
  const pct = ((val - min) / (max - min)) * 100;

  rangeDisplay.textContent = val;
  sliderFill.style.width   = `${pct}%`;
  vehicleHintEl.textContent = vehicleHint(val);
}

rangeSlider.addEventListener('input', updateSlider);
updateSlider(); // initialise

// ── Keyboard shortcut: Enter in any input fires planRoute ────────────────────

['input-start', 'input-end'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') planRoute();
  });
});

// ── Marker helpers ───────────────────────────────────────────────────────────

function makeStartIcon() {
  return L.divIcon({
    html: `<div class="marker-pin marker-start">
             <svg viewBox="0 0 20 20" fill="white">
               <path d="M10 18s-7-6.686-7-10a7 7 0 1114 0c0 3.314-7 10-7 10z"/>
               <circle cx="10" cy="8" r="2.5" fill="#040810"/>
             </svg>
           </div>`,
    className: '',
    iconSize:  [36, 36],
    iconAnchor:[18, 36],
    popupAnchor:[0, -38],
  });
}

function makeEndIcon() {
  return L.divIcon({
    html: `<div class="marker-pin marker-end">
             <svg viewBox="0 0 20 20" fill="white">
               <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"/>
             </svg>
           </div>`,
    className: '',
    iconSize:  [36, 36],
    iconAnchor:[18, 36],
    popupAnchor:[0, -38],
  });
}

function makeStopIcon(number) {
  return L.divIcon({
    html: `<div class="marker-stop">
             <svg viewBox="0 0 20 20" fill="currentColor" style="width:14px;height:14px">
               <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"/>
             </svg>
           </div>`,
    className: '',
    iconSize:  [32, 32],
    iconAnchor:[16, 16],
    popupAnchor:[0, -20],
  });
}

function makeNearbyIcon() {
  return L.divIcon({
    html: '<div class="marker-nearby-dot"></div>',
    className: '',
    iconSize:  [10, 10],
    iconAnchor:[5, 5],
    popupAnchor:[0, -8],
  });
}

// ── Popup builder ─────────────────────────────────────────────────────────────

function stationPopup(s, isStop = false, stopNum = null) {
  const connectors = (s.connectors || [])
    .map(c => `<span class="connector-chip">${c}</span>`)
    .join('');

  const accentColour = isStop ? '#f59e0b' : '#38bdf8';
  const stopBadge    = isStop
    ? `<div class="popup-row" style="color:${accentColour}">
         <svg viewBox="0 0 20 20" fill="currentColor">
           <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"/>
         </svg>
         <strong>Charging Stop ${stopNum}</strong>
       </div>`
    : '';

  const chargeNote = isStop && s.charge_mins
    ? `<div class="popup-row">
         <svg viewBox="0 0 20 20" fill="currentColor">
           <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"/>
         </svg>
         ~${s.charge_mins} min charge (15% → 85%)
       </div>`
    : '';

  return `
    <div class="popup-body">
      ${stopBadge}
      <div class="popup-title">${s.name}</div>
      <div class="popup-row">
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"/>
        </svg>
        ${s.power_kw} kW · ${s.network}
      </div>
      ${chargeNote}
      <div class="popup-connector-list">${connectors}</div>
    </div>`;
}

// ── Route line drawing ───────────────────────────────────────────────────────

function drawRoute(geojsonCoords) {
  // geojsonCoords = [[lon, lat], …]
  const latLngs = geojsonCoords.map(([lon, lat]) => [lat, lon]);

  // Shadow / glow line
  L.polyline(latLngs, {
    color:   '#00e588',
    weight:   8,
    opacity:  0.12,
    lineJoin: 'round',
    lineCap:  'round',
  }).addTo(layerRoute);

  // Main route line
  const routeLine = L.polyline(latLngs, {
    color:     '#00e588',
    weight:     3.5,
    opacity:    0.9,
    lineJoin:  'round',
    lineCap:   'round',
    dashArray: '10, 6',
  }).addTo(layerRoute);

  // Animated dash via SVG style injection
  const el = routeLine.getElement();
  if (el) {
    el.style.animation = 'dash-flow 0.7s linear infinite';
  }

  return latLngs;
}

// ── Background station dots ───────────────────────────────────────────────────

async function loadAllStations() {
  if (allStationsLoaded) return;
  try {
    const res  = await fetch('/api/stations');
    const data = await res.json();
    data.forEach(s => {
      L.marker([s.lat, s.lon], { icon: makeNearbyIcon(), zIndexOffset: -100 })
        .bindPopup(stationPopup(s), { maxWidth: 280 })
        .addTo(layerAll);
    });
    allStationsLoaded = true;
  } catch (_) { /* Non-critical – silently skip */ }
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function showLoading(sub = 'Geocoding locations') {
  document.getElementById('loading').classList.remove('hidden');
  document.getElementById('loading-sub').textContent = sub;
  document.getElementById('plan-btn').disabled = true;
}

function hideLoading() {
  document.getElementById('loading').classList.add('hidden');
  document.getElementById('plan-btn').disabled = false;
}

function showError(msg) {
  const toast = document.getElementById('error-toast');
  document.getElementById('error-msg').textContent = msg;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 7000);
}

function hideError() {
  document.getElementById('error-toast').classList.add('hidden');
}

function formatDuration(hrs) {
  const h = Math.floor(hrs);
  const m = Math.round((hrs - h) * 60);
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

// ── Build journey timeline ─────────────────────────────────────────────────────

function buildTimeline(start, stops, end, stats) {
  const tl = document.getElementById('timeline');
  tl.innerHTML = '';

  const totalStops = stops.length;

  // Helper to create a timeline item
  function tlItem(iconClass, iconSvg, name, badges, lineClass) {
    const div = document.createElement('div');
    div.className = 'tl-item';
    div.innerHTML = `
      <div class="tl-left">
        <div class="tl-icon tl-icon--${iconClass}">${iconSvg}</div>
        ${lineClass ? `<div class="tl-line tl-line--${lineClass}"></div>` : ''}
      </div>
      <div class="tl-content">
        <div class="tl-name">${name}</div>
        <div class="tl-meta">${badges}</div>
      </div>`;
    return div;
  }

  const iconStart = `<svg viewBox="0 0 20 20" fill="currentColor"><circle cx="10" cy="10" r="4"/></svg>`;
  const iconStop  = `<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"/></svg>`;
  const iconEnd   = `<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"/></svg>`;

  // Start node
  tl.appendChild(tlItem(
    'start', iconStart,
    start.query || start.display_name,
    `<span class="tl-badge badge-net">Full charge · ${stats.range_km} km range</span>`,
    totalStops > 0 ? 'green' : 'last'
  ));

  // Charging stops
  stops.forEach((s, i) => {
    const isLast = i === totalStops - 1;
    const distBadge  = `<span class="tl-badge badge-dist">${s.dist_from_here} km from last point</span>`;
    const powerBadge = `<span class="tl-badge badge-power">${s.power_kw} kW · ${s.network}</span>`;
    const timeBadge  = `<span class="tl-badge badge-time">~${s.charge_mins} min charge</span>`;

    tl.appendChild(tlItem(
      'stop', iconStop,
      s.name,
      distBadge + powerBadge + timeBadge,
      isLast ? 'last' : 'amber'
    ));
  });

  // End node
  tl.appendChild(tlItem(
    'end', iconEnd,
    end.query || end.display_name,
    `<span class="tl-badge badge-dist">${stats.total_distance_km} km total</span>`,
    null
  ));
}

// ── Populate stats cards ──────────────────────────────────────────────────────

function populateStats(stats) {
  document.getElementById('stat-dist').textContent   = `${stats.total_distance_km} km`;
  document.getElementById('stat-time').textContent   = formatDuration(stats.duration_hrs);
  document.getElementById('stat-stops').textContent  = stats.num_stops;
  document.getElementById('stat-energy').textContent = `${stats.energy_kwh} kWh`;
}

// ── Main route planning function ─────────────────────────────────────────────

async function planRoute() {
  const startQ  = document.getElementById('input-start').value.trim();
  const endQ    = document.getElementById('input-end').value.trim();
  const rangeKm = +rangeSlider.value;

  if (!startQ || !endQ) {
    showError('Please enter both a starting point and destination.');
    return;
  }

  hideError();
  showLoading('Geocoding locations…');

  // Clear previous layers
  layerRoute.clearLayers();
  layerMarkers.clearLayers();
  layerNearby.clearLayers();

  try {
    showLoading('Calculating optimal charging stops…');

    const res = await fetch('/api/route', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ start: startQ, end: endQ, range_km: rangeKm }),
    });

    const data = await res.json();

    if (!res.ok || !data.success) {
      showError(data.error || 'An unexpected error occurred.');
      hideLoading();
      return;
    }

    showLoading('Drawing route on map…');

    // ── Draw route ──────────────────────────────────────────────────────────
    const latLngs = drawRoute(data.route_geometry);

    // ── Start marker ────────────────────────────────────────────────────────
    L.marker([data.start.lat, data.start.lon], { icon: makeStartIcon(), zIndexOffset: 200 })
      .bindPopup(`<div class="popup-body"><div class="popup-title" style="color:var(--green)">Start</div><div class="popup-row">${data.start.query}</div></div>`, { maxWidth: 280 })
      .addTo(layerMarkers);

    // ── Charging stop markers ────────────────────────────────────────────────
    data.charging_stops.forEach((s, i) => {
      L.marker([s.lat, s.lon], { icon: makeStopIcon(i + 1), zIndexOffset: 150 })
        .bindPopup(stationPopup(s, true, i + 1), { maxWidth: 300 })
        .addTo(layerMarkers);
    });

    // ── End marker ──────────────────────────────────────────────────────────
    L.marker([data.end.lat, data.end.lon], { icon: makeEndIcon(), zIndexOffset: 200 })
      .bindPopup(`<div class="popup-body"><div class="popup-title" style="color:var(--red)">Destination</div><div class="popup-row">${data.end.query}</div></div>`, { maxWidth: 280 })
      .addTo(layerMarkers);

    // ── Nearby stations ─────────────────────────────────────────────────────
    const stopIds = new Set(data.charging_stops.map(s => s.id));
    data.nearby_stations.forEach(s => {
      if (stopIds.has(s.id)) return;  // already shown as a charging stop
      L.marker([s.lat, s.lon], { icon: makeNearbyIcon(), zIndexOffset: -50 })
        .bindPopup(stationPopup(s), { maxWidth: 280 })
        .addTo(layerNearby);
    });

    // ── Fit map to route ────────────────────────────────────────────────────
    if (latLngs.length > 1) {
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
    }

    // ── Update UI ────────────────────────────────────────────────────────────
    populateStats(data.stats);
    buildTimeline(data.start, data.charging_stops, data.end, data.stats);
    document.getElementById('results-panel').classList.remove('hidden');

  } catch (err) {
    console.error(err);
    showError('Network error – is the server running?');
  } finally {
    hideLoading();
  }
}

// ── Load background stations on startup ──────────────────────────────────────

loadAllStations();
