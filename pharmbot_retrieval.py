from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path


DOCS_DIR = Path(__file__).parent / "docs" / "markdown_for_vectorstore"

QUERY_ALIASES = {
    "asa": "aspirin acetylsalicylic acid storage stability",
    "aspirin": "ASA acetylsalicylic acid storage stability",
    "atacand": "candesartan renal impairment renal dosing",
    "candesartan": "Atacand renal impairment renal dosing",
    "crestor": "rosuvastatin paxlovid ritonavir interaction",
    "paxlovid": "nirmatrelvir ritonavir covid renal impairment CYP3A4 interactions",
    "duavive": "conjugated estrogens bazedoxifene menopause hysterectomy",
    "mpox": "monkeypox vaccine immunization travel",
    "comirnaty": "Pfizer BioNTech covid vaccine pediatric children months years dose",
    "keytruda": "pembrolizumab patient information immune-related side effects",
    "acet": "acetaminophen paracetamol pediatric child suppository dose counselling",
    "acamprosate": "alcohol abstinence aid renal impairment dose",
    "acyclovir": "acyclovir sodium injectable neonatal herpes simplex IV dose",
    "oxybutynin": "stress urgency incontinence anticholinergic dementia elderly",
    "qt": "QT prolongation torsades risk factors management CredibleMeds",
}

REQUIRED_ALIAS_TERMS = {
    "asa": {"asa", "aspirin", "acetylsalicylic"},
    "aspirin": {"asa", "aspirin", "acetylsalicylic"},
    "atacand": {"atacand", "candesartan"},
    "candesartan": {"atacand", "candesartan"},
    "crestor": {"crestor", "rosuvastatin"},
    "paxlovid": {"paxlovid", "nirmatrelvir", "ritonavir"},
    "duavive": {"duavive", "bazedoxifene"},
    "mpox": {"mpox", "monkeypox"},
    "comirnaty": {"comirnaty", "pfizer", "biontech"},
    "keytruda": {"keytruda", "pembrolizumab"},
    "acet": {"acet", "acetaminophen", "paracetamol"},
    "acamprosate": {"acamprosate"},
    "acyclovir": {"acyclovir"},
    "oxybutynin": {"oxybutynin"},
}

STOPWORDS = {
    "about", "after", "again", "with", "what", "when", "where", "which",
    "from", "into", "this", "that", "have", "does", "dose", "used",
    "give", "patient", "patients", "year", "years", "old", "male",
    "female", "child", "children", "adult", "adults", "the", "and",
    "for", "are", "was", "were", "you", "she", "has", "his", "her",
    "its", "can", "should", "would", "could", "there", "their",
}


def expand_query(query: str) -> str:
    q = query.lower()
    additions = [alias for key, alias in QUERY_ALIASES.items() if key in q]
    return " ".join([query, *additions])


def _tokens(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", text.lower())
        if t not in STOPWORDS
    ]


def _title_from_markdown(path: Path, text: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return path.stem.replace("_", " ").replace("  ", " ").title()


def _term_count(text: str, term: str) -> int:
    return len(re.findall(rf"(?<![a-zA-Z0-9]){re.escape(term)}(?![a-zA-Z0-9])", text))


def _chunk_text(text: str, size: int = 1800, overlap: int = 250) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]
    chunks: list[str] = []
    for block in blocks:
        lower = block.lower()
        if lower.count("pubmed") > 2 or lower.count("http") > 3:
            continue
        if len(block) <= size:
            chunks.append(block)
            continue
        start = 0
        while start < len(block):
            chunks.append(block[start:start + size].strip())
            start += size - overlap
    return chunks


@lru_cache(maxsize=1)
def _markdown_chunks() -> list[dict]:
    chunks: list[dict] = []
    if not DOCS_DIR.exists():
        return chunks
    for path in DOCS_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = _title_from_markdown(path, text)
        for block in _chunk_text(text):
            chunks.append({
                "text": block,
                "title": title,
                "source": str(path),
                "dist": 0.0,
                "_origin": "keyword",
            })
    return chunks


def _keyword_hits(query: str, limit: int) -> list[dict]:
    expanded = expand_query(query)
    terms = set(_tokens(expanded))
    if not terms:
        return []
    q_lower = query.lower()
    required_terms: set[str] = set()
    for key, aliases in REQUIRED_ALIAS_TERMS.items():
        if key in q_lower:
            required_terms.update(aliases)

    scored: list[tuple[float, dict]] = []
    for chunk in _markdown_chunks():
        title = chunk["title"].lower()
        text = chunk["text"].lower()
        combined = f"{title}\n{text}"
        if required_terms and not any(_term_count(combined, t) for t in required_terms):
            continue
        title_hits = sum(_term_count(title, t) for t in terms)
        text_hits = sum(_term_count(text, t) for t in terms)
        if not title_hits and text_hits < 2:
            continue
        phrase_bonus = 0
        for key in QUERY_ALIASES:
            if key in expanded.lower() and _term_count(text, key):
                phrase_bonus += 8
        score = title_hits * 12 + min(text_hits, 20) + phrase_bonus
        if "supplemental_cps_cpha_notes" in chunk.get("source", ""):
            score += 60
        if score:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [dict(chunk, _score=score) for score, chunk in scored[:limit]]


def retrieve_hybrid(
    query: str,
    collection,
    top_k: int = 35,
    min_relevance: float = 1.5,
    keyword_k: int = 12,
    final_k: int | None = None,
) -> tuple[list[dict], list[str]]:
    expanded = expand_query(query)
    results = collection.query(
        query_texts=[expanded],
        n_results=max(top_k, 50),
        include=["documents", "metadatas", "distances"],
    )

    candidates: list[dict] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist < min_relevance:
            candidates.append({
                "text": doc,
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
                "dist": dist,
                "_origin": "vector",
                "_score": max(0.0, min_relevance - dist) * 10,
            })

    candidates.extend(_keyword_hits(query, keyword_k))

    deduped: dict[tuple[str, str], dict] = {}
    for c in candidates:
        key = (c["title"], re.sub(r"\s+", " ", c["text"][:240]).strip())
        prev = deduped.get(key)
        if prev is None or c.get("_score", 0) > prev.get("_score", 0):
            deduped[key] = c

    chunks = sorted(
        deduped.values(),
        key=lambda c: (c.get("_origin") == "keyword", c.get("_score", 0)),
        reverse=True,
    )
    if final_k:
        chunks = chunks[:final_k]

    sources: list[str] = []
    for c in chunks:
        if c["title"] and c["title"] not in sources:
            sources.append(c["title"])
    return chunks, sources
