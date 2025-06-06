"""
Define an object that represents a hiker/biker closure.
"""

import os
import sys

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )  # pragma: no cover

from roads.Place import Place
from roads.Road import Road


class HikerBiker(Place):
    """
    Object to represent a hiker/biker closure on Going-to-the-Sun Road.
    """

    place_type = "hiker_biker"

    def __init__(self, name: str, coords: tuple, gtsr: Road) -> None:
        """
        Constructor
        """
        super().__init__(name)
        self.locations = self.places[self.place_type]
        self.north = coords
        self.mile_marker = None
        try:
            self.gen_str(gtsr)
        except (ValueError, TypeError):
            self.closure_str = f"{coords} (name of location not found)"

    def get_side(self) -> str:
        """
        See if closure is on east or west side of the park or at Logan Pass.
        """
        longitude = self.north[0]
        latitude = self.north[1]
        # Logan Pass is at 48.6959, -113.7172

        north_boundary = 48.6998
        south_boundary = 48.6940
        west_boundary = -113.72402
        east_boundary = -113.71225

        if longitude < west_boundary:
            return "west"
        elif longitude > east_boundary:
            return "east"
        elif latitude > north_boundary:  # West side is technically north of Logan Pass
            return "west"
        else:
            return "logan"

    def closure_loc(self) -> None:
        """
        Find the name of the location of the hiker/biker closure.
        """
        # Just using the north loc as the vector for convenience here, the super class was really
        # designed for roads that run NS or EW.
        self.closure_spot()
        self.closure_str, self.mile_marker = self.north_loc

    def closure_dist(self, side: str, gtsr: Road) -> str:
        """
        Use GTSR closure data to see how many miles up the road the hiker biker spot is.
        We need to check if we are measuring mileage from the east or west closure of the road.
        """
        if side == "logan":
            return ", 32 miles up"

        if side == "west":
            self.west = gtsr.west
            self.closure_spot()
            return f", {self.mile_marker - self.west_loc[1]:.1f} miles from gate at {self.west_loc[0]}."

        if side == "east":
            self.east = gtsr.east
            self.closure_spot()
            return f", {self.east_loc[1] - self.mile_marker:.1f} miles from gate at {self.east_loc[0]}."

        return ""

    def gen_str(self, gtsr: Road) -> None:
        """
        Generate the string version of the closure.
        """
        side = self.get_side()
        self.closure_loc()

        side_name = ""
        if side != "logan":
            side_name = "West - " if side == "west" else "East - "
        self.closure_str = side_name + self.closure_str
        self.closure_str += self.closure_dist(side, gtsr)
