"""
This module handles the generation of JSON data for sunrise timelapse videos and the uploading of this data to an FTP server.
"""

import io
import json
import os
import socket
from datetime import datetime
from ftplib import FTP
from time import sleep
from typing import List, Tuple, Union


def gen_json(files: List[str]) -> str:
    """
    Generate a JSON string containing metadata for sunrise timelapse videos.

    Args:
        files (List[str]): List of filenames for the timelapse videos.

    Returns:
        str: JSON string containing metadata for the timelapse videos.
    """

    def get_date_from_file_name(file_name: str) -> Tuple[int, int, int]:
        """
        Extract the date from a filename.

        Args:
            file_name (str): Filename in the format 'month_day_year_sunrise_timelapse.mp4'.

        Returns:
            Tuple[int, int, int]: A tuple containing the year, month, and day.
        """
        # Split the file name by underscores to extract the date parts
        parts = file_name.split("_")

        if len(parts) < 3:
            raise IndexError("Sunrise timelapse name malformed.")

        # Assuming the format is month_day_year, convert parts to integers
        month = int(parts[0])
        day = int(parts[1])
        year = int(parts[2])

        # Return a tuple (year, month, day) for sorting
        return (year, month, day)

    files.remove("..")
    files.remove(".")

    if not files:
        raise ValueError("No sunrise timelapse files")

    files.sort(key=get_date_from_file_name, reverse=True)

    timelapses = [{"date": f"{datetime.now()}"}]

    for file in files:
        _, month, day = get_date_from_file_name(file)
        timelapses.append(
            {
                "id": f"{file.replace('.mp4','')}",
                "vid_src": f"/daily/sunrise_vid/{file}",
                "url": f"https://glacier.org/webcam-timelapse/?type=daily&id={file.replace('.mp4','')}",
                "title": f"{month}-{day} Sunrise Timelapse",  # Title of the webpage showing this timelapse.
                "string": f"{month}-{day} Sunrise",
            }
        )

    return json.dumps(timelapses)


def send_timelapse_data(data: str) -> Union[str, bool]:
    """
    Upload the JSON data to an FTP server and return the URL of the latest timelapse video.

    Args:
        data (str): JSON string containing metadata for the timelapse videos.

    Returns:
        Union[str, bool]: URL of the latest timelapse video if successful, False otherwise.
    """
    username = os.environ["webcam_ftp_user"]
    password = os.environ["webcam_ftp_pword"]
    server = os.environ["timelapse_server"]

    try:
        ftp = FTP(server)
    except socket.gaierror:
        sleep(5)
        ftp = FTP(server)

    ftp.login(username, password)

    json_bytes = data.encode()
    json_buffer = io.BytesIO(json_bytes)
    file_path = "daily_timelapse_data.json"

    try:
        ftp.storbinary("STOR " + file_path, json_buffer)
        today = datetime.now().date()
        filename_vid = f"{today.month}_{today.day}_{today.year}_sunrise_timelapse.mp4"
        url = f"https://glacier.org/webcam-timelapse/?type=daily&id={filename_vid.replace('.mp4','')}"
        ftp.quit()
        return url

    except:
        print(f"Failed upload data")
        ftp.quit()
        return False
