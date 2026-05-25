"""
index_docs.py — Indexes your MD/HTML files into a local ChromaDB vector store.
Run once (or re-run to add new files): python index_docs.py
"""

import os
import glob
import hashlib
import re
import argparse
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from bs4 import BeautifulSoup
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
DOCS_DIR    = "./docs"       # drop your 3,000 files here (subfolders are fine)
CHROMA_DIR  = "./chroma_db"  # where the vector DB is persisted
COLLECTION  = "medical_docs"
CHUNK_WORDS = 300            # ~300 words ≈ 400 tokens — good balance for medical text
CHUNK_OVERLAP = 50           # word overlap between consecutive chunks
# ──────────────────────────────────────────────────────────────────────────────


def extract_text(filepath: str) -> tuple[str, str]:
    """Return (plain_text, document_title) from an MD or HTML file."""
    path = Path(filepath)
    raw  = path.read_text(encoding="utf-8", errors="ignore")

    if path.suffix.lower() in (".html", ".htm"):
        soup = BeautifulSoup(raw, "lxml")
        # Pull title from <title> or first <h1>
        title_tag = soup.find("title") or soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else path.stem
        # Strip nav / script / style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
    else:
        # Markdown — extract first heading as title, strip syntax
        heading = re.search(r"^#{1,3}\s+(.+)", raw, re.MULTILINE)
        title   = heading.group(1).strip() if heading else path.stem
        text    = raw
        text    = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)   # links
        text    = re.sub(r"```[\s\S]*?```", " ", text)              # code blocks
        text    = re.sub(r"`[^`]+`", " ", text)                     # inline code
        text    = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings

    # Strip file extensions that sometimes appear in <title> tags or headings
    for ext in (".html", ".htm", ".md", ".pdf", ".txt"):
        if title.lower().endswith(ext):
            title = title[: -len(ext)]
            break

    # Normalise whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), title.strip()


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words  = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        if chunk:
            chunks.append(chunk)
        i += size - overlap
    return chunks


def file_hash(filepath: str) -> str:
    """SHA-1 of file contents — used to skip unchanged files."""
    h = hashlib.sha1()
    h.update(Path(filepath).read_bytes())
    return h.hexdigest()


def main(reset: bool = False) -> None:
    # ── Collect files ─────────────────────────────────────────────────────────
    patterns = ["**/*.md", "**/*.html", "**/*.htm"]
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(os.path.join(DOCS_DIR, pat), recursive=True))

    if not files:
        print(f"\n⚠  No MD/HTML files found in '{DOCS_DIR}'.")
        print("   Create the folder and place your files there, then re-run.\n")
        return

    print(f"\n📂 Found {len(files):,} files in '{DOCS_DIR}'")

    # ── Init ChromaDB ─────────────────────────────────────────────────────────
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef     = embedding_functions.DefaultEmbeddingFunction()  # all-MiniLM-L6-v2 (local, free)

    if reset and COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
        print("🗑  Existing collection deleted (--reset flag).")

    collection = client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"📦 Vector DB at '{CHROMA_DIR}'  (existing chunks: {collection.count():,})\n")

    # ── Index files ───────────────────────────────────────────────────────────
    skipped = 0
    total_chunks = 0
    errors: list[str] = []

    for filepath in tqdm(files, desc="Indexing", unit="file"):
        try:
            fhash = file_hash(filepath)

            text, title = extract_text(filepath)
            if len(text) < 50:
                skipped += 1
                continue

            chunks = chunk_text(text)

            ids       = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{fhash}_{i}".encode()).hexdigest()
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append({
                    "source":       filepath,
                    "title":        title,
                    "file_hash":    fhash,
                    "chunk_index":  i,
                    "total_chunks": len(chunks),
                })

            # Upsert in batches of 100 (ChromaDB default limit)
            BATCH = 100
            for b in range(0, len(ids), BATCH):
                collection.upsert(
                    ids=ids[b : b + BATCH],
                    documents=documents[b : b + BATCH],
                    metadatas=metadatas[b : b + BATCH],
                )

            total_chunks += len(chunks)

        except Exception as exc:
            errors.append(f"{filepath}: {exc}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n✅ Done!")
    print(f"   Files processed : {len(files) - skipped:,}")
    print(f"   Files skipped   : {skipped:,}  (empty/too short)")
    print(f"   Chunks indexed  : {total_chunks:,}")
    print(f"   Total in DB     : {collection.count():,}")
    if errors:
        print(f"\n⚠  {len(errors)} errors:")
        for e in errors[:10]:
            print(f"   {e}")
    print(f"\nRun `streamlit run app.py` to start the chat UI.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index MD/HTML files into ChromaDB")
    parser.add_argument("--reset", action="store_true", help="Delete existing DB and re-index from scratch")
    parser.add_argument("--docs",  default=DOCS_DIR,   help=f"Path to docs folder (default: {DOCS_DIR})")
    args = parser.parse_args()

    DOCS_DIR = args.docs
    main(reset=args.reset)
