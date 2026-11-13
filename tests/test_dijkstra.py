import pytest

from route_planner.dijkstra import earliest_arrival
from route_planner.graph import Graph
from route_planner.gtfs import Connection, Stop
from route_planner.dijkstra import Walk

STOPS = {s: Stop(stop_id=s, name=s, lat=45.0, lon=7.0) for s in "ABCD"}


def conn(u, v, dep, arr, trip, route="1"):
    return Connection(from_stop=u, to_stop=v, dep=dep, arr=arr, trip_id=trip, route=route)


GRAPH = Graph.from_connections(
    STOPS,
    [
        conn("A", "B", 100, 200, "T1"), conn("B", "C", 210, 300, "T1"),
        conn("A", "D", 120, 150, "T2", "2"), conn("D", "C", 160, 250, "T2", "2"),
        conn("A", "B", 400, 500, "T3"), conn("B", "C", 510, 600, "T3"),
    ],
)

WALK_STOPS = {
    "A": Stop("A", "A", 45.05, 7.0),  # lontana: si raggiunge solo in bus
    "B": Stop("B", "B", 45.0, 7.0),
    "C": Stop("C", "C", 45.002, 7.0),  # circa 222 m da B: 232 s a piedi
}

TRANSFER_GRAPH = Graph.from_connections(
    STOPS,
    [
        conn("A", "B", 100, 200, "X"), conn("B", "C", 200, 400, "X"),  # corsa X: lenta, ma ci sono già sopra
        conn("B", "C", 210, 300, "Y"),  # corsa Y: più veloce, parte da B 10 s dopo
    ],
)

def test_picks_fastest_route():
    j = earliest_arrival(GRAPH, "A", "C", 0)
    assert j.arrival == 250
    assert [c.trip_id for c in j.legs] == ["T2", "T2"]


def test_waits_for_next_departure():
    j = earliest_arrival(GRAPH, "A", "C", 121)
    assert j.arrival == 600
    assert [c.trip_id for c in j.legs] == ["T3", "T3"]


@pytest.mark.parametrize(("source", "target", "t0"), [("A", "C", 401), ("C", "A", 0)])
def test_unreachable_returns_none(source, target, t0):
    assert earliest_arrival(GRAPH, source, target, t0) is None


def test_source_equals_target():
    j = earliest_arrival(GRAPH, "A", "A", 100)
    assert j.arrival == 100
    assert j.legs == ()


def test_transfer_between_lines():
    g = Graph.from_connections(STOPS, [conn("A", "B", 100, 200, "X"), conn("B", "C", 250, 300, "Y")])
    j = earliest_arrival(g, "A", "C", 0)
    assert j.arrival == 300
    assert [c.trip_id for c in j.legs] == ["X", "Y"]
    assert j.legs[0].to_stop == j.legs[1].from_stop

def test_walk_after_bus():
    g = Graph.from_connections(WALK_STOPS, [conn("A", "B", 100, 200, "T1")], walk_radius_m=300)
    j = earliest_arrival(g, "A", "C", 0)
    assert j.arrival == 200 + 232
    assert j.legs == (
        conn("A", "B", 100, 200, "T1"),
        Walk(from_stop="B", to_stop="C", dep=200, arr=432),
    )


def test_walk_only_journey():
    g = Graph.from_connections(WALK_STOPS, [], walk_radius_m=300)
    j = earliest_arrival(g, "B", "C", 50)
    assert j.arrival == 282
    assert j.legs == (Walk(from_stop="B", to_stop="C", dep=50, arr=282),)


def test_unreachable_without_walking():
    g = Graph.from_connections(WALK_STOPS, [conn("A", "B", 100, 200, "T1")])
    assert earliest_arrival(g, "A", "C", 0) is None

def test_instant_transfer_by_default():
    j = earliest_arrival(TRANSFER_GRAPH, "A", "C", 0)
    assert j.arrival == 300
    assert [c.trip_id for c in j.legs] == ["X", "Y"]


def test_transfer_time_keeps_me_on_the_same_trip():
    j = earliest_arrival(TRANSFER_GRAPH, "A", "C", 0, min_transfer_s=120)
    assert j.arrival == 400  # Y parte prima che io riesca a cambiare (200 + 120 > 210)
    assert [c.trip_id for c in j.legs] == ["X", "X"]


def test_no_transfer_time_at_the_start():
    j = earliest_arrival(TRANSFER_GRAPH, "B", "C", 210, min_transfer_s=120)
    assert j.arrival == 300  # parto da B: salire su Y non è un cambio