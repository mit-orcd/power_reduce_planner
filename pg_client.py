"""Single place that opens a PostgreSQL connection for the pipeline."""

from __future__ import annotations

import os
import sys

import psycopg2

from config import PG_DB, PG_HOST, PG_PORT, PG_USER


def connect():
    """Return a new psycopg2 connection.

    Reads the password from the PGPASSWORD environment variable, mirroring
    the convention used by the surrounding telegraf_data scripts and by
    psql itself.
    """
    password = os.environ.get("PGPASSWORD")
    if not password:
        sys.stderr.write(
            "Error: PGPASSWORD environment variable is not set.\n"
            "  export PGPASSWORD='your_password'\n"
        )
        sys.exit(2)
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        dbname=PG_DB,
        password=password,
    )


def read_sql(filename: str) -> str:
    """Load a .sql file from the sibling sql/ directory."""
    from config import SQL_DIR
    with open(os.path.join(SQL_DIR, filename)) as f:
        return f.read()
