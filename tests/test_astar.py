import random

import pytest

from route_planner.astar import max_speed, straight_line_heuristic
from route_planner.dijkstra import earliest_arrival
from route_planner.graph import WALK_DETOUR_FACTOR, WALK_SPEED_M_S, Graph
from route_planner.gtfs import Connection, Stop
from route_planner.spatial import haversine


def conn(u, v, dep, arr, trip, route="1"):
    return Connection(from_stop=u, to_stop=v, dep=dep, arr=arr, trip_id=trip, route=route)


# Fermate in fila lungo un meridiano: 0.01° di latitudine sono circa 1112 m
LINE = {s: Stop(s, s, 45.0 + 0.01 * i, 7.0) for i, s in enumerate("WABT")}


def test_max_speed_ignores_zero_duration():
    g = Graph.from_connections(LINE, [conn("A", "B", 0, 100, "X"), conn("B", "T", 100, 100, "Y")])
    assert max_speed(g) == pytest.approx(haversine(45.01, 7.0, 45.02, 7.0) / 100)


def test_max_speed_without_connections_is_walking_speed():
    g = Graph.from_connections(LINE, [])
    assert max_speed(g) == pytest.approx(WALK_SPEED_M_S / WALK_DETOUR_FACTOR)


def test_heuristic_is_zero_at_target_and_grows_with_distance():
    g = Graph.from_connections(LINE, [conn("A", "B", 0, 100, "X")])
    h = straight_line_heuristic(g, "T", max_speed(g))
    assert h("T") == 0
    assert h("W") > h("A") > h("B") > 0


def test_astar_explores_fewer_stops():
    # Da A si arriva prima a W (60 s), che però è nella direzione opposta a T
    g = Graph.from_connections(
        LINE,
        [conn("A", "W", 0, 60, "BACK"), conn("A", "B", 0, 100, "X"), conn("B", "T", 100, 200, "X")],
    )
    dijkstra = earliest_arrival(g, "A", "T", 0)
    astar = earliest_arrival(g, "A", "T", 0, heuristic=straight_line_heuristic(g, "T", max_speed(g)))
    assert astar.arrival == dijkstra.arrival == 200
    assert astar.legs == dijkstra.legs
    assert dijkstra.settled == 4  # A, W, B, T
    assert astar.settled == 3  # A, B, T: W non viene mai estratta


def random_network(rng, n_stops=30, n_trips=40):
    stops = {
        str(i): Stop(str(i), str(i), 45.0 + rng.uniform(0, 0.05), 7.6 + rng.uniform(0, 0.07))
        for i in range(n_stops)
    }
    ids = sorted(stops)
    connections = []
    for k in range(n_trips):
        path = rng.sample(ids, rng.randint(2, 6))
        t = rng.randint(0, 3000)
        for a, b in zip(path, path[1:]):
            duration = rng.randint(30, 600)
            connections.append(conn(a, b, t, t + duration, f"T{k}"))
            t += duration + rng.randint(0, 60)
    return stops, connections


def test_astar_matches_dijkstra_on_random_networks():
    rng = random.Random(7)
    for _ in range(20):
        stops, connections = random_network(rng)
        g = Graph.from_connections(stops, connections, walk_radius_m=300)
        v_max = max_speed(g)
        for _ in range(20):
            source, target = rng.sample(sorted(stops), 2)
            t0 = rng.randint(0, 2000)
            d = earliest_arrival(g, source, target, t0)
            a = earliest_arrival(g, source, target, t0, heuristic=straight_line_heuristic(g, target, v_max))
            assert (a.arrival if a else None) == (d.arrival if d else None)
            if d is not None:
                assert a.settled <= d.settled