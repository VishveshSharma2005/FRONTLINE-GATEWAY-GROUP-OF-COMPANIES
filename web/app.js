let allResults = [];
let messageById = {};
let selectedId = null;

const priorityColor = { P0: 'var(--red)', P1: 'var(--amber)', P2: 'var(--blue)', P3: 'var(--green)' };
const categoryColors = ['var(--amber)', 'var(--blue)', 'var(--violet)', 'var(--green)', 'var(--red)', '#ffd166', 'var(--muted)'];

function setStatus(text, active) {
  document.getElementById('statusText').textContent = text;
  document.getElementById('statusLine').classList.toggle('active', !!active);
  document.getElementById('liveStatus').textContent = active ? 'processing' : 'idle';
}

async function loadMeta() {
  try {
    const r = await fetch('/api/meta');
    const m = await r.json();
    document.getElementById('metaBadge').textContent = `${m.provider} / ${m.model} · ${m.dataset_size} messages`;
  } catch (e) {}
}

async function loadMessages() {
  const r = await fetch('/api/messages');
  const msgs = await r.json();
  messageById = Object.fromEntries(msgs.map(m => [m.id, m.text]));
}

function renderStats() {
  const total = allResults.length;
  const human = allResults.filter(r => r.needs_human).length;
  const p0 = allResults.filter(r => r.priority === 'P0').length;
  const blocked = allResults.filter(r => (r.flags || []).includes('possible_prompt_injection')).length;
  const errors = allResults.filter(r => r.error).length;
  const cards = [
    { v: total, l: 'Total Triaged', c: 'var(--amber)' },
    { v: human, l: 'Flagged For Human', c: 'var(--red)' },
    { v: p0, l: 'P0 Critical', c: 'var(--red)' },
    { v: blocked, l: 'Injections Blocked', c: 'var(--violet)' },
    { v: errors, l: 'Fail-Safe Fallbacks', c: 'var(--dim)' },
  ];
  document.getElementById('stats').innerHTML = cards.map(c =>
    `<div class="stat" style="--accent:${c.c}"><div class="v">${c.v}</div><div class="l">${c.l}</div></div>`
  ).join('');
}

function renderDistributions() {
  if (!allResults.length) { document.getElementById('distPanel').style.display = 'none'; return; }
  document.getElementById('distPanel').style.display = '';
  const total = allResults.length;

  const byPriority = {};
  ['P0','P1','P2','P3'].forEach(p => byPriority[p] = 0);
  allResults.forEach(r => byPriority[r.priority] = (byPriority[r.priority]||0) + 1);
  document.getElementById('priorityDist').innerHTML = Object.entries(byPriority).map(([k,v]) => `
    <div class="dist-row">
      <div class="k">${k}</div>
      <div class="dist-track"><div class="dist-fill" style="width:${total?v/total*100:0}%; background:${priorityColor[k]}"></div></div>
      <div class="n">${v}</div>
    </div>`).join('');

  const byCat = {};
  allResults.forEach(r => byCat[r.category] = (byCat[r.category]||0) + 1);
  const catEntries = Object.entries(byCat).sort((a,b) => b[1]-a[1]);
  document.getElementById('categoryDist').innerHTML = catEntries.map(([k,v], i) => `
    <div class="dist-row">
      <div class="k">${k}</div>
      <div class="dist-track"><div class="dist-fill" style="width:${total?v/total*100:0}%; background:${categoryColors[i % categoryColors.length]}"></div></div>
      <div class="n">${v}</div>
    </div>`).join('');
}

function renderTable() {
  const pf = document.getElementById('filterPriority').value;
  const hf = document.getElementById('filterHuman').value;
  const q = document.getElementById('searchBox').value.trim().toLowerCase();
  const rows = document.getElementById('rows');
  rows.innerHTML = '';

  const filtered = allResults.filter(r => {
    if (pf && r.priority !== pf) return false;
    if (hf === 'true' && !r.needs_human) return false;
    if (hf === 'flagged' && !(r.flags && r.flags.length)) return false;
    if (q) {
      const text = (messageById[r.id] || '') + ' ' + r.summary + ' ' + r.id;
      if (!text.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  document.getElementById('rowCount').textContent = `${filtered.length} / ${allResults.length} shown`;

  for (const r of filtered) {
    const tr = document.createElement('tr');
    if (r.id === selectedId) tr.classList.add('selected');
    const confColor = r.confidence >= 0.7 ? 'var(--green)' : r.confidence >= 0.4 ? 'var(--amber)' : 'var(--red)';
    const flagsHtml = (r.flags || []).map(f => `<span class="flag-pill">${f.replace(/_/g,' ')}</span>`).join('');
    tr.innerHTML = `
      <td class="id-cell">${r.id}</td>
      <td>${r.category}</td>
      <td><span class="badge ${r.priority}">${r.priority}</span></td>
      <td><span class="conf-bar"><span class="conf-fill" style="width:${r.confidence*100}%; background:${confColor}"></span></span>${r.confidence.toFixed(2)}</td>
      <td>${r.needs_human ? '<span class="human-tag">● HUMAN</span>' : ''}</td>
      <td>${r.summary}</td>
      <td>${flagsHtml}</td>
    `;
    tr.onclick = () => { selectedId = r.id; renderTable(); renderInspector(r); };
    rows.appendChild(tr);
  }
}

function flagExplanation(flag) {
  const map = {
    possible_prompt_injection: { icon: '⛔', cls: 'warn', text: 'Regex guardrail detected manipulation language (e.g. "ignore instructions", "developer mode"). Forced needs_human=true and capped confidence, independent of what the model itself claimed.' },
    low_confidence: { icon: '⚠', cls: 'warn', text: 'Model confidence fell below the 0.6 threshold. Code-level rule forces human review regardless of the model\'s own needs_human flag.' },
    empty_message: { icon: '∅', cls: 'warn', text: 'Message had no usable content. Routed to human rather than triaged with false confidence.' },
    triage_error: { icon: '✕', cls: 'warn', text: 'API call, JSON parsing, or schema validation failed. Fail-safe object returned instead of crashing the batch.' },
  };
  return map[flag] || { icon: '•', cls: '', text: flag };
}

function renderInspector(r) {
  const text = messageById[r.id] || '(message text unavailable)';
  const confColor = r.confidence >= 0.7 ? 'var(--green)' : r.confidence >= 0.4 ? 'var(--amber)' : 'var(--red)';
  const flags = r.flags || [];

  let trace = '';
  if (flags.length) {
    trace = flags.map(f => {
      const e = flagExplanation(f);
      return `<div class="trace-item ${e.cls}"><span class="trace-icon">${e.icon}</span><span>${e.text}</span></div>`;
    }).join('');
  } else {
    trace = `<div class="trace-item ok"><span class="trace-icon">✓</span><span>No guardrail intervened — model's own classification and confidence were used as-is.</span></div>`;
  }
  if (r.error) {
    trace += `<div class="trace-item warn"><span class="trace-icon">✕</span><span>Error: ${r.error}</span></div>`;
  }

  document.getElementById('inspector').innerHTML = `
    <h3>Decision Trace</h3>
    <div class="msg-id">${r.id}</div>

    <div class="insp-section">
      <div class="insp-label">Raw customer message</div>
      <div class="insp-raw">${text || '(empty)'}</div>
    </div>

    <div class="insp-section">
      <div class="insp-label">Model confidence</div>
      <div class="gauge">
        <div class="gauge-track"><div class="gauge-fill" style="width:${r.confidence*100}%; background:${confColor}"></div></div>
        <div class="gauge-val" style="color:${confColor}">${r.confidence.toFixed(2)}</div>
      </div>
    </div>

    <div class="insp-section">
      <div class="insp-label">Structured decision</div>
      <div class="insp-fields">
        <div class="insp-field"><span class="k">Category</span><span class="v">${r.category}</span></div>
        <div class="insp-field"><span class="k">Priority</span><span class="v"><span class="badge ${r.priority}">${r.priority}</span></span></div>
        <div class="insp-field"><span class="k">Needs human</span><span class="v">${r.needs_human ? 'YES' : 'no'}</span></div>
        <div class="insp-field"><span class="k">Latency</span><span class="v">${r.latency_ms ? r.latency_ms + ' ms' : '—'}</span></div>
        <div class="insp-field"><span class="k">Tokens in/out</span><span class="v">${r.input_tokens ?? '—'}/${r.output_tokens ?? '—'}</span></div>
      </div>
    </div>

    <div class="insp-section">
      <div class="insp-label">Suggested action</div>
      <div class="insp-raw">${r.suggested_action}</div>
    </div>

    <div class="insp-section">
      <div class="insp-label">Guardrail trace (why this decision is trustworthy)</div>
      ${trace}
    </div>
  `;
}

function renderEval(report) {
  document.getElementById('evalPanel').style.display = '';
  document.getElementById('evalHint').textContent = `${report.n_evaluated} labeled messages · avg ${report.avg_latency_ms}ms · $${report.est_cost_per_message_usd}/msg`;

  const bars = [
    { label: 'Category match', v: report.category_accuracy, color: 'var(--amber)' },
    { label: 'Priority match', v: report.priority_accuracy, color: 'var(--blue)' },
    { label: 'Needs-human match', v: report.needs_human_accuracy, color: 'var(--green)' },
  ];
  document.getElementById('evalBars').innerHTML = bars.map(b => `
    <div class="eval-bar-row">
      <div class="label">${b.label}</div>
      <div class="eval-bar-track"><div class="eval-bar-fill" style="width:${b.v*100}%; background:${b.color}"></div></div>
      <div class="pct">${(b.v*100).toFixed(0)}%</div>
    </div>`).join('');

  document.getElementById('evalChips').innerHTML = `
    <div class="chip">avg latency <b>${report.avg_latency_ms} ms</b></div>
    <div class="chip">avg tokens <b>${report.avg_input_tokens}in / ${report.avg_output_tokens}out</b></div>
    <div class="chip">est. cost <b>$${report.est_cost_per_message_usd}</b>/msg</div>
    <div class="chip">at scale <b>~$${(report.est_cost_per_message_usd*10000).toFixed(2)}</b>/10k msgs</div>
  `;

  const mismatches = report.rows.filter(r => !r.category.match || !r.priority.match || !r.needs_human.match);
  document.getElementById('mismatchList').innerHTML = mismatches.length
    ? mismatches.map(r => `<div class="mismatch-item">${r.id}: expected ${r.category.expected}/${r.priority.expected} got ${r.category.got}/${r.priority.got}${r.needs_human.match ? '' : ' (needs_human mismatch)'}</div>`).join('')
    : `<div class="mismatch-item" style="border-left-color:var(--green); background:var(--green-dim)">No mismatches — 100% agreement on all measured fields.</div>`;
}

document.getElementById('filterPriority').onchange = renderTable;
document.getElementById('filterHuman').onchange = renderTable;
document.getElementById('searchBox').oninput = renderTable;

function startElapsedTicker(label) {
  const t0 = Date.now();
  const tick = () => setStatus(`${label} (${((Date.now()-t0)/1000).toFixed(0)}s elapsed — free-tier APIs are throttled on purpose to avoid rate-limit errors)`, true);
  tick();
  return setInterval(tick, 1000);
}

document.getElementById('runBtn').onclick = async () => {
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  const ticker = startElapsedTicker('Triaging all 40 messages one by one via the live model');
  try {
    const res = await fetch('/api/triage', { method: 'POST' });
    allResults = await res.json();
    clearInterval(ticker);
    setStatus(`Done — ${allResults.length} messages triaged.`, false);
    renderStats(); renderDistributions(); renderTable();
    if (selectedId) { const r = allResults.find(x => x.id === selectedId); if (r) renderInspector(r); }
  } catch (e) {
    clearInterval(ticker);
    setStatus('Error running triage: ' + e, false);
  }
  btn.disabled = false;
};

document.getElementById('evalBtn').onclick = async () => {
  const btn = document.getElementById('evalBtn');
  btn.disabled = true;
  const ticker = startElapsedTicker(allResults.length ? 'Scoring against ground truth' : 'Triaging all 40 messages, then scoring against ground truth');
  try {
    const res = await fetch('/api/eval', { method: 'POST' });
    const report = await res.json();
    clearInterval(ticker);
    renderEval(report);
    const resultsRes = await fetch('/api/results');
    allResults = await resultsRes.json();
    renderStats(); renderDistributions(); renderTable();
    setStatus('Evaluation complete.', false);
  } catch (e) {
    clearInterval(ticker);
    setStatus('Error running eval: ' + e, false);
  }
  btn.disabled = false;
};

document.getElementById('toolBtn').onclick = () => {
  alert('The tool-calling demo (mock ticket-status lookup) runs standalone from the CLI:\n\n  python tool_demo.py\n\nSee AI_DECISIONS.md for what it demonstrates.');
};

(async () => {
  await loadMeta();
  await loadMessages();
  const res = await fetch('/api/results');
  allResults = await res.json();
  renderStats(); renderDistributions(); renderTable();
})();
