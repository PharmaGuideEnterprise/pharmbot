#!/usr/bin/env python3
"""Convert PHARMACIST_REVIEW.md to a single-file HTML for clinical pharmacist
review. Self-contained, no external dependencies, prints nicely.
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown

EVAL = Path("/Users/emad/Code/cps/chatbot_poc/eval")
SRC = EVAL / "PHARMACIST_REVIEW.md"
OUT = EVAL / "PHARMACIST_REVIEW.html"


CSS = """
:root {
  --bg: #fafaf8;
  --paper: #ffffff;
  --ink: #1a1a1a;
  --muted: #6b6b6b;
  --line: #e0ddd5;
  --accent: #1f5582;
  --accent-soft: #e8f0f7;
  --danger: #b03030;
  --warning: #b88a30;
  --ok: #2e7d4f;
  --quote-bg: #f4f1ea;
  --quote-border: #c9c2b0;
  --highlight: #fff3cd;
}

* { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
               Helvetica, Arial, sans-serif;
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 36px 48px 64px;
  background: var(--paper);
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  border-radius: 4px;
}

@media (max-width: 800px) {
  .container { padding: 20px 16px 40px; }
  body { font-size: 14px; }
}

h1 {
  font-size: 28px;
  margin: 0 0 8px;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 12px;
  letter-spacing: -0.01em;
}
h2 {
  font-size: 22px;
  color: var(--accent);
  margin: 36px 0 14px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 6px;
}
h3 {
  font-size: 17px;
  margin: 32px 0 10px;
  padding: 8px 12px;
  background: var(--accent-soft);
  border-left: 4px solid var(--accent);
  border-radius: 2px;
}
h3:has(+ p strong:contains("SHOWSTOPPER")) {
  border-left-color: var(--danger);
  background: #fdebeb;
}

p { margin: 0.5em 0 1em; }

strong { font-weight: 600; }

ul, ol { padding-left: 22px; }
li { margin: 4px 0; }

/* Task lists / checkboxes */
.task-list-item { list-style: none; padding-left: 0; }
.task-list-item-checkbox {
  margin-right: 8px;
  transform: scale(1.2);
  vertical-align: middle;
}
ul:has(> li > input[type="checkbox"]) {
  padding-left: 0;
  list-style: none;
}
ul:has(> li > input[type="checkbox"]) li {
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  margin: 4px 0;
  background: #fafaf8;
}
ul:has(> li > input[type="checkbox"]) li:hover {
  background: #f0ecde;
}

blockquote {
  margin: 0.8em 0;
  padding: 10px 16px;
  background: var(--quote-bg);
  border-left: 3px solid var(--quote-border);
  border-radius: 2px;
  font-size: 14px;
  color: #2a2a2a;
}
blockquote p { margin: 0.3em 0; }
blockquote > * + * { margin-top: 0.5em; }

hr {
  border: 0;
  height: 1px;
  background: var(--line);
  margin: 32px 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13.5px;
  background: var(--paper);
  table-layout: fixed;
  word-wrap: break-word;
}
table.summary-table { display: block; overflow-x: auto; white-space: normal; }

th, td {
  text-align: left;
  padding: 10px 12px;
  border: 1px solid var(--line);
  vertical-align: top;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}
th {
  background: var(--accent);
  color: white;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.01em;
  position: sticky;
  top: 0;
}
tr:nth-child(even) td { background: #fafaf8; }
tr:hover td { background: #f4f1ea; }

/* Sized columns in the summary table */
.summary-table th:nth-child(1), .summary-table td:nth-child(1) { width: 36px; text-align: center; }
.summary-table th:nth-child(2), .summary-table td:nth-child(2) { width: 70px; }
.summary-table th:nth-child(3), .summary-table td:nth-child(3) { width: 32px; text-align: center; font-size: 18px; }
.summary-table th:nth-child(4), .summary-table td:nth-child(4) { width: 28%; }
.summary-table th:nth-child(5), .summary-table td:nth-child(5) { width: 28%; font-size: 13px; }
.summary-table th:nth-child(6), .summary-table td:nth-child(6) { font-size: 13px; }

code {
  background: #f0ecde;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.92em;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

.banner {
  background: var(--accent-soft);
  border: 1px solid #b8d2e3;
  border-radius: 4px;
  padding: 12px 16px;
  margin: 18px 0;
  font-size: 14px;
}

.toc {
  background: #fafaf8;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 12px 18px;
  margin: 18px 0;
  font-size: 14px;
}
.toc ul { margin: 6px 0; padding-left: 24px; }
.toc li { margin: 2px 0; }

/* Reviewer bar (injected by JS) */
.reviewer-bar {
  background: #fff8e8;
  border: 2px solid #d4b85b;
  border-radius: 6px;
  padding: 14px 18px;
  margin: 18px 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.reviewer-row { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 12px; }
.reviewer-row label {
  display: flex; flex-direction: column; gap: 4px;
  font-size: 13px; color: #5a4818; font-weight: 600;
  flex: 1 1 200px;
}
.reviewer-row input {
  padding: 6px 10px; border: 1px solid #c9b675; border-radius: 4px;
  font-size: 14px; font-family: inherit; background: white;
}
.actions-row {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  border-top: 1px solid #d4b85b; padding-top: 10px;
}
.actions-row button {
  padding: 8px 14px; border-radius: 4px; border: 1px solid #1f5582;
  background: #1f5582; color: white; font-size: 13px; font-weight: 600;
  cursor: pointer; font-family: inherit;
}
.actions-row button:hover { background: #16456b; }
.actions-row button.danger { background: white; color: #b03030; border-color: #b03030; }
.actions-row button.danger:hover { background: #fceaea; }
.save-indicator {
  margin-left: auto; font-size: 12px; color: #5a7a5a; opacity: 0.4;
  transition: opacity 0.3s;
}
.hint { font-size: 13px; color: #5a4818; margin: 8px 0 0; }

/* Notes textarea (injected by JS after each verdict list) */
.notes-block {
  margin: 10px 0 16px;
  padding: 10px 12px;
  background: #f4fbf5;
  border: 1px dashed #87b099;
  border-radius: 4px;
}
.notes-block label {
  display: block; font-size: 13px; color: #2e5a3f;
  margin-bottom: 4px;
}
.notes-block textarea {
  width: 100%; padding: 8px 10px; border: 1px solid #b8d0bf;
  border-radius: 3px; font-family: inherit; font-size: 14px;
  background: white; resize: vertical; min-height: 80px;
}
.notes-block textarea:focus { outline: 2px solid var(--accent); outline-offset: 1px; }

/* Print */
@media print {
  body { background: white; }
  .container { box-shadow: none; padding: 0; max-width: 100%; }
  h3 { page-break-before: auto; page-break-after: avoid; }
  blockquote, table { page-break-inside: avoid; }
  th { position: static; }
  hr { page-break-after: always; border: 0; margin: 0; height: 0; }
  .reviewer-bar { position: static; }
  .actions-row button, .save-indicator { display: none; }
  .notes-block { background: white; border: 1px solid #999; }
  .notes-block textarea { border: 1px solid #999; min-height: 60px; }
}
"""


JS = r"""
// =====================================================================
// Pharmacist review — interactivity
// =====================================================================
// What this script does:
// 1. Enables disabled checkboxes (python-markdown emits them disabled)
// 2. Auto-saves every checkbox + textarea to localStorage so the reviewer
//    doesn't lose their work if they close the tab or refresh
// 3. Reloads any saved state when the page opens
// 4. Adds an "Export my review" button bar that downloads two files:
//      - PHARMACIST_REVIEW_verdicts.csv  (one row per question + verdict + notes)
//      - PHARMACIST_REVIEW_verdicts.json (full structured data)
//    The pharmacist emails these back.
//
// All state lives in localStorage under key 'pharmacist_review_v1'.
// Nothing is sent anywhere — fully offline. No innerHTML; DOM nodes built
// explicitly to avoid any XSS surface.

const STORAGE_KEY = 'pharmacist_review_v1';

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) { return {}; }
}

function saveState(state) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
}

function el(tag, attrs, children) {
  const n = document.createElement(tag);
  if (attrs) {
    for (const k in attrs) {
      if (k === 'class') n.className = attrs[k];
      else if (k === 'textContent') n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
  }
  if (children) {
    children.forEach(c => {
      if (c == null) return;
      if (typeof c === 'string') n.appendChild(document.createTextNode(c));
      else n.appendChild(c);
    });
  }
  return n;
}

function setupReview() {
  const state = loadState();

  // 1) Make every checkbox enabled and wire up auto-save
  const checkboxes = document.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach((cb, idx) => {
    cb.disabled = false;
    cb.dataset.checkboxIdx = String(idx);
    if (state.checkboxes && state.checkboxes[idx] !== undefined) {
      cb.checked = state.checkboxes[idx];
    }
    cb.addEventListener('change', () => {
      const s = loadState();
      s.checkboxes = s.checkboxes || {};
      s.checkboxes[idx] = cb.checked;
      saveState(s);
    });
  });

  // 2) After each question's checkbox list, insert a notes textarea
  const detailHeadings = document.querySelectorAll('h3');
  detailHeadings.forEach((h, qIdx) => {
    if (!/^\d+\.\s/.test(h.textContent)) return;
    let sib = h.nextElementSibling;
    let lastUl = null;
    while (sib && sib.tagName !== 'HR' && sib.tagName !== 'H3') {
      if (sib.tagName === 'UL') lastUl = sib;
      sib = sib.nextElementSibling;
    }
    if (!lastUl) return;

    const qIdMatch = h.textContent.match(/(?:^|\s)([A-Z]+-[A-Z0-9_\-]+)/);
    const qId = qIdMatch ? qIdMatch[1] : ('Q' + qIdx);

    const label = el('label',
      { for: 'notes-' + qId },
      [ el('strong', { textContent: 'Notes / corrected answer (optional):' }) ]
    );
    const ta = el('textarea', {
      id: 'notes-' + qId,
      'data-question-id': qId,
      rows: '4',
      placeholder: "What's specifically wrong? What should the answer have said? Any clinical reasoning the chatbot missed?",
    });
    if (state.notes && state.notes[qId]) ta.value = state.notes[qId];
    ta.addEventListener('input', () => {
      const s = loadState();
      s.notes = s.notes || {};
      s.notes[qId] = ta.value;
      saveState(s);
    });

    const noteBlock = el('div', { class: 'notes-block' }, [label, ta]);
    lastUl.insertAdjacentElement('afterend', noteBlock);
  });

  // 3) Reviewer info bar at the top of the body
  const nameInput = el('input', { type: 'text', id: 'reviewer-name', placeholder: 'Your name' });
  const dateInput = el('input', { type: 'date', id: 'reviewer-date' });
  const credsInput = el('input', { type: 'text', id: 'reviewer-creds', placeholder: 'e.g. RPh, BScPharm, PharmD' });

  const csvBtn = el('button', { id: 'btn-export-csv', type: 'button', textContent: '\u{1F4C4} Download verdicts (CSV — email this back)' });
  const jsonBtn = el('button', { id: 'btn-export-json', type: 'button', textContent: '\u{2B07}\u{FE0F} Download JSON (structured)' });
  const clearBtn = el('button', { id: 'btn-clear', type: 'button', class: 'danger', textContent: '\u{21BA} Clear all my answers' });
  const saveInd = el('span', { id: 'save-indicator', class: 'save-indicator', textContent: 'Auto-saving…' });

  const headerBar = el('div', { class: 'reviewer-bar' }, [
    el('div', { class: 'reviewer-row' }, [
      el('label', null, ['Reviewer name: ', nameInput]),
      el('label', null, ['Date: ', dateInput]),
      el('label', null, ['Credentials / title: ', credsInput]),
    ]),
    el('div', { class: 'actions-row' }, [csvBtn, jsonBtn, clearBtn, saveInd]),
    el('p', { class: 'hint' }, [
      'Your answers are saved to this browser automatically. When you’re done, click ',
      el('b', { textContent: 'Download verdicts' }),
      ' and email the file back.',
    ]),
  ]);

  const firstH1 = document.querySelector('h1');
  if (firstH1) firstH1.parentElement.insertBefore(headerBar, firstH1.nextSibling);

  // Restore reviewer fields
  ['reviewer-name', 'reviewer-date', 'reviewer-creds'].forEach(id => {
    const node = document.getElementById(id);
    if (!node) return;
    if (state.meta && state.meta[id]) node.value = state.meta[id];
    node.addEventListener('input', () => {
      const s = loadState();
      s.meta = s.meta || {};
      s.meta[id] = node.value;
      saveState(s);
    });
  });

  // 4) Gather + export
  function gatherReview() {
    const review = [];
    const headings = document.querySelectorAll('h3');
    headings.forEach((h) => {
      const m = h.textContent.match(/^(\d+)\.\s+([A-Z]+-[A-Z0-9_\-]+)/);
      if (!m) return;
      const ordinal = m[1];
      const qId = m[2];
      const isShowstopper = h.textContent.indexOf('SHOWSTOPPER') !== -1;
      const verdicts = [];
      let notes = '';
      let sib = h.nextElementSibling;
      while (sib && sib.tagName !== 'HR' && sib.tagName !== 'H3') {
        if (sib.tagName === 'UL') {
          sib.querySelectorAll('li').forEach(li => {
            const cb = li.querySelector('input[type="checkbox"]');
            if (cb && cb.checked) {
              verdicts.push(li.textContent.replace(/^\s+|\s+$/g, ''));
            }
          });
        }
        if (sib.classList && sib.classList.contains('notes-block')) {
          const ta = sib.querySelector('textarea');
          if (ta) notes = ta.value;
        }
        sib = sib.nextElementSibling;
      }
      review.push({ ordinal, qId, isShowstopper, verdicts, notes });
    });
    return review;
  }

  function reviewerMeta() {
    return {
      name: (document.getElementById('reviewer-name') || { value: '' }).value || '',
      date: (document.getElementById('reviewer-date') || { value: '' }).value || '',
      credentials: (document.getElementById('reviewer-creds') || { value: '' }).value || '',
    };
  }

  function downloadFile(filename, content, mime) {
    const blob = new Blob([content], { type: mime + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function csvEscape(s) {
    if (s == null) return '';
    const str = String(s);
    if (/[",\n]/.test(str)) return '"' + str.replace(/"/g, '""') + '"';
    return str;
  }

  csvBtn.addEventListener('click', () => {
    const review = gatherReview();
    const meta = reviewerMeta();
    const rows = [
      'Reviewer name,' + csvEscape(meta.name),
      'Reviewer credentials,' + csvEscape(meta.credentials),
      'Review date,' + csvEscape(meta.date),
      '',
      '#,Question ID,Showstopper,Verdicts (pipe-separated),Notes / corrected answer',
    ];
    review.forEach(r => {
      rows.push([
        r.ordinal,
        r.qId,
        r.isShowstopper ? 'Y' : '',
        csvEscape(r.verdicts.join(' | ')),
        csvEscape(r.notes),
      ].join(','));
    });
    downloadFile('PHARMACIST_REVIEW_verdicts.csv', rows.join('\n'), 'text/csv');
  });

  jsonBtn.addEventListener('click', () => {
    const payload = {
      reviewer: reviewerMeta(),
      timestamp: new Date().toISOString(),
      verdicts: gatherReview(),
    };
    downloadFile('PHARMACIST_REVIEW_verdicts.json',
                 JSON.stringify(payload, null, 2), 'application/json');
  });

  clearBtn.addEventListener('click', () => {
    if (!confirm('Clear all your answers (checkboxes + notes + reviewer info)? This cannot be undone.')) return;
    localStorage.removeItem(STORAGE_KEY);
    location.reload();
  });

  function pulseSaveIndicator() {
    const node = document.getElementById('save-indicator');
    if (!node) return;
    node.style.opacity = '1';
    clearTimeout(window._saveTimer);
    window._saveTimer = setTimeout(() => { node.style.opacity = '0.4'; }, 600);
  }
  document.addEventListener('input', pulseSaveIndicator, true);
  document.addEventListener('change', pulseSaveIndicator, true);
  pulseSaveIndicator();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupReview);
} else {
  setupReview();
}
"""


def md_to_html(md_text: str) -> str:
    """Convert markdown to HTML with the features we need:
       - tables
       - GitHub-flavored task lists
       - fenced code
       - link auto-conversion
       - convert <br> tags inside table cells (used to flow long text) into <br>
    """
    extensions = [
        "tables",
        "fenced_code",
        "sane_lists",
        "attr_list",
        "md_in_html",
    ]
    # python-markdown doesn't natively render task list checkboxes; do it manually.
    md = markdown.Markdown(extensions=extensions, output_format="html5")
    html = md.convert(md_text)

    # python-markdown leaves "[ ] ..." inside <li>. Replace with real checkboxes.
    def task_li_sub(match):
        body = match.group(1)
        return f'<li class="task-list-item"><input type="checkbox" class="task-list-item-checkbox" /> {body}</li>'

    def task_li_sub_checked(match):
        body = match.group(1)
        return f'<li class="task-list-item"><input type="checkbox" class="task-list-item-checkbox" checked /> {body}</li>'

    html = re.sub(r"<li>\[\s\]\s+(.*?)</li>", task_li_sub, html, flags=re.DOTALL)
    html = re.sub(r"<li>\[x\]\s+(.*?)</li>", task_li_sub_checked, html, flags=re.DOTALL)

    # Add a class to the first table we find (the summary table)
    html = html.replace('<table>', '<table class="summary-table">', 1)

    return html


def main() -> int:
    md_text = SRC.read_text(encoding="utf-8")
    body_html = md_to_html(md_text)

    title = "Failed-Question Review — CPS Chatbot"
    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="container">
{body_html}
</div>
<script>
{JS}
</script>
</body>
</html>"""

    OUT.write_text(document, encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  size: {OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
