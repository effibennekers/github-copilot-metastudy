"""
Shared database utilities (connection, logging).
"""

import logging
import psycopg
from psycopg.rows import dict_row

from src.config import DATABASE_CONFIG


class BaseDatabase:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _connect(self):
        """Return a PostgreSQL connection with dict_row factory."""
        pg = DATABASE_CONFIG["pg"]
        conn = psycopg.connect(
            host=pg["host"],
            port=pg["port"],
            dbname=pg["dbname"],
            user=pg["user"],
            password=pg["password"],
        )
        conn.row_factory = dict_row
        return conn
