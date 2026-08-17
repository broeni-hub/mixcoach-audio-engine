from app.database.database import get_connection


def init_database():
    con = get_connection()

    con.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS track_analysis_id_seq START 1;
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS track_analysis (
            id INTEGER PRIMARY KEY,
            filename TEXT UNIQUE,
            file_path TEXT,
            file_hash TEXT,
            duration DOUBLE,
            tempo DOUBLE,
            musical_key TEXT,
            camelot TEXT,
            analysis JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    con.close()


if __name__ == "__main__":
    init_database()