const state = { segments: [], report: null, selected: 0, sessionId: crypto.randomUUID() };
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

async function initialise() {
  try {
    const [health, audience] = await Promise.all([api("/api/health"), api("/api/segments")]);
    $("health").innerHTML = [
      `ML ${health.segmentation}`,
      `Bedrock marketing ${health.marketing_bedrock}`,
      `Bedrock evaluator ${health.bedrock_evaluation}`,
      `Lex ${health.lex}`
    ].map((label) => `<span class="chip ok">${escapeHtml(label)}</span>`).join("");
    if (health.lex !== "configured") {
      $("advisorStatus").textContent = "Lex is not configured yet. Add LEX_BOT_ID and LEX_BOT_ALIAS_ID to .env, ensure AWS SSO is active, and connect the Lambda fulfillment hook.";
    }
    state.segments = audience.segments;
    renderSegments();
  } catch (error) {
    $("health").innerHTML = `<span class="chip pending">Backend unavailable</span>`;
    $("error").textContent = error.message;
  }
}

function renderSegments() {
  $("segments").innerHTML = state.segments.map((segment) => `
    <label class="segment">
      <input type="checkbox" value="${segment.segment_id}" checked>
      <span><b>${escapeHtml(segment.segment_name)}</b><small>${Number(segment.customer_count || 0).toLocaleString()} customers · ${Math.round(Number(segment.average_confidence || 0) * 100)}% confidence · ${escapeHtml(segment.source)}</small></span>
    </label>`).join("");
}

$("selectAll").addEventListener("click", () => {
  const boxes = [...document.querySelectorAll("#segments input")];
  const shouldCheck = boxes.some((box) => !box.checked);
  boxes.forEach((box) => { box.checked = shouldCheck; });
  $("selectAll").textContent = shouldCheck ? "Clear all" : "Select all";
});

$("run").addEventListener("click", async () => {
  const button = $("run");
  const segmentIds = [...document.querySelectorAll("#segments input:checked")].map((box) => Number(box.value));
  $("error").textContent = "";
  if (!segmentIds.length) { $("error").textContent = "Select at least one audience."; return; }
  button.disabled = true;
    button.innerHTML = "Bedrock generating, Lab evaluating… <span>◌</span>";
  try {
    state.report = await api("/api/campaigns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product: $("product").value,
        brief: $("brief").value,
        channel: $("channel").value,
        timing: $("timing").value,
        persona_count: Number($("personaCount").value),
        segment_ids: segmentIds
      })
    });
    state.selected = 0;
    renderReport();
  } catch (error) {
    $("error").textContent = error.message;
  } finally {
    button.disabled = false;
    button.innerHTML = "Send to Bedrock, then test <span>→</span>";
  }
});

function renderReport() {
  const summary = state.report.portfolio_summary;
  $("empty").hidden = true;
  $("report").hidden = false;
  $("decision").textContent = `${summary.launch_decision} before launch`;
  $("topRisks").textContent = (summary.top_risks || []).join(" · ");
  $("readiness").textContent = summary.readiness;
  $("tabs").innerHTML = state.report.campaigns.map((campaign, index) => `<button class="tab ${index === state.selected ? "active" : ""}" data-index="${index}">${escapeHtml(campaign.segment_name)}</button>`).join("");
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => { state.selected = Number(tab.dataset.index); renderReport(); }));
  renderCampaign(state.report.campaigns[state.selected]);
}

function renderCampaign(c) {
  const scoreLabels = [["clarity", "Clarity"], ["trust", "Trust"], ["stress", "Stress ↓"], ["fairness", "Fairness"], ["accessibility", "Access"], ["readiness", "Ready"]];
  $("campaign").innerHTML = `<div class="campaign-grid">
    <article class="creative card"><div class="card-head"><span class="kicker">BEDROCK AD VERSION</span><span class="risk">${escapeHtml(c.risk_level)} risk</span></div><h2>${escapeHtml(c.headline)}</h2><p class="message">${escapeHtml(c.message)}</p><span class="cta">${escapeHtml(c.cta)}</span><div class="meta"><span>${escapeHtml(c.audience.source)}</span><span>${escapeHtml(c.bedrock_status || "Bedrock")}</span><span>${Number(c.audience.customer_count || 0).toLocaleString()} eligible</span><span>${(c.audience.sample_customer_ids || []).map(escapeHtml).join(", ")}</span></div><p class="rationale"><b>Lab assessment:</b> ${escapeHtml(c.rationale)}</p></article>
    <article class="evidence card"><div class="card-head"><div><span class="kicker">CUSTOMER ASSURANCE</span><h3>Impact scorecard</h3></div></div><div class="scores">${scoreLabels.map(([key, label]) => `<div class="score"><b>${escapeHtml(c.scores[key])}</b><span>${label}</span></div>`).join("")}</div><div class="rewrite"><b>SAFER REWRITE</b><p>${escapeHtml(c.safer_rewrite)}</p></div><ul class="recommendations">${(c.recommendations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></article>
    <article class="personas card"><span class="kicker">SYNTHETIC CUSTOMER PANEL</span><h3>Who might experience this differently?</h3><div class="persona-grid">${(c.personas || []).map((p) => `<div class="persona"><b>${escapeHtml(p.name)}</b><small>${escapeHtml(p.context)}</small><p>${escapeHtml(p.reaction)}</p><div class="mini-scores"><span>C ${p.clarity}</span><span>T ${p.trust}</span><span>S ${p.stress}</span><span>A ${p.accessibility}</span></div></div>`).join("")}</div></article>
  </div>`;
}

$("chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("question");
  const message = input.value.trim();
  if (!message) return;
  addBubble(message, "user"); input.value = "";
  const context = state.report ? {
    product: $("product").value,
    portfolio_summary: state.report.portfolio_summary,
    selected_campaign: state.report.campaigns[state.selected]
  } : { product: $("product").value };
  try {
    const response = await api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, session_id: state.sessionId, context }) });
    addBubble(`${response.reply} (${response.source})`, "bot");
  } catch (error) { addBubble(error.message, "bot"); }
});

function addBubble(text, type) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${type}`;
  bubble.textContent = text;
  $("chat").appendChild(bubble);
  $("chat").scrollTop = $("chat").scrollHeight;
}

initialise();
