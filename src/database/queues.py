"""Repository voor queues, waaronder labeling_queue."""

from typing import Optional, List, Tuple

from .base import BaseDatabase


class QueuesRepository(BaseDatabase):
    def ensure_queue_tables(self) -> None:
        """Zorg dat de labeling_queue tabel bestaat met één kolom."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS labeling_queue (
                    metadata_id TEXT PRIMARY KEY,
                    CONSTRAINT fk_queue_metadata FOREIGN KEY(metadata_id)
                        REFERENCES metadata(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
                """
            )
            conn.commit()

    def prepare_metadata_labeling(self, date_after: Optional[str] = None) -> int:
        """Vul labeling_queue met metadata_id's na een opgegeven datum.

        Parameters
        ----------
        date_after : Optional[str]
            Datumstring (YYYY-MM-DD). Indien opgegeven, worden alleen metadata
            records met update_date > date_after geselecteerd.

        Returns
        -------
        int
            Aantal metadata records waarvoor een enqueue poging is gedaan.
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

            params: List[Tuple[str]] = [(mid,) for mid in metadata_ids]
            cur.executemany(
                """
                INSERT INTO labeling_queue (metadata_id)
                VALUES (%s)
                ON CONFLICT (metadata_id) DO NOTHING
                """,
                params,
            )
            conn.commit()
            return len(metadata_ids)


