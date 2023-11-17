try:
    from drip.subscriber_list import subscriber_list
    from drip.update_subscriber import update_subscriber
except ModuleNotFoundError:
    from subscriber_list import subscriber_list
    from update_subscriber import update_subscriber  
from datetime import datetime, timedelta


def start(subs: list):
    for email in subs:
        updates = {
            'email': email,
            'tags': ['Glacier Daily Update'],
            'custom_fields': {'Daily_Start': ''},
            'remove_tags': ['Daily Start Set']
        }

        update_subscriber(updates)


def end(subs: list):
    for email in subs:
        updates = {
            'email': email,
            'custom_fields': {'Daily_End': ''},
            'remove_tags': ['Daily End Set', 'Glacier Daily Update']
        }

        update_subscriber(updates)


def update_scheduled_subs():
    scheduled = subscriber_list('Daily Start Set, Daily End Set')

    start_today = list()
    end_today = list()
    date_format = "%Y-%m-%d"
    yesterday = datetime.now() - timedelta(days=1)
    tomorrow = datetime.now() + timedelta(days=1)

    for i in scheduled:
        tags = i['tags']
        email = i['email']

        # If start date is earlier than tomorrow (ie is today or before) add to list.
        if 'Daily Start Set' in tags:
            start_day = i['custom_fields']['Daily_Start']
            start_day = datetime.strptime(start_day, date_format)
            if start_day < tomorrow:
                start_today.append(email)
                print(f'{email} is starting today!')
        
        # If end date is yesterday or earlier, stop sending daily updates.
        if 'Daily End Set' in tags:
            end_day = i['custom_fields']['Daily_End']
            end_day = datetime.strptime(end_day, date_format)
            if end_day <= yesterday:
                end_today.append(email)
                print(f'{email} will no longer get daily updates :(')
    
    start(start_today)
    end(end_today)

    updates = {'start' : start_today, 'end' : end_today}
    return updates


if __name__ == '__main__':
    update_scheduled_subs()
