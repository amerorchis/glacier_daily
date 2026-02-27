"""
Define an object that represents a hiker/biker closure.
"""

from roads.place import Place
from roads.road import Road


class HikerBiker(Place):
    """
    Object to represent a hiker/biker closure on Going-to-the-Sun Road.
    """

    place_type = "hiker_biker"

    def __init__(self, name: str, coords: tuple[float, float], gtsr: Road) -> None:
        """Initialize a hiker/biker closure from coordinates and generate its description."""
        super().__init__(name)
        self.north_loc: tuple[str, float] = ("", 0.0)
        self.south_loc: tuple[str, float] = ("", 0.0)
        self.east_loc: tuple[str, float] = ("", 0.0)
        self.west_loc: tuple[str, float] = ("", 0.0)
        self.locations = self.places[self.place_type]
        self.north = coords
        self.mile_marker: float = 0.0
        try:
            self.gen_str(gtsr)
        except (ValueError, TypeError):
            self.closure_str = f"{coords} (name of location not found)"

    def find_min_distance(self, direction: str, coords: tuple[float, float]) -> None:
        """
        Locates the named place that has the minimum distance from the given coordinates.

        Overrides base class to ensure the fallback value is a tuple matching
        the hiker_biker location format (name, mile_marker).
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
                        (f"{coords[0]}, {coords[1]} (name of location not found)", 0.0),
                    )
                min_dist = distance

    def get_side(self) -> str:
        """
        See if closure is on east or west side of the park or at Logan Pass.
        """
        if self.north is None:
            raise RuntimeError("north coordinates not set")
        longitude = self.north[0]
        latitude = self.north[1]
        # Logan Pass is at 48.6959, -113.7172

        north_boundary = 48.6998
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
