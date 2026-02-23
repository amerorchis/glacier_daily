"""
This module retrieves notices from a Google Sheets document.
"""

from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

from shared.data_types import NoticesResult
from shared.datetime_utils import now_mountain
from shared.retry import retry
from shared.settings import get_settings

default = NoticesResult(fallback_message="Notices could not be retrieved.")


@retry(3, (gspread.exceptions.APIError,), default, 3)
def get_notices() -> NoticesResult:
    """
    Retrieves notices from a Google Sheets document.

    Returns:
        NoticesResult: Structured notices data.
    """
    try:
        # Load credentials
        settings = get_settings()
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS, scopes=scopes
        )

        # Create a client
        client = gspread.authorize(credentials)

        # Open a spreadsheet
        spreadsheet = client.open_by_key(settings.NOTICES_SPREADSHEET_ID)

        # Access a worksheet
        worksheet = spreadsheet.sheet1

        values = worksheet.get_all_values()

    except gspread.exceptions.APIError:
        return NoticesResult(
            fallback_message="There was an error retrieving notices today."
        )

    date_format = "%m/%d/%Y"
    if len(values) > 1:
        try:
            notices = [
                i[0:3] for i in values[1:] if i[0] and i[1] and i[2]
            ]  # Grab all notices that have a start and end date and content
            notices = [
                {
                    "start": datetime.strptime(i[0], date_format),
                    "last": datetime.strptime(i[1], date_format) + timedelta(days=1),
                    "notice": i[2],
                }
                for i in notices
            ]  # create a dict for each one
            current_notices = [
                str(i["notice"])
                for i in notices
                if i["start"] < now_mountain().replace(tzinfo=None) < i["last"]
            ]  # isolate the content of the current notices

            if current_notices:
                return NoticesResult(notices=current_notices)

        except ValueError:
            pass

    return NoticesResult(fallback_message="There were no notices for today.")


if __name__ == "__main__":
    print(get_notices())
