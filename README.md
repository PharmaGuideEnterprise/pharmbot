# PharmBot POC 💊

A RAG chatbot for pharmacists — answers questions from your 3,000 medical documents.  
Built with **ChromaDB** (local vector store) + **Claude** (LLM). No external vector DB needed.

---

## Architecture

```
Your MD/HTML files
      │
      ▼
 index_docs.py          ← run once to index
      │  chunks + embeddings
      ▼
  ChromaDB (local)      ← persisted to ./chroma_db/
      │
      │  at query time
      ▼
  app.py (Streamlit)
    │  1. embed query
    │  2. retrieve top-8 chunks
    │  3. send chunks + query → Claude
    └─► streamed answer with citations
```

---

## Quick start (5 steps)

### 1. Clone / download this folder

```bash
cd pharmbot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> Python 3.10+ recommended.

### 3. Add your API key

```bash
cp .env.example .env
# then edit .env and paste your Anthropic API key
```

Get one at https://console.anthropic.com

### 4. Drop your files into `./docs/`

```
pharmbot/
  docs/
    monographs/
      amoxicillin.md
      metformin.html
      ...  (3,000 files, subfolders fine)
```

### 5. Index the files

```bash
python index_docs.py
```

Expected output:
```
📂 Found 3,000 files in './docs'
📦 Vector DB at './chroma_db'  (existing chunks: 0)

Indexing: 100%|████████████| 3000/3000 [02:30<00:00]

✅ Done!
   Files processed : 3,000
   Chunks indexed  : 18,432
   Total in DB     : 18,432
```

Indexing ~3,000 files takes **2–5 minutes** on first run.  
Re-runs only upsert changed files (hash-based).

### 6. Launch the chat UI

```bash
streamlit run app.py
```

Opens at http://localhost:8501

---

## Folder structure

```
pharmbot/
├── docs/             ← put your MD/HTML files here
├── chroma_db/        ← auto-created by index_docs.py
├── index_docs.py     ← indexing script
├── app.py            ← Streamlit chat UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Re-indexing & updates

| Scenario | Command |
|---|---|
| Add new files | `python index_docs.py` (only new files indexed) |
| Full re-index | `python index_docs.py --reset` |
| Custom docs folder | `python index_docs.py --docs /path/to/files` |

---

## Tuning for accuracy

Edit these constants at the top of each file:

**index_docs.py**
| Setting | Default | Effect |
|---|---|---|
| `CHUNK_WORDS` | 300 | Larger = more context per chunk, slower retrieval |
| `CHUNK_OVERLAP` | 50 | Higher = less chance of cutting mid-sentence |

**app.py**
| Setting | Default | Effect |
|---|---|---|
| `TOP_K` | 8 | More chunks = richer context, higher cost |
| `MIN_RELEVANCE` | 1.2 | Lower = stricter matching (0 = exact, 2 = loose) |

---

## Cost estimate

| Item | Cost |
|---|---|
| Indexing (embeddings) | Free — uses local `all-MiniLM-L6-v2` |
| Per query (Claude Sonnet) | ~$0.003–0.008 |
| 1,000 queries/month | ~$5–8 |

---

## Next steps (after POC validates)

- [ ] Switch to `text-embedding-3-large` for higher accuracy
- [ ] Add hybrid BM25 + vector search for exact drug name matching  
- [ ] Add Cohere reranker for better top-K selection
- [ ] Add user authentication
- [ ] Deploy to AWS/GCP with a managed vector DB (Pinecone / Qdrant Cloud)
# pharmbot
