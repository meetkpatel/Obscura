"""Shared test configuration — initializes an isolated encrypted test database."""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

from server.database.core.connection import initialize_database

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DB_ENCRYPTION_KEY", "obscura-test-key")

_test_db_dir = Path(tempfile.mkdtemp(prefix="obscura-tests-"))
atexit.register(shutil.rmtree, _test_db_dir, True)
initialize_database(db_dir=_test_db_dir)
