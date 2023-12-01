from datetime import datetime

def get_season() -> str:
    month = datetime.now().month

    summer_months = [4,5,6,7,8]
    fall_months = [9,10,11]
    winter_months = [12,1,2,3]

    if month in summer_months:
        return 'summer'

    elif month in fall_months:
        return 'fall'
    
    elif month in winter_months:
        return 'winter'

    else:
        return 'summer'


if __name__ == '__main__':
    print(get_season())
