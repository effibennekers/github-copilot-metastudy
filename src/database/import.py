"""
Importeer en valideer arXiv metadata JSON tegen een schema en schrijf naar de database.
"""

import json
import logging
from pathlib import Path
from typing import Generator, Optional
from itertools import islice

from tqdm import tqdm

from jsonschema import Draft4Validator

from src.database.models import PaperDatabase


logger = logging.getLogger(__name__)


def _load_schema(schema_path: str) -> Draft4Validator:
    """Laad en compileer het JSON Schema (Draft-04)."""
    schema_file = Path(schema_path)
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema niet gevonden: {schema_file}")
    with schema_file.open("r", encoding="utf-8") as fh:
        schema_obj = json.load(fh)
    return Draft4Validator(schema_obj)


def _iter_json_records(json_path: str) -> Generator[dict, None, None]:
    """Itereer records uit een JSON-bestand.

    Ondersteunt:
    - Enkel object: { ... }
    - Array van objecten: [ {...}, {...} ]
    - JSON Lines: elke regel een geldig JSON object
    """
    p = Path(json_path)
    if not p.exists():
        raise FileNotFoundError(f"JSON bestand niet gevonden: {p}")

    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if not isinstance(rec, dict):
                raise ValueError("Elke regel in JSON Lines moet een JSON object zijn")
            yield rec


def import_metadata(
    json_path: str,
    schema_path: str,
    db_path: Optional[str] = None,
    max_records: Optional[int] = None,
    batch_size: int = 1000,
) -> int:
    """Valideer JSON records tegen metadataschema en importeer in metadata tabel.

    Parameters:
    - json_path: pad naar JSON (object, array of JSONL)
    - schema_path: pad naar metadataschema (Draft-04)
    - db_path: optioneel alternatief databasepad

    Returns: aantal succesvol geïmporteerde records
    """
    validator = _load_schema(schema_path)
    db = PaperDatabase(db_path)

    inserted_count = 0
    # Gebruik tqdm voortgang; bij onbekend totaal toont tqdm dynamische voortgang
    records_iter = _iter_json_records(json_path)
    if max_records is not None and max_records > 0:
        records_iter = islice(records_iter, max_records)

    buffer: list[dict] = []
    if batch_size <= 0:
        batch_size = 1000

    for record in tqdm(records_iter, desc="Importing metadata", unit="rec"):
        # Valideer record
        errors = sorted(validator.iter_errors(record), key=lambda e: e.path)
        if errors:
            messages = "; ".join([f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors])
            raise ValueError(f"Record validatie faalde: {messages}")

        rec_id = record.get("id")
        if not rec_id:
            raise ValueError("Record mist verplicht veld 'id'")

        buffer.append(record)

        if len(buffer) >= batch_size:
            inserted = db.insert_metadata_batch(buffer)
            inserted_count += inserted
            buffer.clear()

    # flush laatste batch
    if buffer:
        inserted = db.insert_metadata_batch(buffer)
        inserted_count += inserted

    logger.info("%d metadata records geïmporteerd uit %s", inserted_count, json_path)
    return inserted_count
