import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from routing.distance import build_distance_matrix, haversine_miles
from routing.pyomo_milp_solver import solve_assignment_milp

DEPOT = {"lat": 39.9526, "lon": -75.1652}


def _toy_stops(n=10):
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "stop_id": [f"STOP-{i:03d}" for i in range(n)],
            "lat": DEPOT["lat"] + rng.uniform(-0.05, 0.05, n),
            "lon": DEPOT["lon"] + rng.uniform(-0.05, 0.05, n),
            "parcel_count": rng.integers(1, 10, n),
            "window_start_min": 0,
            "window_end_min": 480,
        }
    )


def test_haversine_zero_for_same_point():
    assert haversine_miles(40.0, -75.0, 40.0, -75.0) == 0


def test_distance_matrix_symmetric():
    stops = _toy_stops()
    depot_row = pd.DataFrame([{**DEPOT, "parcel_count": 0}])
    locations = pd.concat([depot_row, stops], ignore_index=True)
    matrix = build_distance_matrix(locations)
    assert matrix.shape == (len(locations), len(locations))
    assert np.allclose(matrix, matrix.T)
    assert np.allclose(np.diag(matrix), 0)


def test_assignment_milp_respects_capacity():
    stops = _toy_stops(n=12)
    solution = solve_assignment_milp(stops, DEPOT, n_vehicles=4, vehicle_capacity=25)
    for v, load in solution["vehicle_loads"].items():
        assert load <= 25
    all_assigned = sorted(stop_id for stops_ in solution["assignments"].values() for stop_id in stops_)
    assert all_assigned == sorted(stops["stop_id"])
