import random
import statistics
import time
from datetime import date

from route_planner.graph import WALK_RADIUS_M
from route_planner.gtfs import load_feed
from route_planner.spatial import nearby_pairs, nearby_pairs_brute

FEED_PATH = "data/raw/gtt_gtfs.zip"
DAY = date(2026, 11, 17)
SIZES = [250, 500, 1000, 2000, 3713]  # quante fermate usare in ogni prova
REPEATS = 3  # ripetizioni per ogni misura

def time_call(func, *args, repeats=REPEATS):
    times = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = func(*args)
        times.append(time.perf_counter() - start)
    return statistics.median(times), result

def as_set(pairs):
    return {frozenset((a,b)) for a,b ,_ in pairs}

def main():
    stops, _ = load_feed(FEED_PATH, DAY)   # dizionario stop_id -> Stop
    all_ids = sorted(stops)                # lista ordinata degli id 
    rng = random.Random(42)

    print(f"Raggio {WALK_RADIUS_M} m, mediana di {REPEATS} ripetizioni\n")
    print(f"{'fermate':>8} {'coppie':>8} {'griglia (ms)':>13} {'forza bruta (ms)':>17} {'rapporto':>9}")

    for size in SIZES:
        chosen = rng.sample(all_ids, size)                          # estraggo dalla lista
        subset = {stop_id: stops[stop_id] for stop_id in chosen}    # prendo gli Stop dal dizionario

        t_grid, grid_pairs = time_call(nearby_pairs, subset, WALK_RADIUS_M)
        t_brute, brute_pairs = time_call(nearby_pairs_brute, subset, WALK_RADIUS_M)

        assert as_set(grid_pairs) == as_set(brute_pairs), f"risultati diversi con {size} fermate"
        
        print(f"{size:>8} {len(grid_pairs):>8} {t_grid * 1000:>13.1f} "
            f"{t_brute * 1000:>17.1f} {t_brute / t_grid:>8.0f}x")

if __name__ == "__main__":
    main()