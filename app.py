"""
app.py — PharmBot chat UI (Streamlit)
Run with: streamlit run app.py
"""

import os
import time
from pathlib import Path

import streamlit as st
import anthropic
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from pharmbot_retrieval import retrieve_hybrid

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_DIR      = "./chroma_db"
COLLECTION_NAME = "medical_docs"
TOP_K           = 35    # chunks retrieved per query
MIN_RELEVANCE   = 1.5   # cosine distance cut-off (lower = stricter)
MAX_TOKENS      = 1024
MODEL           = "claude-sonnet-4-20250514"
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are PharmBot, an AI assistant for licensed pharmacists. You answer from provided CPS/CPhA document excerpts.

GROUNDING (most important):
- Use ONLY facts that appear in the excerpts. Never add a drug name, dose, frequency, threshold, indication, or mechanism that is not written in an excerpt — not even if it is "well known." If you find yourself writing a clinical fact you cannot point to in an excerpt, delete it.
- When you state a fact, name the source document it came from.
- Do NOT pad an answer with general background. Extra unsourced detail is the most common error and will be treated as a mistake.

ENGAGE — do not over-refuse:
- If ANY excerpt is relevant to the question, ANSWER from it. Give the grounded partial answer and then explicitly note what the excerpts do NOT cover. A bare "I couldn't find this" is WRONG whenever relevant excerpts were retrieved.
- Treat brand/generic and close product-name variants as the same item (e.g. "OneTouch Ultra2" ↔ "OneTouch Ultra"; "Atacand" ↔ "candesartan"). If a table row matches the product family, use it.
- Only output "I couldn't find this in the provided documents." when NONE of the excerpts bear on the question.
- A clinical-pharmacy question that names a real drug/device/condition is ALWAYS in scope. Only reply "I can only assist with clinical pharmacy questions." for genuinely non-clinical topics (travel, recipes, lifestyle). When unsure, treat it as in scope and answer.
- Do NOT reframe a genuinely off-topic question (travel itineraries, food/restaurant recommendations, recipes, general lifestyle) into a clinical one in order to answer it. Decline cleanly with the scope line and stop — do not append clinical "however" advice.

HONEST GAPS:
- If the excerpts address the general topic but not the specific sub-scenario asked (exact dose, specific population), say what IS in the excerpts and state plainly that the specific detail is not present. Do not invent the missing value.

STYLE:
- Be precise with dosages, contraindications, interactions — quote them as written.
- Use headings and bullets.
- When asked for THE first-line therapy, commit to the single guideline-preferred agent named in the excerpts. Do not split the answer across severity tiers (e.g. mild vs moderate) unless the question itself specifies severity.
- For multiple-choice, commit to the single best answer supported by the source; do not add defensible-but-extra options unless the question asks for all that apply.
- If a therapy is not recommended or contraindicated for the patient's scenario, say that first and do not provide a dose as though it should be used.
- For vague diagnostic questions, explicitly state that you cannot diagnose from the available information and that more patient-specific assessment is needed before listing possible causes.
- For medication review in older adults, explicitly assess anticholinergic burden, sedating drugs, renal clearance, drug interactions, deprescribing opportunities, collaboration with the prescriber, and Beers Criteria when relevant.
- For QT-prolonging medications, discuss patient risk factors, medication-risk mitigation, ECG/electrolyte monitoring, and external QT-risk resources such as CredibleMeds if supported by the excerpt."""


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading vector database…")
def load_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef     = embedding_functions.DefaultEmbeddingFunction()
    return client.get_collection(name=COLLECTION_NAME, embedding_function=ef)


def retrieve(query: str, collection, top_k: int = TOP_K):
    """Return (chunks, sources) from vector DB."""
    return retrieve_hybrid(
        query,
        collection,
        top_k=top_k,
        min_relevance=MIN_RELEVANCE,
        keyword_k=14,
        final_k=35,
    )


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[Excerpt {i} — {c['title']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def ask_claude(query: str, context: str, history: list[dict]) -> str:
    """Stream answer from Claude."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Build message list (multi-turn)
    messages = []
    for turn in history[-6:]:   # last 3 turns = 6 messages (keep context window sane)
        messages.append({"role": turn["role"], "content": turn["content"]})

    user_msg = f"Context from pharmaceutical documents:\n\n{context}\n\n---\n\nQuestion: {query}"
    messages.append({"role": "user", "content": user_msg})

    full_response = ""
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            yield text

    return full_response


# ── Page layout ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PharmBot POC",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — match PHOXChat aesthetic
st.markdown("""
<style>
    /* Chat input */
    .stChatInput textarea { font-size: 15px; }
    /* Source pill */
    .source-pill {
        display: inline-block;
        background: #e8f4fd;
        border: 1px solid #b8d8f0;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 12px;
        color: #1a6fa8;
        margin: 2px 3px;
    }
    /* Sidebar stats */
    .stat-box {
        background: #f0f7ff;
        border-left: 3px solid #1a6fa8;
        padding: 8px 12px;
        border-radius: 4px;
        margin-bottom: 8px;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
<div style="background:#1a6fa8;border-radius:6px;padding:10px 14px;text-align:center;
            font-size:18px;font-weight:700;color:#fff;letter-spacing:0.5px;">
    💊 PharmBot <span style="font-size:11px;font-weight:400;opacity:0.8;">POC</span>
</div>""", unsafe_allow_html=True)
    st.markdown("---")

    # API key input if not in env
    if not os.environ.get("ANTHROPIC_API_KEY"):
        key = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-…")
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key
        else:
            st.warning("Enter your API key to start.")

    # DB stats
    try:
        col = load_collection()
        chunk_count = col.count()
        st.markdown(f'<div class="stat-box">📦 <b>{chunk_count:,}</b> chunks indexed</div>', unsafe_allow_html=True)
    except Exception:
        st.error("DB not found. Run `python index_docs.py` first.")
        st.stop()

    st.markdown("---")
    st.markdown("**Settings**")
    top_k = st.slider("Chunks retrieved", 5, 50, TOP_K)
    show_sources = st.toggle("Show source excerpts", value=True)

    st.markdown("---")
    if st.button("✚ New Chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("POC · Built with ChromaDB + Claude")


# ── Main chat area ────────────────────────────────────────────────────────────

st.title("💊 PharmBot")
st.caption("Ask questions about your pharmaceutical documents. Answers are grounded in your files.")

# Suggestion cards (shown only at start)
if not st.session_state.get("messages"):
    st.markdown("**Try a suggestion:**")
    cols = st.columns(3)
    suggestions = [
        "What is the adult dosage for amoxicillin?",
        "List contraindications for metformin.",
        "What are common drug interactions with warfarin?",
        "How should ibuprofen be dosed for children?",
        "What are the side effects of lisinopril?",
        "Describe first-line treatment for a UTI.",
    ]
    for i, card_col in enumerate(cols * 2):
        if i < len(suggestions):
            if card_col.button(suggestions[i], use_container_width=True):
                st.session_state.setdefault("messages", [])
                st.session_state["pending_query"] = suggestions[i]
                st.rerun()

st.markdown("---")

# Initialise history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources") and show_sources:
            with st.expander(f"📄 {len(msg['sources'])} source(s)"):
                for src in msg["sources"]:
                    st.markdown(f"- `{src}`")
        if msg.get("latency"):
            st.caption(f"⏱ {msg['latency']:.1f}s")

# Handle suggestion click OR typed query
query = st.session_state.pop("pending_query", None) or st.chat_input("Ask about medications, dosages, interactions…")

if query:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("Please enter your Anthropic API key in the sidebar.")
        st.stop()

    # Show user message
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})

    t0 = time.time()

    # Retrieve chunks
    with st.spinner("🔍 Searching documents…"):
        chunks, sources = retrieve(query, col, top_k)

    if not chunks:
        answer = "I couldn't find relevant information in the provided documents for this query."
        with st.chat_message("assistant"):
            st.warning(answer)
    else:
        context = build_context(chunks)

        # Stream Claude's answer
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_text   = ""
            for token in ask_claude(query, context, st.session_state.messages[:-1]):
                full_text += token
                placeholder.markdown(full_text + "▌")
            placeholder.markdown(full_text)

            if sources and show_sources:
                with st.expander(f"📄 {len(sources)} source(s)"):
                    for src in sources:
                        st.markdown(f"- `{src}`")

            latency = time.time() - t0
            st.caption(f"⏱ {latency:.1f}s · {len(chunks)} chunks used")

        answer = full_text

    st.session_state.messages.append({
        "role":    "assistant",
        "content": answer,
        "sources": sources if chunks else [],
        "latency": time.time() - t0,
    })
