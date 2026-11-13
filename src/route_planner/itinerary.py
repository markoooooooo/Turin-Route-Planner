"""Helpers to show a journey to a person: find stops by name and print the trip step by step"""

import itertools
import re
import unicodedata
from dataclasses import dataclass

from route_planner.dijkstra import Journey, Walk
from route_planner.gtfs import Stop

STOP_PREFIX = re.compile(r"^Fermata \d+ - ")


def display_name(stop: Stop) -> str:
    """Return the stop name without the 'Fermata N - ' prefix used by GTT"""
    return STOP_PREFIX.sub("", stop.name)


def normalize(text: str) -> str:
    """Return the text in upper case and without accents, so "liberta" matches "LIBERTÀ" """
    decomposed = unicodedata.normalize("NFD", text.upper())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn") # tolgo gli accenti


def find_stops(stops: dict[str, Stop], query: str) -> list[str]:
    """Return the ids of the stops that match the name the user typed

    If a stop has exactly this name, only stops with that name are returned.
    Otherwise all stops that contain the text are returned, but only if they all have the same name.
    If they don't, the name is not clear enough and a ValueError lists the possible names.
    """
    wanted = normalize(query.strip())
    exact = [stop_id for stop_id, stop in stops.items() if normalize(display_name(stop)) == wanted]
    if exact:
        return sorted(exact)

    partial = [stop_id for stop_id, stop in stops.items() if wanted in normalize(display_name(stop))]
    if not partial:
        raise ValueError(f"nessuna fermata contiene {query!r}")
    names = sorted({display_name(stops[stop_id]) for stop_id in partial})
    if len(names) > 1:
        raise ValueError(f"{query!r} è ambiguo, scegli tra: " + ", ".join(names))
    return sorted(partial)


def format_time(seconds: int) -> str:
    """Turn seconds after midnight into "HH:MM". Times after midnight get "(+1)", for example 25:10 becomes "01:10 (+1)"."""
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    days_later, hours = divmod(hours, 24)
    suffix = f" (+{days_later})" if days_later else ""
    return f"{hours:02d}:{minutes:02d}{suffix}"


@dataclass(frozen=True, slots=True)
class Step:
    """One line of the trip: a ride on one bus, tram or metro, or a walk."""

    kind: str
    route: str | None
    from_stop: str
    to_stop: str
    dep: int
    arr: int
    stops_count: int


def group_legs(journey: Journey) -> list[Step]:
    """Join the legs of the journey into steps

    Legs on the same trip become one step, and walks next to each other become one step.
    Two different trips of the same line stay separate, because you have to change vehicle.
    """

    def leg_group(leg) -> tuple:
        return ("walk",) if isinstance(leg, Walk) else ("ride", leg.trip_id)

    steps = []
    for key, group in itertools.groupby(journey.legs, key=leg_group):
        legs = list(group)
        first, last = legs[0], legs[-1]
        steps.append(
            Step(
                kind=key[0],
                route=None if key[0] == "walk" else first.route,
                from_stop=first.from_stop,
                to_stop=last.to_stop,
                dep=first.dep,
                arr=last.arr,
                stops_count=len(legs),
            )
        )
    return steps


def describe(journey: Journey, stops: dict[str, Stop], departure_time: int) -> list[str]:
    """Return the trip as a list of lines of text, ready to print"""
    lines = []
    for step in group_legs(journey):
        start = display_name(stops[step.from_stop])
        end = display_name(stops[step.to_stop])
        if step.kind == "walk":
            minutes = max(1, round((step.arr - step.dep) / 60))
            lines.append(f"A piedi da {start} a {end}  ({minutes} min)")
        else:
            lines.append(
                f"Linea {step.route}: sali a {start} alle {format_time(step.dep)}, "
                f"scendi a {end} alle {format_time(step.arr)}  ({step.stops_count} fermate)"
            )
    total = round((journey.arrival - departure_time) / 60)
    lines.append(f"Arrivo alle {format_time(journey.arrival)}  ({total} min in tutto)")
    return lines