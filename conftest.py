"""Root conftest — fixes Windows PermissionError on default pytest temp dir.

On Windows, the default temp dir (%TEMP%/pytest-of-<user>) often gets locked
by stale processes, causing PermissionError: [WinError 5]. This conftest
redirects basetemp to a project-local directory that avoids the conflict.
"""

import pathlib
import shutil
import tempfile


def pytest_configure(config):
    # Use a unique temp dir per session to avoid conflicts between
    # concurrent pytest runs and stale directory locks.
    session_id = pathlib.Path(tempfile.mkdtemp(prefix="pytest-sahiixx-"))
    config.option.basetemp = session_id


def pytest_unconfigure(config):
    # Clean up session temp dir after all tests complete.
    basetemp = getattr(config.option, "basetemp", None)
    if basetemp and basetemp.exists():
        shutil.rmtree(basetemp, ignore_errors=True)
