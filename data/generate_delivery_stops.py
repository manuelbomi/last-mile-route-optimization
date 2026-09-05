"""Synthetic last-mile delivery stop generator.

Creates a single day's worth of delivery stops for one depot/metro area:
random lat/lon points scattered around a depot, each with a parcel count
(demand) and a delivery time window. Distances are computed with the
haversine formula in `src/routing/distance.py`.

No real address or customer data is used -- coordinates are randomly
scattered within a bounding box approximating a mid-size metro area.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RNG_SEED = 7
DEPOT_LAT, DEPOT_LON = 39.9526, -75.1652  # arbitrary metro-area anchor point
N_STOPS = 60


def generate(n_stops: int = N_STOPS, seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Scatter stops within roughly a 12-mile radius of the depot
    radius_deg = 0.18
    angles = rng.uniform(0, 2 * np.pi, n_stops)
    radii = radius_deg * np.sqrt(rng.uniform(0, 1, n_stops))
    lats = DEPOT_LAT + radii * np.sin(angles)
    lons = DEPOT_LON + radii * np.cos(angles) * 1.3  # rough longitude compression

    demand = rng.integers(1, 12, n_stops)  # parcels to drop at this stop

    # Two-hour delivery windows within an 8-hour operating day (in minutes
    # from route start at 08:00)
    window_start = rng.integers(0, 360, n_stops)
    window_end = window_start + rng.integers(90, 180, n_stops)

    df = pd.DataFrame(
        {
            "stop_id": [f"STOP-{i:03d}" for i in range(1, n_stops + 1)],
            "lat": lats,
            "lon": lons,
            "parcel_count": demand,
            "window_start_min": window_start,
            "window_end_min": window_end,
        }
    )
    return df


if __name__ == "__main__":
    df = generate()
    df.to_csv("data/delivery_stops.csv", index=False)
    print(f"Wrote {len(df)} stops to data/delivery_stops.csv")
    print(f"Depot: ({DEPOT_LAT}, {DEPOT_LON})")
    print(f"Total demand: {df['parcel_count'].sum()} parcels")
