""" Without heuristic this is Dijkstra; with an heuristic it is A* """


import heapq

from route_planner.gtfs import Connection
from route_planner.graph import Graph
from dataclasses import dataclass
from collections.abc import Callable

MIN_TRANSFER_S = 120

@dataclass(frozen=True, slots=True)
class Walk:
    """A walking leg of a journey"""
    from_stop : str
    to_stop : str
    dep : int
    arr : int

@dataclass(frozen=True, slots=True)
class Journey:
    arrival: int # best arrival time of the algorithm
    legs: tuple[Connection | Walk, ...] # all the pairs of stops, every leg
    settled: int # best number of stops to arrive at destination


def earliest_arrival(graph: Graph, source: str, target: str, t0: int, min_transfer_s: int = 0, heuristic: Callable[[str],float] | None = None) -> Journey | None:
    """Time-dependent Dijkstra: finds earliest arrival at `target` leaving `source` at `t0`, or None if unreachable"""
    # data structures
    if heuristic is None:
        def heuristic(stop_id: str) -> float:
            return 0.0
    
    arrival = {source: t0} # stop_id : best time
    prev = {} # stop_id : Connection
    heap = [(t0+heuristic(source), t0, source)] # (priority t + h, time t, stop)
    settled = set() # final stops
    on_trip = {source: None}

    def relax(v: str, t_arr: int, leg: Connection | Walk, trip: str | None) -> None:
        if t_arr < arrival.get(v, float("inf")):
            arrival[v] = t_arr
            prev[v] = leg
            on_trip[v] = trip
            heapq.heappush(heap, (t_arr + heuristic(v), t_arr, v))
    # algorithm
    while heap:
        _, t, u = heapq.heappop(heap) # extract minimum O(logn)
        if u in settled:
            continue
        settled.add(u)
        if u == target:
            break

        trip = on_trip[u]
        if trip is not None:
            c = graph.next_on_trip.get((trip,u))
            if c is not None:
                relax(c.to_stop, c.arr, c, trip)
        
        t_board = t if trip is None else t+ min_transfer_s
        for edge in graph.edges[u]:
            c = edge.earliest(t_board)
            if c is not None:
                relax(edge.to_stop, c.arr, c, c.trip_id)

        for walk in graph.walks[u]:
            t_arr = t+ walk.duration
            relax(walk.to_stop, t_arr, Walk(from_stop = u, to_stop = walk.to_stop, dep = t, arr = t_arr), None)

    if target not in settled:
        return None

    legs = []
    stop = target
    while stop!= source:
        leg = prev[stop]
        legs.append(leg)
        stop = leg.from_stop

    legs.reverse()

    return Journey(arrival=arrival[target], legs=tuple(legs), settled=len(settled))