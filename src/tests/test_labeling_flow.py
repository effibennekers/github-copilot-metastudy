import types

from src.main import run_labeling


class DummyDB:
    def __init__(self, records, labeled_ids, question_row):
        self._records = records
        self._labeled_ids = set(labeled_ids)
        self._question_row = question_row
        self.upserts = []

    # repo API shims
    def get_question_by_id(self, qid):
        return self._question_row

    def get_metadata_ids_by_label(self, label_id):
        return list(self._labeled_ids)

    def iter_metadata_records(self, offset=0, limit=None, batch_size=500):
        yield self._records

    def upsert_metadata_label(self, metadata_id, label_id, confidence_score=None):
        self.upserts.append((metadata_id, label_id, confidence_score))


class DummyLLM:
    def __init__(self, positives):
        self._positives = set(positives)

    def classify_record_to_metadata_label(self, question, metadata_record, label_id):
        meta_id = metadata_record.get("id")
        applicable = meta_id in self._positives
        return {
            "metadata_id": meta_id,
            "label_id": label_id,
            "confidence_score": 0.9 if applicable else None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "_applicable": applicable,
        }


def test_run_labeling_smoke(monkeypatch):
    # arrange: 3 records, 1 al gelabeld, 1 positief
    records = [
        {"id": "A", "title": "t1", "abstract": "a1"},
        {"id": "B", "title": "t2", "abstract": "a2"},
        {"id": "C", "title": "t3", "abstract": "a3"},
    ]
    already = ["A"]
    question_row = {"id": 7, "prompt": "Is about X?", "label_id": 3}
    db = DummyDB(records=records, labeled_ids=already, question_row=question_row)
    llm = DummyLLM(positives=["B"])  # alleen B wordt positief

    # act
    stats = run_labeling(7, db=db, llm=llm, limit=None, offset=0, batch_size=10)

    # assert
    assert stats["skipped_existing"] == 1
    assert stats["labeled"] == 1
    assert db.upserts == [("B", 3, 0.9)]
