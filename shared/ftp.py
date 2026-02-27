"""
This module provides FTP functionalities including deleting old files and uploading new files.
"""

import contextlib
import ftplib
from datetime import datetime, timedelta
from ftplib import FTP

from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger
from shared.settings import get_settings

logger = get_logger(__name__)


def delete_on_first(ftp: FTP) -> None:
    """
    Deletes files on the FTP server that are older than 6 months if the current date is the first of the month.

    Args:
        ftp (FTP): An instance of the FTP class connected to the server.
    """
    current_date = now_mountain()

    if current_date.day == 1:
        logger.info("First of the month: deleting files over 6 months old.")
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
        self._ftp: FTP | None = None
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
        self, directory: str, filename: str, file: str | None = None
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
            logger.error("Failed upload %s: %s", filename, e)
            files = []
            url = ""

        return url, files
