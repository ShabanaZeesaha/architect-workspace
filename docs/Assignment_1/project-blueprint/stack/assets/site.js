/* Site — shared rendering, nav, search, illustrations, copy buttons, and the Ask agent.
   Reads everything from the bare STACK identifier declared in stack.js. */
const Site = (function () {

  /* ============================== HELPERS ============================== */
  function escapeHtml(s) { return String(s).replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m])); }
  function recById(id) { return STACK.recommendations.find(r => r.id === id); }
  function fitMeta(fit) { return STACK.fitKey.find(k => k.fit === fit); }
  function shortTech(tech) { return tech.length > 26 ? tech.split(/[\(,]/)[0].trim() : tech; }

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

    add("summary", "The idea", STACK.idea, "01-summary.html");
    add("summary", "Where this stack breaks", STACK.headline, "01-summary.html");
    STACK.fitKey.forEach(k => add("summary", k.icon + " " + k.label, k.meaning, "01-summary.html"));

    STACK.recommendations.forEach(r => add("recommendations", r.component + " — " + r.tech,
      r.why + " " + r.caveat, "02-recommendations.html#rec-" + r.id));

    STACK.recommendations.forEach(r => add("ratings", r.component + " fit rating",
      fitMeta(r.fit).label + ": " + r.why + " " + r.caveat, "03-ratings.html#rate-" + r.id));
    STACK.leastConfident.forEach(l => add("ratings", "Least confident: " + recById(l.recId).component, l.note, "03-ratings.html#least-confident"));

    STACK.learningOrder.forEach(l => add("learning-path", l.n + ". " + recById(l.recId).component, l.why, "04-learning-path.html#learn-" + l.recId));

    STACK.alternatives.forEach(a => add("alternatives", recById(a.recId).component + " vs " + a.alt, a.whyNot, "05-alternatives.html#alt-" + a.recId));

    STACK.lockIn.forEach(l => add("lock-in", recById(l.recId).component + " — " + l.difficulty + " to undo", l.why, "06-lock-in.html#lock-" + l.recId));

    add("topology", "What runs where", STACK.topology.note, "07-topology.html");

    STACK.notTold.forEach((t, i) => add("appendix", "Not told #" + (i + 1), t, "08-appendix.html"));

    return entries;
  }
  function getIndex() { if (!INDEX) INDEX = buildIndex(); return INDEX; }

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
  const FITCOLOR = { green: "var(--green)", amber: "var(--amber)", red: "var(--red)" };
  const FITBG = { green: "var(--green-bg)", amber: "var(--amber-bg)", red: "var(--red-bg)" };

  function svgFitBar(mini) {
    const recs = STACK.recommendations;
    const total = recs.length;
    const w = mini ? 260 : 640, h = mini ? 46 : 96;
    const barY = mini ? 8 : 20, barH = mini ? 22 : 40;
    const counts = { green: 0, amber: 0, red: 0 };
    recs.forEach(r => counts[r.fit]++);
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
    let x = 0;
    ["green", "amber", "red"].forEach(fit => {
      const segW = (counts[fit] / total) * w;
      s += `<rect x="${x}" y="${barY}" width="${Math.max(segW, 0.5)}" height="${barH}" fill="${FITCOLOR[fit]}"/>`;
      if (!mini && segW > 24) s += `<text x="${x + segW / 2}" y="${barY + barH / 2 + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)" font-family="Segoe UI, sans-serif">${counts[fit]}</text>`;
      x += segW;
    });
    s += `<rect x="0" y="${barY}" width="${w}" height="${barH}" rx="6" fill="none" stroke="var(--border)"/>`;
    if (!mini) {
      const redX = w - (counts.red / total) * w / 2;
      s += `<line x1="${redX}" y1="${barY + barH}" x2="${redX}" y2="${barY + barH + 14}" stroke="var(--red)" stroke-width="1.5"/>`;
      s += `<text x="${redX}" y="${barY + barH + 26}" text-anchor="middle" font-size="10.5" fill="var(--red)" font-weight="700" font-family="Segoe UI, sans-serif">${counts.red} to watch closely</text>`;
      s += `<text x="0" y="${barY - 6}" font-size="10" fill="var(--muted)" font-family="Segoe UI, sans-serif">${total} recommendations, by fit</text>`;
    }
    return s + "</svg>";
  }

  function svgFitBands(mini) {
    const w = mini ? 260 : 900;
    const bandH = mini ? 20 : 64, gap = mini ? 3 : 10;
    const order = ["red", "amber", "green"];
    let y = 4;
    let s = `<svg viewBox="0 0 ${w} ${(bandH + gap) * order.length + 4}" xmlns="http://www.w3.org/2000/svg">`;
    order.forEach(fit => {
      const recs = STACK.recommendations.filter(r => r.fit === fit);
      s += `<rect x="0" y="${y}" width="${w}" height="${bandH}" rx="8" fill="none" stroke="${FITCOLOR[fit]}" stroke-width="1.5" stroke-dasharray="4 3"/>`;
      const meta = fitMeta(fit);
      if (!mini) s += `<text x="8" y="${y + 14}" font-size="9.5" fill="${FITCOLOR[fit]}" font-weight="700" font-family="Segoe UI, sans-serif">${meta.icon} ${meta.label.toUpperCase()}</text>`;
      let cx = mini ? 8 : 130;
      recs.forEach(r => {
        const label = shortTech(r.tech);
        const cw = mini ? 34 : Math.max(90, label.length * 6.4);
        s += `<rect x="${cx}" y="${y + (mini ? 3 : 20)}" width="${cw}" height="${mini ? 12 : 32}" rx="6" fill="${FITBG[fit]}" opacity="${mini ? 1 : 1}" stroke="${FITCOLOR[fit]}"/>`;
        if (!mini) s += `<text x="${cx + cw / 2}" y="${y + 40}" text-anchor="middle" font-size="10" fill="var(--text)" font-family="Segoe UI, sans-serif">${escapeHtml(label)}</text>`;
        cx += cw + (mini ? 4 : 10);
      });
      y += bandH + gap;
    });
    return s + "</svg>";
  }

  function svgLearningLadder(mini) {
    const steps = STACK.learningOrder;
    const n = steps.length;
    const w = mini ? 260 : 640, h = mini ? 90 : 260;
    const stepW = (w - (mini ? 20 : 60)) / n, stepH = (h - (mini ? 20 : 60)) / n;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${ARROW}`;
    steps.forEach((st, i) => {
      const bx = mini ? 10 + i * stepW : 20 + i * stepW;
      const bw = mini ? stepW - 3 : stepW - 8;
      const by = h - (mini ? 14 : 40) - (i + 1) * stepH;
      const bh = (i + 1) * stepH;
      s += `<rect x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="4" fill="var(--accent)" opacity="${0.35 + i * (0.55 / n)}"/>`;
      if (!mini) {
        s += `<text x="${bx + bw / 2}" y="${by - 6}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--text)" font-family="Segoe UI, sans-serif">${st.n}</text>`;
        const comp = recById(st.recId).component;
        const words = comp.split(" ");
        let line1 = "", line2 = "";
        words.forEach(w2 => { if ((line1 + w2).length <= 12 && !line2) line1 += w2 + " "; else line2 += w2 + " "; });
        s += `<text x="${bx + bw / 2}" y="${h - 22}" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="Segoe UI, sans-serif">${escapeHtml(line1.trim())}</text>`;
        if (line2) s += `<text x="${bx + bw / 2}" y="${h - 10}" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="Segoe UI, sans-serif">${escapeHtml(line2.trim())}</text>`;
      }
    });
    return s + "</svg>";
  }

  function svgLockInScale(mini) {
    const items = STACK.lockIn;
    const w = mini ? 260 : 640, h = mini ? 60 : 200;
    const axisY = mini ? 30 : 46, axisX0 = mini ? 10 : 30, axisX1 = w - (mini ? 10 : 30);
    const posFor = d => d === "easy" ? axisX0 + (axisX1 - axisX0) * 0.12 : d === "medium" ? axisX0 + (axisX1 - axisX0) * 0.5 : axisX0 + (axisX1 - axisX0) * 0.88;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
    s += `<line x1="${axisX0}" y1="${axisY}" x2="${axisX1}" y2="${axisY}" stroke="var(--border)" stroke-width="2"/>`;
    if (!mini) {
      s += `<text x="${axisX0}" y="${axisY - 10}" font-size="10.5" fill="var(--green)" font-weight="700" font-family="Segoe UI, sans-serif">EASY</text>`;
      s += `<text x="${(axisX0 + axisX1) / 2}" y="${axisY - 10}" text-anchor="middle" font-size="10.5" fill="var(--amber)" font-weight="700" font-family="Segoe UI, sans-serif">MEDIUM</text>`;
      s += `<text x="${axisX1}" y="${axisY - 10}" text-anchor="end" font-size="10.5" fill="var(--red)" font-weight="700" font-family="Segoe UI, sans-serif">HARD</text>`;
    }
    const byDiff = {};
    items.forEach(it => { (byDiff[it.difficulty] = byDiff[it.difficulty] || []).push(it); });
    const diffColor = { easy: "var(--green)", medium: "var(--amber)", hard: "var(--red)" };
    Object.keys(byDiff).forEach(d => {
      byDiff[d].forEach((it, idx) => {
        const x = posFor(d);
        const y = axisY + 16 + idx * (mini ? 8 : 24);
        s += `<circle cx="${x}" cy="${y}" r="${mini ? 3 : 6}" fill="${diffColor[d]}"/>`;
        if (!mini) s += `<text x="${x + 10}" y="${y + 4}" font-size="10" fill="var(--text)" font-family="Segoe UI, sans-serif">${escapeHtml(shortTech(recById(it.recId).component))}</text>`;
      });
    });
    return s + "</svg>";
  }

  function svgTopology(mini) {
    const w = mini ? 260 : 640, h = mini ? 110 : 260;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
    const halfW = w / 2 - (mini ? 4 : 10);
    const zoneH = h - (mini ? 12 : 30);
    s += `<rect x="0" y="${mini ? 4 : 14}" width="${halfW}" height="${zoneH}" rx="10" fill="var(--green-bg)" stroke="var(--green)" stroke-width="1.5" stroke-dasharray="6 4"/>`;
    s += `<rect x="${w - halfW}" y="${mini ? 4 : 14}" width="${halfW}" height="${zoneH}" rx="10" fill="var(--amber-bg)" stroke="var(--amber)" stroke-width="1.5" stroke-dasharray="6 4"/>`;
    if (!mini) {
      s += `<text x="10" y="30" font-size="10" fill="var(--green)" font-weight="700" font-family="Segoe UI, sans-serif">YOUR CODE</text>`;
      s += `<text x="${w - halfW + 10}" y="30" font-size="10" fill="var(--amber)" font-weight="700" font-family="Segoe UI, sans-serif">SOMEONE ELSE'S INFRASTRUCTURE</text>`;
    }
    function chipsIn(ids, zx, zw, zy) {
      let cx = zx + 10, cy = zy + (mini ? 12 : 40);
      ids.forEach((id, i) => {
        const label = shortTech(recById(id).component);
        const cw = mini ? 30 : 130;
        if (cx + cw > zx + zw - 8) { cx = zx + 10; cy += mini ? 16 : 36; }
        s += `<rect x="${cx}" y="${cy}" width="${cw}" height="${mini ? 10 : 24}" rx="5" fill="var(--card)" stroke="var(--border)"/>`;
        if (!mini) s += `<text x="${cx + cw / 2}" y="${cy + 16}" text-anchor="middle" font-size="8.5" fill="var(--text)" font-family="Segoe UI, sans-serif">${escapeHtml(label)}</text>`;
        cx += cw + 8;
      });
    }
    chipsIn(STACK.topology.yourCode, 0, halfW, mini ? 4 : 14);
    chipsIn(STACK.topology.someoneElses, w - halfW, halfW, mini ? 4 : 14);
    return s + "</svg>";
  }

  function svgCompare(mini) {
    const w = 260, h = 90;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${ARROW}`;
    s += `<rect x="20" y="30" width="90" height="30" rx="6" fill="var(--card)" stroke="var(--accent)"/>`;
    s += `<rect x="150" y="30" width="90" height="30" rx="6" fill="var(--slate-bg)" stroke="var(--slate)"/>`;
    s += `<line x1="112" y1="45" x2="146" y2="45" stroke="var(--accent)" stroke-width="2" marker-end="url(#arrowhead)"/>`;
    return s + "</svg>";
  }

  function svgKeys(mini) {
    const w = 260, h = 90;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
    [["green", 20], ["amber", 45], ["red", 70]].forEach(([fit, y]) => {
      s += `<circle cx="30" cy="${y}" r="9" fill="${FITCOLOR[fit]}"/>`;
      s += `<rect x="50" y="${y - 6}" width="190" height="12" rx="6" fill="${FITBG[fit]}"/>`;
    });
    return s + "</svg>";
  }

  function svgDoc(mini) {
    const w = 260, h = 90;
    let s = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">`;
    s += `<rect x="70" y="10" width="120" height="70" rx="8" fill="var(--card)" stroke="var(--border)"/>`;
    [24, 38, 52, 66].forEach(y => s += `<rect x="82" y="${y}" width="${y === 66 ? 60 : 96}" height="6" rx="3" fill="var(--slate-bg)"/>`);
    return s + "</svg>";
  }

  const ILLUSTRATIONS = { fitbar: svgFitBar, fitbands: svgFitBands, ladder: svgLearningLadder, lockscale: svgLockInScale, topology: svgTopology, compare: svgCompare, keys: svgKeys, doc: svgDoc };

  /* ============================== SHELL ============================== */
  function topbarHTML(currentId) {
    const navLinks = STACK.sections.map(s => `<a href="${s.file}" class="${s.id === currentId ? 'current' : ''}">${s.nav}</a>`).join("");
    return `
    <div class="topbar">
      <a class="brand" href="index.html">${STACK.meta.title}<small>Tech Stack Knowledge Base</small></a>
      <nav>${navLinks}</nav>
      <div class="tools">
        <div class="searchwrap">
          <input class="searchbox" id="navSearch" type="search" placeholder="Search stack…" autocomplete="off">
          <div class="searchdrop" id="navSearchDrop"></div>
        </div>
        <button class="iconbtn" id="themeToggle" title="Toggle theme" aria-label="Toggle theme">◐</button>
        <button class="iconbtn" id="printBtn" title="Print" aria-label="Print">🖶</button>
      </div>
    </div>
    <div class="progressbar"><div id="progressFill"></div></div>`;
  }

  function breadcrumbsHTML(currentId) {
    const sec = STACK.sections.find(s => s.id === currentId);
    return `<div class="breadcrumbs"><a href="index.html">Command Center</a> / ${sec ? sec.title : ""}</div>`;
  }

  function footerNavHTML(currentId) {
    const idx = STACK.sections.findIndex(s => s.id === currentId);
    const prev = idx > 0 ? STACK.sections[idx - 1] : null;
    const next = idx < STACK.sections.length - 1 ? STACK.sections[idx + 1] : null;
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
      <button class="ask-launcher" id="askLauncher">✦ Ask the stack</button>
      <div class="ask-window" id="askWindow">
        <div class="ask-head"><strong>Ask the stack</strong><button class="iconbtn" id="askClose">✕</button></div>
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
            <option value="all">Whole stack</option>
          </select>
        </div>
        <div class="ask-body" id="askBody">
          <p class="ask-hint">Search mode reads the same index as the nav search box — no key, no network, works offline. Switch to Claude mode to ask in your own words using your own API key.</p>
        </div>
        <div class="ask-foot">
          <input type="text" id="askInput" placeholder="Ask about this stack…">
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
    const stored = localStorage.getItem("pbi_stack_theme");
    if (stored) document.documentElement.setAttribute("data-theme", stored);
    document.getElementById("themeToggle").addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = cur === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("pbi_stack_theme", next);
      Site._rerenderFigures();
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
        drop.innerHTML = `<div class="empty">No matches. Check the <a href="08-appendix.html">Appendix</a> — a miss may be the answer.</div>`;
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

  /* ---- Copy-ready prompt buttons ---- */
  function fallbackCopy(text) {
    return new Promise(resolve => {
      const ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.focus(); ta.select();
      try { document.execCommand("copy"); } catch (e) { /* ignore */ }
      document.body.removeChild(ta);
      resolve();
    });
  }
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
    }
    return fallbackCopy(text);
  }
  function initCopyButtons() {
    document.querySelectorAll(".copybtn").forEach(btn => {
      btn.addEventListener("click", () => {
        const text = btn.getAttribute("data-copy") || "";
        copyText(text).then(() => {
          const orig = btn.textContent;
          btn.textContent = "Copied!";
          btn.classList.add("copied");
          setTimeout(() => { btn.textContent = orig; btn.classList.remove("copied"); }, 1500);
        });
      });
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

  /* ---- Custom SVG figure ---- */
  const renderedFigures = [];
  function renderSvgFigure(frameId, kind, mini, btnId, title, interpId, interpText) {
    renderedFigures.push({ frameId, kind, mini });
    const el = document.getElementById(frameId);
    el.innerHTML = ILLUSTRATIONS[kind](mini);
    if (btnId) wireExpand(btnId, frameId, title);
    if (interpId && interpText) document.getElementById(interpId).innerHTML = interpText;
  }
  function rerenderFigures() {
    renderedFigures.forEach(f => {
      const el = document.getElementById(f.frameId);
      if (el) el.innerHTML = ILLUSTRATIONS[f.kind](f.mini);
    });
  }

  /* ============================== ASK PANEL ============================== */
  function sectionData(id) {
    switch (id) {
      case "summary": return { idea: STACK.idea, scaleAssumption: STACK.scaleAssumption, headline: STACK.headline, fitKey: STACK.fitKey };
      case "recommendations": return { groups: STACK.groups, recommendations: STACK.recommendations };
      case "ratings": return { fitKey: STACK.fitKey, recommendations: STACK.recommendations, leastConfident: STACK.leastConfident };
      case "learning-path": return { learningOrder: STACK.learningOrder, recommendations: STACK.recommendations };
      case "alternatives": return { alternatives: STACK.alternatives, recommendations: STACK.recommendations };
      case "lock-in": return { lockIn: STACK.lockIn, recommendations: STACK.recommendations };
      case "topology": return { topology: STACK.topology, recommendations: STACK.recommendations };
      case "appendix": return { notTold: STACK.notTold, leastConfident: STACK.leastConfident };
      default: return STACK;
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

    const savedKey = localStorage.getItem("pbi_stack_claude_key");
    if (savedKey) document.getElementById("askApiKey").value = savedKey;
    document.getElementById("askApiKey").addEventListener("change", e => localStorage.setItem("pbi_stack_claude_key", e.target.value));

    modeBtns.forEach(b => b.addEventListener("click", () => {
      modeBtns.forEach(x => x.classList.remove("active"));
      b.classList.add("active"); mode = b.getAttribute("data-mode");
      config.style.display = mode === "claude" ? "flex" : "none";
      body.innerHTML = mode === "claude"
        ? `<p class="ask-hint">Answers come only from this document's data, sent to Claude as context. Paste your own Anthropic API key above — it's stored only in this browser's localStorage.</p>`
        : `<p class="ask-hint">Search mode reads the same index as the nav search box — no key, no network, works offline.</p>`;
    }));

    function runSearch(q) {
      const hits = search(q, 6);
      if (hits.length === 0) {
        body.innerHTML = `<div class="ask-error">No match for "${escapeHtml(q)}". A miss may be the answer — check the <a href="08-appendix.html">Appendix</a> page.</div>`;
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
      const data = scope === "all" ? STACK : sectionData(sectionId);
      const system = "You are answering questions about a technology-stack recommendation document for an AI-powered Power BI requirements system. " +
        "Answer ONLY using the JSON data below. If the answer is not contained in this data, say so plainly and suggest checking the Appendix page (what this document does not tell you). " +
        "Never suggest the user reconsider, soften, or upgrade a 🔴 'consider carefully' rating — treat those ratings as fixed conclusions to explain, not debate. Be concise.\n\nSTACK DATA:\n" + JSON.stringify(data);
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
    initTheme(); initPrint(); initScrollChrome(); initNavSearch(currentId); initModal(); initAskPanel(currentId); initCopyButtons();
  }

  /* ============================== SHARED CARD BUILDERS ============================== */
  function fig(id, title) { return { frameId: "frame-" + id, btnId: "btn-" + id, interpId: "interp-" + id, title }; }
  function figureBlock(id, title) {
    const f = fig(id, title);
    return `<div class="figure">
      <div class="fighead"><h3>${title}</h3><button class="expandbtn" id="${f.btnId}">⤢ Expand</button></div>
      <div class="frame" id="${f.frameId}"></div>
      <p class="interp" id="${f.interpId}"></p>
    </div>`;
  }

  function fitPill(fit) {
    const m = fitMeta(fit);
    return `<span class="fitpill ${fit}">${m.icon} ${m.label}</span>`;
  }

  function promptRow(promptText) {
    return `<div class="promptrow">
      <div class="prompttext">"${escapeHtml(promptText)}"</div>
      <button class="copybtn" data-copy="${escapeHtml(promptText)}">Copy prompt</button>
    </div>`;
  }

  function recCard(r, extra) {
    const searchText = escapeHtml([r.component, r.tech, r.why, r.caveat, r.prompt].join(" "));
    return `<div class="card reccard searchable" data-search-text="${searchText}" id="rec-${r.id}" style="margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
        <div>
          <div style="font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;">${r.fromComponentList ? "Component" : "Needed by the data flow"}</div>
          <h4 style="margin:2px 0 8px; font-size:15px;">${escapeHtml(r.component)}</h4>
          <div style="font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;">Recommended</div>
          <div style="font-weight:700; font-size:14px;">${escapeHtml(r.tech)}</div>
        </div>
        ${fitPill(r.fit)}
      </div>
      <p style="margin:10px 0 0; font-size:13.5px;">${escapeHtml(r.why)}</p>
      ${r.caveat ? `<div class="caveat ${r.fit === "red" ? "is-red" : ""}"><b>Caveat:</b> ${escapeHtml(r.caveat)}</div>` : ""}
      ${extra || ""}
      ${promptRow(r.prompt)}
    </div>`;
  }

  /* ============================== SECTION PAGES ============================== */
  const builders = {
    summary(after) {
      const counts = { green: 0, amber: 0, red: 0 };
      STACK.recommendations.forEach(r => counts[r.fit]++);
      const keyCards = STACK.fitKey.map(k => `
        <div class="card keycard ${k.fit}"><div class="icon">${k.icon}</div><div><h4>${k.label}</h4><p>${escapeHtml(k.meaning)}</p></div></div>`).join("");
      const content = `
        <div class="pagehead"><h1>Summary</h1><p class="sub">One real technology per component, rated against this project's actual day-one scale.</p></div>
        <div class="card" style="margin-bottom:16px;"><p style="font-size:15.5px; margin:0;">${escapeHtml(STACK.idea)}</p></div>
        <div class="card" style="margin-bottom:16px; border-left:4px solid var(--accent);">
          <p style="margin:0;"><strong>Scale assumption driving every rating:</strong> ${escapeHtml(STACK.scaleAssumption)}</p>
        </div>
        <div class="card" style="margin-bottom:20px; border-left:4px solid var(--red);">
          <p style="margin:0;"><strong>Where this stack is most likely to break:</strong> ${escapeHtml(STACK.headline)}</p>
        </div>
        <div class="grid cols-3" style="margin-bottom:20px;">${keyCards}</div>
        ${figureBlock("fitbar", "The whole stack, by fit rating")}
        <div class="card"><p style="margin:0;">${counts.green} great fits, ${counts.amber} good fits with a caveat, ${counts.red} to consider carefully. See <a href="02-recommendations.html">Recommendations</a> for the full table, or <a href="03-ratings.html">Fit Ratings Explained</a> for what each rating actually means here.</p></div>`;
      shell("summary", content);
      after(() => renderSvgFigure("frame-fitbar", "fitbar", false, "btn-fitbar", "The whole stack, by fit rating", "interp-fitbar", STACK.interpretations.summary));
    },

    recommendations(after) {
      const groupsHTML = STACK.groups.map(g => {
        const recs = STACK.recommendations.filter(r => r.group === g.id);
        return `<div class="grouphead">${escapeHtml(g.label)} (${recs.length})</div>` + recs.map(r => recCard(r)).join("");
      }).join("");
      const content = `
        <div class="pagehead"><h1>Recommendations</h1><p class="sub">${STACK.recommendations.length} rows — one real technology per architecture component, plus what the data flow needed that the component list never named.</p></div>
        ${groupsHTML}
        ${figureBlock("fitbands", "The stack as bands, coloured by fit")}`;
      shell("recommendations", content);
      after(() => renderSvgFigure("frame-fitbands", "fitbands", false, "btn-fitbands", "The stack as bands, coloured by fit", "interp-fitbands", STACK.interpretations.recommendations));
    },

    ratings(after) {
      const keyCards = STACK.fitKey.map(k => `
        <div class="card keycard ${k.fit}"><div class="icon">${k.icon}</div><div><h4>${k.label}</h4><p>${escapeHtml(k.meaning)}</p></div></div>`).join("");
      const byFit = fit => STACK.recommendations.filter(r => r.fit === fit).map(r => `
        <div class="phase-row searchable" data-search-text="${escapeHtml(r.component + ' ' + r.why + ' ' + r.caveat)}" id="rate-${r.id}">
          <div class="phase-num" style="background:${FITBG[r.fit]}; color:${FITCOLOR[r.fit]};">${fitMeta(r.fit).icon}</div>
          <div><h4>${escapeHtml(r.component)} <span style="font-weight:400;color:var(--muted);">— ${escapeHtml(r.tech)}</span></h4>
          <div class="proves">${escapeHtml(r.why)}</div>${r.caveat ? `<div class="caveat ${r.fit === "red" ? "is-red" : ""}"><b>Caveat:</b> ${escapeHtml(r.caveat)}</div>` : ""}</div>
        </div>`).join("");
      const leastConf = STACK.leastConfident.map(l => `
        <div class="card" style="margin-bottom:10px; border-left:4px solid var(--amber);" id="least-confident">
          <p style="margin:0;"><strong>${escapeHtml(recById(l.recId).component)}:</strong> ${escapeHtml(l.note)}</p>
        </div>`).join("");
      const content = `
        <div class="pagehead"><h1>Fit Ratings Explained</h1><p class="sub">A rating describes fit for this project's day-one scale — not a verdict on the technology in general.</p></div>
        <div class="grid cols-3" style="margin-bottom:22px;">${keyCards}</div>
        <div class="grouphead">🔴 Consider carefully (${STACK.recommendations.filter(r => r.fit === "red").length})</div>
        <div class="card" style="margin-bottom:18px; padding:6px 20px;">${byFit("red")}</div>
        <div class="grouphead">🟡 Good fit (${STACK.recommendations.filter(r => r.fit === "amber").length})</div>
        <div class="card" style="margin-bottom:18px; padding:6px 20px;">${byFit("amber")}</div>
        <div class="grouphead">🟢 Great fit (${STACK.recommendations.filter(r => r.fit === "green").length})</div>
        <div class="card" style="margin-bottom:22px; padding:6px 20px;">${byFit("green")}</div>
        <div class="pagehead"><h3 style="margin-bottom:8px;">Least confident about</h3></div>
        ${leastConf}`;
      shell("ratings", content);
      after(() => {});
    },

    "learning-path"(after) {
      const rows = STACK.learningOrder.map(l => {
        const r = recById(l.recId);
        return `<div class="phase-row searchable" data-search-text="${escapeHtml(r.component + ' ' + l.why)}" id="learn-${l.recId}">
          <div class="phase-num">${l.n}</div>
          <div style="flex:1;">
            <h4>${escapeHtml(r.component)} <span style="font-weight:400;color:var(--muted);">— ${escapeHtml(r.tech)}</span></h4>
            <div class="proves">${escapeHtml(l.why)}</div>
            ${promptRow(r.prompt)}
          </div>
        </div>`;
      }).join("");
      const content = `
        <div class="pagehead"><h1>What to Learn First</h1><p class="sub">Six steps, in order, with a copy-ready prompt for each one.</p></div>
        <div class="card" style="margin-bottom:18px;">${rows}</div>
        ${figureBlock("ladder", "Learning order as a ladder")}`;
      shell("learning-path", content);
      after(() => renderSvgFigure("frame-ladder", "ladder", false, "btn-ladder", "Learning order as a ladder", "interp-ladder", STACK.interpretations.learningPath));
    },

    alternatives(after) {
      const rows = STACK.alternatives.map(a => {
        const r = recById(a.recId);
        return `<tr class="searchable" id="alt-${a.recId}" data-search-text="${escapeHtml(r.component + ' ' + a.alt + ' ' + a.whyNot)}">
          <td><strong>${escapeHtml(r.component)}</strong><div style="font-size:11.5px;color:var(--muted);">chose: ${escapeHtml(r.tech)}</div></td>
          <td>${escapeHtml(a.alt)}</td>
          <td>${escapeHtml(a.whyNot)}</td>
        </tr>`;
      }).join("");
      const content = `
        <div class="pagehead"><h1>Alternatives Considered</h1><p class="sub">What else was on the table for each row, and why it lost.</p></div>
        <div class="card" style="padding:0; overflow:auto; margin-bottom:18px;">
          <table class="comp-table"><thead><tr><th>Component</th><th>Alternative</th><th>Why not</th></tr></thead><tbody>${rows}</tbody></table>
        </div>
        <div class="card"><p style="margin:0;">${escapeHtml(STACK.interpretations.alternatives)}</p></div>`;
      shell("alternatives", content);
      after(() => {});
    },

    "lock-in"(after) {
      const rows = STACK.lockIn.map(l => {
        const r = recById(l.recId);
        return `<tr class="searchable" id="lock-${l.recId}" data-search-text="${escapeHtml(r.component + ' ' + l.difficulty + ' ' + l.why)}">
          <td><strong>${escapeHtml(r.component)}</strong><div style="font-size:11.5px;color:var(--muted);">${escapeHtml(r.tech)}</div></td>
          <td><span class="difficulty ${l.difficulty}">${l.difficulty}</span></td>
          <td>${escapeHtml(l.why)}</td>
        </tr>`;
      }).join("");
      const content = `
        <div class="pagehead"><h1>How Hard to Undo</h1><p class="sub">Every decision is reversible eventually — this is what it would cost.</p></div>
        <div class="card" style="padding:0; overflow:auto; margin-bottom:18px;">
          <table class="comp-table"><thead><tr><th>Component</th><th>Difficulty</th><th>Why</th></tr></thead><tbody>${rows}</tbody></table>
        </div>
        ${figureBlock("lockscale", "Lock-in scale")}`;
      shell("lock-in", content);
      after(() => renderSvgFigure("frame-lockscale", "lockscale", false, "btn-lockscale", "Lock-in scale", "interp-lockscale", STACK.interpretations.lockIn));
    },

    topology(after) {
      const listHTML = ids => `<ul class="notlist">${ids.map(id => {
        const r = recById(id);
        return `<li style="background:var(--card); border-left-color:var(--border);"><strong>${escapeHtml(r.component)}</strong> — ${escapeHtml(r.tech)}</li>`;
      }).join("")}</ul>`;
      const content = `
        <div class="pagehead"><h1>What Runs Where</h1><p class="sub">What lives in your repo versus what runs on infrastructure you don't own.</p></div>
        <div class="grid cols-2" style="margin-bottom:18px;">
          <div class="card"><h3 style="margin-top:0; color:var(--green); font-size:14px;">Your code</h3>${listHTML(STACK.topology.yourCode)}</div>
          <div class="card"><h3 style="margin-top:0; color:var(--amber); font-size:14px;">Someone else's infrastructure</h3>${listHTML(STACK.topology.someoneElses)}</div>
        </div>
        ${figureBlock("topology", "Topology map")}
        <div class="card"><p style="margin:0;">${escapeHtml(STACK.topology.note)}</p></div>`;
      shell("topology", content);
      after(() => renderSvgFigure("frame-topology", "topology", false, "btn-topology", "Topology map", "interp-topology", STACK.interpretations.topology));
    },

    appendix(after) {
      const items = STACK.notTold.map(t => `<li class="searchable" data-search-text="${escapeHtml(t)}">${escapeHtml(t)}</li>`).join("");
      const leastConf = STACK.leastConfident.map(l => `
        <div class="card" style="margin-bottom:10px; border-left:4px solid var(--amber);">
          <p style="margin:0;"><strong>${escapeHtml(recById(l.recId).component)}:</strong> ${escapeHtml(l.note)}</p>
        </div>`).join("");
      const content = `
        <div class="pagehead"><h1>Appendix</h1><p class="sub">What this document does not tell you, said plainly — plus the ratings we're least confident about.</p></div>
        <ul class="notlist" style="margin-bottom:22px;">${items}</ul>
        <div class="pagehead"><h3 style="margin-bottom:8px;">Least confident about</h3></div>
        ${leastConf}
        <div class="card" style="margin-top:14px;"><p style="margin:0;">Full detail in <code>project-blueprint/tech-stack.md</code>. System context in <code>project-blueprint/architecture.md</code>.</p></div>`;
      shell("appendix", content);
      after(() => {});
    }
  };

  function renderSectionPage(id) {
    const sec = STACK.sections.find(s => s.id === id);
    document.title = (sec ? sec.title : id) + " — " + STACK.meta.title;
    const pending = [];
    builders[id](fn => pending.push(fn));
    initCommon(id);
    pending.forEach(fn => fn());
  }

  /* ============================== COMMAND CENTER ============================== */
  function tileMeta(id) {
    const counts = { green: 0, amber: 0, red: 0 };
    STACK.recommendations.forEach(r => counts[r.fit]++);
    switch (id) {
      case "summary": return { count: counts.green + "🟢 " + counts.amber + "🟡 " + counts.red + "🔴", kind: "fitbar" };
      case "recommendations": return { count: STACK.recommendations.length + " recommendations", kind: "fitbands" };
      case "ratings": return { count: counts.red + " to watch closely", kind: "keys" };
      case "learning-path": return { count: STACK.learningOrder.length + " steps", kind: "ladder" };
      case "alternatives": return { count: STACK.alternatives.length + " alternatives weighed", kind: "compare" };
      case "lock-in": return { count: STACK.lockIn.filter(l => l.difficulty === "hard").length + " hard to undo", kind: "lockscale" };
      case "topology": return { count: STACK.topology.yourCode.length + " in your repo, " + STACK.topology.someoneElses.length + " hosted", kind: "topology" };
      case "appendix": return { count: STACK.notTold.length + " open gaps", kind: "doc" };
    }
  }

  function renderIndex() {
    document.title = "Command Center — " + STACK.meta.title;
    const descByStatic = {
      summary: "The fit-rating key, the headline risk, and the paragraph this document is built from.",
      recommendations: "One real technology per component, grouped by what it actually is.",
      ratings: "What 🟢🟡🔴 mean here specifically, and which ratings we're least sure of.",
      "learning-path": "Six things to learn, in order, each with a copy-ready prompt.",
      alternatives: "What else was on the table for each row, and why it lost.",
      "lock-in": "How expensive each decision is to walk back later.",
      topology: "What runs in your own repo versus on infrastructure you don't own.",
      appendix: "What this document does not tell you, said plainly."
    };
    const tiles = STACK.sections.map(s => {
      const m = tileMeta(s.id);
      return `<a class="tile" href="${s.file}">
        <div class="preview">${ILLUSTRATIONS[m.kind](true)}</div>
        <h3>${s.title}</h3>
        <p>${descByStatic[s.id]}</p>
        <span class="count">${m.count}</span>
      </a>`;
    }).join("");

    document.getElementById("app").innerHTML = `
      ${topbarHTML("")}
      <div class="wrap">
        <div class="pagehead">
          <h1>${STACK.meta.title}</h1>
          <p class="sub">${STACK.meta.tagline}</p>
        </div>
        <div class="card" style="margin-bottom:22px; border-left:4px solid var(--red);">
          <p style="margin:0;"><strong>Where this stack is most likely to break:</strong> ${escapeHtml(STACK.headline)}</p>
        </div>
        <div class="tilegrid">${tiles}</div>
      </div>
      ${askPanelHTML()}${modalHTML()}`;
    initCommon("");
  }

  return { renderSectionPage, renderIndex, search, _rerenderFigures: rerenderFigures };
})();
