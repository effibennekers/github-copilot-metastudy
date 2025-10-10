"""Repository: labels, questions, and metadata_labels operations."""

from datetime import datetime
from typing import List

from .base import BaseDatabase


class LabelsRepository(BaseDatabase):
    def ensure_labels_tables(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            # labels
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS labels (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL
                )
                """
            )
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_labels_name ON labels(name)")
            # questions
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    label_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_questions_label FOREIGN KEY(label_id)
                        REFERENCES labels(id) ON DELETE CASCADE
                )
                """
            )
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_questions_prompt_label ON questions(prompt, label_id)"
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_questions_label_id ON questions(label_id)")
            # metadata_labels
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata_labels (
                    metadata_id TEXT NOT NULL,
                    label_id INTEGER NOT NULL,
                    confidence_score NUMERIC(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT pk_metadata_labels PRIMARY KEY (metadata_id, label_id),
                    CONSTRAINT fk_metadata_labels_metadata FOREIGN KEY(metadata_id)
                        REFERENCES metadata(id) ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT fk_metadata_labels_label FOREIGN KEY(label_id)
                        REFERENCES labels(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_metadata_labels_label_id ON metadata_labels(label_id)"
            )
            conn.commit()
    def get_question_by_id(self, question_id: int) -> dict | None:
        """Haal een question op met bijbehorende label_id.

        Retourneert dict met keys: id, prompt, label_id
        """
        if not isinstance(question_id, int) or question_id <= 0:
            raise ValueError("question_id moet een positief integer zijn")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, prompt, label_id FROM questions WHERE id = %s",
                (question_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

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
