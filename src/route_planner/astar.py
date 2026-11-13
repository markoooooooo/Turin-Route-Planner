"""A* support: an admissible straight line heuristic for earliest arrival search"""

from collections.abc import Callable

from route_planner.graph import WALK_DETOUR_FACTOR, WALK_SPEED_M_S, Graph
from route_planner.spatial import haversine

def max_speed(graph: Graph) -> float:
    """Highest straight-line speed (m/s) of any move in the graph: transit connections and walks.
    Dividing a straight-line distance by this speed never overestimates the travel time,
    which is what makes the heuristic admissible. Zero-duration connections are skipped.
    """

    stops = graph.stops
    fastest = WALK_SPEED_M_S / WALK_DETOUR_FACTOR

    for edges in graph.edges.values():
        for edge in edges:
            for c in edge.connections:
                duration = c.arr - c.dep
                if duration <= 0:
                    continue
                a, b = stops[c.from_stop], stops[c.to_stop]
                speed = haversine(a.lat, a.lon, b.lat, b.lon) / duration
                fastest = max(fastest, speed)
    return fastest

def straight_line_heuristic(graph: Graph, target: str, top_speed: float) ->  Callable[[str], float]:
    """given a stop_id the function estimate how may seconds are still needed to reach target from that stop
    the estimate is never higher than the real travel time so A* always finds the earliest arrival"""
    target_stop = graph.stops[target]

    def seconds_to_target(stop_id: str) -> float:
        stop = graph.stops[stop_id]
        distance = haversine(stop.lat, stop.lon, target_stop.lat, target_stop.lon)
        return distance / top_speed

    return seconds_to_target