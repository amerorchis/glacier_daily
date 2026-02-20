"""
This module provides FTP functionalities including deleting old files and uploading new files.
"""

import contextlib
import ftplib
from datetime import datetime, timedelta
from ftplib import FTP
from typing import Optional

from shared.datetime_utils import now_mountain
from shared.settings import get_settings


def delete_on_first(ftp: FTP) -> None:
    """
    Deletes files on the FTP server that are older than 6 months if the current date is the first of the month.

    Args:
        ftp (FTP): An instance of the FTP class connected to the server.
    """
    current_date = now_mountain()

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


class FTPSession:
    """Reusable FTP session that holds one connection open
    for multiple uploads."""

    def __init__(self) -> None:
        self._ftp: Optional[FTP] = None
        self._cleaned_dirs: set[str] = set()

    def __enter__(self) -> "FTPSession":
        settings = get_settings()
        self._ftp = FTP(settings.FTP_SERVER)  # noqa: S321
        self._ftp.login(settings.FTP_USERNAME, settings.FTP_PASSWORD)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._ftp:
            with contextlib.suppress(OSError, *ftplib.all_errors):
                self._ftp.quit()
            self._ftp = None

    def upload(
        self, directory: str, filename: str, file: Optional[str] = None
    ) -> tuple[str, list[str]]:
        """Upload a file reusing the existing connection. Runs delete_on_first once per directory."""
        assert self._ftp is not None, "FTPSession must be used as a context manager"

        self._ftp.cwd("/")
        self._ftp.cwd(directory)

        if directory not in self._cleaned_dirs:
            delete_on_first(self._ftp)
            self._cleaned_dirs.add(directory)

        try:
            if file:
                temp_filename = f"{filename}.tmp"
                with open(file, "rb") as f:
                    self._ftp.storbinary("STOR " + temp_filename, f)
                self._ftp.rename(temp_filename, filename)

            files = self._ftp.nlst()
            url = f"https://glacier.org/daily/{directory}/{filename}" if file else ""
        except Exception as e:
            print(f"Failed upload {filename}: {e}")
            files = []
            url = ""

        return url, files


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
    settings = get_settings()

    # Connect to the FTP server
    ftp = FTP(settings.FTP_SERVER)  # noqa: S321
    ftp.login(settings.FTP_USERNAME, settings.FTP_PASSWORD)

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
    finally:
        ftp.quit()

    return url, files
