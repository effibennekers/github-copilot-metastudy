"""Repository: labels, questions, and metadata_labels operations."""

from datetime import datetime
from typing import List

from .base import BaseDatabase


class LabelsRepository(BaseDatabase):
    def get_or_create_label(self, name: str) -> int:
        if not name:
            raise ValueError("label name mag niet leeg zijn")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM labels WHERE name = %s", (name,))
            row = cur.fetchone()
            if row:
                return int(row["id"])  # dict_row
            cur.execute("INSERT INTO labels (name) VALUES (%s) RETURNING id", (name,))
            new_id = int(cur.fetchone()["id"])  # dict_row
            conn.commit()
            return new_id

    def get_or_create_question(self, prompt: str, label_id: int) -> int:
        if not prompt:
            raise ValueError("prompt mag niet leeg zijn")
        if not isinstance(label_id, int) or label_id <= 0:
            raise ValueError("label_id moet een positief integer zijn")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM questions WHERE prompt = %s AND label_id = %s",
                (prompt, label_id),
            )
            row = cur.fetchone()
            if row:
                return int(row["id"])  # dict_row
            cur.execute(
                "INSERT INTO questions (prompt, label_id, created_at) VALUES (%s, %s, %s) RETURNING id",
                (prompt, label_id, datetime.now().isoformat()),
            )
            new_id = int(cur.fetchone()["id"])  # dict_row
            conn.commit()
            return new_id

    def upsert_metadata_label(
        self, metadata_id: str, label_id: int, confidence_score: float | None = None
    ) -> None:
        if not metadata_id:
            raise ValueError("metadata_id is verplicht")
        if not isinstance(label_id, int) or label_id <= 0:
            raise ValueError("label_id moet een positief integer zijn")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO metadata_labels (
                    metadata_id, label_id, confidence_score, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (metadata_id, label_id)
                DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    metadata_id,
                    label_id,
                    confidence_score,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_metadata_ids_by_label(self, label_id: int) -> List[str]:
        if not isinstance(label_id, int) or label_id <= 0:
            raise ValueError("label_id moet een positief integer zijn")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT metadata_id FROM metadata_labels WHERE label_id = %s", (label_id,))
            return [row["metadata_id"] for row in cur.fetchall()]


