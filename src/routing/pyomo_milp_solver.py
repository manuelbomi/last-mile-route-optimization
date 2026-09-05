"""Exact MILP formulation of the capacitated stop-to-vehicle assignment
problem, built with Pyomo.

This solves a *relaxed* version of the full routing problem: rather than
sequencing stops into an ordered route (what OR-Tools does in
`or_tools_solver.py`), it decides which vehicle each stop is assigned to,
minimizing total depot-to-stop distance subject to vehicle capacity. This
is a genuinely useful sub-problem on its own (e.g. "which stops should each
of today's available trucks be responsible for") and it is the kind of
problem size (tens to low hundreds of binary variables) where an exact MILP
solve finishes in well under a second and gives you a certified-optimal
answer -- something a metaheuristic can only approximate.

Decision variables
-------------------
x[i, v] in {0, 1}   -- 1 if stop i is assigned to vehicle v

Objective
---------
minimize sum(distance(depot, i) * x[i, v] for all i, v)

Constraints
-----------
- each stop assigned to exactly one vehicle
- each vehicle's total assigned demand <= its capacity

Solver backend
--------------
Uses Pyomo's APPSI interface to HiGHS (`appsi_highs`), a fast open-source
MILP solver with no external binary or license required (pip install
highspy). Swapping to a commercial solver is a one-line change:

    # Gurobi
    solver = pyo.SolverFactory("gurobi")
    # CPLEX
    solver = pyo.SolverFactory("cplex")

Everything else -- the model, variables, constraints -- is solver-agnostic,
which is the whole point of building the model in Pyomo rather than calling
a solver's native Python API directly.
"""
from __future__ import annotations

import pandas as pd
import pyomo.environ as pyo

from .distance import haversine_miles


def solve_assignment_milp(
    stops: pd.DataFrame,
    depot: dict,
    n_vehicles: int = 6,
    vehicle_capacity: int = 140,
    solver_name: str = "appsi_highs",
) -> dict:
    n_stops = len(stops)
    vehicles = list(range(n_vehicles))
    stop_ids = list(stops["stop_id"])

    dist_to_depot = {
        row.stop_id: haversine_miles(depot["lat"], depot["lon"], row.lat, row.lon)
        for row in stops.itertuples()
    }
    demand = dict(zip(stops["stop_id"], stops["parcel_count"]))

    model = pyo.ConcreteModel(name="StopToVehicleAssignment")
    model.STOPS = pyo.Set(initialize=stop_ids)
    model.VEHICLES = pyo.Set(initialize=vehicles)

    model.x = pyo.Var(model.STOPS, model.VEHICLES, domain=pyo.Binary)

    def obj_rule(m):
        return sum(dist_to_depot[i] * m.x[i, v] for i in m.STOPS for v in m.VEHICLES)

    model.total_distance = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    def one_vehicle_per_stop_rule(m, i):
        return sum(m.x[i, v] for v in m.VEHICLES) == 1

    model.one_vehicle_per_stop = pyo.Constraint(model.STOPS, rule=one_vehicle_per_stop_rule)

    def capacity_rule(m, v):
        return sum(demand[i] * m.x[i, v] for i in m.STOPS) <= vehicle_capacity

    model.capacity = pyo.Constraint(model.VEHICLES, rule=capacity_rule)

    solver = pyo.SolverFactory(solver_name)
    results = solver.solve(model, tee=False)

    assignments = {v: [] for v in vehicles}
    for i in model.STOPS:
        for v in model.VEHICLES:
            if pyo.value(model.x[i, v]) > 0.5:
                assignments[v].append(i)

    vehicle_loads = {v: sum(demand[i] for i in stops_) for v, stops_ in assignments.items()}

    return {
        "status": str(results.solver.termination_condition),
        "objective_miles": round(pyo.value(model.total_distance), 2),
        "assignments": {v: stops_ for v, stops_ in assignments.items() if stops_},
        "vehicle_loads": {v: load for v, load in vehicle_loads.items() if load > 0},
        "n_vehicles_used": sum(1 for stops_ in assignments.values() if stops_),
    }
