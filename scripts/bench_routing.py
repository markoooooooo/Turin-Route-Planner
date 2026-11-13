"""Benchmark: Dijkstra vs A* on random journeys in Turin.

Both use the same search function. The only difference is the heuristic,
so any difference in the results comes from A* alone.

Run it from the project folder:
    python scripts/bench_routing.py
"""

import random
import statistics
import time
from datetime import date

from route_planner.astar import max_speed, straight_line_heuristic
from route_planner.cache import load_graph
from route_planner.dijkstra import MIN_TRANSFER_S, earliest_arrival

FEED_PATH = "data/raw/gtt_gtfs.zip"
DAY = date(2026, 11, 17)
QUERIES = 300
SEED = 1


def random_queries(stop_ids, count, rng):
    """Return `count` random (start, end, departure time) triples, between 6:00 and 20:00."""
    queries = []
    for _ in range(count):
        start, end = rng.sample(stop_ids, 2)
        departure = rng.randint(6 * 3600, 20 * 3600)
        queries.append((start, end, departure))
    return queries


def run(graph, queries, top_speed=None):
    """Run every query. Return the journeys and the time of each search in milliseconds."""
    journeys = []
    times_ms = []
    for start, end, departure in queries:
        began = time.perf_counter()
        heuristic = straight_line_heuristic(graph, end, top_speed) if top_speed else None
        journey = earliest_arrival(graph, start, end, departure, MIN_TRANSFER_S, heuristic=heuristic)
        times_ms.append((time.perf_counter() - began) * 1000)
        journeys.append(journey)
    return journeys, times_ms


def main():
    graph = load_graph(FEED_PATH, DAY)
    top_speed = max_speed(graph)
    queries = random_queries(sorted(graph.stops), QUERIES, random.Random(SEED))

    dijkstra_journeys, dijkstra_ms = run(graph, queries)
    astar_journeys, astar_ms = run(graph, queries, top_speed)

    # Both must find the same arrival time, otherwise comparing speed makes no sense
    for dijkstra, astar in zip(dijkstra_journeys, astar_journeys):
        assert (dijkstra.arrival if dijkstra else None) == (astar.arrival if astar else None)

    found = [(d, a) for d, a in zip(dijkstra_journeys, astar_journeys) if d is not None]
    dijkstra_stops = statistics.mean(d.settled for d, _ in found)
    astar_stops = statistics.mean(a.settled for _, a in found)
    fewer = sum(1 for d, a in found if a.settled < d.settled)

    print(f"{QUERIES} random journeys on {DAY}, top speed {top_speed:.1f} m/s, transfer time {MIN_TRANSFER_S} s")
    print(f"Same arrival time: {QUERIES}/{QUERIES}  (no route found: {QUERIES - len(found)})\n")
    print(f"{'':10} {'stops explored':>15} {'median ms':>10} {'mean ms':>8}")
    print(f"{'Dijkstra':10} {dijkstra_stops:>15.0f} {statistics.median(dijkstra_ms):>10.1f} {statistics.mean(dijkstra_ms):>8.1f}")
    print(f"{'A*':10} {astar_stops:>15.0f} {statistics.median(astar_ms):>10.1f} {statistics.mean(astar_ms):>8.1f}")
    print(f"\nA* explores {100 * (1 - astar_stops / dijkstra_stops):.0f}% fewer stops "
          f"(fewer in {fewer}/{len(found)} journeys) and takes {statistics.mean(astar_ms) / statistics.mean(dijkstra_ms):.2f}x the time.")


if __name__ == "__main__":
    main()