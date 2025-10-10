"""Repository voor queues, waaronder labeling_queue."""

from typing import Optional, List, Tuple

from .base import BaseDatabase


class QueuesRepository(BaseDatabase):
    def ensure_queue_tables(self) -> None:
        """Zorg dat de labeling_queue tabel bestaat met kolommen (metadata_id, question_id)."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS labeling_queue (
                    metadata_id TEXT NOT NULL,
                    question_id INTEGER NOT NULL,
                    CONSTRAINT pk_labeling_queue PRIMARY KEY (metadata_id, question_id),
                    CONSTRAINT fk_queue_metadata FOREIGN KEY(metadata_id) REFERENCES metadata(id)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT fk_queue_question FOREIGN KEY(question_id) REFERENCES questions(id)
                        ON DELETE CASCADE ON UPDATE CASCADE
                )
                """
            )
            conn.commit()

    def prepare_metadata_labeling(self, question_id: int, date_after: Optional[str] = None) -> int:
        """Vul labeling_queue met paren (metadata_id, question_id).

        Parameters
        ----------
        question_id : int
            ID van de vraag waarvoor labeling jobs voorbereid worden.
        date_after : Optional[str]
            Datumstring (YYYY-MM-DD). Indien opgegeven, worden alleen metadata
            records met update_date > date_after geselecteerd.

        Returns
        -------
        int
            Aantal metadata records waarvoor een enqueue poging is gedaan
            (per record één rij met opgegeven question_id).
        """
        with self._connect() as conn:
            cur = conn.cursor()
            if date_after:
                cur.execute(
                    "SELECT id FROM metadata WHERE update_date > CAST(%s AS DATE)",
                    (date_after,),
                )
            else:
                cur.execute("SELECT id FROM metadata")

            metadata_ids: List[str] = [row["id"] for row in cur.fetchall()]
            if not metadata_ids:
                return 0

            params: List[Tuple[str, int]] = [(mid, question_id) for mid in metadata_ids]
            cur.executemany(
                """
                INSERT INTO labeling_queue (metadata_id, question_id)
                VALUES (%s, %s)
                ON CONFLICT (metadata_id, question_id) DO NOTHING
                """,
                params,
            )
            conn.commit()
            return len(metadata_ids)


