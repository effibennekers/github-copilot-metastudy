"""Repository: metadata CRUD and queries."""

import json
from datetime import datetime
from typing import List, Dict, Optional

from .base import BaseDatabase


class MetadataRepository(BaseDatabase):
    def ensure_metadata_tables(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    id TEXT PRIMARY KEY,
                    submitter TEXT,
                    authors TEXT NOT NULL,
                    title TEXT NOT NULL,
                    comments TEXT,
                    journal_ref TEXT,
                    doi TEXT,
                    report_no TEXT,
                    categories TEXT NOT NULL,
                    license TEXT,
                    abstract TEXT NOT NULL,
                    versions TEXT NOT NULL,
                    update_date DATE NOT NULL,
                    authors_parsed TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # indexen
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_metadata_categories ON metadata(categories)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_metadata_update_date ON metadata(update_date)"
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_metadata_doi ON metadata(doi)")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_metadata_created_at ON metadata(created_at)"
            )
            conn.commit()
    def metadata_exists(self, metadata_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM metadata WHERE id = %s", (metadata_id,))
            return cur.fetchone() is not None

    def insert_metadata(self, metadata_record: Dict) -> None:
        versions_json = json.dumps(metadata_record.get("versions", []), separators=(",", ":"))
        authors_parsed_json = json.dumps(
            metadata_record.get("authors_parsed", []), separators=(",", ":")
        )
        with self._connect() as conn:
            sql = """
                INSERT INTO metadata (
                    id, submitter, authors, title, comments, journal_ref, doi, report_no,
                    categories, license, abstract, versions, update_date, authors_parsed,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS DATE), %s, %s, %s
                )
                """
            cur = conn.cursor()
            cur.execute(
                sql,
                (
                    metadata_record["id"],
                    metadata_record.get("submitter"),
                    metadata_record["authors"],
                    metadata_record["title"],
                    metadata_record.get("comments"),
                    metadata_record.get("journal-ref"),
                    metadata_record.get("doi"),
                    metadata_record.get("report-no"),
                    metadata_record["categories"],
                    metadata_record.get("license"),
                    metadata_record["abstract"],
                    versions_json,
                    metadata_record["update_date"],
                    authors_parsed_json,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        self.logger.info(f"Metadata inserted: {metadata_record['id']}")

    def insert_metadata_batch(self, metadata_records: List[Dict]) -> int:
        if not metadata_records:
            return 0
        with self._connect() as conn:
            ids = [rec.get("id") for rec in metadata_records if rec.get("id")]
            if not ids:
                return 0
            placeholders = ",".join(["%s"] * len(ids))
            cur = conn.cursor()
            cur.execute(f"SELECT id FROM metadata WHERE id IN ({placeholders})", ids)
            existing_ids = {row["id"] for row in cur.fetchall()}
            rows_to_insert = []
            now_iso = datetime.now().isoformat()
            for rec in metadata_records:
                rec_id = rec.get("id")
                if not rec_id or rec_id in existing_ids:
                    continue
                versions_json = json.dumps(rec.get("versions", []), separators=(",", ":"))
                authors_parsed_json = json.dumps(
                    rec.get("authors_parsed", []), separators=(",", ":")
                )
                rows_to_insert.append(
                    (
                        rec_id,
                        rec.get("submitter"),
                        rec["authors"],
                        rec["title"],
                        rec.get("comments"),
                        rec.get("journal-ref"),
                        rec.get("doi"),
                        rec.get("report-no"),
                        rec["categories"],
                        rec.get("license"),
                        rec["abstract"],
                        versions_json,
                        rec["update_date"],
                        authors_parsed_json,
                        now_iso,
                        now_iso,
                    )
                )
            if not rows_to_insert:
                return 0
            sql = """
                INSERT INTO metadata (
                    id, submitter, authors, title, comments, journal_ref, doi, report_no,
                    categories, license, abstract, versions, update_date, authors_parsed,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS DATE), %s, %s, %s
                )
                """
            cur.executemany(sql, rows_to_insert)
            conn.commit()
            inserted = len(rows_to_insert)
        self.logger.info(f"Metadata batch inserted: {inserted} records")
        return inserted

    def get_metadata_by_id(self, metadata_id: str) -> Optional[Dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM metadata WHERE id = %s", (metadata_id,))
            row = cur.fetchone()
            if row:
                metadata = dict(row)
                if metadata["versions"]:
                    metadata["versions"] = json.loads(metadata["versions"])
                if metadata["authors_parsed"]:
                    metadata["authors_parsed"] = json.loads(metadata["authors_parsed"])
                return metadata
            return None

    def get_metadata_by_category(self, category: str) -> List[Dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            sql = "SELECT * FROM metadata WHERE categories LIKE %s ORDER BY update_date DESC"
            cur.execute(sql, (f"%{category}%",))
            records: List[Dict] = []
            for row in cur.fetchall():
                metadata = dict(row)
                if metadata["versions"]:
                    metadata["versions"] = json.loads(metadata["versions"])
                if metadata["authors_parsed"]:
                    metadata["authors_parsed"] = json.loads(metadata["authors_parsed"])
                records.append(metadata)
            return records

    def get_metadata_statistics(self) -> Dict:
        with self._connect() as conn:
            stats: Dict = {}
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) AS count FROM metadata")
            stats["total_metadata"] = cur.fetchone()["count"]
            cur.execute(
                "SELECT COUNT(1) AS count FROM metadata WHERE doi IS NOT NULL AND doi != ''"
            )
            stats["with_doi"] = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(1) AS count FROM metadata WHERE submitter IS NULL")
            stats["null_submitter"] = cur.fetchone()["count"]
            cur.execute(
                """
                SELECT categories, COUNT(1) as count 
                FROM metadata 
                GROUP BY categories 
                ORDER BY count DESC 
                LIMIT 10
                """
            )
            stats["top_categories"] = {row["categories"]: row["count"] for row in cur.fetchall()}
            return stats
