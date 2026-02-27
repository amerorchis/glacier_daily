"""
Custom class to define a road in the park.
"""

from roads.place import Place


class Road(Place):
    """
    Define a road, and its closed status/location.
    """

    place_type = "roads"

    def __init__(self, name: str, orientation: str = "EW"):
        """
        Constructor
        """
        super().__init__(name)
        try:
            self.locations = self.places[self.place_type][name]
        except KeyError as exc:
            raise ValueError(
                f"Road name '{name}' not found in places['roads']."
            ) from exc
        if orientation.upper() in ["NS", "EW"]:
            self.orientation = orientation.upper()
        else:
            raise ValueError("Road orientation must be NS or EW.")

    def set_coord(self, coord):
        """
        Set appropriate coordinates depending on if road goes NS or EW.
        """
        if self.orientation == "EW":
            long = coord[0]

            if not self.east or long > self.east[0]:
                self.east = coord

            if not self.west or long < self.west[0]:
                self.west = coord

        else:
            lat = coord[1]

            if not self.north or lat > self.north[1]:
                self.north = coord

            if not self.south or lat < self.south[1]:
                self.south = coord

        self.coords_set = True

    def get_coord(self):
        """
        Print the coordinates for a location.
        """
        if self.orientation == "EW":
            print(
                f"West: {self.west[1], self.west[0]}\nEast: {self.east[1], self.east[0]}"
            )

        else:
            print(
                f"North: {self.north[1], self.north[0]}\nSouth: {self.south[1], self.south[0]}"
            )

    def closure_string(self):
        """
        Format a readable explanation of the road closure.
        """
        if not self.closures_found:
            self.closure_spot()

        if self.orientation == "EW":
            if "*" in self.west_loc and "*" in self.east_loc:
                self.entirely_closed = True
                self.closure_str = f"{self.name} is closed in its entirety."

            else:
                self.west_loc = self.west_loc.replace("*", "")
                self.east_loc = self.east_loc.replace("*", "")
                self.closure_str = (
                    f"{self.name} is closed from {self.west_loc} to {self.east_loc}."
                )

        else:
            if "*" in self.north_loc and "*" in self.south_loc:
                self.entirely_closed = True
                self.closure_str = f"{self.name} is closed in its entirety."

            else:
                self.south_loc = self.south_loc.replace("*", "")
                self.north_loc = self.north_loc.replace("*", "")
                self.closure_str = (
                    f"{self.name} is closed from {self.south_loc} to {self.north_loc}."
                )

        return self.closure_str
