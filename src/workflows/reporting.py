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
