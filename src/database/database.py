"""High-level PaperDatabase composing schema and repositories."""

from typing import List, Dict, Optional

from .metadata_repo import MetadataRepository
from .papers_repo import PapersRepository
from .labels_repo import LabelsRepository
from .queues import QueuesRepository


class PaperDatabase(MetadataRepository, PapersRepository, LabelsRepository, QueuesRepository):
    def __init__(self):
        super().__init__()
        # Zorg dat alle tabellen per repository bestaan
        self.ensure_metadata_tables()
        self.ensure_papers_tables()
        self.ensure_labels_tables()
        self.ensure_queue_tables()
