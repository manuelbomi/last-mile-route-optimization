"""Haversine distance utilities used to build the routing distance matrix."""
from __future__ import annotations

import numpy as np
import pandas as pd

EARTH_RADIUS_MILES = 3958.8
AVG_SPEED_MPH = 22.0  # blended city/suburban delivery-vehicle speed


def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(a))


def build_distance_matrix(locations: pd.DataFrame) -> np.ndarray:
    """`locations` must have columns lat, lon; row 0 is treated as the depot."""
    n = len(locations)
    lats = locations["lat"].to_numpy()
    lons = locations["lon"].to_numpy()
    matrix = np.zeros((n, n))
    for i in range(n):
        matrix[i, :] = haversine_miles(lats[i], lons[i], lats, lons)
    return matrix


def build_time_matrix_minutes(distance_matrix: np.ndarray, avg_speed_mph: float = AVG_SPEED_MPH) -> np.ndarray:
    return (distance_matrix / avg_speed_mph) * 60.0
