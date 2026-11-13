# Turin Route Planner

A route planner of gtt services in Turin in Python.

You give it two stops(start and destination) and a starting time. 
It finds the fastest trip to get there: bus, change and walk are all optimized.

I built the core parts myself: reading the data and making it usable for the project, made the graph,
implemented Dijkstra and A\*, a binary heap and a spatial grid.
Every part has tests.

## Demo

```
$ python scripts/plan.py "POLITECNICO" "PORTA NUOVA" 08:00 --date 2026-11-17

POLITECNICO -> PORTA NUOVA, 2026-11-17, partenza alle 08:00

  A piedi da POLITECNICO a STATI UNITI  (4 min)
  Linea 58/: sali a STATI UNITI alle 08:06, scendi a PORTA NUOVA alle 08:12  (4 fermate)
  Arrivo alle 08:12  (12 min in tutto)
```

```
$ python scripts/plan.py "politecnico" "lingotto" 08:00 --date 2026-11-17

  A piedi da POLITECNICO a METRO VINZAGLIO  (10 min)
  Linea M1: sali a METRO VINZAGLIO alle 08:11, scendi a METRO LINGOTTO alle 08:23  (8 fermate)
  A piedi da METRO LINGOTTO a LINGOTTO  (1 min)
  Arrivo alle 08:23  (24 min in tutto)
```

Add `--map trip.html` to also save the trip on an interactive map.

(The output is in Italian, like the stop names.)

## How it works

1. **Read the data.** GTT publishes its timetables in GTFS, a standard format made
   of CSV files. The program reads them from the zip(without extraction) and keeps only
   urban trips of the chosen day.
2. **Build a graph.** Each stop is a node. Each pair of stops connected by a bus,
   tram or metro is an edge. Stops that are less than 300m apart are covered by walks(walking edges).
3. **Search.** Implemented Dijkstra that works with timetables: the cost of an
   edge depends on when you reach the stop, sometime you have to wait for a bus.
   A\* uses the same search, but it's guided towards the destination and has an heuristic.

## What I measured

All numbers come from the scripts in `scripts/`, on the timetable of Tuesday
17 November 2026 (3,713 stops, 344,917 bus/tram/metro connections).

**Finding stops you can walk between.** 
Comparing every pair of stops takes around 7 million checks.
I made a grid where every cell cover 300m and it compares only nearby cells by 1.

| Stops | Grid | Every pair | Faster by |
|------:|-----:|-----------:|----------:|
| 500   | 1.3 ms | 86.5 ms | 66x |
| 1,000 | 4.0 ms | 348.4 ms | 88x |
| 2,000 | 11.1 ms | 1,410.3 ms | 127x |
| 3,713 | 32.2 ms | 4,877.8 ms | **151x** |

Both find exactly the same 11,238 pairs. When the number of stops doubles,
comparing every pair grows its time grows about 4 times, as expected for O(n²).

**Walking between stops.**
I had to introduce walking edges between stops because a lot of trips had no ruote.

**2 minute transfer time.** 
This was introduced to avoid impossible changes, like jumping from one bus to another in 10 seconds.

**Dijkstra vs A\*.**

| | Stops explored (average) | Same arrival time |
|---|---:|---:|
| Dijkstra | 1,792 | 300/300 |
| A\* | 1,580 (-12%) | 300/300 |

A\* gives the same time but explores 12% less of the stops in the graph, it is **not faster** in practice. 
It assumes you always travel at the top speed (78 km/h), in a straight line and without waiting!
while a typical bus in the city goes about 15 km/h and you actually waits at every stops.

**Binary heap.** It gives the same results as Python's `heapq`, which is written in C, it is slower in fact

**Cache.** Building the graph takes about 6 seconds, so every start of the project takes 6 seconds.
Saving it with `pickle` and loading it next time takes about 1.5 seconds.

## Limits

 - **Transfers** Each stop only knows the earliest way to get to destination. Adding a
  transfer time leads to avoid a slightly later bus which was better.
 - **Walking** is approximed from straight line length(x1.3 for streets, at
  4.5 km/h). Short walks could be bound, so late at night the planner can suggest long walks.
 - **Data** Only urban GTT services. In this feed the urban
  timetable ends on 31 December 2026.
 - **Terminus** Some buses reach the end of the line and start the next trip as
  the same bus. The planner always treats it as a change.

## Run it yourself

You need Python 3.11 or newer.

```
python -m venv .venv
.venv\Scripts\activate          # on macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev,map]"
```

Download the GTT GTFS feed from Transitland (feed `f-u0j-torino`, version of
23 October 2026) and save it as `data/raw/gtt_gtfs.zip`.

```
python scripts/plan.py "POLITECNICO" "PORTA NUOVA" 08:00 --date 2026-11-17
python scripts/bench_spatial.py
python scripts/bench_routing.py
pytest
```

## Project layout

```
src/route_planner/
    gtfs.py        read the GTFS zip: stops and connections for one day
    graph.py       the graph: timetable edges and walking edges
    spatial.py     distances and the grid to find nearby stops
    dijkstra.py    the search (Dijkstra, or A\* when given a heuristic)
    astar.py       the A\* heuristic
    heap.py        a binary heap written from scratch
    cache.py       save and load the graph
    itinerary.py   find stops by name and print the trip
scripts/           plan.py and the benchmarks
tests/             pytest tests
```

## Data

Timetables: GTT (Gruppo Torinese Trasporti), from the Transitland feed
`f-u0j-torino`.