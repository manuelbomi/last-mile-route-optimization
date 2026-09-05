"""End-to-end demo:
    1. generate (or load) synthetic delivery stops
    2. solve the full CVRP + time windows with OR-Tools
    3. solve the smaller exact stop-to-vehicle assignment MILP with Pyomo/HiGHS
    4. plot both, export GeoJSON for the frontend map

Usage:
    python scripts/run_route_optimization.py
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

from routing.or_tools_solver import solve_cvrp
from routing.pyomo_milp_solver import solve_assignment_milp
from routing.visualize import export_geojson, plot_routes

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(REPO_ROOT, "data", "delivery_stops.csv")
FIG_DIR = os.path.join(REPO_ROOT, "reports", "figures")
FRONTEND_DATA = os.path.join(REPO_ROOT, "frontend", "routes.geojson")

DEPOT = {"lat": 39.9526, "lon": -75.1652}


def ensure_data():
    if not os.path.exists(DATA_PATH):
        sys.path.insert(0, os.path.join(REPO_ROOT, "data"))
        import generate_delivery_stops as gen

        df = gen.generate()
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        df.to_csv(DATA_PATH, index=False)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    ensure_data()
    stops = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(stops)} delivery stops, total demand = {stops['parcel_count'].sum()} parcels")

    print("\n[1/2] Solving full CVRP + time windows with OR-Tools (local search)...")
    t0 = time.time()
    cvrp_solution = solve_cvrp(stops, DEPOT, n_vehicles=6, vehicle_capacity=140, time_limit_seconds=10)
    elapsed = time.time() - t0
    print(f"  Solved in {elapsed:.2f}s using {cvrp_solution['n_vehicles_used']} vehicles, "
          f"total distance = {cvrp_solution['total_distance_miles']} miles")
    for r in cvrp_solution["routes"]:
        print(f"    Vehicle {r['vehicle_id']}: {len(r['stop_sequence']) - 2} stops, "
              f"{r['load']} parcels, {r['distance_miles']} mi")

    plot_routes(cvrp_solution, os.path.join(FIG_DIR, "cvrp_routes.png"),
                title="CVRP + Time Windows -- OR-Tools Solution")
    os.makedirs(os.path.dirname(FRONTEND_DATA), exist_ok=True)
    export_geojson(cvrp_solution, FRONTEND_DATA)

    print("\n[2/2] Solving exact stop-to-vehicle assignment MILP with Pyomo + HiGHS...")
    t0 = time.time()
    milp_solution = solve_assignment_milp(stops, DEPOT, n_vehicles=6, vehicle_capacity=140)
    elapsed = time.time() - t0
    print(f"  Status: {milp_solution['status']}, solved in {elapsed:.3f}s")
    print(f"  Objective (total depot-to-stop distance): {milp_solution['objective_miles']} miles")
    print(f"  Vehicles used: {milp_solution['n_vehicles_used']}")
    for v, load in milp_solution["vehicle_loads"].items():
        print(f"    Vehicle {v}: {len(milp_solution['assignments'][v])} stops, {load} parcels")

    metrics = {
        "cvrp_ortools": {
            "vehicles_used": cvrp_solution["n_vehicles_used"],
            "total_distance_miles": cvrp_solution["total_distance_miles"],
            "solve_time_seconds": round(elapsed, 3),
        },
        "assignment_milp_pyomo_highs": {
            "vehicles_used": milp_solution["n_vehicles_used"],
            "objective_miles": milp_solution["objective_miles"],
            "status": milp_solution["status"],
        },
    }
    with open(os.path.join(FIG_DIR, "optimization_summary.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nSaved route map, GeoJSON, and summary metrics to {FIG_DIR} and {FRONTEND_DATA}")


if __name__ == "__main__":
    main()
