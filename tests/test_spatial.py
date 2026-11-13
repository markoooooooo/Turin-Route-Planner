import random

import pytest

from route_planner.gtfs import Stop
from route_planner.spatial import haversine, nearby_pairs, nearby_pairs_brute


def test_haversine_one_degree_of_latitude():
    assert haversine(45.0, 7.0, 46.0, 7.0) == pytest.approx(111_195, rel=1e-3)


def test_haversine_same_point():
    assert haversine(45.07, 7.68, 45.07, 7.68) == 0


def test_nearby_pairs_respects_radius():
    stops = {"A": Stop("A", "A", 45.0, 7.0), "B": Stop("B", "B", 45.002, 7.0)}
    assert len(nearby_pairs(stops, 250)) == 1
    assert nearby_pairs(stops, 200) == []


def as_set(pairs):
    return {frozenset((a, b)) for a, b, _ in pairs}


def test_grid_matches_brute_force():
    rng = random.Random(42)
    stops = {
        str(i): Stop(str(i), str(i), 45.0 + rng.uniform(0, 0.05), 7.6 + rng.uniform(0, 0.07))
        for i in range(400)
    }
    assert as_set(nearby_pairs(stops, 300)) == as_set(nearby_pairs_brute(stops, 300))