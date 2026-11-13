"""
Transform the ZIP's text files to python object

the main objectives are:
1) to read CSV files (they are txt files with the CSV file structure)
2) to filter the urban operator
3) to decide which services are active in a specific date using calendar.txt and calendar_dates.txt
4) to convert times in seconds, managing also those over 24
5) to retrieve elementary connection from stop_times.txt, for each couple of consecutive stops

the code write down here produces a dict of stops and a list of connections,
the class Stop and the class Connection
and the functions who create every stop and connection

""" 

from dataclasses import dataclass
import csv
import zipfile
import io
from collections.abc import Iterator
from datetime import date
from collections import defaultdict
from pathlib import Path


@dataclass(frozen=True)
class Stop:
    stop_id: str
    name: str
    lat: float
    lon: float


@dataclass (frozen=True, slots=True)
class Connection:
    from_stop: str
    to_stop: str
    dep: int
    arr: int
    trip_id: str
    route: str

def convert_time(text: str) -> int: 
    """ convert the time with format "hr:min:sec" to seconds"""

    string = text.strip().split(":")
    if len(string)<3:
        raise ValueError(f"invalid time: {text!r}")
    if int(string[1])>=60 or int(string[2])>=60:
        raise ValueError(f"invalid time: {text!r}")

    hr = int(string[0])*3600
    min = int(string[1])*60

    return hr+min+int(string[2])

def read_csv(zf: zipfile.ZipFile, name: str) -> Iterator[dict[str, str]]:
    """Yield the rows of a CSV file inside the ZIP as dicts, it saves memory compared to lists or exporting all .txt files from the ZIP"""
    with zf.open(name) as f:
        # print(f.readline())
        testo = io.TextIOWrapper(f,encoding="utf-8-sig",newline="")
        for row in csv.DictReader(testo):
            yield row


def load_stops(zf: zipfile.ZipFile) -> dict[str,Stop]:
    """Return all boarding stops of the feed, keyed by stop_id (stations excluded (1s), I take only 0s or empty)."""
    stops = {}
    for row in read_csv(zf,"stops.txt"):
        if row["location_type"]== "1":
            continue
        else:
            if row["stop_id"] in stops:
                stop_id = row["stop_id"]
                raise ValueError(f"duplicate stop_id: {stop_id!r}")
            else:
                stops[row["stop_id"]] = Stop(row["stop_id"],row["stop_name"],float(row["stop_lat"]),float(row["stop_lon"]))
    return stops

def active_services(zf: zipfile.ZipFile, day: date) -> set[str]:
    """Return the ids of the service calendars that include `day` (calendar.txt + calendar_dates.txt exceptions)."""
    actives = set()

    week = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    for row in read_csv(zf,"calendar.txt"):
        if row["start_date"]<=day.strftime("%Y%m%d")<=row["end_date"] and row[week[day.weekday()]]=="1":
            actives.add(row["service_id"])

    for row in read_csv(zf,"calendar_dates.txt"):
        if row["date"]==day.strftime("%Y%m%d") and row["exception_type"]=="1":
            actives.add(row["service_id"])
        elif row["date"]==day.strftime("%Y%m%d") and row["exception_type"]=="2":
            actives.discard(row["service_id"])
    
    return actives


def load_trips(zf: zipfile.ZipFile, agency: str, services: set[str]) -> dict[str,str]:
    """Return {trip_id: route_short_name} for the trips of `agency` running on `services`."""

    routes = {}
    for row in read_csv(zf,"routes.txt"):
        if row["agency_id"] == agency:
            routes[row["route_id"]] = row["route_short_name"]

    res = {}
    for row in read_csv(zf,"trips.txt"):
        if (row["route_id"] in routes) and (row["service_id"] in services):
            res[row["trip_id"]] = routes[row["route_id"]]
    
    return res

    


def build_connections(zf: zipfile.ZipFile, trips: dict[str,str]) -> list[Connection]:
    """Build one Connection per pair of consecutive stops of each kept trip, sorted by departure. Every connection is an edge of the graph"""
    tripsDict = defaultdict(list)
    conn = []
    for row in read_csv(zf, "stop_times.txt"):
        if row["trip_id"] not in trips:
            continue
        tripsDict[row["trip_id"]].append((int(row["stop_sequence"]), row["stop_id"], convert_time(row["arrival_time"]), convert_time(row["departure_time"])))

    for trip_id, stops in tripsDict.items():
        stops.sort()
        route = trips[trip_id]
        for a,b in zip(stops, stops[1:]): # a and b are two tuples of 4 values every cycle
            _, stop_a, _, dep_a = a
            _, stop_b, arr_b, _ = b
            conn.append(Connection(from_stop=stop_a, to_stop=stop_b, dep=dep_a, arr=arr_b, trip_id=trip_id, route=route))

    conn.sort(key=lambda c: c.dep)
    return conn

def load_feed(z_path: str | Path, day: date, agency: str = "U") -> tuple[dict[str,Stop], list[Connection]]:
    """Load the stops and connections of `agency` running on `day` from a GTFS ZIP."""
    with zipfile.ZipFile(z_path) as zf:
        services = active_services(zf, day)
        trips = load_trips(zf, agency, services)
        if not trips:
            raise ValueError(f"no trips for agency {agency!r} on {day}")
        conns = build_connections(zf, trips)
        raw_stops = load_stops(zf)
    used_ids = set()
    for c in conns:
        used_ids.add(c.from_stop)
        used_ids.add(c.to_stop)
    stops = {}
    for stop_id, stop in raw_stops.items():
        if stop_id in used_ids:
            stops[stop_id] = stop

    return stops, conns