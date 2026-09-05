"""Static (matplotlib) and web (GeoJSON, for the Leaflet frontend) route
visualizations."""
from __future__ import annotations

import json

import matplotlib.pyplot as plt

ROUTE_COLORS = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b",
    "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
]


def plot_routes(solution: dict, out_path: str, title: str = "Optimized Delivery Routes"):
    locations = solution["locations"]
    fig, ax = plt.subplots(figsize=(8, 8))

    depot = locations.iloc[0]
    ax.scatter(depot["lon"], depot["lat"], marker="s", s=140, color="black", zorder=5, label="Depot")

    for i, route in enumerate(solution["routes"]):
        color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        nodes = route["node_sequence"]
        lons = locations.iloc[nodes]["lon"].to_numpy()
        lats = locations.iloc[nodes]["lat"].to_numpy()
        ax.plot(lons, lats, "-o", color=color, markersize=4, linewidth=1.6,
                label=f"Vehicle {route['vehicle_id']} ({route['load']} pcs, {route['distance_miles']} mi)")

    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def export_geojson(solution: dict, out_path: str):
    """Export routes as a GeoJSON FeatureCollection consumable by the
    Leaflet-based React frontend in ../frontend/."""
    locations = solution["locations"]
    features = []

    depot = locations.iloc[0]
    features.append(
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [depot["lon"], depot["lat"]]},
            "properties": {"kind": "depot"},
        }
    )

    for i, route in enumerate(solution["routes"]):
        nodes = route["node_sequence"]
        coords = locations.iloc[nodes][["lon", "lat"]].to_numpy().tolist()
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "kind": "route",
                    "vehicle_id": route["vehicle_id"],
                    "load": route["load"],
                    "distance_miles": route["distance_miles"],
                    "color": ROUTE_COLORS[i % len(ROUTE_COLORS)],
                },
            }
        )
        for node in nodes[1:-1]:
            row = locations.iloc[node]
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                    "properties": {
                        "kind": "stop",
                        "stop_id": row["stop_id"],
                        "vehicle_id": route["vehicle_id"],
                        "parcel_count": int(row["parcel_count"]),
                        "color": ROUTE_COLORS[i % len(ROUTE_COLORS)],
                    },
                }
            )

    geojson = {"type": "FeatureCollection", "features": features}
    with open(out_path, "w") as f:
        json.dump(geojson, f, indent=2)
