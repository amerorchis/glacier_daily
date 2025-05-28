import pytest

from roads.Road import Road


@pytest.fixture
def ew_road():
    return Road("Going-to-the-Sun Road", orientation="EW")


@pytest.fixture
def ns_road():
    return Road("Kintla Road", orientation="NS")


def test_road_init_orientation():
    road = Road("Going-to-the-Sun Road", orientation="EW")
    assert road.orientation == "EW"
    road = Road("Kintla Road", orientation="NS")
    assert road.orientation == "NS"
    with pytest.raises(ValueError):
        Road("Test Road", orientation="BAD")


def test_set_coord_ew(ew_road):
    ew_road.set_coord((-113.87562, 48.61694))  # West
    ew_road.set_coord((-113.44056, 48.74784))  # East
    assert ew_road.west == (-113.87562, 48.61694)
    assert ew_road.east == (-113.44056, 48.74784)
    assert ew_road.coords_set


def test_get_coord_ew_prints(capsys, ew_road):
    ew_road.set_coord((-113.87562, 48.61694))  # West
    ew_road.set_coord((-113.44056, 48.74784))  # East
    ew_road.get_coord()
    out = capsys.readouterr().out
    assert "West:" in out and "East:" in out


def test_set_coord_ns(ns_road):
    ns_road.set_coord((-114.28275, 48.786906))  # South
    ns_road.set_coord((-114.346676, 48.935763))  # North
    assert ns_road.south == (-114.28275, 48.786906)
    assert ns_road.north == (-114.346676, 48.935763)
    assert ns_road.coords_set


def test_get_coord_ns_prints(capsys, ns_road):
    ns_road.set_coord((-114.28275, 48.786906))  # South
    ns_road.set_coord((-114.346676, 48.935763))  # North
    ns_road.get_coord()
    out = capsys.readouterr().out
    assert "North:" in out and "South:" in out


def test_closure_string_entirely_closed_ew(ew_road):
    ew_road.west_loc = "Lake McDonald Lodge*"
    ew_road.east_loc = "Rising Sun*"
    ew_road.closures_found = True
    result = ew_road.closure_string()
    assert ew_road.entirely_closed
    assert "in its entirety" in result


def test_closure_string_partial_ew(ew_road):
    ew_road.west_loc = "Lake McDonald Lodge"
    ew_road.east_loc = "Rising Sun"
    ew_road.closures_found = True
    result = ew_road.closure_string()
    assert not ew_road.entirely_closed
    assert "closed from" in result
    assert "Lake McDonald Lodge" in result
    assert "Rising Sun" in result


def test_closure_string_entirely_closed_ns(ns_road):
    ns_road.north_loc = "the campground*"
    ns_road.south_loc = "the Polebridge Entrance Station*"
    ns_road.closures_found = True
    result = ns_road.closure_string()
    assert ns_road.entirely_closed
    assert "in its entirety" in result


def test_closure_string_partial_ns(ns_road):
    ns_road.north_loc = "the campground"
    ns_road.south_loc = "the Polebridge Entrance Station"
    ns_road.closures_found = True
    result = ns_road.closure_string()
    assert not ns_road.entirely_closed
    assert "closed from" in result
    assert "the campground" in result
    assert "the Polebridge Entrance Station" in result
