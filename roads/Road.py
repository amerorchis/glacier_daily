from math import radians, sin, cos, sqrt, atan2
from places import places

class Road:
    def __init__(self, name: str, orientation: str = 'EW'):
        self.name = name
        if orientation.upper() in ['NS','EW']:
            self.orientation = orientation.upper()
        else:
            raise Exception('Road orientation must be NS or EW.')
        
        self.locations = places[name]
        self.closures_found = False
        self.entirely_closed = False
        self.closure_str = ''

        self.north = None
        self.east = None
        self.south = None
        self.west = None
    
    def set_coord(self, coord):
        if self.orientation == 'EW':
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

    def get_coord(self):
        if self.orientation == 'EW':
            print(f'West: {self.west[1],self.west[0]}\nEast: {self.east[1],self.east[0]}')
        
        else:
            print(f'North: {self.north[1],self.north[0]}\nSouth: {self.south[1],self.south[0]}')

    def dist(self, lat1, lon1, lat2, lon2):
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

    def find_min_distance(self, direction, coords):
        min_dist = float('inf')
        for j in self.locations:
            distance = self.dist(coords[0], coords[1], j[0], j[1])
            if distance < min_dist:
                if distance < 3:
                    setattr(self, f"{direction}_loc", self.locations[j])
                else:
                    setattr(self, f"{direction}_loc", f'{coords[0]}, {coords[1]} (name of location not found).')
                min_dist = distance

    def closure_spot(self):
        for direction, coords in [('north', self.north), ('south', self.south), ('east', self.east), ('west', self.west)]:
            if coords:
                self.find_min_distance(direction, coords[::-1])
        
        self.closures_found = True
    
    def closure_string(self):

        if not self.closures_found:
            self.closure_spot()

        if self.orientation == 'EW':
            if '*' in self.west_loc and '*' in self.east_loc:
                self.entirely_closed = True
                self.closure_str = f'{self.name} is closed in its entirety.'
            
            else:
                self.west_loc = self.west_loc.replace('*','')
                self.east_loc = self.east_loc.replace('*','')
                self.closure_str = f'{self.name} is closed from {self.west_loc} to {self.east_loc}.'

        else:
            if '*' in self.north_loc and '*' in self.south_loc:
                self.entirely_closed = True
                self.closure_str = f'{self.name} is closed in its entirety.'

            else:
                self.south_loc = self.south_loc.replace('*','')
                self.north_loc = self.north_loc.replace('*','')
                self.closure_str = f'{self.name} is closed from {self.south_loc} to {self.north_loc}.'
        
        return self.closure_str
    
    