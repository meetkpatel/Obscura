"""Browser-development ASGI entry point for the synthetic hackathon demo."""

import os

from server.database.core.connection import initialize_database
from server.server import initialize_and_get_app


def create_dev_app():
    """Initialize the encrypted demo database before loading API routers."""
    passphrase = os.getenv("DB_ENCRYPTION_KEY", "synthetic-demo-only")
    initialize_database(passphrase=passphrase)
    return initialize_and_get_app()


app = create_dev_app()
