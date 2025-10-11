"""Repository voor queues, waaronder labeling_queue en download_queue."""

import json
import re
from typing import Optional, List, Tuple

from .base import BaseDatabase


class QueuesRepository(BaseDatabase):
    def ensure_queue_tables(self) -> None:
        """Zorg dat queue-tabellen bestaan (labeling_queue, download_queue)."""
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
            # download_queue voor paper downloads op basis van arxiv_id (incl. versie)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS download_queue (
                    arxiv_id TEXT PRIMARY KEY,
                    download_status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT ck_download_status CHECK (
                        download_status IN ('PENDING','COMPLETED','FAILED')
                    )
                )
                """
            )
            # Optionele index op status
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_download_queue_status ON download_queue(download_status)"
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
                    "SELECT id FROM metadata WHERE update_date > CAST(%s AS DATE) AND (string_to_array(categories, ' ') @> ARRAY['cs.AI'] OR string_to_array(categories, ' ') @> ARRAY['cs.SE'])",
                    (date_after,),
                )
            else:
                cur.execute(
                    "SELECT id FROM metadata WHERE (string_to_array(categories, ' ') @> ARRAY['cs.AI'] OR string_to_array(categories, ' ') @> ARRAY['cs.SE'])"
                )

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

    def prepare_paper_download(self, label_id: int) -> int:
        """Vul download_queue met arxiv_id's (incl. laatste versie) voor een gegeven label.

        Parameters
        ----------
        label_id : int
            Het label-id waarvoor gekoppelde metadata geselecteerd worden.

        Returns
        -------
        int
            Aantal unieke arxiv_id's waarvoor een enqueue poging is gedaan.
        """
        if not isinstance(label_id, int) or label_id <= 0:
            raise ValueError("label_id moet een positief integer zijn")

        def _extract_last_version(versions_json: Optional[str]) -> int:
            if not versions_json:
                return 1
            try:
                versions = json.loads(versions_json)
                if not isinstance(versions, list) or not versions:
                    return 1
                max_num = 1
                for entry in versions:
                    v = entry.get("version") if isinstance(entry, dict) else None
                    num = None
                    if isinstance(v, str):
                        m = re.search(r"(?i)v?(\d+)", v.strip())
                        if m:
                            num = int(m.group(1))
                    elif isinstance(v, (int, float)):
                        num = int(v)
                    if isinstance(num, int):
                        if num > max_num:
                            max_num = num
                return max_num
            except Exception:
                return 1

        with self._connect() as conn:
            cur = conn.cursor()
            # Haal metadata_id en versions op voor alle metadata met dit label
            cur.execute(
                """
                SELECT ml.metadata_id, m.versions
                FROM metadata_labels ml
                JOIN metadata m ON m.id = ml.metadata_id
                WHERE ml.label_id = %s
                """,
                (label_id,),
            )
            rows = cur.fetchall()
            if not rows:
                return 0

            arxiv_ids: List[str] = []
            for row in rows:
                mid = row["metadata_id"]
                last_ver = _extract_last_version(row["versions"])
                arxiv_ids.append(f"{mid}v{last_ver}")

            # Dedup en prepare inserts
            unique_ids = sorted(set(arxiv_ids))
            if not unique_ids:
                return 0

            params = [(aid, "PENDING") for aid in unique_ids]
            cur.executemany(
                """
                INSERT INTO download_queue (arxiv_id, download_status)
                VALUES (%s, %s)
                ON CONFLICT (arxiv_id) DO NOTHING
                """,
                params,
            )
            conn.commit()
            return len(unique_ids)

    def pop_next_labeling_job(self) -> dict | None:
        """Haal het volgende labeling job item op en verwijder het uit de queue.

        Retourneert dict met keys: metadata_id, question_id, of None als de queue leeg is.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            # pak één item deterministisch
            cur.execute(
                "SELECT metadata_id, question_id FROM labeling_queue ORDER BY metadata_id, question_id LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                return None
            metadata_id = row["metadata_id"]
            question_id = int(row["question_id"])  # dict_row
            # verwijder dit item
            cur.execute(
                "DELETE FROM labeling_queue WHERE metadata_id = %s AND question_id = %s",
                (metadata_id, question_id),
            )
            conn.commit()
            return {"metadata_id": metadata_id, "question_id": question_id}

    def get_pending_downloads(self, limit: int) -> list[str]:
        """Haal tot 'limit' PENDING downloads op uit download_queue."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT arxiv_id
                FROM download_queue
                WHERE download_status = 'PENDING'
                ORDER BY created_at
                LIMIT %s
                """,
                (int(limit),),
            )
            rows = cur.fetchall()
            return [r["arxiv_id"] for r in rows]

    def set_download_status(self, arxiv_id: str, status: str) -> None:
        """Update download_status voor een item in download_queue."""
        if status not in ("PENDING", "COMPLETED", "FAILED"):
            raise ValueError("status moet 'PENDING','COMPLETED' of 'FAILED' zijn")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE download_queue
                SET download_status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE arxiv_id = %s
                """,
                (status, arxiv_id),
            )
            conn.commit()
