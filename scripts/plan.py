"""Find the fastest trip between two stops in Turin and print

Run it from the project folder:
    python scripts/plan.py "POLITECNICO" "PORTA NUOVA" 08:00
    python scripts/plan.py "POLITECNICO" "PORTA NUOVA" 08:00 --date 2026-11-17 --map trip.html
"""

import argparse
import sys
import time
from datetime import date, datetime

from route_planner.astar import max_speed, straight_line_heuristic
from route_planner.cache import load_graph
from route_planner.dijkstra import MIN_TRANSFER_S, Walk, earliest_arrival
from route_planner.itinerary import describe, display_name, find_stops, format_time

FEED_PATH = "data/raw/gtt_gtfs.zip"


def parse_args() -> argparse.Namespace:
    """Read the options from the command line"""
    parser = argparse.ArgumentParser(description="Earliest-arrival journey planner on GTT data.")
    parser.add_argument("origin", help='stop name, e.g. "POLITECNICO"')
    parser.add_argument("destination", help='stop name, e.g. "PORTA NUOVA"')
    parser.add_argument("time", help="departure time, HH:MM")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD (default: today)")
    parser.add_argument("--algorithm", choices=["dijkstra", "astar"], default="dijkstra")
    parser.add_argument("--min-transfer", type=int, default=MIN_TRANSFER_S, help="seconds to change vehicle")
    parser.add_argument("--map", metavar="FILE.html", help="also save the journey on an interactive map (needs folium)")
    return parser.parse_args()


def parse_clock(text: str) -> int:
    """Turn a time like "08:05" into seconds"""
    clock = datetime.strptime(text, "%H:%M")
    return clock.hour * 3600 + clock.minute * 60


def save_map(journey, stops, path: str) -> None:
    """Save the trip as a map in an HTML file. Rides are green lines and walks are grey lines."""
    import folium

    points = [(stops[journey.legs[0].from_stop].lat, stops[journey.legs[0].from_stop].lon)]
    trip_map = folium.Map(location=points[0], zoom_start=14)
    for leg in journey.legs:
        start, end = stops[leg.from_stop], stops[leg.to_stop]
        segment = [(start.lat, start.lon), (end.lat, end.lon)]
        if isinstance(leg, Walk):
            folium.PolyLine(segment, color="gray", weight=3, dash_array="6").add_to(trip_map)
        else:
            folium.PolyLine(segment, color="#1D9E75", weight=5, tooltip=f"Linea {leg.route}").add_to(trip_map)
        points.append((end.lat, end.lon))
    first, last = journey.legs[0], journey.legs[-1]
    folium.Marker(points[0], tooltip=f"Partenza: {display_name(stops[first.from_stop])}").add_to(trip_map)
    folium.Marker(points[-1], tooltip=f"Arrivo: {display_name(stops[last.to_stop])}").add_to(trip_map)
    trip_map.fit_bounds(points)
    trip_map.save(path)


def main() -> int:
    """Load the graph, find the stops, search all start and end pairs, and print the best trip

    Return 0 if a trip was found, 1 if there was an error or no trip.
    """
    args = parse_args()
    departure_time = parse_clock(args.time)

    started = time.perf_counter()
    try:
        graph = load_graph(FEED_PATH, args.date)
        origins = find_stops(graph.stops, args.origin)
        destinations = find_stops(graph.stops, args.destination)
    except ValueError as error:  # nessuna corsa quel giorno, fermata inesistente o ambigua
        print(f"Errore: {error}", file=sys.stderr)
        return 1
    loaded = time.perf_counter() - started

    top_speed = max_speed(graph) if args.algorithm == "astar" else None
    best = None
    for destination in destinations:  # provo ogni coppia di paline e tengo il percorso che arriva prima
        heuristic = straight_line_heuristic(graph, destination, top_speed) if top_speed else None
        for origin in origins:
            journey = earliest_arrival(graph, origin, destination, departure_time, args.min_transfer, heuristic=heuristic)
            if journey is not None and (best is None or (journey.arrival, len(journey.legs)) < (best.arrival, len(best.legs))):
                best = journey

    if best is None:
        print(f"Nessun percorso da {args.origin} a {args.destination} dopo le {args.time} del {args.date}.")
        return 1

    print(f"{args.origin.upper()} -> {args.destination.upper()}, {args.date}, partenza alle {format_time(departure_time)}\n")
    for line in describe(best, graph.stops, departure_time):
        print("  " + line)
    print(f"\n(grafo pronto in {loaded:.1f} s, {len(origins)}x{len(destinations)} ricerche con {args.algorithm})")

    if args.map:
        save_map(best, graph.stops, args.map)
        print(f"Mappa salvata in {args.map}")
    return 0


if __name__ == "__main__":
    sys.exit(main())