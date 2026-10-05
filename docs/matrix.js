"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );

const LEVELS = [
  { id: "native", label: "Native route", short: "Native" },
  { id: "lossy", label: "Route with known loss", short: "Lossy" },
  { id: "cannot-target", label: "Cannot target", short: "Can't target" },
  { id: "no-route", label: "No route", short: "No route" },
  { id: "not-scanned", label: "Not scanned", short: "Not scanned" },
];
const LEVEL = Object.fromEntries(LEVELS.map((l) => [l.id, l]));
const FLAGS = {
  "caller-mechanics": "Caller supplies indices or API details",
  "depends-on-google": "Preservation depends on Google behavior",
};
const METRICS = [
  { id: "coverage", label: "Coverage" },
  { id: "cost", label: "Invocations · latency · tokens" },
];
// The three cost bands, top to bottom; each has its own one-hue ramp and bin upper bounds.
const BANDS = [
  { id: "inv", label: "Invocations", hue: "--blue", bins: [1, 2, 3, 4, 5, Infinity], labels: ["1", "2", "3", "4", "5", "6+"] },
  { id: "lat", label: "Latency", hue: "--orange", bins: [0.5, 1, 2, 4, 8, Infinity], labels: ["≤0.5s", "≤1s", "≤2s", "≤4s", "≤8s", ">8s"] },
  { id: "tok", label: "Response tokens", hue: "--aqua", bins: [250, 500, 1000, 2000, 4000, Infinity], labels: ["≤250", "≤500", "≤1k", "≤2k", "≤4k", ">4k"] },
];

let D; // data
let byTask, resultsByTask, latencyIndex;
const state = {
  view: "grid",
  metric: "coverage",
  focus: "all",
  tags: new Set(),
  search: "",
  differ: true,
  cell: null, // "purpose|item"
  task: null,
  sort: { key: "purpose", dir: 1 },
};

// ---------- state in URL hash, so a view can be linked ----------
function writeHash() {
  const p = new URLSearchParams();
  if (state.view !== "grid") p.set("view", state.view);
  if (state.metric !== "coverage") p.set("metric", state.metric);
  if (state.focus !== "all") p.set("tool", state.focus);
  if (state.tags.size) p.set("tags", [...state.tags].join(","));
  if (state.search) p.set("q", state.search);
  if (!state.differ) p.set("differ", "0");
  if (state.cell) p.set("cell", state.cell);
  if (state.task) p.set("task", state.task);
  history.replaceState(null, "", "#" + p.toString());
}
function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  state.view = p.get("view") || "grid";
  state.metric = ["coverage", "cost"].includes(p.get("metric")) ? p.get("metric") : "coverage";
  state.focus = p.get("tool") || "all";
  state.tags = new Set((p.get("tags") || "").split(",").filter(Boolean));
  state.search = p.get("q") || "";
  state.differ = p.get("differ") !== "0";
  state.cell = p.get("cell");
  state.task = p.get("task");
}

// ---------- derived values ----------
const tools = () =>
  state.focus === "all" ? D.tools : D.tools.filter((t) => t.id === state.focus);
const toolName = (id) => D.tools.find((t) => t.id === id)?.name || id;
const purposeOf = (id) => D.purposes.find((p) => p.id === id);
const itemOf = (id) => D.items.find((i) => i.id === id);
const varOf = (id) => D.variations.find((v) => v.id === id);
const applicable = (p, i) => (D.applicable[p] || []).includes(i);

function invocations(r) {
  if (!r.route?.length) return null;
  const req = r.route.filter((s) => !s.optional).length;
  return [req, r.route.length];
}
// Timing of one command on the baseline (short) fixture.
function stepStat(tool, cmd) {
  const l = latencyIndex[tool + "|" + cmd + "|short"];
  return l && l.status === "measured" ? l : null;
}
// Estimated task cost: sums of required command medians; optional steps add to the upper bounds.
function latency(r) {
  if (!r.route?.length) return null;
  const c = { lo: 0, hi: 0, tokLo: 0, tokHi: 0 };
  for (const s of r.route) {
    const l = stepStat(r.tool, s.command);
    if (!l) return { missing: s.command };
    c.hi += l.median_ms;
    c.tokHi += l.tokens_median;
    if (!s.optional) {
      c.lo += l.median_ms;
      c.tokLo += l.tokens_median;
    }
  }
  return c;
}
const median = (xs) => {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

function taskVisible(t) {
  if (state.tags.size && !t.tags.some((g) => state.tags.has(g))) return false;
  if (state.search && !t.sentence.toLowerCase().includes(state.search.toLowerCase()))
    return false;
  return true;
}
// Disagreement: how far apart the tools' coverage levels are (0 = all agree).
function disagreement(t) {
  const ranks = D.tools
    .map((tool) => resultsByTask[t.id]?.[tool.id]?.coverage)
    .filter((c) => c && c !== "not-scanned")
    .map((c) => LEVELS.findIndex((l) => l.id === c));
  if (ranks.length < 2) return 0;
  return (Math.max(...ranks) - Math.min(...ranks)) * 10 + new Set(ranks).size;
}
function tasksDisagree(t) {
  const lv = D.tools.map((tool) => resultsByTask[t.id]?.[tool.id]?.coverage);
  return new Set(lv).size > 1;
}
function tasksIn(purpose, item) {
  return D.tasks.filter(
    (t) =>
      (!purpose || t.purpose === purpose) &&
      (!item || t.item === item) &&
      taskVisible(t),
  );
}

// Aggregate one tool over a set of tasks.
function summarize(tasks, tool) {
  const counts = Object.fromEntries(LEVELS.map((l) => [l.id, 0]));
  const inv = [],
    lat = [],
    tok = [];
  let latMissing = 0,
    routed = 0;
  for (const t of tasks) {
    const r = resultsByTask[t.id]?.[tool];
    const lv = r?.coverage || "not-scanned";
    counts[lv]++;
    if (!r || !r.route?.length) continue;
    routed++;
    inv.push(invocations(r)[0]);
    const l = latency(r);
    if (l && l.missing == null) {
      lat.push(l.lo / 1000);
      tok.push(l.tokLo);
    } else latMissing++;
  }
  return {
    n: tasks.length,
    counts,
    routed,
    invMedian: median(inv),
    invMin: inv.length ? Math.min(...inv) : null,
    invMax: inv.length ? Math.max(...inv) : null,
    latMedian: median(lat),
    tokMedian: median(tok),
    latN: lat.length,
    latMissing,
  };
}

const binIndex = (v, bins) => bins.findIndex((b) => v <= b);
const rampVar = (band, i) => `var(${band.hue}-${i + 1})`;
const fmtTok = (n) => (n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + "k" : Math.round(n)) + " tok";
const fmtS = (s) => (s < 10 ? s.toFixed(1) : Math.round(s)) + "s";
const fmtInv = (v) => (Number.isInteger(v) ? v : v.toFixed(1));

// ---------- rendering: shared bits ----------
function stripeHTML(sum) {
  if (state.metric === "coverage") {
    if (!sum.n) return `<div class="stripe"></div>`;
    return `<div class="stripe">${LEVELS.filter((l) => sum.counts[l.id])
      .map((l) => `<div class="seg-${l.id}" style="flex:${sum.counts[l.id]}"></div>`)
      .join("")}</div>`;
  }
  const vals = { inv: sum.invMedian, lat: sum.latMedian, tok: sum.tokMedian };
  return `<div class="stripe bands">${BANDS.map((b) =>
    vals[b.id] == null
      ? `<div class="band none"></div>`
      : `<div class="band" style="background:${rampVar(b, binIndex(vals[b.id], b.bins))}"></div>`,
  ).join("")}</div>`;
}

function cellHTML(purpose, item, opts = {}) {
  if (purpose && item && !applicable(purpose, item))
    return `<td class="cell"><div class="cellbox na" title="Not applicable per ACCEPTANCE §3">·</div></td>`;
  const tasks = tasksIn(purpose, item);
  const key = `${purpose || "*"}|${item || "*"}`;
  if (!tasks.length)
    return `<td class="cell ${opts.cls || ""}"><div class="cellbox empty" data-key="${key}" tabindex="0"></div></td>`;
  const dim = state.differ && !tasks.some(tasksDisagree);
  const sel = state.cell === key ? " sel" : "";
  return `<td class="cell ${opts.cls || ""}"><div class="cellbox${dim ? " dim" : ""}${sel}" data-key="${key}" tabindex="0" role="button" aria-label="${esc(cellTitle(key))}">${tools()
    .map((t) => stripeHTML(summarize(tasks, t.id)))
    .join("")}</div></td>`;
}

function cellTitle(key) {
  const [p, i] = key.split("|");
  const pl = p === "*" ? "All purposes" : purposeOf(p).label;
  const il = i === "*" ? "All items" : itemOf(i).label;
  return `${il} × ${pl}`;
}

function legendHTML() {
  if (state.view === "commands") return "";
  if (state.view === "tasks" || state.metric === "coverage")
    return (
      LEVELS.map(
        (l) =>
          `<span class="key"><span class="sw seg-${l.id}"></span>${l.label}</span>`,
      ).join("") +
      (state.view === "grid"
        ? `<span>Stripe height = share of the cell's tasks at each level · hover a cell for counts</span>`
        : "")
    );
  return `<div class="bandlegend">${BANDS.map(
    (b, k) =>
      `<div><span class="bandname">${["Top", "Middle", "Bottom"][k]} · ${b.label}</span>${b.labels
        .map((lab, i) => `<span class="key"><span class="sw" style="background:${rampVar(b, i)}"></span>${lab}</span>`)
        .join("")}</div>`,
  ).join("")}<div class="muted">Each value is the median over the cell's tasks that have a route, using each task's required steps on the short test document. Grey: no route, or a step not yet timed. Hover a cell for numbers.</div></div>`;
}

function controlsHTML() {
  const seg = (name, opts, cur) =>
    `<span class="seg">${opts
      .map(
        (o) =>
          `<button data-${name}="${o.id}" class="${o.id === cur ? "on" : ""}">${esc(o.label)}</button>`,
      )
      .join("")}</span>`;
  const groups = [...new Set(D.variations.map((v) => v.group))];
  const tagPanel = groups
    .map(
      (g) =>
        `<div class="grp"><b>${esc(g)}</b>${D.variations
          .filter((v) => v.group === g)
          .map(
            (v) =>
              `<label><input type="checkbox" data-tag="${v.id}" ${state.tags.has(v.id) ? "checked" : ""}/> ${esc(v.label)}</label>`,
          )
          .join("")}</div>`,
    )
    .join("");
  const metricCtl =
    state.view === "grid"
      ? `<span><span class="ctl-label">Show</span>${seg("metric", METRICS, state.metric)}</span>`
      : "";
  const toolCtl =
    true
      ? `<span><span class="ctl-label">Tools</span>${seg(
          "focus",
          [{ id: "all", label: D.tools.length === 2 ? "Both" : "All three" }, ...D.tools.map((t) => ({ id: t.id, label: t.name }))],
          state.focus,
        )}</span>`
      : "";
  if (state.view === "commands") return toolCtl;
  return `${metricCtl}${toolCtl}
    <details class="tags"><summary>Variations${state.tags.size ? ` (${state.tags.size})` : ""} ▾</summary><div class="panel">${tagPanel}</div></details>
    ${state.tags.size ? `<button class="clear" data-clear="tags">Clear variations</button>` : ""}
    <input type="search" id="search" placeholder="Search task sentences" value="${esc(state.search)}" />
    ${state.view === "grid" ? `<label class="check"><input type="checkbox" id="differ" ${state.differ ? "checked" : ""}/> Dim cells where all tools agree</label>` : ""}`;
}

// ---------- grid view ----------
function gridHTML() {
  const order = tools()
    .map((t) => t.name)
    .join(" · ");
  const head = `<tr><th><span class="tool-order">Stripes: ${esc(order)}</span></th>${D.purposes
    .map((p) => `<th title="${esc(p.outcome)}">${esc(p.label)}</th>`)
    .join("")}<th class="total">All purposes</th></tr>`;
  let body = "";
  let group = null;
  for (const it of D.items) {
    if (it.group !== group) {
      group = it.group;
      body += `<tr class="group"><th colspan="${D.purposes.length + 2}">${esc(group)}</th></tr>`;
    }
    body += `<tr><th class="row">${esc(it.label)}</th>${D.purposes
      .map((p) => cellHTML(p.id, it.id))
      .join("")}${cellHTML(null, it.id, { cls: "total-col" })}</tr>`;
  }
  body += `<tr class="group"><th colspan="${D.purposes.length + 2}">Totals</th></tr><tr class="total-row"><th class="row">All items</th>${D.purposes
    .map((p) => cellHTML(p.id, null))
    .join("")}${cellHTML(null, null, { cls: "total-col" })}</tr>`;
  return `<div class="grid-wrap"><table class="grid"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
}

function tipHTML(key) {
  const [p, i] = key.split("|");
  const tasks = tasksIn(p === "*" ? null : p, i === "*" ? null : i);
  const rows = D.tools
    .map((t) => {
      const s = summarize(tasks, t.id);
      const cov = LEVELS.filter((l) => s.counts[l.id])
        .map((l) => `${s.counts[l.id]} ${l.label.toLowerCase()}`)
        .join(", ");
      const inv =
        s.invMedian == null
          ? "no routes"
          : `${fmtInv(s.invMedian)} invocations (range ${s.invMin}–${s.invMax})`;
      const lat =
        s.latMedian == null
          ? "latency untimed"
          : `${fmtS(s.latMedian)} · ${fmtTok(s.tokMedian)} median${s.latMissing ? ` (${s.latMissing} untimed)` : ""}`;
      return `<tr><td><b>${esc(t.name)}</b></td><td>${esc(cov)}<br><span class="muted">${inv} · ${lat}</span></td></tr>`;
    })
    .join("");
  return `<b>${esc(cellTitle(key))} · ${tasks.length} tasks</b><table>${rows}</table><span class="muted">Click for tasks</span>`;
}

// ---------- drawer: cell or task detail ----------
function chipHTML(r) {
  const lv = r?.coverage || "not-scanned";
  const inv = r && invocations(r);
  const lat = r && latency(r);
  let extra = "";
  if (state.metric === "cost" && inv) extra = ` ${inv[0]}×${lat && lat.missing == null ? " · " + fmtS(lat.lo / 1000) : ""}`;
  return `<span class="chip" title="${esc(toolName(r?.tool))}: ${esc(LEVEL[lv].label)}"><span class="sw seg-${lv}"></span>${esc(toolName(r?.tool))}${extra}</span>`;
}

function toolResultHTML(r) {
  const lv = r.coverage || "not-scanned";
  const inv = invocations(r);
  const lat = latency(r);
  const route = r.route?.length
    ? `<ol class="route">${r.route
        .map((s) => {
          const l = stepStat(r.tool, s.command);
          return `<li class="${s.optional ? "opt" : ""}">${esc(s.command)}${s.optional ? " (if needed)" : ""} <span class="ms">${l ? `· ${(l.median_ms / 1000).toFixed(2)}s · ${fmtTok(l.tokens_median)}` : "· untimed"}</span></li>`;
        })
        .join("")}</ol>`
    : "";
  const meas =
    inv &&
    `<div class="muted" style="font-size:12px">${inv[0]}${inv[1] > inv[0] ? "–" + inv[1] : ""} invocations · ${
      lat.missing != null
        ? `latency unknown (${esc(lat.missing)} untimed)`
        : `≈ ${fmtS(lat.lo / 1000)}${lat.hi > lat.lo ? "–" + fmtS(lat.hi / 1000) : ""} · ${fmtTok(lat.tokLo)}${lat.tokHi > lat.tokLo ? "–" + fmtTok(lat.tokHi) : ""} estimated`
    }</div>`;
  return `<div class="toolres" style="border-left-color:var(--${{ native: "native", lossy: "lossy", "cannot-target": "cannot", "no-route": "noroute" }[lv] || "unscanned"})">
    <h4>${esc(toolName(r.tool))} <span class="muted" style="font-weight:400">${esc(LEVEL[lv].label)}</span>${r.stage === "estimated" ? `<span class="flag" style="border-color:var(--line);color:var(--muted)" title="Estimated from the pull request's diff, not graded by the full pipeline">estimate</span>` : ""}${(r.flags || []).map((f) => `<span class="flag" title="${esc(FLAGS[f])}">${esc(FLAGS[f] || f)}</span>`).join("")}</h4>
    ${r.note ? `<p class="note">${esc(r.note)}</p>` : ""}
    ${route}${meas || ""}
    ${(r.evidence || []).map((e) => `<div class="ev">Evidence: ${esc(e.claim)} — ${e.url ? `<a href="${esc(e.url)}">${esc(e.ref)}</a>` : `<code>${esc(e.ref)}</code>`}</div>`).join("")}
    ${lv !== "not-scanned" && !(r.evidence || []).length ? `<div class="ev muted">No evidence cited</div>` : ""}
  </div>`;
}

function taskHTML(t, open) {
  const res = resultsByTask[t.id] || {};
  return `<div class="task${open ? " open" : ""}" data-task="${t.id}">
    <div class="head"><div><div class="sentence">${esc(t.sentence)}</div>
      <div class="tagrow">${t.tags.map((g) => `<span class="tag">${esc(varOf(g)?.label || g)}</span>`).join("")}<span class="tag" style="background:none">${esc(t.id)}</span></div></div>
      <div class="chips">${tools().map((tool) => chipHTML(res[tool.id] || { tool: tool.id })).join("")}</div></div>
    <div class="body">${tools().map((tool) => toolResultHTML(res[tool.id] || { tool: tool.id, coverage: "not-scanned" })).join("")}</div>
  </div>`;
}

function drawerHTML() {
  if (state.task) {
    const t = byTask[state.task];
    if (!t) return "";
    const it = itemOf(t.item),
      p = purposeOf(t.purpose);
    return `<p class="eyebrow">${esc(it.label)} × ${esc(p.label)}</p><h2>${esc(t.sentence)}</h2><p class="outcome">${esc(p.outcome)}</p>${taskHTML(t, true)}
      <p><button class="clear" data-opencell="${t.purpose}|${t.item}">All tasks in this cell →</button></p>`;
  }
  if (!state.cell) return "";
  const [p, i] = state.cell.split("|");
  const tasks = tasksIn(p === "*" ? null : p, i === "*" ? null : i);
  const outcome = p !== "*" ? purposeOf(p).outcome : "";
  const sums = tools()
    .map((t) => {
      const s = summarize(tasks, t.id);
      return `<tr><td><b>${esc(t.name)}</b></td>${LEVELS.map((l) => `<td class="num">${s.counts[l.id] || ""}</td>`).join("")}<td class="num">${s.invMedian == null ? "–" : fmtInv(s.invMedian)}</td><td class="num">${s.latMedian == null ? "–" : fmtS(s.latMedian)}</td><td class="num">${s.tokMedian == null ? "–" : fmtTok(s.tokMedian)}</td></tr>`;
    })
    .join("");
  const sorted = [...tasks].sort(
    (a, b) => disagreement(b) - disagreement(a) || a.id.localeCompare(b.id, undefined, { numeric: true }),
  );
  return `<p class="eyebrow">Cell</p><h2>${esc(cellTitle(state.cell))}</h2>${outcome ? `<p class="outcome">${esc(outcome)}</p>` : ""}
    <table class="list sumtable" style="margin-bottom:14px"><thead><tr><th>Tool</th>${LEVELS.map((l) => `<th class="num" title="${esc(l.label)}"><span class="sw seg-${l.id}"></span></th>`).join("")}<th class="num">Inv.</th><th class="num">Latency</th><th class="num">Tokens</th></tr></thead><tbody>${sums}</tbody></table>
    <p class="muted" style="font-size:12px">${tasks.length} tasks${state.tags.size || state.search ? " matching filters" : ""}. Most disagreement between tools first. Click a task for routes, evidence and timings.</p>
    ${sorted.map((t) => taskHTML(t, false)).join("")}`;
}

// ---------- tasks view ----------
function tasksViewHTML() {
  const rows = D.tasks.filter(taskVisible).filter((t) => !state.differ || tasksDisagree(t));
  const rank = (t, tool) => LEVELS.findIndex((l) => l.id === (resultsByTask[t.id]?.[tool]?.coverage || "not-scanned"));
  const k = state.sort.key;
  const val = (t) =>
    k === "sentence"
      ? t.sentence
      : k === "item"
        ? D.items.findIndex((i) => i.id === t.item)
        : k === "purpose"
          ? D.purposes.findIndex((p) => p.id === t.purpose) * 100 + D.items.findIndex((i) => i.id === t.item)
          : rank(t, k);
  rows.sort((a, b) => {
    const x = val(a),
      y = val(b);
    return (typeof x === "string" ? x.localeCompare(y) : x - y) * state.sort.dir;
  });
  const th = (key, label, cls = "") =>
    `<th data-sort="${key}" class="${cls}">${esc(label)}${state.sort.key === key ? (state.sort.dir > 0 ? " ↑" : " ↓") : ""}</th>`;
  return `<p class="muted">${rows.length} of ${D.tasks.length} tasks. Click a column to sort, a row for details.</p>
  <table class="list"><thead><tr>${th("sentence", "Task")}${th("item", "Item")}${th("purpose", "Purpose")}<th>Variations</th>${tools().map((t) => th(t.id, t.name)).join("")}</tr></thead><tbody>${rows
    .map(
      (t) =>
        `<tr class="clickable" data-task="${t.id}"><td>${esc(t.sentence)}</td><td>${esc(itemOf(t.item).label)}</td><td>${esc(purposeOf(t.purpose).label)}</td><td>${t.tags.map((g) => `<span class="tag">${esc(varOf(g)?.label || g)}</span>`).join(" ")}</td>${tools()
          .map((tool) => {
            const r = resultsByTask[t.id]?.[tool.id];
            const lv = r?.coverage || "not-scanned";
            const inv = r && invocations(r);
            return `<td style="white-space:nowrap"><span class="sw seg-${lv}" style="vertical-align:-1px"></span> ${esc(LEVEL[lv].short)}${inv ? ` <span class="muted">· ${inv[0]}</span>` : ""}</td>`;
          })
          .join("")}</tr>`,
    )
    .join("")}</tbody></table>`;
}

// ---------- timed commands view ----------
const FIXTURES = [
  { id: "short", label: "Short document" },
  { id: "formatted", label: "Same, heavily formatted" },
  { id: "long", label: "Long document (~20 pages)" },
];
function commandsViewHTML() {
  const uses = (tool, cmd) =>
    D.results.filter((r) => r.tool === tool && r.route?.some((s) => s.command === cmd)).length;
  const cell = (l) =>
    !l
      ? `<td class="num muted">–</td><td class="num muted"></td>`
      : l.status === "measured"
        ? `<td class="num" title="min ${(l.min_ms / 1000).toFixed(2)}s · max ${(l.max_ms / 1000).toFixed(2)}s · ${l.runs} runs">${(l.median_ms / 1000).toFixed(2)}s</td><td class="num">${fmtTok(l.tokens_median)}</td>`
        : `<td class="num muted" title="${esc(l.error || "")}">failed</td><td class="num muted"></td>`;
  return `<p class="muted" style="max-width:860px">Each command runs on its own five times against synthetic documents; the table shows the median time and the median tokens of its output (cl100k_base, a stand-in for Claude's tokenizer). CLI times include process start-up, which an agent pays on every call; MCP tools are called directly over the protocol with the server already running. Reads also run on a heavily formatted copy and a long document. A task's cost is the sum over its route on the short document; optional steps add to the upper bound. “Used by” counts graded task routes that include the command; untimed commands with many uses are the gaps that matter.</p>
  <div class="cols">${tools()
    .map((t) => {
      const timed = [...new Set(D.latency.filter((l) => l.tool === t.id).map((l) => l.command))];
      const routed = [...new Set(D.results.filter((r) => r.tool === t.id).flatMap((r) => (r.route || []).map((s) => s.command)))];
      const cmds = [...new Set([...timed, ...routed])].sort((a, b) => uses(t.id, b) - uses(t.id, a));
      const def = (D.definitions || []).find((d) => d.tool === t.id);
      return `<div><h3>${esc(t.name)} <span class="muted" style="font-weight:400">${esc(t.interface)} · ${esc(t.pin)}</span></h3>
      ${def ? `<p class="muted" style="font-size:12.5px;margin:0 0 6px">Definition cost per session: <b>${fmtTok(def.tokens)}</b> (${esc(def.source)}).</p>` : ""}
      <div class="grid-wrap"><table class="list"><thead><tr><th rowspan="2">Command</th>${FIXTURES.map((f) => `<th colspan="2" class="num">${f.label}</th>`).join("")}<th rowspan="2" class="num">Used by</th></tr><tr>${FIXTURES.map(() => `<th class="num">Time</th><th class="num">Tokens</th>`).join("")}</tr></thead><tbody>${cmds
        .map(
          (c) =>
            `<tr><td><code>${esc(c)}</code></td>${FIXTURES.map((f) => cell(latencyIndex[`${t.id}|${c}|${f.id}`])).join("")}<td class="num">${uses(t.id, c)}</td></tr>`,
        )
        .join("")}</tbody></table></div></div>`;
    })
    .join("")}</div>`;
}

// A pull-request run sets base grades beside head grades; most-disagreement-first sorting puts changed tasks on top.
function runBanner() {
  const r = D.run;
  const head = D.tools[1].id;
  const est = D.results.filter((x) => x.tool === head && x.stage === "estimated").length;
  return `<div class="banner"><b>Pull request #${r.pr}.</b> Base ${r.base_sha.slice(0, 7)} beside head ${r.head_sha.slice(0, 7)}; ${r.regrade} tasks were selected for regrading because their cited code changed${
    est ? `. <b>Estimate:</b> ${est} head grades come from reading the diff, not from the grading pipeline, and are marked “estimate”` : ""
  }. Tasks where the two columns differ sort first.</div>`;
}

// ---------- main render & events ----------
function render() {
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("active", b.dataset.view === state.view));
  $("#banner").innerHTML = (D.run ? runBanner() : "") + (D.mock
    ? `<div class="banner"><b>Mock data.</b> Task sentences, coverage levels, routes and timings are invented to review the interface. Only “Heading × Change wording”, task 1, cites real source notes, and those notes predate the current pins.</div>`
    : D.partial
      ? `<div class="banner"><b>Preview.</b> ${D.tools.length * D.tasks.length - D.results.length} of ${D.tools.length * D.tasks.length} task grades are still pending and show as not scanned. ${D.latency.length ? "" : "Latency has not been measured yet."} The page checks for new results every two minutes.</div>`
      : "");
  $("#counts").textContent = `${D.tasks.length} tasks · ${D.results.length} results · ${D.latency.filter((l) => l.status === "measured").length} timed commands`;
  $("#controls").innerHTML = controlsHTML();
  $("#legend").innerHTML = legendHTML();
  $("#view").innerHTML =
    state.view === "grid" ? gridHTML() : state.view === "tasks" ? tasksViewHTML() : commandsViewHTML();
  renderDrawer();
  writeHash();
}
function renderDrawer() {
  const html = drawerHTML();
  $("#drawer").hidden = !html;
  $("#drawer-content").innerHTML = html;
}

document.addEventListener("click", (e) => {
  const el = e.target.closest("button, .cellbox, [data-task], [data-sort]");
  if (!el) {
    const inside = e.target.closest("#drawer, .controls, .legend, details, input, label");
    if (!inside && !$("#drawer").hidden) {
      state.cell = state.task = null;
      render();
    }
    return;
  }
  if (el.closest("nav") && el.dataset.view) {
    state.view = el.dataset.view;
    return render();
  }
  if (el.dataset.metric) {
    state.metric = el.dataset.metric;
    return render();
  }
  if (el.dataset.focus) {
    state.focus = el.dataset.focus;
    return render();
  }
  if (el.dataset.clear === "tags") {
    state.tags.clear();
    return render();
  }
  if (el.dataset.sort) {
    state.sort = { key: el.dataset.sort, dir: state.sort.key === el.dataset.sort ? -state.sort.dir : 1 };
    return render();
  }
  if (el.dataset.opencell) {
    state.task = null;
    state.cell = el.dataset.opencell;
    return render();
  }
  if (el.id === "drawer-close") {
    state.cell = state.task = null;
    return render();
  }
  if (el.classList.contains("cellbox") && el.dataset.key) {
    state.task = null;
    state.cell = state.cell === el.dataset.key ? null : el.dataset.key;
    return render();
  }
  if (el.dataset.task) {
    if (el.closest("#drawer")) {
      if (e.target.closest(".head")) el.classList.toggle("open");
      return;
    }
    state.cell = null;
    state.task = el.dataset.task;
    renderDrawer();
    writeHash();
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#drawer").hidden) {
    state.cell = state.task = null;
    render();
  }
  if (e.key === "Enter" && e.target.classList?.contains("cellbox")) e.target.click();
});
document.addEventListener("change", (e) => {
  if (e.target.dataset.tag) {
    e.target.checked ? state.tags.add(e.target.dataset.tag) : state.tags.delete(e.target.dataset.tag);
    const open = true;
    render();
    const d = document.querySelector("details.tags");
    if (d && open) d.open = true;
  }
  if (e.target.id === "differ") {
    state.differ = e.target.checked;
    render();
  }
});
let searchTimer;
document.addEventListener("input", (e) => {
  if (e.target.id !== "search") return;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.search = e.target.value;
    render();
    const s = $("#search");
    s.focus();
    s.setSelectionRange(s.value.length, s.value.length);
  }, 200);
});
const tip = $("#tip");
document.addEventListener("mouseover", (e) => {
  const c = e.target.closest(".cellbox[data-key]");
  if (!c || c.classList.contains("empty")) return (tip.hidden = true);
  tip.innerHTML = tipHTML(c.dataset.key);
  tip.hidden = false;
});
document.addEventListener("mousemove", (e) => {
  if (tip.hidden) return;
  const pad = 14;
  const w = tip.offsetWidth,
    h = tip.offsetHeight;
  let x = e.clientX + pad,
    y = e.clientY + pad;
  if (x + w > innerWidth - 8) x = e.clientX - w - pad;
  if (y + h > innerHeight - 8) y = e.clientY - h - pad;
  tip.style.left = x + "px";
  tip.style.top = y + "px";
});

function load(data) {
  D = data;
  byTask = Object.fromEntries(D.tasks.map((t) => [t.id, t]));
  resultsByTask = {};
  for (const r of D.results) (resultsByTask[r.task] ||= {})[r.tool] = r;
  latencyIndex = Object.fromEntries(D.latency.map((l) => [`${l.tool}|${l.command}|${l.fixture || "short"}`, l]));
}
const fingerprint = (d) =>
  [d.results.length, d.results.filter((r) => r.stage === "verified").length, d.latency.length, d.partial].join("|");
// ?data=matrix-pr72.json shows a pull-request run (pipeline/pr.py) instead of the full matrix.
const DATA_FILE = new URLSearchParams(location.search).get("data") || "matrix.json";
const fetchData = async () => (await fetch(DATA_FILE, { cache: "no-store" })).json();

// While results are partial, check for a rebuilt matrix.json every two minutes.
async function poll() {
  if (!D.partial) return;
  try {
    const next = await fetchData();
    if (fingerprint(next) !== fingerprint(D)) {
      load(next);
      render();
    }
  } catch {}
  setTimeout(poll, 120000);
}

(async () => {
  readHash();
  load(await fetchData());
  render();
  setTimeout(poll, 120000);
})();
