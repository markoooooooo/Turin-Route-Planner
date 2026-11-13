"""Implemented a spatial grid instead of a brute force approach and that saves from 3.5s to 22ms of time
300m for every 'walk' edge is the best compromised
Time = distance * 1.3 / 1.25

"""

"""Spatial helpers: great-circle distance and fast nearby-stop search with a uniform grid."""

import math
from collections import defaultdict
from route_planner.gtfs import Stop


EARTH_RADIUS_M = 6_371_000 # earth radius
METRES_PER_DEGREE_LAT = 111_320 # how many metres is each degree of longitude and latitude

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points (metres);
    Haversine's formula computes minimum distance between two points on a sphere knowing latitude and longitude;
    Advantages:
    this method gives correct data for every distance;
    it is the standard formula for GPS coordinates;
    low cost"""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2-lat1)
    d_lambda = math.radians(lon2-lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))

def nearby_pairs(stops: dict[str, Stop], radius_m: float) -> list[tuple[str, str, float]]:
    """All unordered pairs of stops within `radius_m`, found with a uniform grid
    O(n + n*k), k is average number of stops among 9 cells around one cell
    """

    if radius_m < 0:
        raise ValueError(f"radius_m must be positive, got {radius_m!r}")
    if not stops:
        return []

    max_lat = max(abs(stop.lat) for stop in stops.values())
    cell_lat = radius_m / METRES_PER_DEGREE_LAT
    cell_lon = radius_m / (METRES_PER_DEGREE_LAT * math.cos(math.radians(max_lat)))

    cells = defaultdict(list)
    for stop in stops.values():
        row = math.floor(stop.lat / cell_lat)
        col = math.floor(stop.lon / cell_lon)
        cells[(row,col)].append(stop)

    pairs = []
    for (row,col), members in cells.items():
        for d_row in (-1, 0, 1):
            for d_col in (-1, 0, 1):
                nb = cells.get((row + d_row, col + d_col))
                if nb is None:
                    continue
                for a in members:
                    for b in nb:
                        if a.stop_id >= b.stop_id:
                            continue
                        distance = haversine(a.lat, a.lon, b.lat, b.lon)
                        if distance <= radius_m:
                            pairs.append((a.stop_id, b.stop_id, distance))
    return pairs

def nearby_pairs_brute(stops: dict[str, Stop], radius_m: float) -> list[tuple[str, str, float]]:
    """Same result by comparing every pair: O(n²), used as a reference in tests and benchmarks."""

    items = list(stops.values())
    pairs = []

    for i in range(len(items)):
        for j in range(i+1, len(items)):
            a = items[i]
            b = items[j]
            distance = haversine(a.lat, a.lon, b.lat, b.lon)
            if distance <= radius_m:
                first, second = sorted((a.stop_id, b.stop_id))
                pairs.append((first,second, distance))
    return pairs