import json
from typing import Any, Dict, List, Optional

from app.database.database import get_connection


def init_set_tables() -> None:
    con = get_connection()

    con.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS set_analysis_id_seq START 1;
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS set_analysis (
            id INTEGER PRIMARY KEY,
            filename TEXT UNIQUE,
            file_path TEXT,
            duration DOUBLE,
            analysis JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    con.close()


def save_set_analysis(
    filename: str,
    file_path: str,
    duration: float,
    analysis: Dict[str, Any],
) -> None:
    init_set_tables()

    con = get_connection()
    analysis_json = json.dumps(analysis, ensure_ascii=False)

    existing = con.execute(
        "SELECT id FROM set_analysis WHERE filename = ?",
        [filename],
    ).fetchone()

    if existing:
        con.execute(
            """
            UPDATE set_analysis
            SET file_path = ?, duration = ?, analysis = ?, updated_at = CURRENT_TIMESTAMP
            WHERE filename = ?
            """,
            [file_path, duration, analysis_json, filename],
        )
    else:
        con.execute(
            """
            INSERT INTO set_analysis (
                id, filename, file_path, duration, analysis
            )
            VALUES (
                nextval('set_analysis_id_seq'), ?, ?, ?, ?
            )
            """,
            [filename, file_path, duration, analysis_json],
        )

    con.close()


def get_set_analysis(filename: str) -> Optional[Dict[str, Any]]:
    init_set_tables()

    con = get_connection()

    row = con.execute(
        """
        SELECT filename, file_path, duration, analysis
        FROM set_analysis
        WHERE filename = ?
        """,
        [filename],
    ).fetchone()

    con.close()

    if row is None:
        return None

    return {
        "filename": row[0],
        "file_path": row[1],
        "duration": row[2],
        "analysis": json.loads(row[3]) if row[3] else None,
    }


def list_set_analyses() -> List[Dict[str, Any]]:
    init_set_tables()

    con = get_connection()

    rows = con.execute(
        """
        SELECT filename, file_path, duration, updated_at
        FROM set_analysis
        ORDER BY updated_at DESC
        """
    ).fetchall()

    con.close()

    return [
        {
            "filename": row[0],
            "file_path": row[1],
            "duration": row[2],
            "updated_at": str(row[3]),
        }
        for row in rows
    ]