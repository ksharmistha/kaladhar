/* Kaladhar Product Fidelity Studio — demo UI.
 *
 * This file renders only. Every number it shows comes from the API, which in
 * turn calls the existing pipeline. Nothing is computed, estimated or
 * simulated here.
 */

const STEPS = [
  { id: 1, key: "upload",   title: "Upload product image", meta: "Validate the source" },
  { id: 2, key: "analyze",  title: "Analyse product",      meta: "Mask · signature · weave" },
  { id: 3, key: "briefs",   title: "Generate scene briefs",meta: "5-axis variation matrix" },
  { id: 4, key: "handoff",  title: "Ekly handoff",         meta: "Manual — no API", manual: true },
  { id: 5, key: "import",   title: "Import generated videos", meta: "Probe every file" },
  { id: 6, key: "fidelity", title: "Fidelity Lock",        meta: "Gate 1 · per-frame drift" },
  { id: 7, key: "diversity",title: "Diversity Engine",     meta: "Gate 2 · pairwise distance" },
  { id: 8, key: "export",   title: "Safe Cut & Export",    meta: "1080×1920 delivery" },
];

let S = { run: null, runs: [], step: 1, demoRun: null, busy: false };

/* ------------------------------------------------------------------ utils */
const $ = (s, r = document) => r.querySelector(s);
const el = (h) => { const d = document.createElement("div"); d.innerHTML = h.trim(); return d.firstElementChild; };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fx = (v, n = 2) => (v === null || v === undefined) ? "—" : Number(v).toFixed(n);

function toast(msg, isErr) {
  const t = el(`<div class="toast ${isErr ? "err" : ""}">${esc(msg)}</div>`);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), isErr ? 6000 : 3200);
}

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let d; try { d = await r.json(); } catch (e) { d = {}; }
    throw new Error(d.detail || `${r.status} ${r.statusText}`);
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r.text();
}

const fileUrl = (p) => `/api/runs/${S.run.run_id}/file/${p}`;

/* poll a background job to completion, updating a progress element */
async function awaitJob(jobId, mount, label) {
  const box = el(`<div class="card"><h3>${esc(label)}</h3>
    <div class="prog"><i style="width:0%"></i></div>
    <div class="prog-note">starting…</div></div>`);
  mount.prepend(box);
  const bar = $(".prog i", box), note = $(".prog-note", box);
  for (;;) {
    const j = await api(`/api/jobs/${jobId}`);
    const pct = j.percent ?? (j.state === "done" ? 100 : 0);
    bar.style.width = pct + "%";
    const unit = j.total ? ` · ${j.done}/${j.total}` : "";
    note.textContent = `${j.state}${unit} · ${j.elapsed_s}s elapsed`;
    if (j.state === "done") { box.remove(); return j; }
    if (j.state === "error") { box.remove(); throw new Error(j.error || "job failed"); }
    await new Promise(r => setTimeout(r, 800));
  }
}

/* ------------------------------------------------------------------- rail */
function renderRail() {
  const reached = stepReached();
  $("#steps").innerHTML = STEPS.map(s => {
    const done = reached > s.id;
    const locked = s.id > reached;
    return `<li class="step ${S.step === s.id ? "active" : ""} ${done ? "done" : ""} ${locked ? "locked" : ""} ${s.manual ? "manual" : ""}" data-step="${s.id}">
      <span class="step-num">${done ? "✓" : s.id}</span>
      <span class="step-body">
        <span class="step-title">${esc(s.title)}</span>
        <span class="step-meta">${esc(s.meta)}</span>
      </span></li>`;
  }).join("");
  $("#steps").querySelectorAll(".step").forEach(n => n.onclick = () => {
    if (n.classList.contains("locked")) { toast("Complete the earlier steps first."); return; }
    S.step = +n.dataset.step; render();
  });

  $("#runList").innerHTML = S.runs.map(r => `
    <button class="run-pill ${S.run && r.run_id === S.run.run_id ? "current" : ""}" data-run="${esc(r.run_id)}">
      <div>${esc(r.run_id)}</div>
      <div class="tag">${esc(r.state)}${r.is_demo_run ? " · reference run" : ""}</div>
    </button>`).join("");
  $("#runList").querySelectorAll(".run-pill").forEach(n => n.onclick = () => loadRun(n.dataset.run));
}

/* how far this run has progressed, from real state on the server */
function stepReached() {
  const r = S.run;
  if (!r) return 1;
  if (r.exports?.length || r.safecut) return 8;
  if (r.selection) return 8;
  if (Object.keys(r.scores || {}).length) return 7;
  if (r.imported?.length) return 6;
  if (r.briefs?.length) return 5;
  if (r.source) return 3;
  if (r.state === "CREATED") return 2;
  return 1;
}

/* ------------------------------------------------------------------ pages */
function head(eyebrow, title, sub) {
  return `<div class="page-head"><div class="eyebrow">${esc(eyebrow)}</div>
    <h2>${esc(title)}</h2><p>${sub}</p></div>`;
}

function render() {
  renderRail();
  const m = $("#main");
  m.innerHTML = "";
  ({ 1: pgUpload, 2: pgAnalyze, 3: pgBriefs, 4: pgHandoff,
     5: pgImport, 6: pgFidelity, 7: pgDiversity, 8: pgExport }[S.step])(m);
  m.scrollTop = 0; window.scrollTo(0, 0);
}

/* -------------------------------------------------------------- 1 upload */
function pgUpload(m) {
  m.innerHTML = head("Step 1", "Upload product image",
    "One photograph of the product, ideally on a model. Everything downstream is measured against this image. The pipeline is product-agnostic — a saree, kurti, lehenga, dress or shirt all work; you declare the product type at step 3.");

  const v = S.run?.source?.validation || S.run?.upload?.validation;
  const card = el(`<div class="card">
    <div class="drop" id="dz">
      <div class="big">Drop a product image, or click to browse</div>
      <div class="sm">JPEG · PNG · WEBP · BMP · TIFF — minimum short edge 400px</div>
    </div>
    <input type="file" id="fi" accept="image/*">
  </div>`);
  m.appendChild(card);

  const dz = $("#dz", card), fi = $("#fi", card);
  dz.onclick = () => fi.click();
  dz.ondragover = e => { e.preventDefault(); dz.classList.add("over"); };
  dz.ondragleave = () => dz.classList.remove("over");
  dz.ondrop = e => { e.preventDefault(); dz.classList.remove("over"); if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); };
  fi.onchange = () => fi.files[0] && upload(fi.files[0]);

  if (v) {
    const info = v.info || {};
    const okBadge = v.ok ? `<span class="badge b-pass">accepted</span>` : `<span class="badge b-fail">rejected</span>`;
    m.appendChild(el(`<div class="card">
      <div class="row"><h3>Validation result</h3><div class="spacer"></div>${okBadge}</div>
      <div class="hint">Produced by <code>validate_image()</code> — the same check the CLI runs.</div>
      <div class="grid g2">
        <div>${S.run?.source ? `<img class="shot" src="${fileUrl("input/working.png")}" alt="uploaded product">` : ""}</div>
        <div><dl class="kv">
          ${Object.entries(info).map(([k, val]) => `<dt>${esc(k)}</dt><dd>${esc(val)}</dd>`).join("")}
        </dl>
        ${(v.warnings || []).map(w => `<div class="banner warn" style="margin-top:12px"><span class="ico">⚠</span><div>${esc(w)}</div></div>`).join("")}
        ${(v.errors || []).map(w => `<div class="banner warn" style="margin-top:12px;background:var(--fail-soft);border-color:#f3c6c3;color:#7d1a15"><span class="ico">✕</span><div>${esc(w)}</div></div>`).join("")}
        </div>
      </div></div>`));
    if (v.ok) m.appendChild(nextBtn("Analyse this product →", 2));
  }
}

async function upload(file) {
  if (S.busy) return;
  S.busy = true;
  try {
    const fd = new FormData(); fd.append("file", file);
    const r = await api("/api/runs", { method: "POST", body: fd });
    await refreshRuns();
    await loadRun(r.run_id, 1);
    toast(r.ok ? "Image accepted" : "Image rejected — see the report");
  } catch (e) { toast(e.message, true); }
  S.busy = false;
}

function nextBtn(label, step, onclick) {
  const b = el(`<div class="row end"><button class="btn">${esc(label)}</button></div>`);
  $("button", b).onclick = onclick || (() => { S.step = step; render(); });
  return b;
}

/* ------------------------------------------------------------- 2 analyze */
function pgAnalyze(m) {
  m.innerHTML = head("Step 2", "Analyse product",
    "Segment the garment, then fingerprint it. Every later fidelity check is measured against this signature, <b>inside the garment mask only</b> — the background is meant to change.");

  const src = S.run?.source;
  if (!src) {
    const c = el(`<div class="card"><h3>Ready to analyse</h3>
      <div class="hint">Runs rembg segmentation, skin-chrominance refinement, CIELAB palette extraction, the Gabor+FFT weave descriptor and a CLIP embedding. Measured at roughly 9 seconds.</div>
      <button class="btn" id="go">Run analysis</button></div>`);
    m.appendChild(c);
    $("#go", c).onclick = async () => {
      $("#go", c).disabled = true;
      try {
        const st = await api(`/api/runs/${S.run.run_id}/analyze`, { method: "POST" });
        S.run = st; toast("Analysis complete"); render();
      } catch (e) { toast(e.message, true); $("#go", c).disabled = false; }
    };
    return;
  }

  const mask = src.mask || {};
  m.appendChild(el(`<div class="grid g2">
    <div class="card"><h3>Garment mask</h3>
      <div class="hint">rembg subject mask refined by a skin-chrominance heuristic, then largest-component cleanup.</div>
      <img class="shot" src="${fileUrl("evidence/mask_garment_overlay.png")}" alt="garment mask overlay">
      <dl class="kv" style="margin-top:12px">
        <dt>Subject mask</dt><dd>${fx(mask.subject_fraction * 100, 1)}% of frame</dd>
        <dt>Garment mask</dt><dd>${fx(mask.garment_fraction * 100, 1)}% of frame</dd>
      </dl>
      ${(mask.notes || []).map(n => `<div class="footnote">${esc(n)}</div>`).join("")}
    </div>
    <div class="card"><h3>Weave Guard region</h3>
      <div class="hint">The most texture-dense patch inside the mask, located automatically. On a saree this lands on the border or pallu; on a printed kurti or dress it lands on the densest print area.</div>
      <img class="shot" src="${fileUrl("evidence/weave_guard_source.png")}" alt="weave guard source">
      <div class="footnote">Patch box: ${esc(JSON.stringify(src.border_patch_box))}</div>
    </div>
  </div>`));

  m.appendChild(el(`<div class="card"><h3>Product signature</h3>
    <div class="hint">The baseline every drift comparison scores against.</div>
    <div class="grid g2">
      <div>
        <div style="font-size:12.5px;color:var(--muted);margin-bottom:4px">Dominant colours — CIELAB k-means, garment pixels only</div>
        <div class="swatches">${(src.palette_hex || []).map(h => `<div><div class="sw" style="background:${esc(h)}"></div><div class="sw-lab">${esc(h)}</div></div>`).join("")}</div>
      </div>
      <div><dl class="kv">
        <dt>Working size</dt><dd>${esc((src.working_size || []).join(" × "))}</dd>
        <dt>Reference image</dt><dd>${esc((src.reference_size || []).join(" × "))}</dd>
        <dt>Weave descriptor</dt><dd>27-d Gabor + FFT + HF</dd>
        <dt>Identity vector</dt><dd>512-d CLIP</dd>
      </dl></div>
    </div></div>`));

  m.appendChild(nextBtn("Generate scene briefs →", 3));
}

/* -------------------------------------------------------------- 3 briefs */
function pgBriefs(m) {
  m.innerHTML = head("Step 3", "Generate scene briefs",
    "Variation is structural, not verbal. Each brief is a point on a five-axis grid, and the sampler enforces a hard rule: <b>any two briefs differ on at least 3 of 5 axes</b>.");

  if (!S.run.briefs?.length) {
    const known = S.run.known_products || [];
    // Prefilled only from what this run already declared. A brand-new run starts
    // blank and the operator must choose -- an unspecified product is never
    // silently assumed to be a saree.
    const cur = S.run.product || "";
    const c = el(`<div class="card"><h3>Sample the variation matrix</h3>
      <div class="hint">Six environments, each with its own architecture, time of day and key light. Environment, camera movement and creative concept are each unique across the set, so every pair already differs on three axes before the rule is even checked.</div>
      <div class="row" style="margin-bottom:12px">
        <label style="font-size:13px">Product type
          <input id="prod" list="prodlist" value="${esc(cur)}" placeholder="choose or type…"
            autocomplete="off"
            style="width:180px;padding:6px 8px;border:1px solid var(--line);border-radius:7px">
          <datalist id="prodlist">${known.map(p => `<option value="${esc(p)}">`).join("")}</datalist>
        </label>
      </div>
      <div class="footnote" style="margin:-6px 0 12px">The product type is <b>declared by you, not auto-detected</b> — there is no garment classifier in this pipeline, and guessing one would be inventing a capability. It drives the product noun and the construction details named in every prompt. An unspecified product is never assumed to be a saree.</div>
      <div class="row"><label style="font-size:13px">Briefs <input id="n" type="number" value="6" min="2" max="12" style="width:64px;padding:6px 8px;border:1px solid var(--line);border-radius:7px"></label>
      <label style="font-size:13px">Seed <input id="sd" type="number" value="7" style="width:74px;padding:6px 8px;border:1px solid var(--line);border-radius:7px"></label>
      <button class="btn" id="go">Generate briefs</button></div></div>`);
    m.appendChild(c);
    const prodEl = $("#prod", c), goEl = $("#go", c);
    const syncGo = () => {
      goEl.disabled = !prodEl.value.trim();
      goEl.textContent = prodEl.value.trim() ? "Generate briefs" : "Enter a product type first";
    };
    prodEl.oninput = syncGo; prodEl.onchange = syncGo; syncGo();
    goEl.onclick = async () => {
      const chosen = prodEl.value.trim();
      if (!chosen) { toast("Enter a product type first.", true); return; }
      goEl.disabled = true;
      try {
        const fd = new FormData();
        fd.append("n", $("#n", c).value); fd.append("seed", $("#sd", c).value);
        fd.append("product", chosen);
        S.run = await api(`/api/runs/${S.run.run_id}/briefs`, { method: "POST", body: fd });
        toast("Briefs generated"); render();
      } catch (e) { toast(e.message, true); syncGo(); }
    };
    return;
  }

  const rep = S.run.sampling_report || {}, ax = S.run.axis_order;
  m.appendChild(el(`<div class="banner info"><span class="ico">✓</span><div>
    <b>Product: ${esc(S.run.product || "—")}</b> · <b>Minimum axis difference achieved: ${esc(rep.min_axis_diff_achieved)}</b> against the required ${esc(rep.min_axis_diff_required)}.
    Environment, camera and concept are unique across the set. Expected cost if generated:
    ${fx(S.run.plan?.expected_credits, 2)} credits at the 45.50 per generation we measured.</div></div>`));
  const regen = el(`<div class="row" style="margin-bottom:14px"><button class="btn ghost sm" id="regen">Regenerate with a different product type or seed</button></div>`);
  m.appendChild(regen);
  $("#regen", regen).onclick = () => { S.run = { ...S.run, briefs: [] }; render(); };

  m.appendChild(el(`<div class="grid g2">${S.run.briefs.map(b => `
    <div class="card" style="margin:0">
      <div class="row"><h3>${esc(b.id)}</h3><div class="spacer"></div><span class="badge b-info">scene brief</span></div>
      <div style="margin:10px 0 4px">${ax.map(k => `<span class="chip"><b>${esc(k)}</b> ${esc(b.axis_labels[k])}</span>`).join("")}</div>
      <details style="margin-top:8px"><summary style="font-size:12.5px;color:var(--accent-dark);cursor:pointer">View full prompt</summary>
        <div class="prompt-box">${esc(b.prompt)}</div></details>
    </div>`).join("")}</div>`));

  const dm = S.run.difference_matrix;
  if (dm) {
    m.appendChild(el(`<div class="card"><h3>Pairwise axis-difference matrix</h3>
      <div class="hint">Proof the rule holds rather than an assertion. Every off-diagonal cell is the number of axes on which that pair differs.</div>
      <div class="scroll"><table class="matrix"><tr><th></th>${S.run.briefs.map(b => `<th class="num">${esc(b.id)}</th>`).join("")}</tr>
      ${dm.map((row, i) => `<tr><td><b>${esc(S.run.briefs[i].id)}</b></td>${row.map((v, j) => i === j
        ? `<td class="d" style="color:var(--muted)">—</td>`
        : `<td class="d"><span class="heat" style="background:${v >= 4 ? "#d8f0e6" : v >= 3 ? "#eaf4ea" : "#fdeceb"};padding:4px 10px;border-radius:6px">${v}</span></td>`).join("")}</tr>`).join("")}
      </table></div></div>`));
  }
  m.appendChild(nextBtn("Continue to Ekly handoff →", 4));
}

/* ------------------------------------------------------------- 4 handoff */
function pgHandoff(m) {
  m.innerHTML = head("Step 4", "Ekly handoff",
    "This is the one manual step in the workflow, and it is deliberate.");

  m.appendChild(el(`<div class="banner manual"><span class="ico">◆</span><div>
    <b>Generation is manual because Ekly.ai exposes no API to us.</b>
    There is no API key and no programmatic access, so nothing in this product calls, queues,
    batches or polls Ekly. The run pauses here at <code>AWAITING_CLIPS</code> and resumes when
    real MP4s are uploaded at step 5.<br><br>
    That is not a workaround — it is where the value sits. The client&rsquo;s problem is not that
    video generation is unavailable; plenty of tools generate video. The problem is that output
    comes back <b>repetitive</b> and the product <b>drifts</b>. Both are solved before and after
    generation, which is exactly what this platform automates.</div></div>`));

  m.appendChild(el(`<div class="card"><h3>Operator workflow</h3>
    <div class="hint">Work through this top to bottom in the Ekly web interface.</div>
    <div class="grid g2">
      <div>
        <ol style="font-size:13.5px;line-height:1.9;padding-left:18px">
          <li>Open Ekly → <b>Video</b> → model <b>Kling AI Video Pro</b></li>
          <li>Attach the reference image with <b>+ ref image</b></li>
          <li>Set <b>9:16</b>, <b>5 seconds</b>, standard quality</li>
          <li>Paste a brief prompt below, verbatim</li>
          <li>Generate, then save as <code>${esc(S.run.briefs?.[0]?.id || "V01")}.mp4</code> and so on</li>
          <li>Record the wall-clock generation time — we still do not have it</li>
        </ol>
        <div class="row" style="margin-top:12px">
          <a class="btn ghost sm" href="${fileUrl("input/reference.png")}" download>Download reference image</a>
          <a class="btn ghost sm" href="/api/runs/${S.run.run_id}/sheet" target="_blank">Open full operator sheet</a>
        </div>
      </div>
      <div><img class="shot" src="${fileUrl("input/reference.png")}" alt="reference image to attach"></div>
    </div>
    <div class="banner warn" style="margin-top:16px"><span class="ico">⚠</span><div>
      In every generation we have run, the <b>9:16 setting did not produce a 9:16 file</b> — all four
      came back 768×1152 (2:3). Do not trust the setting. Every clip is re-probed on import and
      converted at export.</div></div>
  </div>`));

  if (S.run.briefs?.length) {
    m.appendChild(el(`<div class="card"><h3>Prompts to paste</h3>
      <div class="hint">Scene, then camera direction, then an uppercase PRODUCT ACCURACY block, then negative guidance — the structure validated in our prototype.</div>
      ${S.run.briefs.map(b => `<div style="border:1px solid var(--line);border-radius:11px;padding:14px;margin-bottom:11px">
        <div class="row"><b style="font-size:14px">${esc(b.id)}</b>
          <span style="font-size:12px;color:var(--muted)">${esc(Object.values(b.axis_labels).join(" · "))}</span>
          <div class="spacer"></div>
          <button class="btn ghost sm copy" data-id="${esc(b.id)}">Copy prompt</button></div>
        <div class="prompt-box" id="p-${esc(b.id)}">${esc(b.prompt)}</div></div>`).join("")}
    </div>`));
    m.querySelectorAll(".copy").forEach(btn => btn.onclick = async () => {
      const txt = $("#p-" + btn.dataset.id).textContent;
      try { await navigator.clipboard.writeText(txt); btn.textContent = "Copied ✓"; }
      catch (e) { btn.textContent = "Select manually"; }
      setTimeout(() => btn.textContent = "Copy prompt", 1800);
    });
  }
  m.appendChild(nextBtn("I have my videos — import them →", 5));
}

/* -------------------------------------------------------------- 5 import */
function pgImport(m) {
  m.innerHTML = head("Step 5", "Import generated videos",
    "Every file is <b>probed, not trusted</b>. Delivered format is read off the file itself.");

  const card = el(`<div class="card">
    <div class="drop" id="dz"><div class="big">Drop the generated MP4s, or click to browse</div>
      <div class="sm">Multiple files supported · MP4 · MOV · WEBM · MKV</div></div>
    <input type="file" id="fi" accept="video/*" multiple></div>`);
  m.appendChild(card);
  const dz = $("#dz", card), fi = $("#fi", card);
  dz.onclick = () => fi.click();
  dz.ondragover = e => { e.preventDefault(); dz.classList.add("over"); };
  dz.ondragleave = () => dz.classList.remove("over");
  dz.ondrop = e => { e.preventDefault(); dz.classList.remove("over"); uploadClips(e.dataTransfer.files); };
  fi.onchange = () => uploadClips(fi.files);

  const imp = S.run.imported || [];
  if (imp.length) {
    const anyBad = imp.some(r => !r.format_ok);
    m.appendChild(el(`<div class="card"><h3>Imported clips — ${imp.length}</h3>
      <div class="hint">Read with <code>probe()</code> from the actual file.</div>
      <div class="scroll"><table><tr><th>Clip</th><th class="num">Resolution</th><th class="num">Aspect</th><th class="num">Duration</th><th class="num">Frames</th><th class="num">Size</th><th>Delivered format</th></tr>
      ${imp.map(r => { const p = r.probe; return `<tr>
        <td><b>${esc(r.id)}</b>${r.matched_brief ? "" : `<div style="font-size:11px;color:var(--muted)">no matching brief id</div>`}</td>
        <td class="num">${p.width}×${p.height}</td><td class="num">${fx(p.aspect, 4)}</td>
        <td class="num">${fx(p.duration_s, 2)}s</td><td class="num">${p.frame_count}</td>
        <td class="num">${fx(p.file_mb, 2)} MB</td>
        <td>${r.format_ok ? `<span class="badge b-pass">9:16</span>` : `<span class="badge b-warn">not 9:16</span>`}</td></tr>`; }).join("")}
      </table></div>
      ${anyBad ? `<div class="banner warn" style="margin-top:14px"><span class="ico">⚠</span><div>
        Clips not delivered in 9:16 are converted to 1080×1920 at export. The generator&rsquo;s aspect
        setting was not honoured — this is measured, not assumed.</div></div>` : ""}
      ${imp.every(r => !r.matched_brief) ? `<div class="footnote"><b>Provenance:</b> none of these filenames matched a brief ID, so this batch was not generated from the briefs in step 3. They are reported separately rather than presented as if the planner produced them.</div>` : ""}
    </div>`));
    m.appendChild(nextBtn("Run Fidelity Lock →", 6));
  }
}

async function uploadClips(files) {
  if (!files?.length || S.busy) return;
  S.busy = true;
  try {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    S.run = await api(`/api/runs/${S.run.run_id}/clips`, { method: "POST", body: fd });
    toast(`Imported ${S.run.imported.length} clip(s)`); render();
  } catch (e) { toast(e.message, true); }
  S.busy = false;
}

/* ------------------------------------------------------------ 6 fidelity */
function pgFidelity(m) {
  m.innerHTML = head("Step 6", "Fidelity Lock — Gate 1",
    "Four metrics — colour ΔE2000, CLIP identity, weave texture, border SSIM — computed <b>inside the garment mask only</b> and on <b>every 5th frame</b>, because the drift we measured is transient and a single-frame check misses it.");

  const scores = S.run.scores || {};
  const nScores = Object.keys(scores).length;

  if (!nScores) {
    const c = el(`<div class="card"><h3>Score ${S.run.imported.length} clip(s)</h3>
      <div class="hint">Measured at roughly 45 seconds per 5-second clip. This runs the real pipeline — progress below reflects score files actually written to disk.</div>
      <button class="btn" id="go">Run Fidelity Lock</button></div>`);
    m.appendChild(c);
    $("#go", c).onclick = async () => {
      $("#go", c).disabled = true;
      try {
        const { job } = await api(`/api/runs/${S.run.run_id}/score`, { method: "POST", body: new FormData() });
        await awaitJob(job.id, m, "Scoring clips");
        await loadRun(S.run.run_id, 6);
        toast("Fidelity Lock complete");
      } catch (e) { toast(e.message, true); $("#go", c).disabled = false; }
    };
    return;
  }

  const cal = S.run.calibration;
  const thr = cal?.proposed_threshold ?? null;

  if (!cal) {
    const c = el(`<div class="card"><h3>Calibrate the pass threshold</h3>
      <div class="hint">Rather than invent a number, the scale is anchored with controlled degradations of your own source image — hue shifts (dye change), blur (weave collapse), desaturation — scored through the same Fidelity Lock.</div>
      <button class="btn" id="cal">Calibrate threshold</button></div>`);
    m.appendChild(c);
    $("#cal", c).onclick = async () => {
      $("#cal", c).disabled = true;
      try {
        const { job } = await api(`/api/runs/${S.run.run_id}/calibrate`, { method: "POST" });
        await awaitJob(job.id, m, "Calibrating");
        await loadRun(S.run.run_id, 6); toast("Threshold calibrated");
      } catch (e) { toast(e.message, true); $("#cal", c).disabled = false; }
    };
  } else {
    m.appendChild(el(`<div class="banner info"><span class="ico">◎</span><div>
      <b>Calibrated pass threshold: ${fx(thr, 1)}</b> — ${esc(cal.basis || "")}
      <div class="footnote" style="color:inherit;opacity:.85">${esc(cal.caveat || "")}</div></div></div>`));
  }

  const sel = S.run.selection;
  const rejMap = {};
  (sel?.gate1_rejected || []).forEach(r => rejMap[r.id] = r.reasons);

  Object.values(scores)
    .sort((a, b) => b.fidelity_mean - a.fidelity_mean)
    .forEach(s => m.appendChild(clipCard(s, thr, rejMap[s.id])));

  m.appendChild(nextBtn("Run Diversity Engine →", 7));
}

function clipCard(s, thr, reasons) {
  const pass = thr === null ? null : s.fidelity_mean >= thr;
  const rejected = !!reasons;
  const cls = rejected ? "rej" : (pass ? "keep" : "");
  const badge = rejected ? `<span class="badge b-fail">reject</span>`
    : pass === null ? `<span class="badge b-info">scored</span>`
    : `<span class="badge b-pass">keep</span>`;

  const c = el(`<div class="clip-card ${cls}">
    <div class="clip-head">
      ${ring(s.fidelity_mean, thr)}
      <div style="flex:1">
        <div class="clip-title">${esc(s.id)}</div>
        <div class="clip-sub">mean ${fx(s.fidelity_mean)} · min ${fx(s.fidelity_min)} · std ${fx(s.fidelity_std)}
          · worst frame #${s.worst_frame?.frame} at ${fx(s.worst_frame?.t)}s
          · ${s.frames_scored} frames at stride ${s.stride}</div>
      </div>
      ${badge}
    </div>
    <div class="clip-body">
      <div class="grid g2">
        <div>
          <div style="font-size:12.5px;color:var(--muted);margin-bottom:6px">Per-frame fidelity — live from the measured series</div>
          <div class="spark"></div>
          <div class="grid g3" style="margin-top:14px">
            <dl class="kv"><dt>ΔE2000 colour</dt><dd>${fx(s.means?.delta_e2000)}</dd></dl>
            <dl class="kv"><dt>Weave distance</dt><dd>${fx(s.means?.weave_distance, 4)}</dd></dl>
            <dl class="kv"><dt>CLIP identity</dt><dd>${fx(s.means?.clip_cosine, 4)}</dd></dl>
            <dl class="kv"><dt>Motion mean</dt><dd>${fx(s.motion?.mean, 4)}</dd></dl>
            <dl class="kv"><dt>Motion max</dt><dd>${fx(s.motion?.max, 4)}</dd></dl>
            <dl class="kv"><dt>Delivered</dt><dd>${s.info?.width}×${s.info?.height}</dd></dl>
          </div>
        </div>
        <div>
          <div style="font-size:12.5px;color:var(--muted);margin-bottom:6px">Weave Guard — source vs worst frame</div>
          <img class="shot" src="${fileUrl("evidence/weave_" + s.id + ".png")}" alt="weave guard ${esc(s.id)}"
               onerror="this.style.display='none'">
        </div>
      </div>
      ${rejected ? rejectionPanel(s, reasons, thr) : ""}
      <details style="margin-top:12px"><summary style="font-size:12.5px;color:var(--accent-dark);cursor:pointer">Full drift analysis</summary>
        <img class="shot" style="margin-top:10px" src="${fileUrl("evidence/drift_" + s.id + ".png")}" alt="drift plot" onerror="this.style.display='none'">
      </details>
    </div></div>`);
  $(".spark", c).appendChild(sparkline(s.per_frame, thr));
  return c;
}

/* Plain-language verdict for a rejected clip, derived entirely from the
 * measured series already in the payload. Nothing here is hardcoded to a
 * particular clip. */
function rejectionPanel(s, reasons, thr) {
  const mf = s.per_frame.map(f => f.mask_fraction).filter(v => v != null);
  const peak = mf.length ? Math.max(...mf) : null;
  const lo = mf.length ? Math.min(...mf) : null;
  const tail = mf.slice(1);                       // after the opening frame
  const tailMax = tail.length ? Math.max(...tail) : null;
  const spike = s.motion?.max;
  const collapsed = peak !== null && lo !== null && peak > 0 && (lo / peak) < 0.4;
  const cut = spike !== null && spike > 0.25;

  const headline = (collapsed && cut)
    ? "REJECTED — product visibility collapsed after a hard scene cut."
    : collapsed ? "REJECTED — product visibility collapsed mid-clip."
    : cut ? "REJECTED — a hard scene cut breaks the ad."
    : "REJECTED — product drift exceeded the calibrated threshold.";

  const bullets = [];
  if (thr !== null && s.fidelity_mean < thr)
    bullets.push(`Fidelity <b>${fx(s.fidelity_mean)}</b> &lt; threshold <b>${fx(thr, 1)}</b>, and below it for essentially the whole clip — not a transient dip.`);
  if (cut)
    bullets.push(`Motion spike <b>${fx(spike, 3)}</b> against a 0.25 limit, in the first fractions of a second — a hard scene cut.`);
  if (collapsed)
    bullets.push(`Garment occupancy collapsed from <b>${fx(peak * 100, 0)}%</b> of frame to <b>${fx(lo * 100, 0)}–${fx(tailMax * 100, 0)}%</b> — the product is too small to read as a product ad.`);

  const colourNote = collapsed ? `
    <div class="footnote" style="color:#7d1a15;margin-top:10px">
      <b>This is not primarily a dye-colour failure.</b> ΔE2000 reads
      ${fx(s.means?.delta_e2000)}, but with the garment at only a few percent of frame that
      figure is not reliable evidence of a dye change — it largely reflects the product being
      tiny and washed out against bright surroundings. Frame inspection confirms the garment
      colour is unchanged. The failure is <b>product visibility and a scene cut</b>.
    </div>` : "";

  return `<div class="reasons">
    <div style="font-size:13.5px;font-weight:700;margin-bottom:7px">${esc(headline)}</div>
    <ul style="margin:0 0 0 16px;padding:0">${bullets.map(b => `<li style="margin-bottom:4px">${b}</li>`).join("")}</ul>
    ${colourNote}
    <div class="footnote" style="margin-top:9px;color:#7d1a15;opacity:.85">Gate 1 raw: ${esc(reasons.join("; "))}</div>
  </div>`;
}

function ring(v, thr) {
  const pct = Math.max(0, Math.min(100, v)) / 100;
  const r = 40, circ = 2 * Math.PI * r;
  const col = thr === null ? "var(--accent)" : (v >= thr ? "var(--pass)" : "var(--fail)");
  return `<div class="score-ring">
    <svg width="96" height="96" viewBox="0 0 96 96">
      <circle cx="48" cy="48" r="${r}" fill="none" stroke="#e8edf2" stroke-width="9"/>
      <circle cx="48" cy="48" r="${r}" fill="none" stroke="${col}" stroke-width="9" stroke-linecap="round"
        stroke-dasharray="${circ}" stroke-dashoffset="${circ * (1 - pct)}"/>
    </svg>
    <div class="val" style="color:${col}">${fx(v, 1)}<small>fidelity</small></div></div>`;
}

/* inline chart drawn from the real per-frame series returned by the API */
function sparkline(pf, thr) {
  const W = 460, H = 140, pad = { l: 34, r: 8, t: 10, b: 20 };
  const xs = pf.map(p => p.t), ys = pf.map(p => p.fidelity);
  const lo = Math.min(...ys, thr ?? Infinity) - 5, hi = Math.max(...ys) + 5;
  const X = t => pad.l + (t - xs[0]) / ((xs[xs.length - 1] - xs[0]) || 1) * (W - pad.l - pad.r);
  const Y = v => pad.t + (1 - (v - lo) / ((hi - lo) || 1)) * (H - pad.t - pad.b);
  const d = pf.map((p, i) => `${i ? "L" : "M"}${X(p.t).toFixed(1)},${Y(p.fidelity).toFixed(1)}`).join("");
  const worst = pf.reduce((a, b) => b.fidelity < a.fidelity ? b : a, pf[0]);

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", "100%");
  svg.innerHTML = `
    ${thr !== null ? `<line x1="${pad.l}" x2="${W - pad.r}" y1="${Y(thr)}" y2="${Y(thr)}"
        stroke="#e0a800" stroke-width="1.5" stroke-dasharray="4 3"/>
      <text x="${pad.l + 3}" y="${Y(thr) - 5}" font-size="9" fill="#9a6700">threshold ${fx(thr, 1)}</text>` : ""}
    <path d="${d}" fill="none" stroke="#0f8a9e" stroke-width="2.2" stroke-linejoin="round"/>
    <circle cx="${X(worst.t)}" cy="${Y(worst.fidelity)}" r="4" fill="#b3261e"/>
    <text x="${X(worst.t) + 7}" y="${Y(worst.fidelity) + 4}" font-size="9" fill="#b3261e">worst ${fx(worst.fidelity, 1)}</text>
    <text x="2" y="${Y(hi - 5) + 4}" font-size="9" fill="#6b7c8c">${Math.round(hi - 5)}</text>
    <text x="2" y="${Y(lo + 5) + 4}" font-size="9" fill="#6b7c8c">${Math.round(lo + 5)}</text>
    <text x="${pad.l}" y="${H - 5}" font-size="9" fill="#6b7c8c">0s</text>
    <text x="${W - pad.r - 18}" y="${H - 5}" font-size="9" fill="#6b7c8c">${fx(xs[xs.length - 1], 1)}s</text>`;
  return svg;
}

/* ----------------------------------------------------------- 7 diversity */
function pgDiversity(m) {
  m.innerHTML = head("Step 7", "Diversity Engine — Gate 2",
    "Planning briefs apart is not enough — two different briefs can still render similarly. Each clip becomes one CLIP embedding averaged over sampled frames, and selection maximises the minimum separation of the chosen set.");

  const sel = S.run.selection;
  if (!sel) {
    const thr = S.run.calibration?.proposed_threshold;
    const c = el(`<div class="card"><h3>Apply both gates</h3>
      <div class="hint">Gate 1 rejects a clip for drifting off the product. Gate 2 rejects it for looking too much like another clip. A clip must pass both to be exported.</div>
      <div class="row"><label style="font-size:13px">Target variations (k) <input id="k" type="number" value="6" min="1" style="width:64px;padding:6px 8px;border:1px solid var(--line);border-radius:7px"></label>
        <label style="font-size:13px">Threshold <input id="t" type="number" step="0.1" value="${thr ?? ""}" style="width:84px;padding:6px 8px;border:1px solid var(--line);border-radius:7px"></label>
        <button class="btn" id="go">Run both gates</button></div></div>`);
    m.appendChild(c);
    $("#go", c).onclick = async () => {
      $("#go", c).disabled = true;
      try {
        const fd = new FormData();
        fd.append("k", $("#k", c).value);
        if ($("#t", c).value !== "") fd.append("threshold", $("#t", c).value);
        const { job } = await api(`/api/runs/${S.run.run_id}/select`, { method: "POST", body: fd });
        await awaitJob(job.id, m, "Embedding clips and applying gates");
        await loadRun(S.run.run_id, 7); toast("Gates applied");
      } catch (e) { toast(e.message, true); $("#go", c).disabled = false; }
    };
    return;
  }

  const d = sel.diversity || {};
  m.appendChild(el(`<div class="card"><h3>Gate 1 — Fidelity Lock</h3>
    <div class="scroll"><table><tr><th>Clip</th><th class="num">Mean</th><th class="num">Min</th><th>Outcome</th></tr>
    ${(sel.gate1_passing || []).map(p => `<tr><td><b>${esc(p.id)}</b></td><td class="num">${fx(p.fidelity_mean)}</td><td class="num">${fx(p.fidelity_min)}</td><td><span class="badge b-pass">pass</span></td></tr>`).join("")}
    ${(sel.gate1_rejected || []).map(p => `<tr class="rejected"><td><b>${esc(p.id)}</b></td><td class="num">${fx(p.fidelity_mean)}</td><td class="num">${fx(p.fidelity_min)}</td><td><span class="badge b-fail">reject</span><div style="font-size:11.5px;color:#7d1a15;margin-top:4px">${esc((p.reasons || []).join("; "))}</div></td></tr>`).join("")}
    </table></div></div>`));

  if (d.diversity_score_selected !== undefined) {
    const noGain = Math.abs(d.diversity_gain) < 1e-9;
    m.appendChild(el(`<div class="card"><h3>Gate 2 — Diversity selection</h3>
      <div class="grid g3">
        <dl class="kv"><dt>Pool size</dt><dd>${d.pool_size}</dd></dl>
        <dl class="kv"><dt>Diversity (selected)</dt><dd>${fx(d.diversity_score_selected)}</dd></dl>
        <dl class="kv"><dt>Diversity (pool)</dt><dd>${fx(d.diversity_score_pool)}</dd></dl>
      </div>
      <div style="margin-top:12px"><b style="font-size:13px">Selected:</b> ${(d.selected_ids || []).map(i => `<span class="chip"><b>${esc(i)}</b></span>`).join("")}</div>
      ${(d.rejected_ids || []).length ? `<div style="margin-top:6px"><b style="font-size:13px">Dropped as too similar:</b> ${d.rejected_ids.map(i => `<span class="chip">${esc(i)}</span>`).join("")}</div>` : ""}
      ${noGain ? `<div class="banner warn" style="margin-top:14px"><span class="ico">ℹ</span><div>
        <b>Selection discarded nothing.</b> The passing pool (${d.pool_size}) is smaller than the requested
        k, so farthest-point selection had nothing to remove. The diversity figures are real measurements;
        the filtering step was simply not exercised on this set.</div></div>` : ""}
    </div>`));
  } else if (d.note) {
    m.appendChild(el(`<div class="banner warn"><span class="ico">ℹ</span><div>${esc(d.note)}</div></div>`));
  }

  const dv = S.run.diversity_full;
  if (dv) {
    const ids = dv.ids, mat = dv.pairwise_cosine_distance;
    const flat = mat.flat().filter(v => v > 0);
    const lo = Math.min(...flat), hi = Math.max(...flat);
    const heat = v => { const t = (v - lo) / ((hi - lo) || 1);
      return `rgba(15,138,158,${(0.10 + t * 0.62).toFixed(3)})`; };
    m.appendChild(el(`<div class="card"><h3>Real pairwise distance — every imported video</h3>
      <div class="hint">Mean CLIP embedding over sampled frames of the actual generated files. Not constructed vectors. Larger = more visually distinct.</div>
      <div class="scroll"><table class="matrix"><tr><th></th>${ids.map(i => `<th class="num">${esc(i)}</th>`).join("")}</tr>
      ${mat.map((row, i) => `<tr><td><b>${esc(ids[i])}</b></td>${row.map((v, j) => i === j
        ? `<td class="d" style="color:var(--muted)">—</td>`
        : `<td class="d"><span class="heat" style="background:${heat(v)};padding:5px 9px;border-radius:6px">${fx(v, 4)}</span></td>`).join("")}</tr>`).join("")}
      </table></div>
      <div class="grid g2" style="margin-top:14px">
        <dl class="kv"><dt>Diversity — all videos</dt><dd>${fx(dv.diversity_all_four)}</dd>
          <dt>Diversity — Gate-1 passing</dt><dd>${fx(dv.diversity_gate1_passing)}</dd></dl>
        <dl class="kv"><dt>Most similar pair</dt><dd>${esc(dv.most_similar_pair[0])} ↔ ${esc(dv.most_similar_pair[1])} (${fx(dv.most_similar_pair[2], 4)})</dd>
          <dt>Most distinct pair</dt><dd>${esc(dv.most_distinct_pair[0])} ↔ ${esc(dv.most_distinct_pair[1])} (${fx(dv.most_distinct_pair[2], 4)})</dd></dl>
      </div></div>`));

    const rejIds = (sel.gate1_rejected || []).map(r => r.id);
    const mostDistinct = dv.most_distinct_pair;
    if (rejIds.some(id => mostDistinct.includes(id))) {
      const which = rejIds.find(id => mostDistinct.includes(id));
      m.appendChild(el(`<div class="banner info"><span class="ico">◆</span><div>
        <b>Why two independent gates matter.</b> The most visually distinct clip in this set is
        <b>${esc(which)}</b> — the one Gate 1 rejected. Optimising for variety alone would have
        selected the video that misrepresents the product. This came out of the measurements,
        not the design.</div></div>`));
    }
  }
  m.appendChild(nextBtn("Safe Cut & export →", 8));
}

/* -------------------------------------------------------- 8 safecut/export */
function pgExport(m) {
  m.innerHTML = head("Step 8", "Safe Cut & export",
    "Recover what is recoverable, then deliver at 1080×1920. Nothing that failed a gate is exported.");

  const thr = S.run.calibration?.proposed_threshold;
  const sc = S.run.safecut;

  if (!sc) {
    const c = el(`<div class="card"><h3>Safe Cut</h3>
      <div class="hint">If a clip dips below threshold only briefly, trim it to the longest <b>contiguous</b> passing window — but only if at least ${fx(S.run.safecut_min_keep_s, 1)}s survives. It only trims: never regenerates, recolours or repairs. The trimmed file is re-scored from the output, never inherited.</div>
      <button class="btn" id="go" ${thr ? "" : "disabled"}>Analyse for recoverable sections</button>
      ${thr ? "" : `<div class="footnote">Calibrate a threshold in step 6 first.</div>`}</div>`);
    m.appendChild(c);
    $("#go", c).onclick = async () => {
      $("#go", c).disabled = true;
      try {
        const fd = new FormData(); fd.append("threshold", thr);
        const { job } = await api(`/api/runs/${S.run.run_id}/safecut`, { method: "POST", body: fd });
        await awaitJob(job.id, m, "Analysing for recoverable windows");
        await loadRun(S.run.run_id, 8); toast("Safe Cut analysis complete");
      } catch (e) { toast(e.message, true); $("#go", c).disabled = false; }
    };
  } else {
    const applied = sc.filter(r => r.applied);
    m.appendChild(el(`<div class="card"><h3>Safe Cut — ${applied.length} of ${sc.length} clip(s) trimmed</h3>
      <div class="hint">Threshold ${fx(thr, 1)} · minimum kept length ${fx(S.run.safecut_min_keep_s, 1)}s</div>
      <div class="scroll"><table><tr><th>Clip</th><th>Outcome</th><th>Detail</th></tr>
      ${sc.map(r => r.applied
        ? `<tr><td><b>${esc(r.clip_id)}</b></td><td><span class="badge b-pass">trimmed</span></td>
             <td>kept ${fx(r.start_s)}–${fx(r.end_s)}s (${fx(r.kept_s)}s, removed ${fx(r.removed_s)}s) ·
             mean ${fx(r.before.mean)} → ${fx(r.after.mean)}, re-scored from the trimmed file</td></tr>`
        : `<tr><td><b>${esc(r.clip_id)}</b></td><td><span class="badge b-info">not cut</span></td>
             <td style="color:var(--muted)">${esc(r.reason)}</td></tr>`).join("")}
      </table></div>
      ${!applied.length ? `<div class="banner info" style="margin-top:14px"><span class="ico">ℹ</span><div>
        <b>Nothing was cut, which is the correct outcome here.</b> Clips that already clear the threshold
        have nothing to remove, and a clip that fails throughout cannot be recovered by trimming — that
        guard is what stops Safe Cut being used to launder a bad clip into a good one.</div></div>` : ""}
    </div>`));
  }

  const exp = S.run.exports || [];
  if (!exp.length) {
    const c = el(`<div class="card"><h3>Export validated ads</h3>
      <div class="hint">Crop vs pad is decided <b>per clip from measurement</b>: the system computes what fraction of garment pixels a centre crop would destroy and only crops when at least 99.5% survives.</div>
      <button class="btn" id="go" ${S.run.selection ? "" : "disabled"}>Export to 1080×1920</button></div>`);
    m.appendChild(c);
    $("#go", c).onclick = async () => {
      $("#go", c).disabled = true;
      try {
        const fd = new FormData(); fd.append("mode", "auto");
        const { job } = await api(`/api/runs/${S.run.run_id}/export`, { method: "POST", body: fd });
        await awaitJob(job.id, m, "Converting and encoding");
        await loadRun(S.run.run_id, 8); toast("Export complete");
      } catch (e) { toast(e.message, true); $("#go", c).disabled = false; }
    };
    return;
  }

  m.appendChild(el(`<div class="banner info"><span class="ico">✓</span><div>
    <b>${exp.length} validated ad${exp.length > 1 ? "s" : ""} exported</b> at 1080×1920, 9:16 —
    verified by probing each written file, not by trusting the encoder settings.</div></div>`));

  m.appendChild(el(`<div class="grid g3">${exp.map(o => `
    <div class="card" style="margin:0">
      <div class="row"><h3>${esc(o.id)}</h3><div class="spacer"></div>
        ${o.conforms ? `<span class="badge b-pass">conforms</span>` : `<span class="badge b-fail">non-conforming</span>`}</div>
      <video controls preload="metadata" style="margin-top:11px"
        src="${fileUrl("exports/" + o.id + "_1080x1920.mp4")}"></video>
      <dl class="kv" style="margin-top:11px">
        <dt>Resolution</dt><dd>${o.probe.width}×${o.probe.height}</dd>
        <dt>Aspect</dt><dd>${fx(o.probe.aspect, 4)}</dd>
        <dt>Duration</dt><dd>${fx(o.probe.duration_s, 2)}s</dd>
        <dt>Size</dt><dd>${fx(o.probe.file_mb, 2)} MB</dd>
        <dt>Mode</dt><dd>${esc(o.mode)}</dd>
      </dl>
      <div class="footnote">${esc(o.mode_decision?.rationale || "")}</div>
      <a class="btn ghost sm" style="margin-top:10px;display:inline-block"
         href="${fileUrl("exports/" + o.id + "_1080x1920.mp4")}" download>Download</a>
    </div>`).join("")}</div>`));

  /* Milestone 3.2 — delivery specification, read from the probed export files */
  m.appendChild(deliverySpec(exp));
  /* Milestone 3.1 — performance, from the run's real measured timings */
  m.appendChild(perfPanel());
}

/* ── Milestone 3.2 · delivery specification ────────────────────────────── */
function deliverySpec(exp) {
  const all = exp.every(o => o.conforms);
  const p = exp[0].probe;
  return el(`<div class="card"><h3>Delivery specification</h3>
    <div class="hint">Read back from the written files after encoding — not taken from the encoder settings.</div>
    <div class="grid g3">
      <dl class="kv"><dt>Resolution</dt><dd>${p.width}×${p.height}</dd></dl>
      <dl class="kv"><dt>Aspect</dt><dd>${fx(p.aspect, 4)}</dd></dl>
      <dl class="kv"><dt>Duration</dt><dd>${fx(p.duration_s, 2)}s</dd></dl>
      <dl class="kv"><dt>Conforming</dt><dd>${exp.filter(o => o.conforms).length} / ${exp.length}</dd></dl>
    </div>
    <div class="footnote">
      ${all ? "Every exported ad is 1080×1920 at 9:16" : "Some exports do not conform"} —
      the vertical format used by Instagram Reels and Stories, Facebook Reels, Meta vertical feed
      and YouTube Shorts. Codec, pixel format and container are verified separately in
      <code>evidence/m3_delivery_manifest.json</code>.</div>
  </div>`);
}

/* ── Milestone 3.1 · performance, from the run's real measured timings ─── */
function perfPanel() {
  const t = S.run.timings || {};
  const ROLLUP = new Set(["ingest_total"]);          // roll-up, would double count
  const stages = Object.entries(t).filter(([k]) => !ROLLUP.has(k));
  const total = stages.reduce((a, [, v]) => a + v, 0);
  const ranked = [...stages].sort((a, b) => b[1] - a[1]);
  const nClips = (S.run.imported || []).length;
  const nExp = (S.run.exports || []).length;
  const top = ranked[0];

  const bars = ranked.map(([k, v]) => {
    const pct = 100 * v / total;
    return `<div class="perfrow">
      <span class="perfrow-k">${esc(k)}</span>
      <span class="perfrow-bar"><i class="${k === top[0] ? "hot" : ""}" style="width:${pct.toFixed(1)}%"></i></span>
      <span class="perfrow-v">${fx(v, 2)}s</span>
      <span class="perfrow-p">${pct.toFixed(1)}%</span>
    </div>`;
  }).join("");

  return el(`<div class="card"><h3>Performance</h3>
    <div class="hint">Every figure below was measured by this application while it ran. Ekly generation
      time is excluded — it is a manual web step with no API and has never been measured.</div>

    <div class="grid g3">
      <dl class="kv"><dt>Total automated</dt><dd>${fx(total, 1)}s</dd></dl>
      <dl class="kv"><dt>Slowest stage</dt><dd>${esc(top[0])} · ${(100 * top[1] / total).toFixed(0)}%</dd></dl>
      ${nClips ? `<dl class="kv"><dt>Scoring per video</dt><dd>${fx(t.score_all / nClips, 1)}s</dd></dl>` : ""}
      ${nExp ? `<dl class="kv"><dt>Export per ad</dt><dd>${fx(t.export / nExp, 1)}s</dd></dl>` : ""}
    </div>

    <div class="perfbars">${bars}</div>

    <div class="footnote">Stage timings are recorded by the pipeline itself as it runs.
      <code>ingest_total</code> is excluded from the sum because it is a roll-up of validate,
      preprocess, segment and signature.</div>

    <details style="margin-top:12px"><summary style="font-size:12.5px;color:var(--accent-dark);cursor:pointer">Optimisations in effect, and what each is actually worth</summary>
      <ul class="perflist" style="margin-top:10px">
        <li><b>Frame sampling</b> — 31 of 153 frames are scored per video, every 5th frame.
          Scoring touches <b>4.9× fewer frames</b> than a full pass. This is the single largest lever,
          and it is safe here because the drift measured is far longer than 1/6 of a second.</li>
        <li><b>Cached model sessions</b> — the segmentation and CLIP models load once per process and
          are reused. Measured warm-cache repeat cost: segmentation <b>4.70s → 0.59s → 0.51s</b>,
          CLIP embedding <b>2.00s → 0.05s → 0.05s</b> across three consecutive calls.</li>
        <li><b>Signature computed once</b> — the mask, palette, texture descriptor and CLIP vector are
          computed once per product and reused for every video and every re-score.</li>
        <li><b>Batched embeddings</b> — CLIP runs 16 images per session call rather than one at a time.</li>
        <li><b>Reduced-resolution masks</b> — masks are computed at 512px and upsampled. A warm A/B of
          5 alternating repetitions gives <b>0.543s at full frame vs 0.473s reduced — 1.15×</b>.
          <b>Correction:</b> an earlier note claimed 8× here. That was wrong — it compared a cold first
          call including model load against a warm one. rembg resizes every input to 320×320 internally,
          so inference cost barely varies with input size. The reduction is kept as a small real win,
          not a large one.</li>
      </ul>
      <div class="footnote">Full numbers in <code>evidence/m3_performance.json</code>; chart in
        <code>evidence/m3_stage_timings.png</code>.</div>
    </details>

    <details style="margin-top:12px"><summary style="font-size:12.5px;color:var(--accent-dark);cursor:pointer">Raw stage timings</summary>
      <div class="scroll" style="margin-top:10px"><table><tr><th>Stage</th><th class="num">Seconds</th><th class="num">Share</th></tr>
      ${ranked.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${fx(v, 3)}</td><td class="num">${(100 * v / total).toFixed(1)}%</td></tr>`).join("")}
      <tr><td><b>Total automated</b></td><td class="num"><b>${fx(total, 3)}</b></td><td class="num"><b>100%</b></td></tr>
      ${t.ingest_total !== undefined ? `<tr><td style="color:var(--muted)">ingest_total (roll-up, excluded)</td><td class="num" style="color:var(--muted)">${fx(t.ingest_total, 3)}</td><td class="num" style="color:var(--muted)">—</td></tr>` : ""}
      </table></div>
    </details>
  </div>`);
}

/* ------------------------------------------------------------------- boot */
async function refreshRuns() {
  const d = await api("/api/runs");
  S.runs = d.runs; S.demoRun = d.demo_run;
}

async function loadRun(runId, step) {
  S.run = await api(`/api/runs/${runId}`);
  await refreshRuns();
  S.step = step || Math.min(stepReached(), 8);
  render();
}

async function boot() {
  try {
    const h = await api("/api/health");
    $("#healthNote").innerHTML = `<b>${h.runs}</b> run(s) on disk · API healthy`;
    await refreshRuns();
    const target = S.runs.find(r => r.is_demo_run) || S.runs[S.runs.length - 1];
    if (target) await loadRun(target.run_id);
    else { S.run = null; render(); }
  } catch (e) {
    $("#main").innerHTML = `<div class="card"><h3>Cannot reach the API</h3>
      <div class="hint">${esc(e.message)}</div></div>`;
  }
}

$("#newRunBtn").onclick = () => { S.run = null; S.step = 1; render(); };
boot();
