# Dispatch Dashboard (frontend)

A lightweight React map view for reviewing the day's optimized routes. It
reads `routes.geojson` (produced by `scripts/run_route_optimization.py`) and
renders each vehicle's route on a Leaflet map, with a KPI strip and a
per-vehicle summary panel.

This is intentionally shipped as a single dependency-free HTML file (React
+ Babel + Leaflet loaded from CDN, no build step) so it's trivial to run
anywhere. The component structure (`App` / `MapView` / `Sidebar`, `useState`/
`useEffect` hooks) maps directly onto what this would look like as a Next.js
page + client components in a production build -- that's the natural next
step once this needs auth, multi-day history, or server-rendered data.

## Run it

**Option 1 -- plain static server:**
```bash
cd frontend
python -m http.server 8080
# open http://localhost:8080
```

**Option 2 -- Docker (dev mode):**
```bash
cd frontend
docker build -t route-dashboard .
docker run --rm -p 8080:80 route-dashboard
# open http://localhost:8080
```

Regenerate `routes.geojson` first by running the optimizer from the repo
root: `python scripts/run_route_optimization.py`.
