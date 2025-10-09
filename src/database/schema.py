"""
Database schema creation and indexes.
"""

from .base import BaseDatabase


class SchemaManager(BaseDatabase):
    def init_database(self):
        with self._connect() as conn:
            cur = conn.cursor()
            # Drop order respecting FKs
            cur.execute("DROP TABLE IF EXISTS papers CASCADE")
            cur.execute("DROP TABLE IF EXISTS metadata_labels CASCADE")
            cur.execute("DROP TABLE IF EXISTS questions CASCADE")
            cur.execute("DROP TABLE IF EXISTS labels CASCADE")
            cur.execute("DROP TABLE IF EXISTS metadata CASCADE")
            conn.commit()

            # metadata
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

            # papers
            cur.execute(
                """
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
            )

            # labels
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS labels (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL
                )
                """
            )

            # questions
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    label_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_questions_label FOREIGN KEY(label_id) REFERENCES labels(id) ON DELETE CASCADE
                )
                """
            )

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
                    CONSTRAINT fk_metadata_labels_metadata FOREIGN KEY(metadata_id) REFERENCES metadata(id) ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT fk_metadata_labels_label FOREIGN KEY(label_id) REFERENCES labels(id) ON DELETE CASCADE ON UPDATE CASCADE
                )
                """
            )

            # indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_download_status ON papers(download_status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_download_type ON papers(download_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_llm_status ON papers(llm_check_status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON papers(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_papers_metadata_id ON papers(metadata_id)")

            cur.execute("CREATE INDEX IF NOT EXISTS idx_metadata_categories ON metadata(categories)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_metadata_update_date ON metadata(update_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_metadata_doi ON metadata(doi)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_metadata_created_at ON metadata(created_at)")

            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_labels_name ON labels(name)")
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_questions_prompt_label ON questions(prompt, label_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_questions_label_id ON questions(label_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_metadata_labels_label_id ON metadata_labels(label_id)"
            )

            conn.commit()
        self.logger.info("Database initialized (PostgreSQL)")


