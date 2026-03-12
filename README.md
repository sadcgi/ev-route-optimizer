# EV Route Optimiser

## What It Does

You type in a start location and a destination, set your EV's range, and the app plans the most efficient route with charging stops along the way. It draws everything on an interactive map, shows you how long each charge will take, and gives you a journey summary with total distance, drive time, and estimated energy used.

It uses three external services, all free with no API key required:
- **Nominatim** (OpenStreetMap) to turn place names into coordinates
- **OSRM** (Open Source Routing Machine) to get real road routes
- **CARTO** (via Leaflet) for the dark map tiles

---

## Project Structure

```
ev-route-optimizer/
├── app.py                  # Everything Python — the backend, the API, the algorithm
├── requirements.txt        # The two Python packages you need to install
├── start.bat               # Windows shortcut to run the app
├── templates/
│   └── index.html          # The single HTML page the app serves
└── static/
    ├── css/
    │   └── style.css       # All the visual styling
    └── js/
        └── app.js          # All the frontend JavaScript and map logic
```

---

## Getting Started

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate it (Windows)
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py

# 5. Open in your browser
# http://localhost:5000
```

---

## Python Imports (`app.py`)

```python
from flask import Flask, render_template, request, jsonify
```
**Flask** is the web framework — it's what turns the Python file into a running web server. I'm importing four specific things from it:
- `Flask` — creates the app instance
- `render_template` — serves HTML files from the `templates/` folder
- `request` — lets Flask read data sent from the browser (form values, JSON)
- `jsonify` — converts Python dictionaries and lists into proper JSON HTTP responses

```python
import requests
```
**requests** is a third-party package (hence it's in `requirements.txt`) for making HTTP calls from Python. I use it to call the Nominatim geocoding API and the OSRM routing API.

```python
import math
```
Part of Python's standard library — no install needed. Used for the haversine distance formula: `math.radians`, `math.sin`, `math.cos`, `math.sqrt`, `math.atan2`.

```python
import time
```
Also standard library. Used for one thing only: `time.sleep(1.1)` between the two Nominatim geocoding calls, because Nominatim's usage policy requires you not to send more than one request per second.

---

## The Charging Station Data

The `CHARGING_STATIONS` list is **hardcoded** — I got ChatGPT to write it and copy and pasted it. It is not pulled from a live API or database. It's based on well-known real-world locations: motorway services (Moto, Welcome Break), GRIDSERVE Electric Forecourts, IONITY hubs, retail parks, airports, and city centres across the UK.

Each station is a Python dictionary with these fields:

| Field | What it is |
|---|---|
| `id` | A unique number, used to avoid drawing duplicate markers |
| `name` | Human-readable name shown in popups and the journey timeline |
| `lat` / `lon` | GPS coordinates — where the station actually is |
| `power_kw` | Charger speed in kilowatts (50, 150, or 350 kW) |
| `network` | The operator (BP Pulse, GRIDSERVE, Pod Point, etc.) |
| `connectors` | List of plug types supported (CCS, CHAdeMO, Type 2) |

There are 125 stations in total. This is enough to cover most UK routes but it is **not live data** — stations may have changed. For production use, we'd replace this with a live feed from Open Charge Map or the National Chargepoint Registry.

I chose to hardcode it rather than call a live API because:
1. It keeps the project self-contained — no extra API keys or rate limits to worry about
2. The data doesn't change often enough to matter for a learning project
3. It makes the algorithm easier to understand when the data is right there in the file

---

## Python Functions

### `haversine(lat1, lon1, lat2, lon2)`

Calculates the straight-line distance in kilometres between two GPS coordinates, accounting for the curvature of the Earth.

You can't use Pythagoras (flat-plane geometry) for GPS coordinates because the Earth is a sphere. At short distances the error is small, but London to Edinburgh is roughly 650 km — the flat-plane error would be significant. The haversine formula is the standard solution for this.

**What it returns:** a distance in kilometres.

**Where it's used:** throughout the routing algorithm to measure distances between the current position, candidate charging stations, and the destination — all without making any network calls - This has its shortcomings too and isn't perfect.

---

### `off_route_penalty(s_lat, s_lon, cur_lat, cur_lon, end_lat, end_lon)`

Estimates how far sideways a charging station sits from the direct line between your current position and your destination.

Imagine drawing a straight line from where you are now to where you're going. This function measures how far a given station sits off to the side of that line — its perpendicular deviation. A station bang on the direct route scores 0. One that requires a significant detour gets a high penalty.

**Why this matters:** without it, the algorithm might pick a station that's technically reachable but requires driving 30 km off to one side, which wastes range and time. The penalty steers the algorithm towards stations that keep you on track.

**How it works:** it projects the station's coordinates onto the line segment using a dot product, then measures the perpendicular distance. The result is converted from degrees to kilometres using the approximation that 1 degree ≈ 111 km.

**What it returns:** lateral deviation in kilometres.

---

### `geocode_location(query)`

Takes a place name as a text string (e.g. `"Manchester"`) and returns its GPS coordinates by calling the **Nominatim API** (OpenStreetMap's free geocoding service).

I've restricted results to Great Britain (`countrycodes: "gb"`) so that searching for "Newport" gives you Newport, Wales, not Newport, Rhode Island.

**What it returns:** a dictionary with `lat`, `lon`, and `display_name` — or `None` if the place wasn't found.

**Why Nominatim?** It's completely free, requires no API key, and is based on OpenStreetMap data which has excellent UK coverage. The only constraint is their rate limit of one request per second, which is why there's a `time.sleep(1.1)` between the two calls in the route planning endpoint.

---

### `get_osrm_route(waypoints)`

Takes a list of coordinates (start, any charging stops, destination) and fetches the actual road route from the **OSRM public API**.

OSRM is an open source routing engine built on OpenStreetMap road data. The public instance at `router.project-osrm.org` is free to use for development. It returns the full road geometry as a list of coordinates, the total road distance in metres, and the estimated journey time in seconds.

I ask for `geometries: geojson` so the coordinates come back in a standard format, and `overview: full` to get the complete detailed route rather than a simplified version.

**What it returns:** a dictionary with `geometry` (list of `[lon, lat]` pairs), `distance_km`, and `duration_hrs` — or `None` if the request fails.

**Why only call it once?** Each OSRM call is a network request that takes time. Calling it for every candidate station during the routing algorithm would make it very slow. Instead, haversine does the fast filtering, and OSRM is called just once at the end with the final chosen waypoints.

---

### `estimate_charge_minutes(range_km, power_kw)`

Estimates how many minutes a charging stop will take.

It assumes the driver arrives at around 15% battery and charges to 85% — a standard real-world recommendation that avoids the slowdown at the top and bottom of the battery's charge curve (most EV batteries charge noticeably slower below 10% and above 80-85%).

That 70% charge window is applied to the estimated battery capacity, which is back-calculated from the car's range using an assumed consumption rate of **180 Wh/km** (0.18 kWh per kilometre). This is a reasonable average for a mid-size EV on a motorway journey.

The formula: `(range_km × 0.18 × 0.70) / power_kw × 60 = minutes`

**What it returns:** estimated charge time as a whole number of minutes.

---

### `calculate_charging_stops(start, end, range_km)`

This is the core algorithm. Given a start coordinate, end coordinate, and the car's range, it works out which charging stations to stop at.

**The algorithm — Greedy Maximum-Advance with Detour Penalty:**

It works iteratively. At each step, it asks: "can I reach the destination from here?" If yes, it stops. If not, it looks at every charging station within reachable range and scores each one:

```
score = progress_km + fast_charger_bonus - (detour_penalty × 0.4)
```

- **progress_km** — how much closer this station gets you to the destination (straight-line). This is the main factor.
- **fast_charger_bonus** — up to +20 km equivalent for a 350 kW charger, scaling down proportionally for slower ones. This nudges the algorithm to prefer faster chargers when two options are otherwise similar.
- **detour_penalty** — the lateral deviation from the direct route, multiplied by 0.4 to weight it appropriately. A heavily off-route station needs to offer significant progress to be worth the detour.

It picks the highest-scoring station, marks the car as fully recharged, moves there, and repeats.

**Safety margin:** the algorithm keeps an 18% battery reserve at all times. So a car with a 300 km range is treated as having a 246 km usable range. This compensates for the fact that haversine distances are straight-line, not road distances (roads are always longer), and for real-world factors like headwinds and motorway speeds.

**Hard cap:** the loop runs a maximum of 25 times. This is a safety measure — it prevents an infinite loop if the algorithm somehow gets stuck.

**What it returns:** a tuple of `(list_of_stops, error_message)`. If successful, the error is `None`. If it can't find a viable route, the list is `None` and the error explains why.

---

### `get_nearby_stations(route_geom, max_dist_km=12)`

After the route has been planned, this finds all charging stations within 12 km of the road route — not just the ones you're stopping at. These are shown as small blue dots on the map as background context.

It samples the route geometry at roughly 80 evenly-spaced points (rather than checking every single coordinate), which keeps it fast. For each sample point it uses haversine to find stations within 12 km.

**What it returns:** a list of station dictionaries.

---

## Flask Routes (API Endpoints)

### `GET /`
Serves the `index.html` file. This is the only page in the app — everything else happens via API calls from the browser.

---

### `GET /api/stations`
Returns the full `CHARGING_STATIONS` list as JSON. Called once when the page loads, so the frontend can draw all 125 stations as background dots on the map before the user searches for anything.

---

### `POST /api/route`
The main endpoint. Receives a JSON body with `start`, `end`, and `range_km`, and returns a full route plan.

The sequence inside this endpoint:
1. Validate inputs (both locations present, range at least 30 km)
2. Geocode the start location via Nominatim
3. Sleep 1.1 seconds (rate limit compliance)
4. Geocode the end location via Nominatim
5. Run `calculate_charging_stops()` to find the optimal stops
6. Call `get_osrm_route()` with all waypoints to get the real road path
7. If OSRM fails, fall back to straight-line segments between waypoints
8. Run `get_nearby_stations()` on the route geometry
9. Calculate total energy estimate (distance × 0.18 kWh/km)
10. Return everything as a JSON response

---

## Frontend — `static/js/app.js`

The JavaScript file handles everything visual. It never refreshes the page — it communicates with Flask via `fetch()` calls and updates the DOM directly.

### Map Setup
The map is initialised using **Leaflet.js** (loaded via CDN — nothing to install), centred on the UK at zoom level 6. The tile layer comes from CARTO's dark map style, which suits the dark UI theme.

Four separate layer groups are created so that different types of markers can be cleared independently between searches without wiping everything:
- `layerRoute` — the route polyline
- `layerMarkers` — start, end, and charging stop markers
- `layerNearby` — nearby station markers
- `layerAll` — background dots for all 125 stations

---

### `vehicleHint(km)`
Maps the slider value to a recognisable vehicle name (e.g. "Tesla Model 3 Long Range ≈ 300 km"). The hints are stored as a lookup table with `max` thresholds. It helps users set a realistic range without having to look up their car's spec.

---

### `updateSlider()`
Runs every time the range slider moves. Updates the displayed km value, fills the coloured track to the left of the thumb, and updates the vehicle hint label.

---

### `makeStartIcon()`, `makeEndIcon()`, `makeStopIcon()`, `makeNearbyIcon()`
These create custom Leaflet marker icons using `L.divIcon`, which lets you use HTML and CSS instead of image files.
- Start = green teardrop pin
- End = red teardrop pin
- Charging stops = amber circle with a lightning bolt
- Nearby stations = small blue dot

The `iconAnchor` property tells Leaflet where the "point" of the icon is so it lines up correctly with the coordinate on the map.

---

### `stationPopup(s, isStop, stopNum)`
Builds the HTML string for the popup that appears when you click a marker. If the station is a planned charging stop, it includes a "Charging Stop N" badge and the estimated charge time. Both stop and background station popups show the station name, power rating, network operator, and supported connector types.

---

### `drawRoute(geojsonCoords)`
Draws the route line on the map. It actually draws two overlapping polylines — a thick, low-opacity one for a glow/shadow effect, and a thinner dashed line on top for the actual route. The dashed line has a CSS animation applied (`dash-flow`) that makes it appear to flow in the direction of travel.

Note: GeoJSON coordinates come in `[lon, lat]` order, but Leaflet expects `[lat, lon]` — this function flips them.

---

### `loadAllStations()`
Called once on page load. Fetches all 125 stations from `/api/stations` and places a small blue dot marker on the map for each one. The `allStationsLoaded` flag prevents this from running twice if the function is somehow called again.

---

### `showLoading(sub)`, `hideLoading()`
Show and hide the loading overlay on the map. The overlay includes a spinning ring and a pulsing lightning bolt, plus a subtitle that updates to describe the current step ("Geocoding locations…", "Calculating optimal charging stops…" etc.). The Plan Route button is disabled while loading to prevent duplicate requests.

---

### `showError(msg)`, `hideError()`
Show and hide the error toast that appears at the top of the map. Errors automatically disappear after 7 seconds.

---

### `formatDuration(hrs)`
Converts a decimal hours value (e.g. `2.75`) into a readable string (`"2h 45m"`). Handles edge cases where hours or minutes are zero.

---

### `buildTimeline(start, stops, end, stats)`
Builds the journey plan list in the sidebar — the vertical timeline showing start, each charging stop, and the destination, with distance, charger power, network, and estimated charge time badges for each stop.

---

### `populateStats(stats)`
Updates the four stat cards (Distance, Drive Time, Charge Stops, Energy Used) with values from the API response.

---

### `planRoute()`
The main function, triggered by the Plan Route button or pressing Enter in either input. It:
1. Reads the form values
2. Clears previous map layers
3. Sends a POST request to `/api/route`
4. On success: draws the route, places all markers, fits the map to the route bounds, and updates the sidebar
5. On failure: shows the error toast
6. Always: hides the loading overlay when done

---

## Styling — `static/css/style.css`

The CSS uses **design tokens** — variables defined once in `:root` and reused throughout. This means if you want to change the green accent colour, you change `--green` in one place and it updates everywhere. The main colours are:

| Variable | Colour | Used for |
|---|---|---|
| `--green` `#00e588` | Bright green | Start marker, active elements, the brand accent |
| `--red` `#f87171` | Soft red | End marker, error states |
| `--amber` `#f59e0b` | Amber | Charging stop markers and badges |
| `--blue` `#38bdf8` | Sky blue | Nearby station markers, connector chips |
| `--bg-base` `#080c14` | Near-black | Page background |

The layout is a simple CSS Flexbox split: the sidebar is a fixed 380px wide, the map takes all remaining space.

The two fonts — **Inter** (body text) and **Space Grotesk** (headings and numbers) — are loaded from Google Fonts via CDN. Inter is a clean, legible sans-serif. Space Grotesk gives the numeric stats a slightly technical feel.

---

## Energy Consumption Assumption

The app uses a flat **180 Wh/km (0.18 kWh/km)** for two things:
1. Estimating total energy used for the journey: `distance_km × 0.18`
2. Back-calculating battery size from range, to estimate charge time: `range_km × 0.18`

180 Wh/km is a reasonable real-world average for a mid-size EV on a mixed motorway trip, but it does not vary by speed, weather, elevation, vehicle type, or any other factor. The displayed energy figure is an approximation — good enough for planning purposes but not something you'd quote precisely.

---

## Known Limitations

- **Charging station data is static** — it will go out of date. A production version would pull from a live API.
- **Haversine, not road distance** — the algorithm uses straight-line distances to score stations. Road distances are always longer. The 18% safety margin absorbs most of this, but it means the algorithm can occasionally underestimate how far a station really is by road.
- **No real-time charger availability** — the app can't tell you if a charger is broken or occupied.
- **Flat energy consumption** — no adjustment for speed, temperature, hills, or vehicle type.
- **UK only** — Nominatim calls are restricted to `countrycodes: gb` and the station dataset only covers the UK.