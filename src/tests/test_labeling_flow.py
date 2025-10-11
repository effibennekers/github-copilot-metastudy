import pytest

from src.workflows.labeling import run_labeling


class DummyDB:
    jobs = [
        {"metadata_id": "A", "question_id": 7},
        {"metadata_id": "B", "question_id": 7},
        {"metadata_id": "C", "question_id": 7},
    ]
    upserts = []

    def __init__(self):
        pass

    def pop_next_labeling_job(self):
        return self.jobs.pop(0) if self.jobs else None

    def get_question_by_id(self, qid):
        return {"id": 7, "prompt": "Is about X?", "label_id": 3}

    def get_title_and_abstract(self, metadata_id):
        titles = {"A": "t1", "B": "t2", "C": "t3"}
        return {"title": titles[metadata_id], "abstract": "a"}

    def upsert_metadata_label(self, metadata_id, label_id, confidence_score=None):
        self.upserts.append((metadata_id, label_id, confidence_score))


class DummyChatClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyChecker:
    def __init__(self, _chat_client):
        pass

    async def classify_title_abstract_structured_async(self, question, title, abstract):
        applicable = title == "t2"
        return {
            "answer_value": applicable,
            "confidence_score": 0.9 if applicable else None,
        }


def test_run_labeling_queue_smoke(monkeypatch):
    import src.workflows.labeling as labeling_mod

    DummyDB.jobs = [
        {"metadata_id": "A", "question_id": 7},
        {"metadata_id": "B", "question_id": 7},
        {"metadata_id": "C", "question_id": 7},
    ]
    DummyDB.upserts = []

    monkeypatch.setattr(labeling_mod, "PaperDatabase", DummyDB)
    monkeypatch.setattr(labeling_mod, "LLMChatClient", DummyChatClient)
    monkeypatch.setattr(labeling_mod, "LLMChecker", DummyChecker)

    stats = run_labeling(labeling_jobs=3)

    assert stats["errors"] == 0
    assert stats["skipped_missing"] == 0
    assert stats["labeled"] == 1
    assert DummyDB.upserts == [("B", 3, 0.9)]
