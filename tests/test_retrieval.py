import pytest

from agent.config import settings
from agent.ingest import load_chunks
from agent.retriever import HybridRetriever


@pytest.fixture(scope="module")
def retriever():
    return HybridRetriever(load_chunks(settings.docs_dir), settings.embedding_model)


def test_employee_never_sees_confidential(retriever):
    hits = retriever.search("salary range L3 Lead bonus", role="employee", top_k=10)
    assert all(h.chunk.access_level == "all" for h in hits)


def test_executive_can_see_confidential(retriever):
    hits = retriever.search("salary range L3 Lead bonus", role="executive", top_k=4)
    assert hits[0].chunk.doc_id == "HR-SAL-CONF"


@pytest.mark.parametrize("query, expected_prefix", [
    ("เบิกเงิลค่าแท็กซี่ได้เท่าไหร่อ่ะ", "POL-EXP"),
    ("ลาป่วยต้องมีใบแพทย์ป่ะ", "POL-LEAVE"),
    ("How do I reset my password?", "IT-SUP"),
])
def test_slang_and_cross_language_queries_find_right_doc(retriever, query, expected_prefix):
    hits = retriever.search(query, role="employee", top_k=4)
    assert any(h.chunk.doc_id.startswith(expected_prefix) for h in hits)


def test_added_chunks_are_searchable(retriever, tmp_path):
    from agent.ingest import chunk_document, save_upload
    src = tmp_path / "parking.txt"
    src.write_text("Parking policy: employees can park in building B, floor 3. Parking is free.", encoding="utf-8")
    doc = save_upload(src, tmp_path / "uploads", "Parking Policy", "policy", "all")
    retriever.add_chunks(chunk_document(doc))
    hits = retriever.search("Where can I park my car?", role="employee", top_k=2)
    assert hits[0].chunk.doc_id == doc.doc_id
