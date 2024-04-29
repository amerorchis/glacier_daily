"""
Dictionaries of locations that are commonly accessed by road modules.
"""

roads = {
    'Going-to-the-Sun Road' : {
        (48.61703, -113.875531) : 'Lake McDonald Lodge',
        (48.749905, -113.44709) : 'the foot of St. Mary Lake',
        (48.52818, -113.97677) : 'the foot of Lake McDonald',
        (48.52169, -113.98857) : 'the foot of Lake McDonald',
        (48.67990, -113.81932) : 'Avalanche',
        (48.70158, -113.66778) : 'Siyeh Bend',
        (48.67815, -113.65335) : 'Jackson Glacier Overlook',
        (48.69231, -113.52234) : 'Rising Sun',
        (48.73853, -113.45783) : 'the Mile-and-a-Half Gate',
        (48.74755, -113.44056) : 'the St. Mary Visitor Center',
    },
    'Camas Road' : {
        (48.52744, -113.99826) : 'Apgar*',
        (48.62074, -114.13835) : 'the Outside North Fork Road*',
    },
    'Two Medicine Road' : {
        (48.484638, -113.36904) : 'Two Medicine Lake*',
        (48.50516, -113.329091) : 'the Park Boundary*',
        (48.49612, -113.34811) : 'Running Eagle Falls',
        (48.50495, -113.32998) : 'the entrance station'
    },
    'Many Glacier Road' : {
        (48.797482, -113.676452) : 'the Swiftcurrent Trailhead*',
        (48.80082, -113.65713) : 'the T-intersection at the Many Glacier Hotel',
        (48.829879, -113.524473) : 'the Park Boundary*'
    },
    'Bowman Lake Road' : {
        (48.786903, -114.282752) : 'the Polebridge Entrance Station*',
        (48.827523, -114.203345) : 'the campground*'
    },
    'Kintla Road' : {
        (48.935763, -114.346676) : 'the campground*',
        (48.786906, -114.28275) : 'the Polebridge Entrance Station*',
        (48.86518, -114.35921) : 'Round Prairie',
        (48.85974, -114.35400) : 'Round Prairie',
        (48.83144, -114.33511) : 'Doverspike Meadow',
        (48.84176, -114.34430) : 'Big Prairie',
        (48.81254, -114.32426) : 'Big Prairie',
    },
    'Cut Bank Road' : {
        (48.61017, -113.36781) : 'the park boundary*',
        (48.60157, -113.38362) : 'the campground*',
        (48.60581, -113.37711) : 'the ranger station',
    }
}

hiker_biker = {
    (48.52822, -113.97697) : ('Apgar', 2.8),
    (48.61694, -113.87562) : ('Lake McDonald Lodge', 10.7),
    (48.64601, -113.84608) : ('Moose Country', 13.5),
    (48.67968, -113.81944) : ('Avalanche', 16.4),
    (48.69523, -113.81716) : ('Red Rock Point', 17.6),
    (48.72470, -113.76506) : ('Logan Creek', 20.9),
    (48.74058, -113.76986) : ('Packer\'s Roost', 22.1),
    (48.74713, -113.77647) : ('Lower BPR', 22.6),
    (48.75494, -113.80047) : ('The Loop', 24.2),
    (48.74960, -113.77401) : ('Swede Point', 25.5),
    (48.73921, -113.75244) : ('Road Camp', 27),
    (48.73928, -113.74776) : ('Bird Woman Falls Overlook', 27.1),
    (48.72755, -113.72500) : ('Big Bend', 28.9),
    (48.72183, -113.72551) : ('Rip Rap Point', 29.6),
    (48.71747, -113.71817) : ('Triple Arches', 29.8),
    (48.69960, -113.72521) : ('Oberlin Bend', 31.6),
    (48.69659, -113.71800) : ('Logan Pass', 31.7),
    (48.69746, -113.71041) : ('Big Drift', 32.1),
    (48.69987, -113.70358) : ('Lunch Creek', 32.8),
    (48.70143, -113.66861) : ('Siyeh Bend', 34.5),
    (48.67766, -113.65241) : ('Jackson Glacier Overlook', 36.4),
    (48.67526, -113.62927) : ('Grizzly Point', 37.4),
    (48.68847, -113.55780) : ('Dead Horse Point', 41.2),
    (48.69147, -113.53130) : ('Wild Goose Island', 42.7),
    (48.69241, -113.52193) : ('Rising Sun', 43.4),
    (48.73853, -113.45783) : ('Mile and a Half Gate', 49.2),
    (48.74784, -113.44109) : ('St. Mary Visitor Center', 49.2),
}

places = {
    'roads': roads,
    'hiker_biker': hiker_biker
}
