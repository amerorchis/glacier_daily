"""Process-level lock file for preventing concurrent runs.

Uses a PID-based lock file with OS-level advisory locking (fcntl.flock)
for safe cleanup even on crashes. The lock file contains the PID of the
owning process for diagnostic purposes.

On platforms without fcntl (Windows), locking is a no-op — the production
target is a Raspberry Pi (Linux).
"""

import os
import sys
from pathlib import Path

from shared.logging_config import get_logger

logger = get_logger(__name__)

LOCK_FILE = Path(".glacier_daily.lock")

_HAS_FCNTL = sys.platform != "win32"
if _HAS_FCNTL:
    import fcntl


def acquire_lock() -> int | None:
    """Acquire an exclusive lock, writing our PID to the lock file.

    Returns the file descriptor on success, or None if the lock is
    already held by another process. On Windows, always succeeds (no-op).
    """
    if not _HAS_FCNTL:
        logger.info("Lock not supported on this platform, skipping")
        return -1

    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(fd, str(os.getpid()).encode())
        os.fsync(fd)
        logger.info("Lock acquired (PID %d)", os.getpid())
        return fd
    except BlockingIOError:
        logger.warning("Lock file held by another process, aborting")
        os.close(fd)
        return None
    except OSError as e:
        logger.warning("Could not acquire lock: %s", e)
        return None


def release_lock(fd: int | None) -> None:
    """Release the lock and remove the lock file."""
    if fd is None or not _HAS_FCNTL:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        LOCK_FILE.unlink(missing_ok=True)
        logger.info("Lock released")
    except OSError as e:
        logger.warning("Error releasing lock: %s", e)
