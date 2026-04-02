/* Polymath frontend — vanilla JS */
"use strict";

const API = (window.POLYMATH_API_URL ?? "http://localhost:8000");

// ── DOM refs ─────────────────────────────────────────────────────────────────
const fileInput        = document.getElementById("fileInput");
const uploadText       = document.getElementById("uploadText");
const ingestBtn        = document.getElementById("ingestBtn");
const ingestStatus     = document.getElementById("ingestStatus");
const sourcesList      = document.getElementById("sourcesList");
const refreshSourcesBtn= document.getElementById("refreshSourcesBtn");
const queryForm        = document.getElementById("queryForm");
const questionInput    = document.getElementById("questionInput");
const sendBtn          = document.getElementById("sendBtn");
const sendLabel        = document.getElementById("sendLabel");
const sendSpinner      = document.getElementById("sendSpinner");
const messagesEl       = document.getElementById("messages");

// ── File selection ───────────────────────────────────────────────────────────
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file) {
    uploadText.textContent = file.name;
    ingestBtn.disabled = false;
  } else {
    uploadText.textContent = "Drop file or click to browse";
    ingestBtn.disabled = true;
  }
});

// ── Drag & drop on label ─────────────────────────────────────────────────────
const uploadLabel = document.getElementById("uploadLabel");
uploadLabel.addEventListener("dragover", (e) => { e.preventDefault(); uploadLabel.style.borderColor = "var(--accent)"; });
uploadLabel.addEventListener("dragleave", () => { uploadLabel.style.borderColor = ""; });
uploadLabel.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadLabel.style.borderColor = "";
  const file = e.dataTransfer?.files[0];
  if (file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    uploadText.textContent = file.name;
    ingestBtn.disabled = false;
  }
});

// ── Ingest ───────────────────────────────────────────────────────────────────
ingestBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  ingestBtn.disabled = true;
  setStatus(ingestStatus, "Ingesting…", "");

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch(`${API}/ingest`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Ingest failed");

    setStatus(ingestStatus, `✓ ${data.chunks_stored} chunks stored`, "status-ok");
    uploadText.textContent = "Drop file or click to browse";
    fileInput.value = "";
    await loadSources();
  } catch (err) {
    setStatus(ingestStatus, `✗ ${err.message}`, "status-err");
    ingestBtn.disabled = false;
  }
});

// ── Sources list ─────────────────────────────────────────────────────────────
async function loadSources() {
  try {
    const res = await fetch(`${API}/sources`);
    const data = await res.json();
    renderSources(data.sources ?? []);
  } catch {
    sourcesList.innerHTML = '<span class="empty-note">Could not load sources</span>';
  }
}

function renderSources(sources) {
  if (!sources.length) {
    sourcesList.innerHTML = '<span class="empty-note">No documents yet</span>';
    return;
  }
  sourcesList.innerHTML = sources.map((s) => `
    <div class="source-chip">
      <div class="src-name">${escHtml(s.source)}</div>
      <div class="src-meta">${escHtml(s.doc_type)} · ${s.chunk_count} chunks</div>
    </div>
  `).join("");
}

refreshSourcesBtn.addEventListener("click", loadSources);

// ── Query ────────────────────────────────────────────────────────────────────
queryForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  questionInput.value = "";
  appendMessage("user", question);

  const thinkingEl = appendThinking();
  setSendLoading(true);

  try {
    const res = await fetch(`${API}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 5 }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Query failed");

    thinkingEl.remove();
    appendAssistantMessage(data.answer, data.sources ?? []);
  } catch (err) {
    thinkingEl.remove();
    appendAssistantMessage(`Error: ${err.message}`, []);
  } finally {
    setSendLoading(false);
  }
});

// ── Message rendering ─────────────────────────────────────────────────────────
function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}-message`;
  const content = document.createElement("div");
  content.className = "msg-content";
  content.textContent = text;
  div.appendChild(content);
  messagesEl.appendChild(div);
  scrollToBottom();
  return div;
}

function appendThinking() {
  const div = document.createElement("div");
  div.className = "message assistant-message";
  div.innerHTML = '<div class="msg-content"><span class="thinking-dots">···</span></div>';
  messagesEl.appendChild(div);
  scrollToBottom();
  return div;
}

function appendAssistantMessage(answer, sources) {
  const div = document.createElement("div");
  div.className = "message assistant-message";

  const content = document.createElement("div");
  content.className = "msg-content";
  content.textContent = answer;
  div.appendChild(content);

  if (sources.length) {
    const block = document.createElement("div");
    block.className = "sources-block";
    sources.forEach((s) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.innerHTML = `${escHtml(s.source)}<span class="tag-score">${(s.score * 100).toFixed(0)}%</span>`;
      block.appendChild(tag);
    });
    div.appendChild(block);
  }

  messagesEl.appendChild(div);
  scrollToBottom();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setStatus(el, msg, cls) {
  el.textContent = msg;
  el.className = `status-msg ${cls}`;
}

function setSendLoading(loading) {
  sendBtn.disabled = loading;
  sendLabel.classList.toggle("hidden", loading);
  sendSpinner.classList.toggle("hidden", !loading);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadSources();
