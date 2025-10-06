"""
This module provides FTP functionalities including deleting old files and uploading new files.
"""

import ftplib
import os
from datetime import datetime, timedelta
from ftplib import FTP
from typing import Optional


def delete_on_first(ftp: FTP) -> None:
    """
    Deletes files on the FTP server that are older than 6 months if the current date is the first of the month.

    Args:
        ftp (FTP): An instance of the FTP class connected to the server.
    """
    current_date = datetime.now()

    if current_date.day == 1:
        print("First of the Month: Deleting files over 6 months old.")
        six_months_ago = current_date - timedelta(days=6 * 30)
        files = ftp.nlst()

        # Iterate through the files and delete those older than 6 months
        for file in files:
            try:
                ftp.size(file)
            except ftplib.error_perm:
                continue

            file_modification_date = ftp.sendcmd("MDTM " + file)
            file_modification_date = datetime.strptime(
                file_modification_date[4:], "%Y%m%d%H%M%S"
            )

            if file_modification_date < six_months_ago:
                ftp.delete(file)


def upload_file(
    directory: str, filename: str, file: Optional[str] = None
) -> tuple[str, list[str]]:
    """
    Uploads a file to the specified directory on the FTP server and deletes old files if necessary.
    Uses atomic upload (temp file then rename) to prevent partial file reads.

    Args:
        directory (str): The directory on the FTP server where the file will be uploaded.
        filename (str): The name of the file to be uploaded.
        file (Optional[str]): The local path to the file to be uploaded.

    Returns:
        tuple: A tuple containing the URL of the uploaded file and a list of files in the directory.
    """
    username = os.environ["FTP_USERNAME"]
    password = os.environ["FTP_PASSWORD"]
    server = "ftp.glacier.org"

    # Connect to the FTP server
    ftp = FTP(server)
    ftp.login(username, password)

    ftp.cwd(directory)
    delete_on_first(ftp)

    try:
        if file:
            # Use temporary filename for atomic upload
            temp_filename = f"{filename}.tmp"

            # Open the local file in binary mode
            with open(file, "rb") as f:
                # Upload to temporary filename first
                ftp.storbinary("STOR " + temp_filename, f)

            # Atomically rename from temp to final filename
            ftp.rename(temp_filename, filename)

        files = ftp.nlst()

        url = f"https://glacier.org/daily/{directory}/{filename}" if file else ""
    except Exception as e:
        print(f"Failed upload {filename}: {e}")
        files = []
        url = ""

    return url, files
