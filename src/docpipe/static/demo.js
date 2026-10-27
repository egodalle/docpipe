const SAMPLES = [
  { label: "JSONB", question: "How does JSONB store JSON in PostgreSQL?" },
  { label: "HNSW", question: "What is an HNSW index in pgvector?" },
  { label: "WAL", question: "What is write-ahead logging (WAL) in PostgreSQL?" },
  { label: "GIN index", question: "What is a GIN index in PostgreSQL?" },
  {
    label: "Refuse: weather",
    question: "What is the weather in Paris tomorrow?",
    refuse: true,
  },
];

const form = document.getElementById("ask-form");
const questionEl = document.getElementById("question");
const kEl = document.getElementById("k");
const sourceEl = document.getElementById("source");
const askBtn = document.getElementById("ask-btn");
const samplesEl = document.getElementById("samples");
const charCount = document.getElementById("char-count");
const banner = document.getElementById("banner");
const result = document.getElementById("result");
const verdict = document.getElementById("verdict");
const resultMeta = document.getElementById("result-meta");
const answerEl = document.getElementById("answer");
const citationsEl = document.getElementById("citations");
const healthPill = document.getElementById("health-pill");

function setText(node, value) {
  node.textContent = value == null ? "" : String(value);
}

function renderAnswer(node, text) {
  const raw = String(text || "");
  const escaped = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  node.innerHTML = escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/(^|\n)[ \t]*\* /g, "$1• ");
}

function showBanner(message) {
  banner.hidden = !message;
  setText(banner, message || "");
}

function basename(uri) {
  const path = String(uri || "").split("?")[0];
  const parts = path.split("/").filter(Boolean);
  return parts.length ? parts[parts.length - 1] : uri;
}

function updateCount() {
  const max = Number(questionEl.getAttribute("maxlength") || 2000);
  setText(charCount, `${questionEl.value.length} / ${max}`);
}

function renderSamples() {
  samplesEl.replaceChildren();
  for (const sample of SAMPLES) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = sample.label;
    if (sample.refuse) button.className = "refuse";
    button.addEventListener("click", () => {
      questionEl.value = sample.question;
      updateCount();
      questionEl.focus();
    });
    samplesEl.append(button);
  }
}

async function loadStatus() {
  try {
    const health = await fetch("/health");
    if (health.ok) {
      healthPill.className = "pill ok";
      setText(healthPill, "local db up");
    } else {
      healthPill.className = "pill down";
      setText(healthPill, "database down");
      showBanner("Postgres is not reachable. Start it with docker compose up -d.");
    }
  } catch {
    healthPill.className = "pill err";
    setText(healthPill, "api down");
    showBanner("The API is not responding. Run docpipe serve.");
    return;
  }

  try {
    const stats = await fetch("/stats");
    if (!stats.ok) return;
    const body = await stats.json();
    for (const key of ["documents", "chunks", "retrieval_mode"]) {
      const node = document.querySelector(`[data-bind="${key}"]`);
      if (node) setText(node, body[key]);
    }
    const refuseRate = document.querySelector('[data-bind="refuse_rate"]');
    if (refuseRate && body.refuse_rate != null) {
      setText(refuseRate, `${Math.round(Number(body.refuse_rate) * 100)}%`);
    }
    const p50 = document.querySelector('[data-bind="latency_p50_ms"]');
    if (p50) {
      setText(p50, body.latency_p50_ms == null ? "—" : `${body.latency_p50_ms} ms`);
    }
    const refuse = document.querySelector('[data-bind="refuse"]');
    if (refuse && body.refuse_min_score != null) {
      setText(refuse, Number(body.refuse_min_score).toFixed(2));
    }
    if (body.k_default) kEl.value = String(body.k_default);
  } catch {
    /* stats are optional chrome */
  }

  try {
    const api = await fetch("/api");
    if (!api.ok) return;
    const body = await api.json();
    if (body.question_max_chars) {
      questionEl.setAttribute("maxlength", String(body.question_max_chars));
      updateCount();
    }
    if (body.k_max) kEl.max = String(body.k_max);
  } catch {
    /* keep defaults */
  }
}

function renderResult(body) {
  result.hidden = false;
  result.scrollIntoView({ behavior: "smooth", block: "nearest" });
  const refused = Boolean(body.refused);
  verdict.className = `verdict ${refused ? "refused" : "answered"}`;
  setText(
    verdict,
    refused ? "Refused — below score floor" : "Answered from retrieved chunks",
  );
  const latency = body.latency_ms == null ? "—" : `${body.latency_ms} ms`;
  const rid = body.request_id ? body.request_id.slice(0, 8) : "—";
  const mode = body.retrieval_mode || "vector";
  setText(resultMeta, `${mode} · ${latency} · ${rid}`);
  renderAnswer(
    answerEl,
    refused
      ? "No passage in this corpus scored high enough. Gemini was not called."
      : body.answer || "",
  );

  citationsEl.replaceChildren();
  const citations = Array.isArray(body.citations) ? body.citations : [];
  if (!citations.length) {
    const empty = document.createElement("li");
    setText(empty, "No citations.");
    citationsEl.append(empty);
    return;
  }
  for (const cite of citations) {
    const li = document.createElement("li");
    const top = document.createElement("div");
    top.className = "cite-top";
    const file = document.createElement("span");
    file.className = "cite-file";
    const extras = [cite.source, cite.license].filter(Boolean).join(" · ");
    setText(file, extras ? `${basename(cite.uri)} · ${extras}` : basename(cite.uri));
    const score = document.createElement("span");
    score.className = "cite-score";
    const value = Number(cite.score || 0);
    setText(score, value.toFixed(3));
    top.append(file, score);

    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("span");
    fill.style.width = `${Math.max(0, Math.min(100, value * 100))}%`;
    bar.append(fill);

    const snippet = document.createElement("p");
    snippet.className = "snippet";
    setText(snippet, cite.snippet || "");
    li.append(top, bar, snippet);
    citationsEl.append(li);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionEl.value.trim();
  if (!question) return;
  showBanner("");
  askBtn.disabled = true;
  setText(askBtn, "Retrieving…");
  try {
    const payload = { question };
    const k = Number(kEl.value);
    if (Number.isFinite(k) && k > 0) payload.k = k;
    if (sourceEl && sourceEl.value) payload.source = sourceEl.value;
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body.detail || `Ask failed (${response.status})`;
      showBanner(typeof detail === "string" ? detail : "Ask failed.");
      result.hidden = true;
      return;
    }
    renderResult(body);
  } catch {
    showBanner("Could not reach POST /ask. Is docpipe serve running?");
    result.hidden = true;
  } finally {
    askBtn.disabled = false;
    setText(askBtn, "Ask the corpus");
  }
});

questionEl.addEventListener("input", updateCount);
renderSamples();
updateCount();
loadStatus();
