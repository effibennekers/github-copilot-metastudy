"""
Importeer en valideer arXiv metadata JSON tegen een schema en schrijf naar de database.
"""

import json
import logging
from pathlib import Path
from typing import Generator, Optional
from itertools import islice
from datetime import datetime

from tqdm import tqdm

from jsonschema import Draft4Validator

from src.database import PaperDatabase


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
    max_records: Optional[int] = None,
    batch_size: int = 1000,
) -> int:
    """Valideer JSON records tegen metadataschema en importeer in metadata tabel.

    Parameters:
    - json_path: pad naar JSON (object, array of JSONL)
    - schema_path: pad naar metadataschema (Draft-04)

    Returns: aantal succesvol geïmporteerde records
    """
    validator = _load_schema(schema_path)
    db = PaperDatabase()

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


def prepare_paper_from_metadata(batch_size: int = 5000, limit: Optional[int] = None) -> int:
    """Maak paper-records aan voor alle metadata records.

    - arxiv_id: concateneer metadata.id met laatste versie uit "versions" (bv. 2510.01576v2)
    - metadata_id: foreign key verwijzing naar metadata.id

    Returns: aantal nieuw aangemaakte paper records
    """
    db = PaperDatabase()
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


def import_labels_questions(labels_path: Optional[str] = None) -> int:
    """Laad labels en questions uit data/labels.json en seed de database.

    Returns: aantal (label, questions) records dat is toegevoegd (som van nieuwe labels en nieuwe questions).
    """
    db = PaperDatabase()

    # Bepaal pad naar labels.json
    if labels_path is None:
        project_root = Path(__file__).resolve().parent.parent
        labels_file = project_root / "data" / "labels.json"
    else:
        labels_file = Path(labels_path)

    if not labels_file.exists():
        raise FileNotFoundError(f"labels.json niet gevonden: {labels_file}")

    data = json.loads(labels_file.read_text(encoding="utf-8"))
    added = 0

    with db._connect() as conn:
        cur = conn.cursor()
        now_iso = None
        for item in data:
            name = (item or {}).get("name")
            questions = (item or {}).get("questions") or []
            if not name:
                continue
            # Insert label (ignore if exists)
            cur.execute(
                "INSERT INTO labels (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (name,),
            )
            cur.execute("SELECT id FROM labels WHERE name = %s", (name,))
            label_row = cur.fetchone()
            if not label_row:
                continue
            label_id = int(label_row["id"])  # dict_row

            for q in questions:
                if not isinstance(q, dict):
                    raise ValueError("Elke vraag moet een object met keys {name,prompt} zijn")
                q_name = q.get("name")
                prompt = q.get("prompt")
                if not q_name or not prompt:
                    raise ValueError("Question items vereisen zowel 'name' als 'prompt'")
                if now_iso is None:
                    now_iso = datetime.now().isoformat()
                cur.execute(
                    """
                    INSERT INTO questions (name, prompt, label_id, created_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name, label_id) DO NOTHING
                    """,
                    (q_name, prompt, label_id, now_iso),
                )
                # Check of er daadwerkelijk een nieuwe rij is toegevoegd (rowcount kan 0 zijn bij DO NOTHING)
                if cur.rowcount > 0:
                    added += 1
        conn.commit()

    logger.info("Seeding voltooid uit %s; %d nieuwe items toegevoegd", labels_file, added)
    return added
