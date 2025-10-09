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


def _build_arxiv_id_from_metadata(meta_id: str, versions: object) -> str:
    """Bepaal het volledige arXiv ID inclusief laatste versiesuffix.

    - meta_id: basis ID zonder versiesuffix, bv. "2510.01576"
    - versions: lijst (of JSON-string) met versieobjecten, bv. [{"version": "v1"}, {"version": "v2"}]
    """
    try:
        if isinstance(versions, str):
            versions_list = json.loads(versions)
        else:
            versions_list = versions or []
    except Exception:
        versions_list = []

    suffix = "v1"
    if isinstance(versions_list, list) and versions_list:
        last = versions_list[-1]
        if isinstance(last, dict):
            candidate = last.get("version") or last.get("v")
            if isinstance(candidate, str) and candidate:
                suffix = candidate if candidate.startswith("v") else f"v{candidate}"
        elif isinstance(last, str):
            suffix = last if last.startswith("v") else f"v{last}"

    return f"{meta_id}{suffix}"


def prepare_paper_from_metadata(
    db_path: Optional[str] = None, batch_size: int = 5000, limit: Optional[int] = None
) -> int:
    """Maak paper-records aan voor alle metadata records.

    - arxiv_id: concateneer metadata.id met laatste versie uit "versions" (bv. 2510.01576v2)
    - metadata_id: foreign key verwijzing naar metadata.id

    Returns: aantal nieuw aangemaakte paper records
    """
    db = PaperDatabase(db_path)
    created = 0

    # Stream metadata records in batches om geheugen te sparen
    with db._connect() as conn:
        cur = conn.cursor(name="metadata_iter")  # server-side cursor voor streaming
        base_sql = "SELECT id, versions FROM metadata ORDER BY id"
        if limit and limit > 0:
            # server-side cursor ondersteunt LIMIT in query
            cur.execute(f"{base_sql} LIMIT %s", (limit,))
        else:
            cur.execute(base_sql)

        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break

            for row in rows:
                meta_id = row["id"]
                versions = row.get("versions")
                arxiv_id = _build_arxiv_id_from_metadata(meta_id, versions)

                try:
                    if db.paper_exists(arxiv_id):
                        continue
                    db.insert_paper({"arxiv_id": arxiv_id, "metadata_id": meta_id})
                    created += 1
                except Exception as exc:
                    logger.warning("Overslaan van %s door fout: %s", meta_id, exc)

    logger.info("%d paper records aangemaakt uit metadata", created)
    return created
