import json
from typing import Any, Dict, List, Optional

from app.database.database import get_connection


def save_track_analysis(
    filename: str,
    file_path: str,
    file_hash: str,
    duration: float,
    tempo: float,
    musical_key: str,
    camelot: Optional[str],
    analysis: Dict[str, Any],
) -> None:
    con = get_connection()

    analysis_json = json.dumps(analysis, ensure_ascii=False)

    existing = con.execute(
        """
        SELECT id
        FROM track_analysis
        WHERE filename = ?
        """,
        [filename],
    ).fetchone()

    if existing:
        con.execute(
            """
            UPDATE track_analysis
            SET
                file_path = ?,
                file_hash = ?,
                duration = ?,
                tempo = ?,
                musical_key = ?,
                camelot = ?,
                analysis = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE filename = ?
            """,
            [
                file_path,
                file_hash,
                duration,
                tempo,
                musical_key,
                camelot,
                analysis_json,
                filename,
            ],
        )
    else:
        con.execute(
            """
            INSERT INTO track_analysis (
                id,
                filename,
                file_path,
                file_hash,
                duration,
                tempo,
                musical_key,
                camelot,
                analysis
            )
            VALUES (
                nextval('track_analysis_id_seq'),
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                filename,
                file_path,
                file_hash,
                duration,
                tempo,
                musical_key,
                camelot,
                analysis_json,
            ],
        )

    con.close()


def get_track_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    con = get_connection()

    row = con.execute(
        """
        SELECT
            filename,
            file_path,
            file_hash,
            duration,
            tempo,
            musical_key,
            camelot,
            analysis
        FROM track_analysis
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
        "file_hash": row[2],
        "duration": row[3],
        "tempo": row[4],
        "musical_key": row[5],
        "camelot": row[6],
        "analysis": json.loads(row[7]) if row[7] else None,
    }


def list_tracks() -> List[Dict[str, Any]]:
    con = get_connection()

    rows = con.execute(
        """
        SELECT
            filename,
            file_path,
            file_hash,
            duration,
            tempo,
            musical_key,
            camelot
        FROM track_analysis
        ORDER BY filename
        """
    ).fetchall()

    con.close()

    return [
        {
            "filename": row[0],
            "file_path": row[1],
            "file_hash": row[2],
            "duration": row[3],
            "tempo": row[4],
            "musical_key": row[5],
            "camelot": row[6],
        }
        for row in rows
    ]


def delete_track(filename: str) -> None:
    con = get_connection()

    con.execute(
        """
        DELETE FROM track_analysis
        WHERE filename = ?
        """,
        [filename],
    )

    con.close()