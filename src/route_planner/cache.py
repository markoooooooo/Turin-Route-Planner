"""Save the graph to a file, so the next run can load it instead of building it again.
Building the graph from the GTFS zip takes a few seconds. Loading it from the
cache file is about 4-5 times faster.
"""

import hashlib
import os
import pickle
from datetime import date
from pathlib import Path

from route_planner.graph import WALK_RADIUS_M, Graph
from route_planner.gtfs import load_feed

CACHE_DIR = Path("data/cache")
CACHE_VERSION = 1


def cache_path(feed_path: str | Path, day: date, agency: str, walk_radius_m: float, cache_dir: Path) -> Path:
    """Return the path of the cache file for these settings.
    The file name changes if the feed, the day, the agency, the walking radius
    or CACHE_VERSION changes, so an old cache is never used by mistake.
    """

    feed_stat = os.stat(feed_path)
    key = "|".join(
        str(part)
        for part in (CACHE_VERSION, Path(feed_path).name, feed_stat.st_size, feed_stat.st_mtime_ns,
                     day.isoformat(), agency, walk_radius_m))
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    return cache_dir / f"graph-{day.isoformat()}-{agency}-{digest}.pkl"

def load_graph(feed_path: str | Path, day: date, agency: str = "U", walk_radius_m: float = WALK_RADIUS_M, cache_dir: Path = CACHE_DIR,) -> Graph:
    """Return the graph for this day. Use the cache file if it exists, otherwise build the graph and save it.
    If the cache file is broken, the graph is built again.
    Only load cache files made by this program: pickle can run code when it loads a file.
    """

    path = cache_path(feed_path, day, agency, walk_radius_m, cache_dir)

    if path.exists():
        try:
            with open(path, "rb") as file:
                return pickle.load(file)
        except(OSError, EOFError, pickle.UnpicklingError, AttributeError, TypeError):
            pass

    stops , connections = load_feed(feed_path, day, agency)
    graph = Graph.from_connections(stops, connections, walk_radius_m = walk_radius_m)
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    with open(temporary_path, "wb") as file:
        pickle.dump(graph, file, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temporary_path, path)
    return graph