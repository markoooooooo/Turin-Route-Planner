"""Time-dependent graph of the transit network: stops are nodes, edges carry timetables."""

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
import math
from route_planner.gtfs import Connection, Stop
from route_planner.spatial import nearby_pairs

WALK_RADIUS_M = 300
WALK_SPEED_M_S = 1.25
WALK_DETOUR_FACTOR = 1.3

@dataclass(slots=True)
class Edge:
    to_stop: str
    connections: list[Connection]
    deps: list[int]
    best: list[int]

    def earliest(self, t: int) -> Connection | None:
        """Return the connection with the earliest arrival among those departing at or after t."""
        i = bisect_left(self.deps, t) # i is the position where t has to go, it keeps the list sorted. It uses a O(logn) binary search
        if i==len(self.deps):
            return None
        return self.connections[self.best[i]] # precomputed suffix minimum : earliest arrival among departures >= t

@dataclass(frozen=True, slots=True)
class WalkEdge:
    to_stop: str
    duration: int

def walk_time(distance: float) -> int:
    return math.ceil(distance*WALK_DETOUR_FACTOR/WALK_SPEED_M_S)

class Graph:
    def __init__(self, stops: dict[str, Stop], edges: dict[str, list[Edge]], walks: dict[str, list[WalkEdge]] | None = None,
                next_on_trip: dict[tuple[str,str], Connection] | None = None):
        self.stops = stops
        self.edges = edges
        if walks is None:
            walks = {stop_id: [] for stop_id in stops}
        self.walks = walks
        if next_on_trip is None:
            next_on_trip = {}
        self.next_on_trip = next_on_trip

    @classmethod
    def from_connections(cls, stops: dict[str, Stop], connections: list[Connection], walk_radius_m: float = 0) -> "Graph":
        """Group the connections by (from_stop, to_stop) and build one Edge per pair."""

        groups = defaultdict(list)
        next_on_trip = {}
        for c in connections:
            groups[(c.from_stop,c.to_stop)].append(c)
            next_on_trip[(c.trip_id, c.from_stop)] = c
            
        edges = {stop_id : [] for stop_id in stops}

        for (from_stop,to_stop), group in groups.items():
            group.sort(key=lambda c: c.dep)
            deps = [c.dep for c in group]

            n = len(group)
            best = [0] * n
            best[n-1] = n-1
            # implementing suffix minimum algorithm to precompute once (O(n)) so that
            # earliest() can answer in O(logn) even when a later bus overtakes an earlier one
            for i in range(n-2,-1,-1): 
                if group[i].arr < group[best[i+1]].arr:
                    best[i] = i
                else:
                    best[i] = best[i+1]

            edge = Edge(to_stop = to_stop, connections = group, deps = deps, best = best)
            edges[from_stop].append(edge)

        walks = {stop_id : [] for stop_id in stops}
        if walk_radius_m > 0:
            for a,b, distance in nearby_pairs(stops, walk_radius_m):
                duration = walk_time(distance)
                walks[a].append(WalkEdge(to_stop=b, duration=duration))
                walks[b].append(WalkEdge(to_stop=a, duration=duration))


        return cls(stops,edges,walks,next_on_trip) # can do the same with Graph(stops,edges,walks,next_on_trip)