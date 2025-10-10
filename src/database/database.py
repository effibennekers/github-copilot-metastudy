"""High-level PaperDatabase composing schema and repositories."""

from typing import List, Dict, Optional

from .schema import SchemaManager
from .metadata_repo import MetadataRepository
from .papers_repo import PapersRepository
from .labels_repo import LabelsRepository


class PaperDatabase(SchemaManager, MetadataRepository, PapersRepository, LabelsRepository):
    def __init__(self):
        super().__init__()
        self.init_database()
