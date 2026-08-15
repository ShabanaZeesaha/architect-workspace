/* Site — shared rendering, nav, search, illustrations, and the Ask agent.
   Reads everything from the bare BLUEPRINT identifier declared in blueprint.js. */
const Site = (function () {

  /* ============================== SEARCH ============================== */
  const STOPWORDS = new Set(["a","an","the","of","to","in","on","for","and","or","is","are","it","its","this",
    "that","be","by","with","as","at","from","into","when","if","does","do","not","no","but","so","than","then",
    "there","their","they","them","these","those","was","were","will","would","should","could","can","has","have",
    "had","i","you","he","she","we","us","our","your","what","how","why","who"]);

  function tokenize(text) { return (text.toLowerCase().match(/[a-z0-9']+/g) || []); }

  function stem(w) {
    if (w.length > 5 && w.endsWith("ing")) return w.slice(0, -3);
    if (w.length > 4 && w.endsWith("ed")) return w.slice(0, -2);
    if (w.length > 4 && w.endsWith("es")) return w.slice(0, -2);
    if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) return w.slice(0, -1);
    return w;
  }

  let INDEX = null;
  function buildIndex() {
    const entries = [];
    const add = (section, title, text, url) => { if (text) entries.push({ section, title, text: String(text), url }); };

    add("summary", "The Idea", BLUEPRINT.idea, "01-summary.html");
    add("summary", "Day-one bar", BLUEPRINT.dayOneSentence, "01-summary.html");

    BLUEPRINT.components.forEach(c => add("components", c.name, c.sentence + " " + c.words.join(" ") + " layer:" + c.layer, "02-components.html#c-" + c.id));

    add("architecture", "How It Fits Together", BLUEPRINT.interpretations.architecture, "03-architecture.html");

    BLUEPRINT.flowSteps.forEach(s => add("data-flow", "Step " + s.n + " — " + s.actor, s.action, "04-data-flow.html#step-" + s.n));
    add("data-flow", "Data flow meaning", BLUEPRINT.interpretations.dataFlow, "04-data-flow.html");

    BLUEPRINT.phases.forEach(p => add("build-order", "Phase " + p.n + " — " + p.name, p.proves + " Adds: " + p.adds.join(", "), "05-build-order.html#phase-" + p.n));
    add("build-order", "Build order meaning", BLUEPRINT.interpretations.buildOrder, "05-build-order.html");

    BLUEPRINT.coverage.forEach(r => add("coverage", r.phrase, r.status + " covered by: " + (r.coveredBy.join(", ") || "none"), "06-coverage.html"));
    add("coverage", "Coverage meaning", BLUEPRINT.interpretations.coverage, "06-coverage.html");

    BLUEPRINT.assumptions.forEach(a => add("assumptions", "Assumption " + a.n, a.text + " Impact: " + a.impact, "07-assumptions.html#assume-" + a.n));
    add("assumptions", "Open question", BLUEPRINT.openQuestion.question + " " + BLUEPRINT.openQuestion.branches.map(b => b.label + ": " + b.detail).join(" "), "07-assumptions.html#open-question");

    BLUEPRINT.notCovered.forEach((t, i) => add("not-covered", "Not covered #" + (i + 1), t, "08-not-covered.html"));

    return entries;
  }
  function getIndex() { if (!INDEX) INDEX = buildIndex(); return INDEX; }

  function escapeHtml(s) { return s.replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m])); }

  function highlight(text, terms) {
    let out = escapeHtml(text);
    terms.forEach(t => {
      if (t.length < 2) return;
      const re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }

  function search(query, limit) {
    limit = limit || 8;
    const rawTerms = tokenize(query).filter(t => !STOPWORDS.has(t));
    if (rawTerms.length === 0) return [];
    const phrase = query.trim().toLowerCase();
    const results = [];
    getIndex().forEach(entry => {
      const hay = (entry.title + " " + entry.text).toLowerCase();
      let score = 0;
      rawTerms.forEach(t => {
        const count = hay.split(t).length - 1;
        const titleCount = entry.title.toLowerCase().split(t).length - 1;
        if (count > 0) { score += count + titleCount * 3; }
        else {
          const st = stem(t);
          if (st.length > 2 && hay.includes(st)) score += 0.5;
        }
      });
      if (phrase.length > 2 && hay.includes(phrase)) score += 5;
      if (score > 0) results.push({ entry, score });
    });
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, limit).map(r => ({
      section: r.entry.section, title: r.entry.title, url: r.entry.url,
      snippet: highlight(r.entry.text.slice(0, 160) + (r.entry.text.length > 160 ? "…" : ""), rawTerms)
    }));
  }

  /* ============================== SVG ILLUSTRATIONS ============================== */
  const ARROW = '<defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="var(--accent)"/></marker></defs>';

  function svgPipeline(mini) {
    const w = mini ? 260 : 640, h = mini ? 90 : 160;
    const boxes = [
      { x: 8, w: mini ? 70 : 180, label: "Stakeholder's\nRequest" },
      { x: mini ? 95 : 230, w: mini ? 70 : 220, label: "Analyze · Ask ·\nRecommend · Structure" },
      { x: mini ? 182 : 480, w: mini ? 70 : 150, label: "Structured\nRequirement" }
    ];
    const by = mini ? 20 : 55, bh = mini ? 50 : 55;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${ARROW}`;
    boxes.forEach((b, i) => {
      s += `<rect x="${b.x}" y="${by}" width="${b.w}" height="${bh}" rx="10" fill="${i === 1 ? 'var(--accent)' : 'var(--card)'}" stroke="var(--border)"/>`;
      if (!mini) {
        b.label.split("\n").forEach((line, li) => {
          s += `<text x="${b.x + b.w / 2}" y="${by + bh / 2 - 6 + li * 14}" text-anchor="middle" font-size="11.5" fill="${i === 1 ? 'var(--accent-ink)' : 'var(--text)'}" font-family="Segoe UI, sans-serif">${escapeHtml(line)}</text>`;
        });
      }
      if (i < boxes.length - 1) {
        const nx = boxes[i + 1].x;
        s += `<line x1="${b.x + b.w}" y1="${by + bh / 2}" x2="${nx - 4}" y2="${by + bh / 2}" stroke="var(--accent)" stroke-width="2" marker-end="url(#arrowhead)"/>`;
      }
    });
    return s + "</svg>";
  }

  function svgLayers(mini) {
    const w = mini ? 260 : 900;
    const bandH = mini ? 20 : 62, gap = mini ? 3 : 8;
    let y = 4;
    let s = `<svg viewBox="0 0 ${w} ${(bandH + gap) * BLUEPRINT.layers.length + 4}" xmlns="http://www.w3.org/2000/svg">`;
    const colors = { Interaction: "var(--blue)", Orchestration: "var(--amber)", Intelligence: "var(--green)", Data: "var(--slate)" };
    BLUEPRINT.layers.forEach(layer => {
      const comps = BLUEPRINT.components.filter(c => c.layer === layer);
      s += `<rect x="0" y="${y}" width="${w}" height="${bandH}" rx="8" fill="none" stroke="${colors[layer]}" stroke-width="1.5" stroke-dasharray="4 3"/>`;
      if (!mini) s += `<text x="8" y="${y + 14}" font-size="9.5" fill="${colors[layer]}" font-weight="700" font-family="Segoe UI, sans-serif">${layer.toUpperCase()}</text>`;
      let cx = mini ? 8 : 90;
      comps.forEach(c => {
        const cw = mini ? 34 : Math.max(90, c.name.length * 6.4);
        s += `<rect x="${cx}" y="${y + (mini ? 3 : 18)}" width="${cw}" height="${mini ? 12 : 34}" rx="6" fill="${colors[layer]}" opacity="${mini ? 0.85 : 0.16}" stroke="${colors[layer]}"/>`;
        if (!mini) s += `<text x="${cx + cw / 2}" y="${y + 39}" text-anchor="middle" font-size="10.5" fill="var(--text)" font-family="Segoe UI, sans-serif">${escapeHtml(c.name)}</text>`;
        cx += cw + (mini ? 4 : 10);
      });
      y += bandH + gap;
    });
    return s + "</svg>";
  }

  function svgRibbon(mini) {
    const n = BLUEPRINT.flowSteps.length;
    const w = mini ? 260 : n * 56 + 20, h = mini ? 60 : 120;
    const cy = mini ? 20 : 30, r = mini ? 6 : 14;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
    let x = mini ? 12 : 30;
    const step = mini ? (w - 24) / (n - 1) : 56;
    BLUEPRINT.flowSteps.forEach((st, i) => {
      if (i > 0) s += `<line x1="${x - step}" y1="${cy}" x2="${x - r - 2}" y2="${cy}" stroke="var(--border)" stroke-width="2"/>`;
      const col = st.model ? "var(--accent)" : "var(--slate)";
      s += `<circle cx="${x}" cy="${cy}" r="${r}" fill="${col}"/>`;
      if (!mini) {
        s += `<text x="${x}" y="${cy + 4}" text-anchor="middle" font-size="11" fill="var(--accent-ink)" font-weight="700" font-family="Segoe UI, sans-serif">${st.n}</text>`;
        s += `<text x="${x}" y="${cy + r + 18}" text-anchor="middle" font-size="9.5" fill="var(--muted)" font-family="Segoe UI, sans-serif">${escapeHtml(st.actor)}</text>`;
        if (st.loop) s += `<text x="${x}" y="${cy - r - 8}" text-anchor="middle" font-size="9.5" fill="var(--amber)" font-family="Segoe UI, sans-serif">↻</text>`;
      }
      x += step;
    });
    if (!mini) {
      s += `<circle cx="14" cy="${h - 10}" r="5" fill="var(--accent)"/><text x="24" y="${h - 6}" font-size="10" fill="var(--muted)" font-family="Segoe UI, sans-serif">AI touches this step</text>`;
      s += `<circle cx="180" cy="${h - 10}" r="5" fill="var(--slate)"/><text x="190" y="${h - 6}" font-size="10" fill="var(--muted)" font-family="Segoe UI, sans-serif">no model call</text>`;
    }
    return s + "</svg>";
  }

  function svgTimeline(mini) {
    const phases = BLUEPRINT.phases;
    const w = mini ? 260 : 640, rowH = mini ? 14 : 40, gap = mini ? 3 : 10;
    const totalDays = phases.reduce((a, p) => a + p.days, 0);
    const chartW = w - (mini ? 4 : 140);
    let s = `<svg viewBox="0 0 ${w} ${(rowH + gap) * phases.length + 4}" xmlns="http://www.w3.org/2000/svg">`;
    let cum = 0;
    phases.forEach((p, i) => {
      const y = i * (rowH + gap) + 2;
      const bx = mini ? 2 : 130, barW = (p.days / totalDays) * chartW;
      if (!mini) s += `<text x="0" y="${y + rowH / 2 + 4}" font-size="10.5" fill="var(--text)" font-family="Segoe UI, sans-serif">${p.n}. ${escapeHtml(p.name)}</text>`;
      s += `<rect x="${bx + (cum / totalDays) * chartW}" y="${y}" width="${Math.max(barW, 2)}" height="${rowH}" rx="5" fill="${p.critical ? 'var(--accent)' : 'var(--slate)'}" opacity="${p.critical ? 1 : 0.55}"/>`;
      if (!mini && p.critical) s += `<text x="${bx + chartW + 6}" y="${y + rowH / 2 + 4}" font-size="9.5" fill="var(--accent)" font-weight="700" font-family="Segoe UI, sans-serif">gate</text>`;
      cum += p.days;
    });
    return s + "</svg>";
  }

  function svgGrid(mini) {
    const rows = BLUEPRINT.coverage;
    const w = mini ? 260 : 640, rowH = mini ? 8 : 30, gap = mini ? 2 : 5;
    let s = `<svg viewBox="0 0 ${w} ${(rowH + gap) * rows.length}" xmlns="http://www.w3.org/2000/svg">`;
    rows.forEach((r, i) => {
      const y = i * (rowH + gap);
      const fill = r.status === "covered" ? "var(--green-bg)" : r.status === "partial" ? "var(--amber-bg)" : "var(--red-bg)";
      const stroke = r.status === "covered" ? "var(--green)" : r.status === "partial" ? "var(--amber)" : "var(--red)";
      s += `<rect x="0" y="${y}" width="${w}" height="${rowH}" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="1"/>`;
      if (!mini) s += `<text x="8" y="${y + rowH / 2 + 4}" font-size="10" fill="${stroke}" font-family="Segoe UI, sans-serif">${escapeHtml(r.phrase)}</text>`;
    });
    return s + "</svg>";
  }

  function svgFork(mini) {
    const w = mini ? 260 : 640, h = mini ? 90 : 220;
    const q = BLUEPRINT.openQuestion;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${ARROW}`;
    const topW = mini ? 140 : 400, topX = (w - topW) / 2, topY = mini ? 4 : 10, topH = mini ? 22 : 46;
    s += `<rect x="${topX}" y="${topY}" width="${topW}" height="${topH}" rx="8" fill="var(--card)" stroke="var(--accent)" stroke-width="1.5"/>`;
    if (!mini) s += `<text x="${w / 2}" y="${topY + topH / 2 + 4}" text-anchor="middle" font-size="11" fill="var(--text)" font-family="Segoe UI, sans-serif">${escapeHtml(q.question.length > 60 ? "Catalog: exists already, or built here?" : q.question)}</text>`;
    const branchY = mini ? 40 : 110, branchW = mini ? 100 : 260, branchH = mini ? 30 : 70;
    const positions = [w / 2 - branchW - (mini ? 8 : 20), w / 2 + (mini ? 8 : 20)];
    q.branches.forEach((b, i) => {
      const bx = positions[i];
      s += `<line x1="${w / 2}" y1="${topY + topH}" x2="${bx + branchW / 2}" y2="${branchY}" stroke="var(--border)" stroke-width="2" marker-end="url(#arrowhead)"/>`;
      const col = i === 0 ? "var(--green)" : "var(--amber)";
      s += `<rect x="${bx}" y="${branchY}" width="${branchW}" height="${branchH}" rx="8" fill="${i === 0 ? 'var(--green-bg)' : 'var(--amber-bg)'}" stroke="${col}"/>`;
      if (!mini) {
        s += `<text x="${bx + branchW / 2}" y="${branchY + 18}" text-anchor="middle" font-size="10.5" font-weight="700" fill="${col}" font-family="Segoe UI, sans-serif">${escapeHtml(b.label)}</text>`;
        const words = b.detail.split(" "); let line = "", ly = branchY + 34, lines = [];
        words.forEach(word => { if ((line + word).length > 34) { lines.push(line); line = word + " "; } else line += word + " "; });
        lines.push(line);
        lines.slice(0, 2).forEach((ln, li) => s += `<text x="${bx + branchW / 2}" y="${ly + li * 12}" text-anchor="middle" font-size="8.5" fill="var(--text)" font-family="Segoe UI, sans-serif">${escapeHtml(ln.trim())}</text>`);
      }
    });
    return s + "</svg>";
  }

  function svgBoundary(mini) {
    const w = mini ? 260 : 640, h = mini ? 110 : 260;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
    const bx = mini ? 6 : 20, by = mini ? 6 : 20, bw = w - bx * 2, bh = h - by * 2 - (mini ? 20 : 60);
    s += `<rect x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="12" fill="var(--green-bg)" stroke="var(--green)" stroke-width="1.5" stroke-dasharray="6 4"/>`;
    if (!mini) s += `<text x="${bx + 10}" y="${by + 16}" font-size="10" fill="var(--green)" font-weight="700" font-family="Segoe UI, sans-serif">THIS SYSTEM</text>`;
    let cx = bx + 12, cy = by + (mini ? 14 : 28);
    BLUEPRINT.components.forEach((c, i) => {
      const cw = mini ? 30 : 140;
      if (cx + cw > bx + bw - 10) { cx = bx + 12; cy += mini ? 16 : 32; }
      s += `<rect x="${cx}" y="${cy}" width="${cw}" height="${mini ? 10 : 22}" rx="5" fill="var(--card)" stroke="var(--green)"/>`;
      if (!mini) s += `<text x="${cx + cw / 2}" y="${cy + 15}" text-anchor="middle" font-size="8.5" fill="var(--text)" font-family="Segoe UI, sans-serif">${escapeHtml(c.name.split(" ").slice(0, 2).join(" "))}</text>`;
      cx += cw + 8;
    });
    const outsideItems = ["Auth", "Notifications", "PBIX Publish"];
    let ox = bx, oy = by + bh + (mini ? 8 : 20);
    if (!mini) s += `<text x="${bx}" y="${oy - 4}" font-size="10" fill="var(--red)" font-weight="700" font-family="Segoe UI, sans-serif">OUTSIDE THIS DESIGN</text>`;
    outsideItems.forEach(item => {
      const ow = mini ? 40 : 110;
      s += `<rect x="${ox}" y="${oy}" width="${ow}" height="${mini ? 10 : 22}" rx="5" fill="var(--red-bg)" stroke="var(--red)"/>`;
      if (!mini) s += `<text x="${ox + ow / 2}" y="${oy + 15}" text-anchor="middle" font-size="8.5" fill="var(--red)" font-family="Segoe UI, sans-serif">${escapeHtml(item)}</text>`;
      ox += ow + 8;
    });
    return s + "</svg>";
  }

  function svgMiniNodeGraph() {
    const pts = [[20, 40], [80, 15], [80, 65], [150, 40], [220, 15], [220, 65]];
    const edges = [[0, 1], [0, 2], [1, 3], [2, 3], [3, 4], [3, 5]];
    let s = `<svg viewBox="0 0 260 90" xmlns="http://www.w3.org/2000/svg">`;
    edges.forEach(([a, b]) => s += `<line x1="${pts[a][0]}" y1="${pts[a][1]}" x2="${pts[b][0]}" y2="${pts[b][1]}" stroke="var(--border)" stroke-width="2"/>`);
    pts.forEach((p, i) => s += `<circle cx="${p[0]}" cy="${p[1]}" r="9" fill="${i === 3 ? 'var(--accent)' : 'var(--slate)'}"/>`);
    return s + "</svg>";
  }

  const ILLUSTRATIONS = { pipeline: svgPipeline, layers: svgLayers, ribbon: svgRibbon, timeline: svgTimeline, grid: svgGrid, fork: svgFork, boundary: svgBoundary };

  /* ============================== SHELL ============================== */
  function topbarHTML(currentId) {
    const navLinks = BLUEPRINT.sections.map(s => `<a href="${s.file}" class="${s.id === currentId ? 'current' : ''}">${s.nav}</a>`).join("");
    return `
    <div class="topbar">
      <a class="brand" href="index.html">${BLUEPRINT.meta.title}<small>Project Blueprint</small></a>
      <nav>${navLinks}</nav>
      <div class="tools">
        <div class="searchwrap">
          <input class="searchbox" id="navSearch" type="search" placeholder="Search blueprint…" autocomplete="off">
          <div class="searchdrop" id="navSearchDrop"></div>
        </div>
        <button class="iconbtn" id="themeToggle" title="Toggle theme" aria-label="Toggle theme">◐</button>
        <button class="iconbtn" id="printBtn" title="Print" aria-label="Print">🖶</button>
      </div>
    </div>
    <div class="progressbar"><div id="progressFill"></div></div>`;
  }

  function breadcrumbsHTML(currentId) {
    const sec = BLUEPRINT.sections.find(s => s.id === currentId);
    return `<div class="breadcrumbs"><a href="index.html">Command Center</a> / ${sec ? sec.title : ""}</div>`;
  }

  function footerNavHTML(currentId) {
    const idx = BLUEPRINT.sections.findIndex(s => s.id === currentId);
    const prev = idx > 0 ? BLUEPRINT.sections[idx - 1] : null;
    const next = idx < BLUEPRINT.sections.length - 1 ? BLUEPRINT.sections[idx + 1] : null;
    const prevHref = prev ? prev.file : "index.html";
    const prevLbl = prev ? prev.title : "Command Center";
    const nextHref = next ? next.file : "index.html";
    const nextLbl = next ? next.title : "Command Center";
    return `<div class="footer-nav">
      <a href="${prevHref}"><span class="lbl">← Previous</span>${prevLbl}</a>
      <a class="next" href="${nextHref}"><span class="lbl">Next →</span>${nextLbl}</a>
    </div>`;
  }

  function askPanelHTML() {
    return `
    <div class="ask-panel">
      <button class="ask-launcher" id="askLauncher">✦ Ask the blueprint</button>
      <div class="ask-window" id="askWindow">
        <div class="ask-head"><strong>Ask the blueprint</strong><button class="iconbtn" id="askClose">✕</button></div>
        <div class="ask-modes">
          <button class="mode-btn active" data-mode="search">Search — no key</button>
          <button class="mode-btn" data-mode="claude">Claude — needs key</button>
        </div>
        <div class="ask-config" id="askConfig" style="display:none;">
          <label>Anthropic API key (stored only in this browser)</label>
          <input type="password" id="askApiKey" placeholder="sk-ant-…">
          <label>Model</label>
          <select id="askModel">
            <option value="claude-opus-5">claude-opus-5 (default)</option>
            <option value="claude-sonnet-5">claude-sonnet-5</option>
            <option value="claude-haiku-4-5">claude-haiku-4-5</option>
          </select>
          <label>Scope</label>
          <select id="askScope">
            <option value="section">This section</option>
            <option value="all">Whole blueprint</option>
          </select>
        </div>
        <div class="ask-body" id="askBody">
          <p class="ask-hint">Search mode reads the same index as the nav search box — no key, no network, works offline. Switch to Claude mode to ask in your own words using your own API key.</p>
        </div>
        <div class="ask-foot">
          <input type="text" id="askInput" placeholder="Ask about this blueprint…">
          <button id="askSend">Ask</button>
        </div>
      </div>
    </div>`;
  }

  function modalHTML() {
    return `
    <div class="modal-overlay" id="modalOverlay">
      <div class="modal-box">
        <div class="modal-toolbar">
          <strong id="modalTitle" style="margin-right:auto; font-size:13.5px;"></strong>
          <button class="iconbtn" id="zoomOut" title="Zoom out">−</button>
          <button class="iconbtn" id="zoomReset" title="Reset zoom">⟳</button>
          <button class="iconbtn" id="zoomIn" title="Zoom in">+</button>
          <button class="iconbtn" id="modalClose" title="Close (Esc)">✕</button>
        </div>
        <div class="modal-body"><div class="zoomwrap" id="zoomwrap"></div></div>
      </div>
    </div>
    <div class="backtotop" id="backToTop"><button title="Back to top">↑</button></div>`;
  }

  /* ============================== BEHAVIORS ============================== */
  function initTheme() {
    const stored = localStorage.getItem("pbi_blueprint_theme");
    if (stored) document.documentElement.setAttribute("data-theme", stored);
    document.getElementById("themeToggle").addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = cur === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("pbi_blueprint_theme", next);
      Site._rerenderMermaid();
    });
  }

  function initPrint() { document.getElementById("printBtn").addEventListener("click", () => window.print()); }

  function initScrollChrome() {
    const fill = document.getElementById("progressFill");
    const backBtn = document.getElementById("backToTop");
    window.addEventListener("scroll", () => {
      const h = document.documentElement;
      const pct = h.scrollTop / (h.scrollHeight - h.clientHeight || 1) * 100;
      if (fill) fill.style.width = pct + "%";
      if (backBtn) backBtn.classList.toggle("show", h.scrollTop > 400);
    });
    if (backBtn) backBtn.querySelector("button").addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  }

  function initNavSearch(currentId) {
    const box = document.getElementById("navSearch");
    const drop = document.getElementById("navSearchDrop");
    if (!box) return;
    box.addEventListener("input", () => {
      const q = box.value.trim();
      filterOnPage(currentId, q);
      if (q.length < 2) { drop.classList.remove("open"); drop.innerHTML = ""; return; }
      const hits = search(q, 8);
      if (hits.length === 0) {
        drop.innerHTML = `<div class="empty">No matches. Check the <a href="06-coverage.html">Coverage</a> page — a miss may be the answer.</div>`;
      } else {
        drop.innerHTML = hits.map(h => `<a class="hit" href="${h.url}"><div class="sec">${h.section}</div><div class="snip">${h.snippet}</div></a>`).join("");
      }
      drop.classList.add("open");
    });
    document.addEventListener("click", e => { if (!box.contains(e.target) && !drop.contains(e.target)) drop.classList.remove("open"); });
  }

  function filterOnPage(currentId, q) {
    const items = document.querySelectorAll(".searchable");
    const needle = q.toLowerCase();
    items.forEach(el => {
      const hay = (el.getAttribute("data-search-text") || el.textContent).toLowerCase();
      el.style.display = (!needle || hay.includes(needle)) ? "" : "none";
    });
  }

  /* ---- Fullscreen expand modal ---- */
  let zoomLevel = 1;
  function applyZoom() { document.getElementById("zoomwrap").style.transform = `scale(${zoomLevel})`; }
  function initModal() {
    const overlay = document.getElementById("modalOverlay");
    document.getElementById("modalClose").addEventListener("click", closeModal);
    overlay.addEventListener("click", e => { if (e.target === overlay) closeModal(); });
    document.getElementById("zoomIn").addEventListener("click", () => { zoomLevel = Math.min(zoomLevel + 0.2, 3); applyZoom(); });
    document.getElementById("zoomOut").addEventListener("click", () => { zoomLevel = Math.max(zoomLevel - 0.2, 0.4); applyZoom(); });
    document.getElementById("zoomReset").addEventListener("click", () => { zoomLevel = 1; applyZoom(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && overlay.classList.contains("open")) closeModal(); });
  }
  function closeModal() { document.getElementById("modalOverlay").classList.remove("open"); }
  function openModalFrom(frameEl, title) {
    zoomLevel = 1;
    const zw = document.getElementById("zoomwrap");
    zw.innerHTML = frameEl.innerHTML;
    zw.style.transform = "scale(1)";
    document.getElementById("modalTitle").textContent = title;
    document.getElementById("modalOverlay").classList.add("open");
  }
  function wireExpand(btnId, frameId, title) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener("click", () => openModalFrom(document.getElementById(frameId), title));
  }

  /* ---- Mermaid ---- */
  let mermaidReady = false;
  const mermaidFigs = [];
  function mermaidThemeVars() {
    const cs = getComputedStyle(document.documentElement);
    const v = n => cs.getPropertyValue(n).trim();
    return {
      background: v("--card"), primaryColor: v("--card"), primaryTextColor: v("--text"),
      primaryBorderColor: v("--accent"), lineColor: v("--muted"), secondaryColor: v("--slate-bg"),
      tertiaryColor: v("--bg"), fontFamily: "Segoe UI, system-ui, sans-serif", textColor: v("--text"),
      actorBkg: v("--card"), actorBorder: v("--accent"), actorTextColor: v("--text"),
      signalColor: v("--muted"), signalTextColor: v("--text"), labelBoxBkgColor: v("--slate-bg"),
      labelTextColor: v("--text"), noteBkgColor: v("--amber-bg"), noteTextColor: v("--text"),
      sectionBkgColor: v("--slate-bg"), altSectionBkgColor: v("--bg"), taskTextColor: v("--text"),
      taskTextOutsideColor: v("--text"), critBkgColor: v("--accent"), critBorderColor: v("--accent"),
      taskBkgColor: v("--slate-bg"), taskBorderColor: v("--border")
    };
  }
  function ensureMermaid() {
    if (mermaidReady || typeof mermaid === "undefined") return;
    mermaid.initialize({ startOnLoad: false, theme: "base", themeVariables: mermaidThemeVars(), securityLevel: "loose" });
    mermaidReady = true;
  }
  async function renderMermaid(frameId, code, btnId, title, interpId, interpText) {
    ensureMermaid();
    mermaidFigs.push({ frameId, code, btnId, title });
    const el = document.getElementById(frameId);
    try {
      const { svg } = await mermaid.render(frameId + "-svg", code);
      el.innerHTML = svg;
    } catch (err) {
      el.innerHTML = `<p style="color:var(--red);font-size:12px;">Diagram failed to render: ${escapeHtml(String(err.message || err))}</p>`;
    }
    if (btnId) wireExpand(btnId, frameId, title);
    if (interpId && interpText) document.getElementById(interpId).innerHTML = interpText;
  }
  async function rerenderMermaid() {
    if (typeof mermaid === "undefined") return;
    mermaidReady = false; ensureMermaid();
    for (const fig of mermaidFigs) {
      const el = document.getElementById(fig.frameId);
      if (!el) continue;
      try { const { svg } = await mermaid.render(fig.frameId + "-svg-" + Date.now(), fig.code); el.innerHTML = svg; } catch (e) { /* keep previous */ }
    }
  }

  /* ---- Custom SVG figure ---- */
  function renderSvgFigure(frameId, kind, mini, btnId, title, interpId, interpText) {
    const el = document.getElementById(frameId);
    el.innerHTML = ILLUSTRATIONS[kind](mini);
    if (btnId) wireExpand(btnId, frameId, title);
    if (interpId && interpText) document.getElementById(interpId).innerHTML = interpText;
  }

  /* ---- Chart.js ---- */
  function renderCoverageChart(canvasId, btnId, title) {
    if (typeof Chart === "undefined") return;
    const counts = {};
    BLUEPRINT.components.forEach(c => counts[c.name] = 0);
    BLUEPRINT.coverage.forEach(r => r.coveredBy.forEach(name => { counts[name] = (counts[name] || 0) + 1; }));
    const labels = Object.keys(counts), data = Object.values(counts);
    const cs = getComputedStyle(document.documentElement);
    const chart = new Chart(document.getElementById(canvasId), {
      type: "bar",
      data: { labels, datasets: [{ label: "Paragraph phrases mapped to this component", data, backgroundColor: cs.getPropertyValue("--accent").trim() }] },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: cs.getPropertyValue("--muted").trim(), stepSize: 1 }, grid: { color: cs.getPropertyValue("--border").trim() } },
          y: { ticks: { color: cs.getPropertyValue("--text").trim(), font: { size: 10.5 } }, grid: { display: false } }
        }
      }
    });
    const btn = document.getElementById(btnId);
    if (btn) btn.addEventListener("click", () => {
      const img = document.createElement("img");
      img.src = chart.toBase64Image();
      img.style.maxWidth = "100%";
      zoomLevel = 1;
      const zw = document.getElementById("zoomwrap");
      zw.innerHTML = ""; zw.appendChild(img); zw.style.transform = "scale(1)";
      document.getElementById("modalTitle").textContent = title;
      document.getElementById("modalOverlay").classList.add("open");
    });
  }

  /* ============================== ASK PANEL ============================== */
  function sectionData(id) {
    switch (id) {
      case "summary": return { idea: BLUEPRINT.idea, dayOneSentence: BLUEPRINT.dayOneSentence };
      case "components": return { components: BLUEPRINT.components };
      case "architecture": return { components: BLUEPRINT.components, diagram: BLUEPRINT.diagrams.architecture, interpretation: BLUEPRINT.interpretations.architecture };
      case "data-flow": return { flowSteps: BLUEPRINT.flowSteps, interpretation: BLUEPRINT.interpretations.dataFlow };
      case "build-order": return { phases: BLUEPRINT.phases, interpretation: BLUEPRINT.interpretations.buildOrder };
      case "coverage": return { coverage: BLUEPRINT.coverage, interpretation: BLUEPRINT.interpretations.coverage };
      case "assumptions": return { assumptions: BLUEPRINT.assumptions, openQuestion: BLUEPRINT.openQuestion };
      case "not-covered": return { notCovered: BLUEPRINT.notCovered };
      default: return BLUEPRINT;
    }
  }

  function initAskPanel(sectionId) {
    const launcher = document.getElementById("askLauncher");
    const win = document.getElementById("askWindow");
    const closeBtn = document.getElementById("askClose");
    const body = document.getElementById("askBody");
    const input = document.getElementById("askInput");
    const send = document.getElementById("askSend");
    const modeBtns = document.querySelectorAll(".mode-btn");
    const config = document.getElementById("askConfig");
    let mode = "search";

    launcher.addEventListener("click", () => win.classList.toggle("open"));
    closeBtn.addEventListener("click", () => win.classList.remove("open"));

    const savedKey = localStorage.getItem("pbi_blueprint_claude_key");
    if (savedKey) document.getElementById("askApiKey").value = savedKey;
    document.getElementById("askApiKey").addEventListener("change", e => localStorage.setItem("pbi_blueprint_claude_key", e.target.value));

    modeBtns.forEach(b => b.addEventListener("click", () => {
      modeBtns.forEach(x => x.classList.remove("active"));
      b.classList.add("active"); mode = b.getAttribute("data-mode");
      config.style.display = mode === "claude" ? "flex" : "none";
      body.innerHTML = mode === "claude"
        ? `<p class="ask-hint">Answers come only from this blueprint's data, sent to Claude as context. Paste your own Anthropic API key above — it's stored only in this browser's localStorage.</p>`
        : `<p class="ask-hint">Search mode reads the same index as the nav search box — no key, no network, works offline.</p>`;
    }));

    function runSearch(q) {
      const hits = search(q, 6);
      if (hits.length === 0) {
        body.innerHTML = `<div class="ask-error">No match for "${escapeHtml(q)}". A miss may be the answer — check the <a href="06-coverage.html">Coverage</a> or <a href="08-not-covered.html">Not Covered</a> page.</div>`;
        return;
      }
      body.innerHTML = hits.map(h => `<div class="ask-answer"><div class="sec">${h.section}</div>${h.snippet}<div style="margin-top:6px;"><a href="${h.url}">Open page →</a></div></div>`).join("");
    }

    async function runClaude(q) {
      const key = document.getElementById("askApiKey").value.trim();
      const model = document.getElementById("askModel").value;
      const scope = document.getElementById("askScope").value;
      if (!key) { body.innerHTML = `<div class="ask-error">No API key entered. Paste your Anthropic API key above, or switch to Search mode (no key needed).</div>`; return; }
      body.innerHTML = `<p class="ask-hint">Asking Claude…</p>`;
      const data = scope === "all" ? BLUEPRINT : sectionData(sectionId);
      const system = "You are answering questions about a system design blueprint for an AI-powered Power BI requirements system. " +
        "Answer ONLY using the JSON data below. If the answer is not contained in this data, say so plainly and suggest checking the Coverage or Not Covered page. " +
        "Be concise.\n\nBLUEPRINT DATA:\n" + JSON.stringify(data);
      const payload = { model, max_tokens: 16000, system, messages: [{ role: "user", content: q }] };
      if (model !== "claude-haiku-4-5") payload.output_config = { effort: "low" };
      try {
        const res = await fetch("https://api.anthropic.com/v1/messages", {
          method: "POST",
          headers: {
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true"
          },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          let msg = res.status === 401 ? "Invalid API key." : res.status === 429 ? "Rate limited — try again shortly." : "Request failed (" + res.status + ").";
          body.innerHTML = `<div class="ask-error">${msg} You can switch to Search mode instead — it needs no key.</div>`;
          return;
        }
        const data2 = await res.json();
        if (data2.stop_reason === "refusal") {
          body.innerHTML = `<div class="ask-error">The model declined to answer that. Try rephrasing, or switch to Search mode.</div>`;
          return;
        }
        const text = (data2.content || []).filter(b => b.type === "text").map(b => b.text).join("\n").trim();
        body.innerHTML = `<div class="ask-answer"><div class="sec">Claude · ${model}</div>${escapeHtml(text || "(empty response)").replace(/\n/g, "<br>")}</div>`;
      } catch (err) {
        body.innerHTML = `<div class="ask-error">Connection failed: ${escapeHtml(String(err.message || err))}. Check your internet connection, or switch to Search mode.</div>`;
      }
    }

    function ask() {
      const q = input.value.trim();
      if (!q) return;
      if (mode === "search") runSearch(q); else runClaude(q);
    }
    send.addEventListener("click", ask);
    input.addEventListener("keydown", e => { if (e.key === "Enter") ask(); });
  }

  /* ============================== PAGE SHELL ============================== */
  function shell(currentId, contentHTML) {
    document.getElementById("app").innerHTML =
      topbarHTML(currentId) +
      `<div class="wrap">${breadcrumbsHTML(currentId)}${contentHTML}${footerNavHTML(currentId)}</div>` +
      askPanelHTML() + modalHTML();
  }

  function initCommon(currentId) {
    initTheme(); initPrint(); initScrollChrome(); initNavSearch(currentId); initModal(); initAskPanel(currentId);
  }

  /* ============================== SECTION PAGES ============================== */
  function fig(id, title) {
    return { frameId: "frame-" + id, btnId: "btn-" + id, interpId: "interp-" + id, title };
  }

  function figureBlock(id, title) {
    const f = fig(id, title);
    return `<div class="figure">
      <div class="fighead"><h3>${title}</h3><button class="expandbtn" id="${f.btnId}">⤢ Expand</button></div>
      <div class="frame mermaid-frame" id="${f.frameId}"></div>
      <p class="interp" id="${f.interpId}"></p>
    </div>`;
  }

  const builders = {
    summary(after) {
      const content = `
        <div class="pagehead"><h1>The Idea</h1><p class="sub">What the paragraph actually says, verbatim.</p></div>
        <div class="card" style="margin-bottom:16px;"><p style="font-size:16px; margin:0;">${escapeHtml(BLUEPRINT.idea)}</p></div>
        <div class="card" style="margin-bottom:20px; border-left:4px solid var(--accent);">
          <p style="margin:0;"><strong>Day-one bar (outranks everything else):</strong> ${escapeHtml(BLUEPRINT.dayOneSentence)}</p>
        </div>
        ${figureBlock("pipeline", "The idea as a pipeline")}
        <div class="card"><p style="margin:0;">This system takes one input — a stakeholder's plain-language request — runs it through a loop of analysis, clarification, and recommendation, and produces one output — a structured requirement. See <a href="03-architecture.html">How It Fits Together</a> for the full mechanism, or jump straight to <a href="02-components.html">Components</a> for what each piece does.</p></div>`;
      shell("summary", content);
      after(() => renderSvgFigure("frame-pipeline", "pipeline", false, "btn-pipeline", "The idea as a pipeline", "interp-pipeline",
        "Nothing is \"finished\" until the request has passed through analysis, clarification, and structuring — the middle box is where the AI-powered part of the paragraph lives."));
    },

    components(after) {
      const rows = BLUEPRINT.components.map(c => `
        <tr class="searchable" data-search-text="${escapeHtml(c.name + " " + c.sentence + " " + c.words.join(" "))}">
          <td><strong>${escapeHtml(c.name)}</strong>${c.thirdParty ? '<span class="tag third-party">third party</span>' : ""}${c.guarantee ? '<span class="tag guarantee">day-one guarantee</span>' : ""}</td>
          <td><span class="tag layer-${c.layer}">${c.layer}</span></td>
          <td>${escapeHtml(c.sentence)}</td>
          <td class="evidence">"${c.words.map(escapeHtml).join('" · "')}"</td>
        </tr>`).join("");
      const content = `
        <div class="pagehead"><h1>Components</h1><p class="sub">${BLUEPRINT.components.length} components. Each one traces back to specific words in the idea — no padding.</p></div>
        <div class="card" style="padding:0; overflow:auto;">
          <table class="comp-table">
            <thead><tr><th>Component</th><th>Layer</th><th>What it does here</th><th>Evidence in the paragraph</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
        ${figureBlock("layers", "Components grouped by layer")}`;
      shell("components", content);
      after(() => renderSvgFigure("frame-layers", "layers", false, "btn-layers", "Components grouped by layer", "interp-layers", BLUEPRINT.interpretations.componentsLayers));
    },

    architecture(after) {
      const content = `
        <div class="pagehead"><h1>How It Fits Together</h1><p class="sub">The full flowchart — every arrow is labelled with what actually crosses it.</p></div>
        ${figureBlock("arch", "Architecture flowchart")}
        <div class="card"><p style="margin:0;">Two loops keep this honest: the AI Engine loops back to the stakeholder when information is missing, and loops back from Structuring and Validation when a draft doesn't fit the schema. See <a href="04-data-flow.html">Data Flow</a> for the step-by-step walkthrough.</p></div>`;
      shell("architecture", content);
      after(() => renderMermaid("frame-arch", BLUEPRINT.diagrams.architecture, "btn-arch", "Architecture flowchart", "interp-arch", BLUEPRINT.interpretations.architecture));
    },

    "data-flow"(after) {
      const steps = BLUEPRINT.flowSteps.map(s => `
        <li class="searchable" data-search-text="${escapeHtml(s.actor + " " + s.action)}" id="step-${s.n}" style="margin-bottom:10px;">
          <strong>${s.n}. ${escapeHtml(s.actor)}</strong>
          ${s.model ? '<span class="tag layer-Intelligence">AI</span>' : ""}${s.loop ? '<span class="tag layer-Orchestration">loop</span>' : ""}
          — ${escapeHtml(s.action)}
        </li>`).join("");
      const content = `
        <div class="pagehead"><h1>Data Flow</h1><p class="sub">Numbered walkthrough of one request, start to finish.</p></div>
        <div class="card" style="margin-bottom:18px;"><ol style="margin:0; padding-left:18px;">${steps}</ol></div>
        ${figureBlock("ribbon", "Steps as a ribbon, colour-coded by AI involvement")}
        ${figureBlock("seq", "Sequence diagram")}`;
      shell("data-flow", content);
      after(() => {
        renderSvgFigure("frame-ribbon", "ribbon", false, "btn-ribbon", "Steps as a ribbon", "interp-ribbon",
          "Of the 11 steps, the AI Engine is invoked for 4 — everything else is deterministic routing, storage, or a schema check.");
        renderMermaid("frame-seq", BLUEPRINT.diagrams.dataFlow, "btn-seq", "Sequence diagram", "interp-seq", BLUEPRINT.interpretations.dataFlow);
      });
    },

    "build-order"(after) {
      const rows = BLUEPRINT.phases.map(p => `
        <div class="phase-row ${p.critical ? "critical" : ""} searchable" data-search-text="${escapeHtml(p.name + " " + p.proves + " " + p.adds.join(" "))}" id="phase-${p.n}">
          <div class="phase-num">${p.n}</div>
          <div>
            <h4>${escapeHtml(p.name)}${p.critical ? '<span class="critbadge">day-one gate</span>' : ""}</h4>
            <div class="adds">Adds: ${p.adds.map(escapeHtml).join(", ")} · ${p.days} days</div>
            <div class="proves"><strong>Proves:</strong> ${escapeHtml(p.proves)}</div>
          </div>
        </div>`).join("");
      const content = `
        <div class="pagehead"><h1>Build Order</h1><p class="sub">Four phases. Phase 4 is what actually keeps the day-one promise.</p></div>
        <div class="card" style="margin-bottom:18px;">${rows}</div>
        ${figureBlock("timeline", "Phases as a proportional timeline")}
        ${figureBlock("gantt", "Gantt chart")}`;
      shell("build-order", content);
      after(() => {
        renderSvgFigure("frame-timeline", "timeline", false, "btn-timeline", "Phases as a proportional timeline", "interp-timeline", BLUEPRINT.interpretations.buildOrder);
        renderMermaid("frame-gantt", BLUEPRINT.diagrams.buildOrder, "btn-gantt", "Gantt chart", "interp-gantt", BLUEPRINT.interpretations.buildOrder);
      });
    },

    coverage(after) {
      const rows = BLUEPRINT.coverage.map(r => `
        <tr class="searchable" data-search-text="${escapeHtml(r.phrase + " " + r.coveredBy.join(" "))}">
          <td>${escapeHtml(r.phrase)}</td>
          <td><span class="status ${r.status}">${r.status.replace("-", " ")}</span></td>
          <td>${r.coveredBy.length ? r.coveredBy.map(escapeHtml).join(", ") : "—"}</td>
        </tr>`).join("");
      const content = `
        <div class="pagehead"><h1>Coverage</h1><p class="sub">Every clause in the idea, mapped to what covers it — and what a reader might assume is included but isn't.</p></div>
        <div class="card" style="padding:0; overflow:auto; margin-bottom:18px;">
          <table class="comp-table"><thead><tr><th>Phrase / expectation</th><th>Status</th><th>Covered by</th></tr></thead><tbody>${rows}</tbody></table>
        </div>
        ${figureBlock("grid", "Coverage grid")}
        <div class="figure">
          <div class="fighead"><h3>Phrases mapped per component</h3><button class="expandbtn" id="btn-chart">⤢ Expand</button></div>
          <div class="frame" style="height:260px;"><canvas id="coverageChart"></canvas></div>
          <p class="interp"><b>What this means:</b> components with more mapped phrases carry more of the paragraph's meaning — the AI Engine and Structuring/Validation are the load-bearing pieces.</p>
        </div>`;
      shell("coverage", content);
      after(() => {
        renderSvgFigure("frame-grid", "grid", false, "btn-grid", "Coverage grid", "interp-grid", BLUEPRINT.interpretations.coverage);
        renderCoverageChart("coverageChart", "btn-chart", "Phrases mapped per component");
      });
    },

    assumptions(after) {
      const rows = BLUEPRINT.assumptions.map(a => `
        <tr class="searchable" data-search-text="${escapeHtml(a.text + " " + a.impact)}" id="assume-${a.n}">
          <td>${a.n}</td><td>${escapeHtml(a.text)}</td><td>${escapeHtml(a.impact)}</td>
        </tr>`).join("");
      const content = `
        <div class="pagehead"><h1>Assumptions &amp; Open Question</h1><p class="sub">Where this design could be wrong, and what it would cost.</p></div>
        <div class="card" style="padding:0; overflow:auto; margin-bottom:18px;">
          <table class="assume-table"><thead><tr><th>#</th><th>Assumption</th><th>Impact if wrong</th></tr></thead><tbody>${rows}</tbody></table>
        </div>
        <div class="card" style="margin-bottom:18px; border-left:4px solid var(--accent);" id="open-question">
          <p style="margin:0 0 6px;"><strong>The one question that would most change the design:</strong></p>
          <p style="margin:0;">${escapeHtml(BLUEPRINT.openQuestion.question)}</p>
        </div>
        ${figureBlock("fork", "What changes under each answer")}`;
      shell("assumptions", content);
      after(() => renderSvgFigure("frame-fork", "fork", false, "btn-fork", "What changes under each answer", "interp-fork",
        "If the catalog already exists, Phase 3 is a quick integration. If it doesn't, a whole curation subsystem has to be built first — the same paragraph, two very different project sizes."));
    },

    "not-covered"(after) {
      const items = BLUEPRINT.notCovered.map(t => `<li class="searchable" data-search-text="${escapeHtml(t)}">${escapeHtml(t)}</li>`).join("");
      const content = `
        <div class="pagehead"><h1>What This Design Does Not Cover</h1><p class="sub">Said plainly, not buried.</p></div>
        <ul class="notlist" style="margin-bottom:20px;">${items}</ul>
        ${figureBlock("boundary", "Inside the design vs. outside it")}`;
      shell("not-covered", content);
      after(() => renderSvgFigure("frame-boundary", "boundary", false, "btn-boundary", "Inside the design vs. outside it", "interp-boundary",
        "Everything inside the dashed line is built to guarantee the day-one sentence. Everything outside it is a real gap, not an oversight — see Assumption 5 for the biggest one (auth)."));
    }
  };

  function renderSectionPage(id) {
    const sec = BLUEPRINT.sections.find(s => s.id === id);
    document.title = (sec ? sec.title : id) + " — " + BLUEPRINT.meta.title;
    const pending = [];
    builders[id](fn => pending.push(fn));
    initCommon(id);
    pending.forEach(fn => fn());
  }

  /* ============================== COMMAND CENTER ============================== */
  function tileMeta(id) {
    switch (id) {
      case "summary": return { count: "1 idea, 1 day-one bar", kind: "pipeline" };
      case "components": return { count: BLUEPRINT.components.length + " components", kind: "layers" };
      case "architecture": return { count: BLUEPRINT.diagrams.architecture.split("-->").length - 1 + " connections", kind: "graph" };
      case "data-flow": return { count: BLUEPRINT.flowSteps.length + " steps", kind: "ribbon" };
      case "build-order": return { count: BLUEPRINT.phases.length + " phases, 1 gate", kind: "timeline" };
      case "coverage": return { count: BLUEPRINT.coverage.filter(r => r.status === "covered").length + " covered, " + BLUEPRINT.coverage.filter(r => r.status !== "covered").length + " flagged", kind: "grid" };
      case "assumptions": return { count: BLUEPRINT.assumptions.length + " assumptions, 1 open question", kind: "fork" };
      case "not-covered": return { count: BLUEPRINT.notCovered.length + " exclusions", kind: "boundary" };
    }
  }
  function tilePreview(kind) {
    if (kind === "graph") return svgMiniNodeGraph();
    return ILLUSTRATIONS[kind](true);
  }

  function renderIndex() {
    document.title = "Command Center — " + BLUEPRINT.meta.title;
    const descByStatic = {
      summary: "The paragraph this whole design is built from, and the sentence that outranks everything else.",
      components: "Seven components, each traced back to specific words — no padding.",
      architecture: "The full flowchart: every box, every labelled arrow, both loops.",
      "data-flow": "One request, start to finish, numbered.",
      "build-order": "Four phases and the one that's the actual day-one gate.",
      coverage: "Every phrase in the idea, mapped — plus what a reader might wrongly assume is included.",
      assumptions: "Where the design could be wrong, and the one question that would change it most.",
      "not-covered": "The honest boundary of scope, said plainly."
    };
    const tiles = BLUEPRINT.sections.map(s => {
      const m = tileMeta(s.id);
      return `<a class="tile" href="${s.file}">
        <div class="preview">${tilePreview(m.kind)}</div>
        <h3>${s.title}</h3>
        <p>${descByStatic[s.id]}</p>
        <span class="count">${m.count}</span>
      </a>`;
    }).join("");

    document.getElementById("app").innerHTML = `
      ${topbarHTML("")}
      <div class="wrap">
        <div class="pagehead">
          <h1>${BLUEPRINT.meta.title}</h1>
          <p class="sub">${BLUEPRINT.meta.tagline}</p>
        </div>
        <div class="card" style="margin-bottom:22px; border-left:4px solid var(--accent);">
          <p style="margin:0;"><strong>Day-one bar:</strong> ${escapeHtml(BLUEPRINT.dayOneSentence)}</p>
        </div>
        <div class="tilegrid">${tiles}</div>
      </div>
      ${askPanelHTML()}${modalHTML()}`;
    initCommon("");
  }

  return { renderSectionPage, renderIndex, search, _rerenderMermaid: rerenderMermaid };
})();
