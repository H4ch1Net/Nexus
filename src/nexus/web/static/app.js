"use strict";

// ---------------------------------------------------------------------------
// Small DOM helpers
// ---------------------------------------------------------------------------
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v != null) node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid == null) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
};
const pct = (x) => `${Math.round((x || 0) * 100)}%`;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function barEl(score) {
  const cls = score >= 0.85 ? "" : score >= 0.6 ? "mid" : "low";
  return el("div", { class: "bar-wrap" },
    el("div", { class: `bar ${cls}` }, el("span", { style: `width:${pct(score)}` })),
    el("span", { class: "mono" }, pct(score)));
}

function tableEl(headers, rows) {
  return el("table", {},
    el("thead", {}, el("tr", {}, ...headers.map((h) => el("th", {}, h)))),
    el("tbody", {}, ...rows.map((r) => el("tr", {}, ...r.map((c) =>
      c && c.nodeType ? el("td", {}, c) : el("td", { class: "mono" }, c == null ? "" : String(c)))))));
}

function kvEl(pairs) {
  return el("div", { class: "kv" }, ...pairs.map(([k, v]) =>
    el("div", {}, el("span", { class: "k" }, k), el("span", { class: "v" }, v == null ? "" : String(v)))));
}

async function api(route, body) {
  const res = await fetch(route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------
const TOOLS = {
  detect: {
    title: "Detect",
    desc: "Identify encodings, classical ciphers, and modern crypto from a string.",
    fields: [{ name: "input", type: "textarea", placeholder: "SGVsbG8gV29ybGQh", label: "input" }],
    route: "/api/crypt/detect",
    render(r) {
      if (!r.candidates || !r.candidates.length) return el("div", { class: "empty" }, "No matches found.");
      const m = r.metrics;
      const meta = el("div", { class: "status" },
        `length ${r.input_length} · entropy ${m.entropy.toFixed(2)} · IC ${m.index_of_coincidence.toFixed(4)}`);
      const rows = r.candidates.map((c) => [
        c.name.replace(/_/g, " "), barEl(c.score), (c.category || "").replace(/_/g, " ")]);
      return el("div", {}, meta, tableEl(["name", "score", "category"], rows));
    },
  },
  decode: {
    title: "Decode / Magic",
    desc: "Decode with a named codec, or let auto mode find the recipe.",
    fields: [
      { name: "input", type: "textarea", placeholder: "Paste encoded text...", label: "input" },
      { name: "codec", type: "select", label: "codec", options: ["auto"], dynamic: "codecs" },
      { name: "shift", type: "number", label: "caesar shift", value: 3 },
      { name: "key", type: "text", label: "xor key", placeholder: "(for xor)" },
    ],
    route: "/api/crypt/decode",
    render(r) {
      if (r.mode !== "auto") return el("pre", { class: "out" }, r.output);
      if (!r.candidates.length) return el("div", { class: "empty" }, "No readable decoding found.");
      return el("div", {}, ...r.candidates.map((c) =>
        el("div", { class: "card", style: "margin:8px 0;padding:12px" },
          el("div", { class: "bar-wrap" }, barEl(c.score),
            el("span", { class: "recipe" }, c.recipe.join(" → "))),
          el("pre", { class: "out" }, c.output))));
    },
  },
  hash: {
    title: "Hash",
    desc: "Compute common digests of a string (md5, sha family, blake2, crc32).",
    fields: [{ name: "input", type: "textarea", placeholder: "text to hash", label: "input" }],
    route: "/api/crypt/hash",
    render(r) { return kvEl(Object.entries(r.hashes)); },
  },
  hashid: {
    title: "Hash ID",
    desc: "Identify the likely algorithm of a hash by format, length, and charset.",
    fields: [{ name: "input", type: "text", placeholder: "5d41402abc4b2a76b9719d911017c592", label: "hash" }],
    route: "/api/crypt/hash-id",
    render(r) {
      if (!r.candidates.length) return el("div", { class: "empty" }, "Not a recognized hash format.");
      return tableEl(["algorithm", "confidence", "basis"],
        r.candidates.map((c) => [c.name, barEl(c.confidence), c.basis]));
    },
  },
  codeid: {
    title: "Code ID",
    desc: "Identify the programming language of a code snippet.",
    fields: [{ name: "input", type: "textarea", placeholder: "def hello():\n    print('hi')", label: "snippet" }],
    route: "/api/enum/code-id",
    render(r) {
      return tableEl(["language", "confidence", "evidence"],
        r.candidates.map((c) => [c.language, barEl(c.confidence), c.evidence]));
    },
  },
  ports: {
    title: "Ports",
    desc: "Look up a well-known port by number, or search services by name.",
    fields: [{ name: "input", type: "text", placeholder: "443  or  smb", label: "port or service" }],
    route: "/api/enum/ports",
    render(r) {
      if (!r.matches.length) return el("div", { class: "empty" }, `No match for "${r.query}".`);
      return tableEl(["port", "service", "proto", "description"],
        r.matches.map((m) => [m.port, m.service, m.protocol, m.description]));
    },
  },
  iocs: {
    title: "IOC Extract",
    desc: "Pull indicators (URLs, IPs, domains, emails, hashes) out of pasted text.",
    fields: [{ name: "input", type: "textarea", placeholder: "Paste logs or text...", label: "text" }],
    route: "/api/osint/iocs",
    render(r) {
      const keys = Object.keys(r.iocs);
      if (!keys.length) return el("div", { class: "empty" }, "No indicators found.");
      return el("div", {}, el("div", { class: "status" }, `${r.ioc_total} indicator(s)`),
        ...keys.map((k) => el("div", { style: "margin-bottom:10px" },
          el("label", {}, `${k} (${r.iocs[k].length})`),
          el("div", {}, ...r.iocs[k].map((v) => el("span", { class: "chip" }, v))))));
    },
  },
  defang: {
    title: "Defang / Refang",
    desc: "Neutralize indicators for safe sharing, or restore them.",
    fields: [
      { name: "input", type: "textarea", placeholder: "http://evil.example.com/x", label: "text" },
      { name: "mode", type: "select", label: "mode", options: ["defang", "refang"] },
    ],
    route: "/api/osint/defang",
    render(r) { return el("pre", { class: "out" }, r.output); },
  },
};

// ---------------------------------------------------------------------------
// Rendering + wiring
// ---------------------------------------------------------------------------
let CODECS = ["auto"];

function buildField(f) {
  const id = `f-${f.name}`;
  let input;
  if (f.type === "textarea") {
    input = el("textarea", { id, name: f.name, placeholder: f.placeholder || "" });
  } else if (f.type === "select") {
    const opts = f.dynamic === "codecs" ? CODECS : f.options;
    input = el("select", { id, name: f.name }, ...opts.map((o) => el("option", { value: o }, o)));
  } else {
    input = el("input", { id, type: f.type === "number" ? "number" : "text", name: f.name,
      placeholder: f.placeholder || "", value: f.value != null ? f.value : "" });
  }
  const wrap = el("div", { class: "field" }, el("label", { for: id }, f.label || f.name), input);
  return { wrap, input };
}

function showTool(key) {
  const tool = TOOLS[key];
  const panel = document.getElementById("panel");
  panel.innerHTML = "";

  const inputs = {};
  const bigFields = tool.fields.filter((f) => f.type === "textarea");
  const smallFields = tool.fields.filter((f) => f.type !== "textarea");
  const card = el("div", { class: "card" });

  for (const f of bigFields) {
    const { wrap, input } = buildField(f);
    inputs[f.name] = input;
    card.append(wrap);
  }
  const controls = el("div", { class: "controls" });
  for (const f of smallFields) {
    const { wrap, input } = buildField(f);
    inputs[f.name] = input;
    controls.append(wrap);
  }
  const runBtn = el("button", { class: "btn", type: "button" }, "Run");
  controls.append(el("div", { class: "field", style: "flex:0" }, el("label", { html: "&nbsp;" }), runBtn));
  card.append(controls);
  card.append(el("div", { class: "hint" }, "Ctrl/⌘ + Enter to run"));

  const result = el("div", { class: "result", role: "region", "aria-live": "polite" });

  async function run() {
    const body = {};
    for (const [k, inp] of Object.entries(inputs)) body[k] = inp.value;
    result.innerHTML = "";
    result.append(el("div", { class: "status" }, "running..."));
    try {
      const data = await api(tool.route, body);
      result.innerHTML = "";
      if (data && data.error) result.append(el("div", { class: "error" }, `error: ${data.error}`));
      else result.append(tool.render(data));
    } catch (e) {
      result.innerHTML = "";
      result.append(el("div", { class: "error" }, `request failed: ${e}`));
    }
  }
  runBtn.addEventListener("click", run);
  card.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); run(); }
  });

  panel.append(
    el("div", { class: "tool-head" }, el("h1", {}, tool.title), el("p", {}, tool.desc)),
    card, result);
  const first = panel.querySelector("textarea, input, select");
  if (first) first.focus();
}

function initNav() {
  const items = document.querySelectorAll(".nav-item");
  items.forEach((btn) => btn.addEventListener("click", () => {
    items.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    showTool(btn.dataset.tool);
  }));
}

async function init() {
  // The server validates the real codec set; this list drives the picker.
  CODECS = ["auto", "base64", "base32", "hex", "base58", "ascii85", "base85", "url",
    "html", "quoted_printable", "rot13", "rot47", "atbash", "binary", "decimal",
    "morse", "reverse", "caesar", "xor"];
  try {
    const meta = await (await fetch("/api/meta")).json();
    if (meta.version) document.getElementById("version").textContent = `v${meta.version} · offline`;
  } catch (e) { /* ignore */ }
  initNav();
  showTool("detect");
}

init();
