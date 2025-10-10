"""Repository voor queues, waaronder labeling_queue."""

from typing import Optional, List, Tuple

from .base import BaseDatabase


class QueuesRepository(BaseDatabase):
    def ensure_queue_tables(self) -> None:
        """Zorg dat de labeling_queue tabel bestaat met kolommen (metadata_id, question_id).

        Voert een eenvoudige migratie uit indien de tabel al bestaat met alleen
        `metadata_id` als primaire sleutel.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            # Maak tabel aan indien niet aanwezig (met beide kolommen)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS labeling_queue (
                    metadata_id TEXT NOT NULL,
                    question_id INTEGER NOT NULL
                )
                """
            )
            # Voeg question_id kolom toe als migratiepad
            cur.execute(
                """
                ALTER TABLE labeling_queue
                ADD COLUMN IF NOT EXISTS question_id INTEGER
                """
            )
            # Verwijder eventuele rijen zonder question_id (van oude staat)
            cur.execute("DELETE FROM labeling_queue WHERE question_id IS NULL")
            # Drop bestaande constraints en voeg correcte constraints toe
            cur.execute(
                "ALTER TABLE labeling_queue DROP CONSTRAINT IF EXISTS pk_labeling_queue"
            )
            cur.execute(
                "ALTER TABLE labeling_queue DROP CONSTRAINT IF EXISTS labeling_queue_pkey"
            )
            cur.execute(
                "ALTER TABLE labeling_queue DROP CONSTRAINT IF EXISTS fk_queue_metadata"
            )
            cur.execute(
                "ALTER TABLE labeling_queue DROP CONSTRAINT IF EXISTS fk_queue_question"
            )
            cur.execute(
                """
                ALTER TABLE labeling_queue
                ADD CONSTRAINT pk_labeling_queue PRIMARY KEY (metadata_id, question_id)
                """
            )
            cur.execute(
                """
                ALTER TABLE labeling_queue
                ADD CONSTRAINT fk_queue_metadata
                FOREIGN KEY(metadata_id) REFERENCES metadata(id)
                ON DELETE CASCADE ON UPDATE CASCADE
                """
            )
            cur.execute(
                """
                ALTER TABLE labeling_queue
                ADD CONSTRAINT fk_queue_question
                FOREIGN KEY(question_id) REFERENCES questions(id)
                ON DELETE CASCADE ON UPDATE CASCADE
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


