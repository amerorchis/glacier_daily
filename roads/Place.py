"""
A super class for Roads and Hiker/Biker that finds the nearest named location from coordinates.
"""

import sys
import os
from typing import Tuple
from math import radians, sin, cos, sqrt, atan2

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from roads.places import places


class Place:
    """
    A super class used for an object with GPS coordinates that needs a named location.
    """

    place_type = None

    def __init__(self, name: str) -> None:
        """
        Constructor
        """
        self.name = name
        self.closures_found = False
        self.entirely_closed = False
        self.coords_set = False
        self.closure_str = ""
        self.places = places
        self.locations = []
        self.north = []
        self.north_loc = (None, None)
        self.east = []
        self.east_loc = ()
        self.south = []
        self.south_loc = ()
        self.west = []
        self.west_loc = ()
        self.orientation = ""

    def dist(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Find Euclidean distance between 2 sets of gps coordinates.
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        # Radius of the Earth in kilometers
        R = 6371.0
        return R * c

    def find_min_distance(self, direction: str, coords: Tuple[float, float]) -> None:
        """
        Locates the named place that has the minimum distance from the given coordinates.
        """
        min_dist = float("inf")
        for j in self.locations:
            distance = self.dist(coords[0], coords[1], j[0], j[1])
            if distance < min_dist:
                if distance < 3:
                    setattr(self, f"{direction}_loc", self.locations[j])
                else:
                    setattr(
                        self,
                        f"{direction}_loc",
                        f"{coords[0]}, {coords[1]} (name of location not found).",
                    )
                min_dist = distance

    def closure_spot(self) -> None:
        """
        Get the closure spot for any direction that has coordinates given.
        """
        for direction, coords in [
            ("north", self.north),
            ("south", self.south),
            ("east", self.east),
            ("west", self.west),
        ]:
            if coords:
                self.find_min_distance(direction, coords[::-1])

        self.closures_found = True

    def __str__(self) -> str:
        """
        Overload the string method with our closure string.
        """
        return self.closure_str

    def __bool__(self) -> bool:
        """
        Check if any closures have been listed.
        """
        return self.coords_set
