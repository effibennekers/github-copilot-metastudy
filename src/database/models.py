"""
Database module voor GitHub Copilot Metastudy
Beheert PostgreSQL database voor paper metadata en status tracking
"""

import psycopg
from psycopg.rows import dict_row
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Import configuratie
from src.config import DATABASE_CONFIG


class PaperDatabase:
    def __init__(self, db_path: str = None):
        self.logger = logging.getLogger(__name__)

        self.init_database()

    def _connect(self):
        """Return a PostgreSQL connection."""
        pg = DATABASE_CONFIG["pg"]
        conn = psycopg.connect(
            host=pg["host"],
            port=pg["port"],
            dbname=pg["dbname"],
            user=pg["user"],
            password=pg["password"],
        )
        # Gebruik dict_row zodat fetches dicts opleveren i.p.v. tuples
        conn.row_factory = dict_row
        return conn

    def _execute(self, conn, query: str, params: tuple = ()):
        cur = conn.cursor()
        cur.execute(query, params)
        return cur

    def init_database(self):
        """Initialiseer database schema"""
        with self._connect() as conn:
            # Postgres: cascade drops, bestaan kunnen ontbreken
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS papers CASCADE")
            # Nieuwe tabellen worden afhankelijk van metadata; droppen in correcte volgorde
            cur.execute("DROP TABLE IF EXISTS llm_answers CASCADE")
            cur.execute("DROP TABLE IF EXISTS questions CASCADE")
            cur.execute("DROP TABLE IF EXISTS metadata CASCADE")
            conn.commit()

            # Maak metadata-tabel
            create_metadata = """
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
            conn.cursor().execute(create_metadata)

            # Maak papers-tabel met foreign key naar metadata
            create_papers = """
                CREATE TABLE IF NOT EXISTS papers (
                    arxiv_id TEXT PRIMARY KEY,
                    download_status TEXT DEFAULT 'PENDING',
                    download_type TEXT DEFAULT 'PENDING',
                    llm_check_status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_id TEXT,
                    CONSTRAINT fk_metadata FOREIGN KEY(metadata_id) REFERENCES metadata(id) ON DELETE SET NULL ON UPDATE CASCADE
                )
                """
            conn.cursor().execute(create_papers)

            # Maak questions-tabel (LLM vragen catalogus)
            create_questions = """
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    question_text VARCHAR(512) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            conn.cursor().execute(create_questions)

            # Unieke index op vraagtekst voor idempotent gedrag
            conn.cursor().execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_questions_text ON questions(question_text)"
            )

            # Maak llm_answers-tabel (tussentabel met samengestelde PK)
            create_llm_answers = """
                CREATE TABLE IF NOT EXISTS llm_answers (
                    metadata_id TEXT NOT NULL,
                    question_id INTEGER NOT NULL,
                    answer_value BOOLEAN,
                    confidence_score NUMERIC(3,2),
                    llm_model VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT pk_llm_answers PRIMARY KEY (metadata_id, question_id),
                    CONSTRAINT fk_llm_answers_metadata FOREIGN KEY(metadata_id) REFERENCES metadata(id) ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT fk_llm_answers_question FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
                """
            conn.cursor().execute(create_llm_answers)

            # Indexen voor performance
            cur = conn.cursor()
            cur.execute("CREATE INDEX IF NOT EXISTS idx_download_status ON papers(download_status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_download_type ON papers(download_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_llm_status ON papers(llm_check_status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON papers(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_papers_metadata_id ON papers(metadata_id)")

            # Indexen voor metadata tabel
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

            # Indexen voor questions en llm_answers
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_answers_question_id ON llm_answers(question_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_answers_answer_value ON llm_answers(answer_value)"
            )

            conn.commit()

        self.logger.info("Database initialized (PostgreSQL)")

    def paper_exists(self, arxiv_id: str) -> bool:
        """Check of paper al in database staat"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM papers WHERE arxiv_id = %s", (arxiv_id,))
            return cur.fetchone() is not None

    def insert_paper(self, paper_data: Dict) -> None:
        """Voeg nieuw paper toe aan database"""
        with self._connect() as conn:
            # Bepaal metadata_id: expliciet meegegeven of afgeleid van arxiv_id wanneer metadata aanwezig is
            explicit_metadata_id = paper_data.get("metadata_id")
            derived_metadata_id = None
            if explicit_metadata_id is None:
                # Koppel automatisch als er een metadata record bestaat met dezelfde arxiv_id
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM metadata WHERE id = %s", (paper_data["arxiv_id"],))
                    if cur.fetchone() is not None:
                        derived_metadata_id = paper_data["arxiv_id"]
                except Exception:
                    # Metadata tabel kan nog niet bestaan in sommige testsituaties; dan geen koppeling
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

    # =============================
    # Questions & LLM Answers API
    # =============================

    def get_or_create_question(self, question_text: str) -> int:
        """Haal het id op voor een vraag, of maak deze aan indien niet bestaand."""
        if not question_text:
            raise ValueError("question_text mag niet leeg zijn")

        with self._connect() as conn:
            cur = conn.cursor()
            # Probeer te vinden via unieke index
            cur.execute("SELECT id FROM questions WHERE question_text = %s", (question_text,))
            row = cur.fetchone()
            if row:
                return int(row["id"])  # dict_row

            # Niet gevonden: insert en retourneer id
            cur.execute(
                "INSERT INTO questions (question_text, created_at) VALUES (%s, %s) RETURNING id",
                (question_text, datetime.now().isoformat()),
            )
            new_id = int(cur.fetchone()["id"])  # dict_row
            conn.commit()
            return new_id

    def upsert_llm_answer(
        self,
        metadata_id: str,
        question_id: int,
        answer_value: bool | None,
        confidence_score: float | None = None,
        llm_model: str | None = None,
    ) -> None:
        """Voeg een LLM antwoord in of werk het bij op (metadata_id, question_id)."""
        if not metadata_id:
            raise ValueError("metadata_id is verplicht")
        if not isinstance(question_id, int) or question_id <= 0:
            raise ValueError("question_id moet een positief integer zijn")

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO llm_answers (
                    metadata_id, question_id, answer_value, confidence_score, llm_model, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (metadata_id, question_id)
                DO UPDATE SET
                    answer_value = EXCLUDED.answer_value,
                    confidence_score = EXCLUDED.confidence_score,
                    llm_model = EXCLUDED.llm_model,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    metadata_id,
                    question_id,
                    answer_value,
                    confidence_score,
                    llm_model,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_metadata_ids_by_answer(self, question_id: int, answer_value: bool = True) -> List[str]:
        """Haal lijst met metadata_id's waar het antwoord voor de vraag gelijk is aan answer_value."""
        if not isinstance(question_id, int) or question_id <= 0:
            raise ValueError("question_id moet een positief integer zijn")

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT metadata_id FROM llm_answers WHERE question_id = %s AND answer_value = %s",
                (question_id, answer_value),
            )
            return [row["metadata_id"] for row in cur.fetchall()]

    def get_metadata_ids_by_date_and_answer(
        self,
        question_id: int,
        answer_value: bool = True,
        date_from: str | None = None,
    ) -> List[str]:
        """Selecteer metadata ids op basis van optionele datumfilter (metadata.update_date) en LLM antwoord.

        - date_from: string in formaat YYYY-MM-DD; indien None, geen datumfilter.
        """
        if not isinstance(question_id, int) or question_id <= 0:
            raise ValueError("question_id moet een positief integer zijn")

        base_sql = (
            "SELECT la.metadata_id FROM llm_answers la "
            "INNER JOIN metadata m ON m.id = la.metadata_id "
            "WHERE la.question_id = %s AND la.answer_value = %s"
        )
        params: list = [question_id, answer_value]
        if date_from:
            base_sql += " AND m.update_date > CAST(%s AS DATE)"
            params.append(date_from)
        base_sql += " ORDER BY m.update_date DESC"

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(base_sql, tuple(params))
            return [row["metadata_id"] for row in cur.fetchall()]

    def get_papers_by_status(
        self, download_status: str = None, download_type: str = None, llm_status: str = None
    ) -> List[Dict]:
        """Haal papers op op basis van status"""
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

            papers = []
            for row in cur.fetchall():
                paper = dict(row)
                papers.append(paper)

            return papers

    def validate_download_type(self, download_type: str) -> bool:
        """Valideer download_type waarde"""
        valid_types = ["PENDING", "SRC", "HTML", "PDF"]
        return download_type in valid_types

    def update_paper_status(self, arxiv_id: str, **kwargs) -> None:
        """Update paper status en timestamps"""
        # Always update the updated_at timestamp
        kwargs["updated_at"] = datetime.now().isoformat()

        # Valideer download_type als deze wordt geupdate
        if "download_type" in kwargs:
            if not self.validate_download_type(kwargs["download_type"]):
                raise ValueError(
                    f"Invalid download_type: {kwargs['download_type']}. Must be one of: PENDING, SRC, HTML, PDF"
                )

        # Build UPDATE query dynamically
        set_clauses = []
        params = []

        for field, value in kwargs.items():
            set_clauses.append(f"{field} = %s")
            params.append(value)

        params.append(arxiv_id)  # For WHERE clause

        query = f"UPDATE papers SET {', '.join(set_clauses)} WHERE arxiv_id = %s"

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()

        self.logger.info(f"Paper updated: {arxiv_id} - {kwargs}")

    def update_paper(self, arxiv_id: str, updates: Dict) -> None:
        """Alias voor update_paper_status voor backward compatibility"""
        self.update_paper_status(arxiv_id, **updates)

    def get_statistics(self) -> Dict:
        """Haal database statistieken op"""
        with self._connect() as conn:
            stats = {}

            # Total papers
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) AS count FROM papers")
            stats["total_papers"] = cur.fetchone()["count"]

            # Download status breakdown
            cur.execute(
                """
                SELECT download_status, COUNT(1) AS count
                FROM papers 
                GROUP BY download_status
            """
            )
            stats["download_status"] = {
                row["download_status"]: row["count"] for row in cur.fetchall()
            }

            # Download type breakdown
            cur.execute(
                """
                SELECT download_type, COUNT(1) AS count
                FROM papers 
                GROUP BY download_type
            """
            )
            stats["download_type"] = {row["download_type"]: row["count"] for row in cur.fetchall()}

            # LLM status breakdown
            cur.execute(
                """
                SELECT llm_check_status, COUNT(1) AS count
                FROM papers 
                GROUP BY llm_check_status
            """
            )
            stats["llm_status"] = {row["llm_check_status"]: row["count"] for row in cur.fetchall()}

            return stats

    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        """Haal specifiek paper op via arxiv_id"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM papers WHERE arxiv_id = %s", (arxiv_id,))

            row = cur.fetchone()
            if row:
                paper = dict(row)
                return paper

            return None

    def search_papers_by_category(self, category: str) -> List[Dict]:
        """Zoek papers op basis van categorie (nu via metadata tabel)"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT p.* FROM papers p 
                INNER JOIN metadata m ON p.arxiv_id = m.id 
                WHERE m.categories LIKE %s
                ORDER BY p.created_at DESC
            """,
                (f"%{category}%",),
            )

            papers = []
            for row in cur.fetchall():
                paper = dict(row)
                papers.append(paper)
            return papers

    def get_papers_with_doi(self) -> List[Dict]:
        """Haal papers op die een DOI hebben (via metadata tabel)"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT p.* FROM papers p 
                INNER JOIN metadata m ON p.arxiv_id = m.id 
                WHERE m.doi IS NOT NULL AND m.doi != ''
                ORDER BY p.created_at DESC
            """
            )

            papers = []
            for row in cur.fetchall():
                paper = dict(row)
                papers.append(paper)
            return papers

    def metadata_exists(self, metadata_id: str) -> bool:
        """Check of metadata record al in database staat"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM metadata WHERE id = %s", (metadata_id,))
            return cur.fetchone() is not None

    def insert_metadata(self, metadata_record: Dict) -> None:
        """Voeg nieuw metadata record toe aan database"""
        # Convert arrays to minified JSON strings
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
                    metadata_record.get("submitter"),  # Can be null
                    metadata_record["authors"],
                    metadata_record["title"],
                    metadata_record.get("comments"),  # Can be null
                    metadata_record.get("journal-ref"),  # Can be null (note hyphen)
                    metadata_record.get("doi"),  # Can be null
                    metadata_record.get("report-no"),  # Can be null (note hyphen)
                    metadata_record["categories"],
                    metadata_record.get("license"),  # Can be null
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
        """Voeg meerdere metadata records in één batch toe.

        Retourneert het aantal nieuw ingevoegde records.
        """
        if not metadata_records:
            return 0

        with self._connect() as conn:
            # Bepaal bestaande IDs in één query
            ids = [rec.get("id") for rec in metadata_records if rec.get("id")]
            if not ids:
                return 0

            placeholders = ",".join(["%s"] * len(ids))
            cur = conn.cursor()
            cur.execute(f"SELECT id FROM metadata WHERE id IN ({placeholders})", ids)
            existing_ids = {row["id"] for row in cur.fetchall()}

            # Prepare insert tuples, sla bestaande over
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
            # Beperkte logging om spam te voorkomen bij grote batches
            self.logger.info(f"Metadata batch inserted: {inserted} records")
            return inserted

    def get_metadata_by_id(self, metadata_id: str) -> Optional[Dict]:
        """Haal specifiek metadata record op via id"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM metadata WHERE id = %s", (metadata_id,))

            row = cur.fetchone()
            if row:
                metadata = dict(row)
                # Parse JSON fields back to Python objects
                if metadata["versions"]:
                    metadata["versions"] = json.loads(metadata["versions"])
                if metadata["authors_parsed"]:
                    metadata["authors_parsed"] = json.loads(metadata["authors_parsed"])
                return metadata

            return None

    def get_metadata_by_category(self, category: str) -> List[Dict]:
        """Zoek metadata records op basis van categorie"""
        with self._connect() as conn:
            cur = conn.cursor()
            sql = "SELECT * FROM metadata WHERE categories LIKE %s ORDER BY update_date DESC"
            cur.execute(sql, (f"%{category}%",))
            records = []
            for row in cur.fetchall():
                metadata = dict(row)
                # Parse JSON fields back to Python objects
                if metadata["versions"]:
                    metadata["versions"] = json.loads(metadata["versions"])
                if metadata["authors_parsed"]:
                    metadata["authors_parsed"] = json.loads(metadata["authors_parsed"])
                records.append(metadata)
            return records

    def get_metadata_statistics(self) -> Dict:
        """Haal metadata statistieken op"""
        with self._connect() as conn:
            stats = {}

            # Total metadata records
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) AS count FROM metadata")
            stats["total_metadata"] = cur.fetchone()["count"]

            # Records with DOI
            cur.execute(
                "SELECT COUNT(1) AS count FROM metadata WHERE doi IS NOT NULL AND doi != ''"
            )
            stats["with_doi"] = cur.fetchone()["count"]

            # Records without submitter
            cur.execute("SELECT COUNT(1) AS count FROM metadata WHERE submitter IS NULL")
            stats["null_submitter"] = cur.fetchone()["count"]

            # Most common categories (top 10)
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

    def search_metadata_by_title(self, title_search: str) -> List[Dict]:
        """Zoek metadata records op basis van titel"""
        with self._connect() as conn:
            cur = conn.cursor()
            sql = "SELECT * FROM metadata WHERE title LIKE %s ORDER BY update_date DESC"
            cur.execute(sql, (f"%{title_search}%",))
            records = []
            for row in cur.fetchall():
                metadata = dict(row)
                # Parse JSON fields back to Python objects
                if metadata["versions"]:
                    metadata["versions"] = json.loads(metadata["versions"])
                if metadata["authors_parsed"]:
                    metadata["authors_parsed"] = json.loads(metadata["authors_parsed"])
                records.append(metadata)
            return records
