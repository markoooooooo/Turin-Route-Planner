import pytest

from route_planner.gtfs import Connection, Stop
from route_planner.graph import Graph
from route_planner.graph import WalkEdge
from route_planner.graph import walk_time

STOPS = {s: Stop(stop_id=s, name=s, lat=45.0, lon=7.0) for s in "ABC"}

WALK_STOPS = {
    "A": Stop("A", "A", 45.0, 7.0),
    "B": Stop("B", "B", 45.002, 7.0),  # circa 222 m da A
    "C": Stop("C", "C", 45.1, 7.0),  # circa 11 km: troppo lontana
}

def conn(u, v, dep, arr, trip):
    return Connection(from_stop=u, to_stop=v, dep=dep, arr=arr, trip_id=trip, route="R")


def test_from_connections_groups_by_edge():
    g = Graph.from_connections(
        STOPS, [conn("A", "B", 100, 200, "T1"), conn("A", "C", 50, 90, "T2"), conn("A", "B", 10, 60, "T3")]
    )
    assert sorted(e.to_stop for e in g.edges["A"]) == ["B", "C"]
    edge_ab = next(e for e in g.edges["A"] if e.to_stop == "B")
    assert edge_ab.deps == [10, 100]
    assert g.edges["C"] == []


@pytest.mark.parametrize(
    ("t", "expected_trip"),
    [
        (0, "FAST"),
        (10, "FAST"),
        (20, "FAST"),
        (21, "T3"),
        (30, "T3"),
        (31, None),
    ],
)
def test_earliest_handles_overtaking(t, expected_trip):
    conns = [conn("A", "B", 10, 50, "T1"), conn("A", "B", 20, 40, "FAST"), conn("A", "B", 30, 60, "T3")]
    edge = Graph.from_connections(STOPS, conns).edges["A"][0]
    result = edge.earliest(t)
    assert (result.trip_id if result else None) == expected_trip

def test_walk_time():
    assert walk_time(0) == 0
    assert walk_time(125) == 130  # 125 m × 1.3 / 1.25 m/s


def test_walking_edges_are_symmetric_and_respect_radius():
    g = Graph.from_connections(WALK_STOPS, [], walk_radius_m=300)
    assert g.walks["A"] == [WalkEdge(to_stop="B", duration=232)]
    assert g.walks["B"] == [WalkEdge(to_stop="A", duration=232)]
    assert g.walks["C"] == []


def test_no_walking_edges_by_default():
    g = Graph.from_connections(WALK_STOPS, [])
    assert all(walks == [] for walks in g.walks.values())