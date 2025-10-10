"""Repository: papers CRUD and queries."""

from datetime import datetime
from typing import List, Dict, Optional

from .base import BaseDatabase


class PapersRepository(BaseDatabase):
    def paper_exists(self, arxiv_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM papers WHERE arxiv_id = %s", (arxiv_id,))
            return cur.fetchone() is not None

    def insert_paper(self, paper_data: Dict) -> None:
        with self._connect() as conn:
            explicit_metadata_id = paper_data.get("metadata_id")
            derived_metadata_id = None
            if explicit_metadata_id is None:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM metadata WHERE id = %s", (paper_data["arxiv_id"],))
                    if cur.fetchone() is not None:
                        derived_metadata_id = paper_data["arxiv_id"]
                except Exception:
                    derived_metadata_id = None

            metadata_id_value = (
                explicit_metadata_id if explicit_metadata_id is not None else derived_metadata_id
            )

            sql = """
                INSERT INTO papers (
                    arxiv_id, download_status, download_type, llm_check_status,
                    created_at, updated_at, metadata_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
            cur = conn.cursor()
            cur.execute(
                sql,
                (
                    paper_data["arxiv_id"],
                    paper_data.get("download_status", "PENDING"),
                    paper_data.get("download_type", "PENDING"),
                    paper_data.get("llm_check_status", "PENDING"),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    metadata_id_value,
                ),
            )
            conn.commit()
        self.logger.info(f"Paper inserted: {paper_data['arxiv_id']}")

    def get_papers_by_status(
        self, download_status: str = None, download_type: str = None, llm_status: str = None
    ) -> List[Dict]:
        query = "SELECT * FROM papers WHERE 1=1"
        params = []
        if download_status:
            query += " AND download_status = %s"
            params.append(download_status)
        if download_type:
            query += " AND download_type = %s"
            params.append(download_type)
        if llm_status:
            query += " AND llm_check_status = %s"
            params.append(llm_status)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            papers: List[Dict] = []
            for row in cur.fetchall():
                papers.append(dict(row))
            return papers

    def validate_download_type(self, download_type: str) -> bool:
        return download_type in ["PENDING", "SRC", "HTML", "PDF"]

    def update_paper_status(self, arxiv_id: str, **kwargs) -> None:
        kwargs["updated_at"] = datetime.now().isoformat()
        if "download_type" in kwargs:
            if not self.validate_download_type(kwargs["download_type"]):
                raise ValueError(
                    f"Invalid download_type: {kwargs['download_type']}. Must be one of: PENDING, SRC, HTML, PDF"
                )
        set_clauses = []
        params = []
        for field, value in kwargs.items():
            set_clauses.append(f"{field} = %s")
            params.append(value)
        params.append(arxiv_id)
        query = f"UPDATE papers SET {', '.join(set_clauses)} WHERE arxiv_id = %s"
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
        self.logger.info(f"Paper updated: {arxiv_id} - {kwargs}")

    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM papers WHERE arxiv_id = %s", (arxiv_id,))
            row = cur.fetchone()
            return dict(row) if row else None
