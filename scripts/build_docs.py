"""Build the mock knowledge base from data/source_md/ into data/docs/.

  python scripts/build_docs.py

- policy docs -> PDF (like real company documents)
- chat docs   -> plain .txt (like a LINE / Facebook chat export)
- metadata    -> data/docs/catalog.yaml (PDFs have no front matter, so metadata lives in a registry)

The generated files are committed, so you only need this script if you change the source markdown.
Needs a font with Thai glyphs. Default is macOS Tahoma; set FONT_DIR to use another folder with Tahoma.ttf.
"""
import os
from pathlib import Path

import yaml
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source_md"
OUT = ROOT / "data" / "docs"
FONT_DIR = Path(os.getenv("FONT_DIR", "/System/Library/Fonts/Supplemental"))


def read_source(path: Path) -> tuple[dict, str]:
    _, front_matter, body = path.read_text(encoding="utf-8").split("---", 2)
    return yaml.safe_load(front_matter), body.strip()


def write_pdf(body: str, out_path: Path) -> None:
    pdf = FPDF()
    pdf.add_font("Tahoma", "", str(FONT_DIR / "Tahoma.ttf"))
    pdf.add_font("Tahoma", "B", str(FONT_DIR / "Tahoma Bold.ttf"))
    pdf.set_text_shaping(True)  # needed so Thai vowels/tone marks render in the right place
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    for line in body.splitlines():
        if line.startswith("# "):
            pdf.set_font("Tahoma", "B", 16)
            pdf.multi_cell(0, 10, line[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Tahoma", "B", 12.5)
            pdf.multi_cell(0, 8, line[3:], new_x="LMARGIN", new_y="NEXT")
        elif line.strip():
            pdf.set_font("Tahoma", "", 11)
            text = "•  " + line[2:] if line.startswith("- ") else line
            pdf.multi_cell(0, 6.5, text, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(out_path))


def write_chat_export(meta: dict, body: str, out_path: Path) -> None:
    """Turn the markdown chat into a plain chat-export style text file. Threads are separated by blank lines."""
    lines = [f"[{meta['title']}]", ""]
    for line in body.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            lines += ["", f"--- {line[3:]} ---"]
        elif line.strip():
            lines.append(line)
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = []
    for src in sorted(SRC.glob("*.md")):
        meta, body = read_source(src)
        if meta["doc_type"] == "chat":
            out = OUT / f"{src.stem}.txt"
            write_chat_export(meta, body, out)
        else:
            out = OUT / f"{src.stem}.pdf"
            write_pdf(body, out)
        catalog.append({**meta, "file": out.name, "lang": str(meta["lang"])})
        print(f"built {out.relative_to(ROOT)}")

    with (OUT / "catalog.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(catalog, f, allow_unicode=True, sort_keys=False)
    print(f"wrote {(OUT / 'catalog.yaml').relative_to(ROOT)} ({len(catalog)} docs)")


if __name__ == "__main__":
    main()
