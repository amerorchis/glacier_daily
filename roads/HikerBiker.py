try:
    from roads.Place import Place
except ModuleNotFoundError:
    from Place import Place

class HikerBiker(Place):
    place_type = 'hiker_biker'

    def __init__(self, name: str, coords):
        super().__init__(name)
        self.north = coords
        self.closure_string()

    def closure_string(self):

        if not self.closures_found:
            self.closure_spot()

        self.closure_str = self.north_loc

        return self.closure_str
