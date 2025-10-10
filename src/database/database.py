"""High-level PaperDatabase composing schema and repositories."""

from typing import List, Dict, Optional

from .schema import SchemaManager
from .metadata_repo import MetadataRepository
from .papers_repo import PapersRepository
from .labels_repo import LabelsRepository
from .queues import QueuesRepository


class PaperDatabase(SchemaManager, MetadataRepository, PapersRepository, LabelsRepository, QueuesRepository):
    def __init__(self):
        super().__init__()
        self.init_database()
        # Zorg dat alle tabellen per repository bestaan
        self.ensure_metadata_tables()
        self.ensure_papers_tables()
        self.ensure_labels_tables()
        self.ensure_queue_tables()
