# PharmBot POC 💊

A RAG chatbot for pharmacists — answers questions from your 3,000 medical documents.  
Built with **ChromaDB** (local vector store) + **Claude** (LLM). No external vector DB needed.


#### Small demo

https://www.loom.com/share/5744bf2a60dd48babae418f6f5195cde

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

## Eval harness

Regression suite of 32 pharmacist Q&A pairs (30 clinical + 2 off-topic adversarials). Scores retrieval, keyword coverage, off-topic refusal, and citation presence — no LLM-as-judge.

```bash
python eval/run_eval.py           # full run (32 questions)
python eval/run_eval.py --limit 5 # quick smoke test
```

### Scorecard axes

| Axis | What it checks | Pass bar |
|---|---|---|
| Retrieval correct | Expected chapter slug appears in retrieved chunk sources | ≥ 70% |
| Avg keyword coverage | Fraction of expected drug names / mechanisms in answer | ≥ 0.50 |
| Off-topic refusal | Bot declines non-clinical questions | ≥ 90% |
| Citation present | ≥1 chunk retrieved for `must_cite` questions | 100% |

### Baseline (v1, 2026-05-25)

| Axis | Score |
|---|---|
| Retrieval | 100% |
| Keyword coverage | 0.72 |
| Refusal | 100% |
| Citation present | 100% |

Regression is any axis dropping ≥10 percentage points run-over-run or any bar breached.

Per-question results are written to `eval/results_<utc_timestamp>.jsonl` for inspection.

### Adding questions

`eval/golden_set.jsonl` — one JSON object per line:

```json
{
  "id": "Q033",
  "question": "string",
  "expected_chapter": "slug matching a file under docs/ (or null for off-topic)",
  "expected_keywords": ["3-5 precise terms"],
  "must_cite": true,
  "category": "treatment-selection | dose-titration | adverse-effects | drug-interactions | monitoring | off-topic",
  "expected_refusal": true
}
```

---

## Folder structure

```
pharmbot/
├── docs/             ← put your MD/HTML files here
├── chroma_db/        ← auto-created by index_docs.py
├── eval/
│   ├── golden_set.jsonl  ← 32 Q&A pairs
│   ├── run_eval.py       ← eval harness
│   └── results_*.jsonl   ← per-run output (gitignored)
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
# pharmbot
