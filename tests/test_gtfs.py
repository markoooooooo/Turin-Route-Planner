import pytest
import zipfile

from route_planner.gtfs import read_csv
from route_planner.gtfs import convert_time
from route_planner.gtfs import load_stops
from route_planner.gtfs import Stop
from route_planner.gtfs import Connection
from route_planner.gtfs import active_services
from route_planner.gtfs import load_trips
from route_planner.gtfs import build_connections
from route_planner.gtfs import load_feed
from datetime import date

STOPS_HEADER = "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"

CALENDAR = (
    "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
    "FERIALE,1,1,1,1,1,0,0,20261101,20261130\n"
    "FESTIVO,0,0,0,0,0,1,1,20261101,20261130\n"
)
CALENDAR_DATES = (
    "service_id,date,exception_type\n"
    "FERIALE,20261110,2\n"   # martedì 10/11: feriale soppresso
    "FESTIVO,20261110,1\n"   # martedì 10/11: orario festivo aggiunto
    "SPECIALE,20261117,1\n"  # servizio presente solo in calendar_dates
)

ROUTES = (
    "route_id,agency_id,route_short_name,route_type\n"
    "4U,U,4,0\n"
    "METROU,U,M1,1\n"
    "3301E,E,3301,3\n"
)
TRIPS = (
    "route_id,service_id,trip_id\n"
    "4U,FERIALE,T1\n"
    "4U,FESTIVO,T2\n"
    "METROU,FERIALE,T3\n"
    "3301E,FERIALE,T4\n"
)

STOP_TIMES = (
    "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
    "T1,08:05:00,08:06:00,B,2\n"     
    "T2,25:00:00,25:00:00,X,1\n"     
    "T1,08:00:00,08:00:00,A,1\n"
    "T9,09:00:00,09:00:00,A,1\n"     
    "T1,08:10:00,08:10:00,C,10\n"    
    "T2,25:04:00,25:04:00,Y,2\n"
    "T9,09:05:00,09:05:00,B,2\n"
)

MINI_FEED = {
    "stops.txt": (
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "A,PORTA NUOVA,45.06,7.67,,\n"
        "B,VINZAGLIO,45.07,7.66,,\n"
        "C,PORTA SUSA,45.07,7.66,,\n"
        "Z,RIVOLI,45.07,7.51,,\n"             # usata solo dall'extraurbano
        "S1,STAZIONE PORTA NUOVA,45.06,7.67,1,\n"
    ),
    "routes.txt": (
        "route_id,agency_id,route_short_name,route_type\n"
        "4U,U,4,0\n"
        "3301E,E,3301,3\n"
    ),
    "trips.txt": (
        "route_id,service_id,trip_id\n"
        "4U,FERIALE,T1\n"
        "4U,FESTIVO,T2\n"
        "3301E,FERIALE,T3\n"
    ),
    "calendar.txt": (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "FERIALE,1,1,1,1,1,0,0,20261101,20261130\n"
        "FESTIVO,0,0,0,0,0,1,1,20261101,20261130\n"
    ),
    "calendar_dates.txt": "service_id,date,exception_type\n",
    "stop_times.txt": (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,08:00:00,08:00:00,A,1\n"
        "T1,08:05:00,08:06:00,B,2\n"
        "T1,08:10:00,08:10:00,C,3\n"
        "T2,10:00:00,10:00:00,A,1\n"
        "T2,10:05:00,10:05:00,B,2\n"
        "T3,09:00:00,09:00:00,C,1\n"
        "T3,09:30:00,09:30:00,Z,2\n"
    ),
}

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:00:00", 0),
        ("08:05:30", 29130),
        ("25:10:00", 90600),
        ("5:03:00", 18180),
        (" 08:05:30 ", 29130),
    ],
)



def test_convert_time_valid(text, expected):
    assert convert_time(text) == expected


@pytest.mark.parametrize("text", ["08:05", "ab:cd:ef", "08:60:00", "08:05:60"])
def test_convert_time_invalid(text):
    with pytest.raises(ValueError):
        convert_time(text)



def make_zip(path, files):
    """Create a ZIP at `path` containing {filename: text content}."""
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return path


def test_read_csv_parses_quoted_commas(tmp_path):
    content = '"stop_id","stop_name"\n"1","Via Casale, 230"\n"2","PORTA NUOVA"\n'
    path = make_zip(tmp_path / "feed.zip", {"stops.txt": content})
    with zipfile.ZipFile(path) as zf:
        rows = list(read_csv(zf, "stops.txt"))
    assert rows == [
        {"stop_id": "1", "stop_name": "Via Casale, 230"},
        {"stop_id": "2", "stop_name": "PORTA NUOVA"},
    ]


def test_read_csv_handles_bom(tmp_path):
    content = "\ufeffstop_id,stop_name\n1,A\n"
    path = make_zip(tmp_path / "feed.zip", {"stops.txt": content})
    with zipfile.ZipFile(path) as zf:
        rows = list(read_csv(zf, "stops.txt"))
    assert rows == [{"stop_id": "1", "stop_name": "A"}]


def test_read_csv_missing_file(tmp_path):
    path = make_zip(tmp_path / "feed.zip", {"stops.txt": "a\n1\n"})
    with zipfile.ZipFile(path) as zf:
        with pytest.raises(KeyError):
            list(read_csv(zf, "routes.txt"))


def test_load_stops_builds_stops(tmp_path):
    content = STOPS_HEADER + (
        "1,PORTA NUOVA,45.06,7.67,,\n"
        '2,"Via Casale, 230",45.07,7.68,0,\n'
    )
    path = make_zip(tmp_path / "feed.zip", {"stops.txt": content})
    with zipfile.ZipFile(path) as zf:
        stops = load_stops(zf)
    assert stops == {
        "1": Stop(stop_id="1", name="PORTA NUOVA", lat=45.06, lon=7.67),
        "2": Stop(stop_id="2", name="Via Casale, 230", lat=45.07, lon=7.68),
    }


def test_load_stops_skips_stations(tmp_path):
    content = STOPS_HEADER + (
        "1,METRO PORTA NUOVA,45.06,7.67,,S1\n"
        "S1,STAZIONE PORTA NUOVA,45.06,7.67,1,\n"
    )
    path = make_zip(tmp_path / "feed.zip", {"stops.txt": content})
    with zipfile.ZipFile(path) as zf:
        stops = load_stops(zf)
    assert list(stops) == ["1"]


def test_load_stops_rejects_duplicate_ids(tmp_path):
    content = STOPS_HEADER + "1,A,45.0,7.0,,\n1,B,45.1,7.1,,\n"
    path = make_zip(tmp_path / "feed.zip", {"stops.txt": content})
    with zipfile.ZipFile(path) as zf:
        with pytest.raises(ValueError):
            load_stops(zf)

def services_on(tmp_path, day):
    path = make_zip(
        tmp_path / "feed.zip",
        {"calendar.txt": CALENDAR, "calendar_dates.txt": CALENDAR_DATES},
    )
    with zipfile.ZipFile(path) as zf:
        return active_services(zf, day)


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 11, 3), {"FERIALE"}),               # martedì normale
        (date(2026, 11, 7), {"FESTIVO"}),               # sabato
        (date(2026, 11, 10), {"FESTIVO"}),              # eccezioni: tolto uno, aggiunto l'altro
        (date(2026, 11, 17), {"FERIALE", "SPECIALE"}),  # servizio solo in calendar_dates
        (date(2026, 11, 30), {"FERIALE"}),              # ultimo giorno: estremo incluso
        (date(2026, 12, 1), set()),                     # fuori dal periodo
    ],
)
def test_active_services(tmp_path, day, expected):
    assert services_on(tmp_path, day) == expected


def trips_for(tmp_path, agency, services):
    path = make_zip(tmp_path / "feed.zip", {"routes.txt": ROUTES, "trips.txt": TRIPS})
    with zipfile.ZipFile(path) as zf:
        return load_trips(zf, agency, services)


def test_load_trips_filters_agency_and_service(tmp_path):
    assert trips_for(tmp_path, "U", {"FERIALE"}) == {"T1": "4", "T3": "M1"}


def test_load_trips_other_agency(tmp_path):
    assert trips_for(tmp_path, "E", {"FERIALE"}) == {"T4": "3301"}


def test_load_trips_no_active_services(tmp_path):
    assert trips_for(tmp_path, "U", set()) == {}

def test_build_connections(tmp_path):
    path = make_zip(tmp_path / "feed.zip", {"stop_times.txt": STOP_TIMES})
    with zipfile.ZipFile(path) as zf:
        connections = build_connections(zf, {"T1": "4", "T2": "M1"})
    assert connections == [
        Connection(from_stop="A", to_stop="B", dep=28800, arr=29100, trip_id="T1", route="4"),
        Connection(from_stop="B", to_stop="C", dep=29160, arr=29400, trip_id="T1", route="4"),
        Connection(from_stop="X", to_stop="Y", dep=90000, arr=90240, trip_id="T2", route="M1"),
    ]


def test_build_connections_single_stop_trip(tmp_path):
    content = "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,A,1\n"
    path = make_zip(tmp_path / "feed.zip", {"stop_times.txt": content})
    with zipfile.ZipFile(path) as zf:
        assert build_connections(zf, {"T1": "4"}) == []

def test_load_feed(tmp_path):
    path = make_zip(tmp_path / "feed.zip", MINI_FEED)
    stops, connections = load_feed(path, date(2026, 11, 17))   # martedì
    assert set(stops) == {"A", "B", "C"}
    assert connections == [
        Connection(from_stop="A", to_stop="B", dep=28800, arr=29100, trip_id="T1", route="4"),
        Connection(from_stop="B", to_stop="C", dep=29160, arr=29400, trip_id="T1", route="4"),
    ]


def test_load_feed_no_trips(tmp_path):
    path = make_zip(tmp_path / "feed.zip", MINI_FEED)
    with pytest.raises(ValueError):
        load_feed(path, date(2026, 12, 1))   # fuori dal periodo dei calendari