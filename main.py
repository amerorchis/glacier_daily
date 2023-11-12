#!/usr/bin/env python3.9

import os
from dotenv import load_dotenv
load_dotenv("email.env")

from drip.get_subs import get_subs, send_in_drip
from sunrise_timelapse.sleep_to_sunrise import sleep_time as sleep_to_sunrise
from generate_and_upload import serve_api


def main(tag = 'Glacier Daily Update'):
    sleep_to_sunrise() # Sleep until sunrise timelapse is finished.

    # Retrieve subscribers from Drip.
    subscribers = get_subs(tag)
    print('Subscribers found')
    
    # Generated data and upload to website.
    serve_api()

    # Send the email to each subscriber using Drip API.
    for recipient in subscribers:
        try:
            send_in_drip(recipient)
        except Exception as e:
            print(f'Error in sending to {recipient}: {e}')

if __name__ == "__main__":
    environ = os.environ.get('TERM')
    
    if environ is None:
        main()

    elif environ == "xterm-256color":
        print('Test')
        # main('Test Glacier Daily Update')
        # main()
        # serve_api()
        