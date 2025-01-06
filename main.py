#!/usr/bin/env python3.9

"""
This script performs the Glacier Daily Update by retrieving subscribers,
generating data, uploading it to a website, and sending emails to subscribers.
"""

import os
from dotenv import load_dotenv
load_dotenv("email.env")

from drip.drip_actions import get_subs, bulk_workflow_trigger
from sunrise_timelapse.sleep_to_sunrise import sleep_time as sleep_to_sunrise
from generate_and_upload import serve_api
import argparse
from typing import List

def main(tag: str = 'Glacier Daily Update', test: bool = False) -> None:
    """
    Main function to perform the Glacier Daily Update.

    Args:
        tag (str): Tag to filter subscribers. Defaults to 'Glacier Daily Update'.
    """
    sleep_to_sunrise()  # Sleep until sunrise timelapse is finished.

    # Retrieve subscribers from Drip.
    subscribers: List[str] = get_subs(tag)
    print('Subscribers found')

    # Generated data and upload to website.
    serve_api()

    # See if this fixes the issue with timelapse not showing.
    from time import sleep
    sleep(630 if not test else 0)

    # Send the email to each subscriber using Drip API.
    bulk_workflow_trigger(subscribers)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Glacier Daily Update')
    parser.add_argument('--tag', type=str, default='Glacier Daily Update',
                       help='Tag to filter subscribers (default: Glacier Daily Update)')
    args = parser.parse_args()

    environ = os.environ.get('TERM')

    if environ is None:
        main()
    elif environ == "xterm-256color":
        print(args.tag)
        main(args.tag, test=True)
