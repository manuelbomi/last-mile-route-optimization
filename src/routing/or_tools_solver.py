"""Capacitated Vehicle Routing Problem (CVRP) with time windows, solved with
Google OR-Tools' constraint-programming routing engine.

This is the "production-shaped" solver in this repo: OR-Tools scales to
hundreds of stops in seconds using local-search metaheuristics (guided local
search + simulated annealing), which is what you actually want once a
routing problem is too large for an exact MILP solve to finish quickly.

For a *small-scale, exact* MILP formulation of essentially the same idea
(useful when you need a provably optimal answer for a small daily
sub-problem, or want to show the underlying LP relaxation), see
`pyomo_milp_solver.py` in this same package.
"""
from __future__ import annotations

import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .distance import build_distance_matrix, build_time_matrix_minutes


def solve_cvrp(
    stops: pd.DataFrame,
    depot: dict,
    n_vehicles: int = 6,
    vehicle_capacity: int = 140,
    time_limit_seconds: int = 10,
) -> dict:
    """Solve a CVRP + time-window problem.

    `stops` must have columns: lat, lon, parcel_count, window_start_min,
    window_end_min. `depot` is {"lat": ..., "lon": ...}.

    Returns a dict with per-vehicle routes, load, distance, and total stats.
    """
    depot_row = pd.DataFrame([{**depot, "parcel_count": 0, "window_start_min": 0, "window_end_min": 10_000}])
    locations = pd.concat([depot_row, stops], ignore_index=True)

    dist_matrix = build_distance_matrix(locations)
    time_matrix = build_time_matrix_minutes(dist_matrix)
    demands = locations["parcel_count"].to_numpy().astype(int)
    time_windows = list(zip(locations["window_start_min"], locations["window_end_min"]))

    n = len(locations)
    manager = pywrapcp.RoutingIndexManager(n, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(dist_matrix[from_node, to_node] * 100)  # scaled to int (0.01 mi units)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        return demands[manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, [vehicle_capacity] * n_vehicles, True, "Capacity"
    )

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(time_matrix[from_node, to_node]) + 5  # + 5 min service time per stop

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_callback_index, 60, 600, False, "Time")
    time_dimension = routing.GetDimensionOrDie("Time")
    for location_idx, (start, end) in enumerate(time_windows):
        if location_idx == 0:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(int(start), int(end))

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.FromSeconds(time_limit_seconds)

    solution = routing.SolveWithParameters(search_params)
    if solution is None:
        raise RuntimeError("OR-Tools failed to find a feasible solution within the time limit.")

    routes = []
    total_distance = 0.0
    for vehicle_id in range(n_vehicles):
        index = routing.Start(vehicle_id)
        route_nodes, route_load = [], 0
        route_distance = 0.0
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route_nodes.append(node)
            route_load += demands[node]
            prev_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += dist_matrix[manager.IndexToNode(prev_index), manager.IndexToNode(index)]
        route_nodes.append(manager.IndexToNode(index))  # back to depot
        if len(route_nodes) > 2:  # skip unused vehicles (depot -> depot only)
            routes.append(
                {
                    "vehicle_id": vehicle_id,
                    "stop_sequence": [locations.iloc[n]["stop_id"] if n != 0 else "DEPOT" for n in route_nodes],
                    "node_sequence": route_nodes,
                    "load": int(route_load),
                    "distance_miles": round(float(route_distance), 2),
                }
            )
            total_distance += route_distance

    return {
        "routes": routes,
        "n_vehicles_used": len(routes),
        "total_distance_miles": round(total_distance, 2),
        "locations": locations,
    }
