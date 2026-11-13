import heapq
import random

import pytest

from route_planner.heap import MinHeap


def test_pops_in_sorted_order():
    h = MinHeap()
    for x in [5, 1, 4, 1, 9, 2]:
        h.push(x)
    assert [h.pop() for _ in range(len(h))] == [1, 1, 2, 4, 5, 9]


def test_empty_heap_raises():
    h = MinHeap()
    assert len(h) == 0 and not h
    with pytest.raises(IndexError):
        h.pop()
    with pytest.raises(IndexError):
        h.peek()


def test_works_with_tuples_like_dijkstra():
    h = MinHeap()
    for item in [(300, "C"), (100, "A"), (200, "B"), (100, "0")]:
        h.push(item)
    assert h.peek() == (100, "0")
    assert [h.pop() for _ in range(4)] == [(100, "0"), (100, "A"), (200, "B"), (300, "C")]


def test_matches_heapq_on_random_operations():
    rng = random.Random(0)
    mine, reference = MinHeap(), []
    for _ in range(5000):
        if reference and rng.random() < 0.4:
            assert mine.pop() == heapq.heappop(reference)
        else:
            x = rng.randint(0, 1000)
            mine.push(x)
            heapq.heappush(reference, x)
        assert len(mine) == len(reference)
        if reference:
            assert mine.peek() == reference[0]


def test_heap_property_holds():
    rng = random.Random(1)
    h = MinHeap()
    for _ in range(1000):
        h.push(rng.random())
        if rng.random() < 0.3:
            h.pop()
        items = h._items
        for i in range(1, len(items)):
            assert items[(i - 1) // 2] <= items[i]