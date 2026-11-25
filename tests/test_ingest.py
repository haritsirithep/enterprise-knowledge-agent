from pathlib import Path

import pytest

from agent.config import settings
from agent.ingest import chunk_text, clean_text, load_documents, save_upload


def test_catalog_lists_pdfs_and_chats():
    docs = load_documents(settings.docs_dir)
    assert len(docs) == 10
    assert {d.path.suffix for d in docs} == {".pdf", ".txt"}


@pytest.mark.parametrize("dirty, clean", [
    ("ต ้องมีใบรับรองแพทย์", "ต้องมีใบรับรองแพทย์"),  # space before a tone mark
    ("ลาป่ วย", "ลาป่วย"),                              # space after a tone mark
    ("กำ=หนด ทำ_งาน จำ\x12กัด", "กำหนด ทำงาน จำกัด"),     # junk glyph after สระอำ
    ("Hello   world", "Hello world"),
])
def test_clean_text_fixes_thai_pdf_noise(dirty, clean):
    assert clean_text(dirty) == clean


def test_thai_pdf_extracts_cleanly():
    doc = next(d for d in load_documents(settings.docs_dir) if d.doc_id == "POL-EXP-TH")
    assert "ใบรับรองแทนใบเสร็จ" in doc.text
    assert "600 บาทต่อเที่ยว" in doc.text
    assert "=" not in doc.text


def test_chunks_respect_max_size_and_keep_chat_threads_apart():
    thread = "--- thread {i} ---\nA: " + "question " * 15 + "\nB: " + "answer " * 15  # ~250 chars, like a real thread
    text = "\n\n".join(thread.format(i=i) for i in range(3))
    chunks = chunk_text(text, max_chars=600)
    assert len(chunks) == 3
    assert all(c.count("--- thread") == 1 for c in chunks)
    # a lone heading is merged into the next paragraph, not left as a tiny chunk
    assert len(chunk_text("Title\n\n" + thread.format(i=0), max_chars=600)) == 1
    long_text = "\n".join(f"line {i} " + "x" * 50 for i in range(40))
    assert all(len(c) <= 600 for c in chunk_text(long_text, max_chars=600))


def test_save_upload_registers_in_catalog(tmp_path):
    src = tmp_path / "wfh.txt"
    src.write_text("นโยบาย WFH: ทำงานจากบ้านได้ 2 วันต่อสัปดาห์", encoding="utf-8")
    doc = save_upload(src, tmp_path / "uploads", "WFH Policy", "policy", "all")
    assert doc.lang == "th"
    assert [d.doc_id for d in load_documents(tmp_path / "uploads")] == [doc.doc_id]


def test_save_upload_rejects_unsupported_type(tmp_path):
    src = tmp_path / "data.xlsx"
    src.write_bytes(b"fake")
    with pytest.raises(ValueError):
        save_upload(src, tmp_path / "uploads", "x", "policy", "all")
