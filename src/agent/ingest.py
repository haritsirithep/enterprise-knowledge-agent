"""Load documents (PDF / TXT / MD) listed in catalog.yaml files, clean the text, and split it into chunks.

A catalog entry holds the metadata a PDF can't carry itself:
  doc_id, title, file, lang, doc_type ("policy" = official, "chat" = unofficial), access_level ("all" / "executive")
"""
import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml
from pypdf import PdfReader

SUPPORTED_TYPES = {".pdf", ".txt", ".md"}
MAX_CHUNK_CHARS = 600
CATALOG = "catalog.yaml"

# Thai vowel and tone marks that sit above/below a consonant.
_THAI_MARKS = "ัิ-ฺ็-๎"
_THAI_CHAR = "ก-๎"


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    path: Path
    lang: str
    doc_type: str
    access_level: str
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str  # short label: first line of the chunk
    text: str
    lang: str
    doc_type: str
    access_level: str


def clean_text(text: str) -> str:
    """Fix common PDF extraction noise.

    PDF extractors often insert spaces around Thai vowel/tone marks ("ต ้อง", "ป่ วย").
    That breaks keyword search, so we remove spaces next to a mark when the other side is Thai.
    Trade-off: this can also join a real phrase space in Thai, which is harmless for search.
    """
    # Control characters are always extraction junk.
    text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", text)
    # Shaped fonts split สระอำ into two glyphs, and pypdf maps the leftover glyph to a random symbol
    # ("กำ=หนด", "ทำ_งาน"). Drop one stray symbol right after ำ, but keep normal punctuation.
    text = re.sub(r"(?<=ำ)[^฀-๿\sA-Za-z0-9.,!?:;()\"']", "", text)
    text = re.sub(rf"[ \t]+(?=[{_THAI_MARKS}])", "", text)
    text = re.sub(rf"(?<=[{_THAI_MARKS}])[ \t]+(?=[{_THAI_CHAR}])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        pages = [page.extract_text() or "" for page in PdfReader(path).pages]
        return clean_text("\n\n".join(pages))
    return clean_text(path.read_text(encoding="utf-8"))


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Pack paragraphs (or lines, if a paragraph is too long) into chunks of up to max_chars.

    Works for any document, not just ones with markdown headings. The last line of each chunk is
    repeated at the start of the next one (overlap), so a fact split across chunks keeps its context.
    """
    chunks, current = [], []
    for paragraph in re.split(r"\n\s*\n", text):
        for line in paragraph.splitlines() or [""]:
            line = line.strip()
            if not line:
                continue
            if current and len("\n".join(current + [line])) > max_chars:
                chunks.append("\n".join(current))
                current = current[-1:]  # overlap
            current.append(line)
        # A paragraph boundary (e.g. the end of a chat thread) closes the chunk, so threads don't mix.
        # Very small paragraphs (a lone heading) are merged with the next one instead of becoming tiny chunks.
        if current and len("\n".join(current)) > max_chars // 3:
            chunks.append("\n".join(current))
            current = []
    if current:
        chunks.append("\n".join(current))
    return chunks


def chunk_document(doc: Document) -> list[Chunk]:
    return [
        Chunk(
            chunk_id=f"{doc.doc_id}#{i}",
            doc_id=doc.doc_id,
            title=doc.title,
            section=piece.splitlines()[0][:70],
            # Put the title in every chunk so each one makes sense on its own.
            text=f"{doc.title}\n{piece}",
            lang=doc.lang,
            doc_type=doc.doc_type,
            access_level=doc.access_level,
        )
        for i, piece in enumerate(chunk_text(doc.text), start=1)
    ]


def load_documents(folder: Path) -> list[Document]:
    catalog_path = folder / CATALOG
    if not catalog_path.exists():
        return []
    entries = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or []
    return [
        Document(
            doc_id=e["doc_id"],
            title=e["title"],
            path=folder / e["file"],
            lang=str(e["lang"]),
            doc_type=e["doc_type"],
            access_level=e["access_level"],
            text=extract_text(folder / e["file"]),
        )
        for e in entries
    ]


def load_chunks(*folders: Path) -> list[Chunk]:
    return [chunk for folder in folders for doc in load_documents(folder) for chunk in chunk_document(doc)]


def save_upload(src: Path, folder: Path, title: str, doc_type: str, access_level: str) -> Document:
    """Copy an uploaded file into `folder`, register it in that folder's catalog, and return it."""
    if src.suffix.lower() not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported file type {src.suffix}. Use PDF, TXT, or MD.")
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(src.read_bytes()).hexdigest()[:8]
    doc_id = f"UP-{digest}"
    dest = folder / f"{doc_id}{src.suffix.lower()}"
    shutil.copy(src, dest)

    text = extract_text(dest)
    if not text:
        dest.unlink()
        raise ValueError("No text found in the file. Scanned PDFs need OCR, which this prototype doesn't do.")
    lang = "th" if re.search(f"[{_THAI_CHAR}]", text) else "en"

    catalog_path = folder / CATALOG
    entries = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else []
    entries = [e for e in (entries or []) if e["doc_id"] != doc_id]  # same file uploaded again -> replace
    entries.append({"doc_id": doc_id, "title": title, "lang": lang, "doc_type": doc_type,
                    "access_level": access_level, "file": dest.name})
    catalog_path.write_text(yaml.safe_dump(entries, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return Document(doc_id, title, dest, lang, doc_type, access_level, text)
