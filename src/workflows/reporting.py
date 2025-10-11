import logging
from src.database import PaperDatabase

logger = logging.getLogger(__name__)


def print_stats() -> None:
    db = PaperDatabase()
    table_counts: dict[str, int] = {}
    with db._connect() as conn:
        cur = conn.cursor()
        for table in [
            "metadata",
            "papers",
            "labels",
            "questions",
            "metadata_labels",
            "labeling_queue",
            "download_queue",
        ]:
            try:
                cur.execute(f"SELECT COUNT(1) AS count FROM {table}")
                row = cur.fetchone()
                table_counts[table] = row["count"] if row else 0
            except Exception:
                table_counts[table] = 0

    print("\n" + "=" * 60)
    print("DATABASE STATISTIEKEN")
    print("=" * 60)
    print("Tabellen (aantal rijen):")
    for tbl in [
        "metadata",
        "papers",
        "labels",
        "questions",
        "metadata_labels",
        "labeling_queue",
        "download_queue",
    ]:
        print(f"  {tbl}: {table_counts.get(tbl, 0)}")


def list_questions() -> list[str]:
    db = PaperDatabase()
    qrows = db.list_questions()
    lrows = db.list_labels()
    out: list[str] = []
    out.append("Questions:")
    out.extend(
        [
            f"q_id: {r['id']}, q_name: {r['name']}, label_id: {r['label_id']}, label: {r['label_name']}"
            for r in qrows
        ]
    )
    out.append("")
    out.append("Labels:")
    out.extend([f"l_id: {r['id']}, l_name: {r['name']}"] for r in lrows)
    return out


def download_queue_summary() -> list[str]:
    """Maak een samenvatting van de download_queue.

    - Geeft aantallen voor PENDING en COMPLETED
    - Geeft de arxiv_ids weer voor FAILED
    """
    db = PaperDatabase()
    with db._connect() as conn:
        cur = conn.cursor()

        counts: dict[str, int] = {"PENDING": 0, "COMPLETED": 0, "FAILED": 0}
        try:
            cur.execute(
                "SELECT download_status, COUNT(1) AS cnt FROM download_queue GROUP BY download_status"
            )
            for row in cur.fetchall():
                status = row["download_status"]
                cnt = int(row["cnt"]) if row["cnt"] is not None else 0
                if status in counts:
                    counts[status] = cnt
        except Exception:
            pass

        failed_ids: list[str] = []
        try:
            cur.execute(
                "SELECT arxiv_id FROM download_queue WHERE download_status='FAILED' ORDER BY created_at"
            )
            failed_ids = [r["arxiv_id"] for r in cur.fetchall()]
        except Exception:
            failed_ids = []

    lines: list[str] = []
    lines.append("Download Queue Summary:")
    lines.append(f"  PENDING:   {counts['PENDING']}")
    lines.append(f"  COMPLETED: {counts['COMPLETED']}")
    lines.append(f"  FAILED:    {counts['FAILED']}")
    lines.append("")
    lines.append("Failed arxiv_ids:")
    if failed_ids:
        lines.extend([f"  - {aid}" for aid in failed_ids])
    else:
        lines.append("  (geen)")
    return lines
