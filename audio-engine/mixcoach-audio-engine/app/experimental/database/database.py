from pathlib import Path

import duckdb


DATABASE_PATH = Path("mixcoach.duckdb")


def get_connection():
    return duckdb.connect(str(DATABASE_PATH))