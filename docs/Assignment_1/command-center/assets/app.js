(function () {
  const TABS = [
    { id: "overview", label: "Overview", href: "index.html" },
    { id: "outcomes", label: "Outcomes" },
    { id: "users", label: "Users & Use Case" },
    { id: "guardrails", label: "Guardrails" },
    { id: "systems", label: "Systems" },
    { id: "pm", label: "Project Management" },
    { id: "agents", label: "AI Agents" },
    { id: "kb", label: "Knowledge Base" },
    { id: "datamodel", label: "Data Model" }
  ];

  const MODE_KEY = "cc-mode";
  function getMode() { return localStorage.getItem(MODE_KEY) === "sample" ? "sample" : "real"; }
  function setMode(m) { localStorage.setItem(MODE_KEY, m); render(); }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function fmtRelativeChecked(iso) {
    if (!iso) return "never checked";
    const d = new Date(iso);
    const mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    return Math.round(hrs / 24) + "d ago";
  }

  function currentRelease(releases) {
    const now = Date.now();
    for (const r of releases) {
      const start = new Date(r.start + "T00:00:00").getTime();
      const end = new Date(r.end + "T00:00:00").getTime();
      if (now >= start && now < end) return r.id;
    }
    if (now < new Date(releases[0].start + "T00:00:00").getTime()) return null;
    return "done";
  }

  function statusLabel(status) {
    return { unknown: "Unknown", connected: "Connected", not_connected: "Not connected", error: "Error" }[status] || status;
  }
  function storyStatusLabel(status) {
    return { not_started: "Not started", in_progress: "In progress", done: "Done" }[status] || status;
  }

  function topbarHTML(currentId) {
    const tabs = TABS.map(t => {
      if (t.id === currentId) return `<a class="current" href="${t.href || '#'}">${t.label}</a>`;
      if (t.href) return `<a href="${t.href}">${t.label}</a>`;
      return `<span class="disabled" title="Built after the Overview tab is reviewed">${t.label}</span>`;
    }).join("");
    const mode = getMode();
    return `
    <div class="topbar">
      <div class="brand">PowerBI Blueprint<small>Command Center</small></div>
      <div class="tabbar">${tabs}</div>
      <div class="datatoggle">
        <span class="modelabel" data-real>Real</span>
        <label class="switch">
          <input type="checkbox" id="modeSwitch" ${mode === "sample" ? "checked" : ""}>
          <span class="track"></span>
        </label>
        <span class="modelabel" data-sample>Sample</span>
      </div>
    </div>`;
  }

  function sampleBannerHTML(mode) {
    if (mode !== "sample") return "";
    return `<div class="samplebanner"><b>SAMPLE DATA</b> — this is believable made-up data so you can see the shape of the Command Center. Switch to Real to see what the project has actually produced.</div>`;
  }

  function overviewHTML(data, mode) {
    const isSample = mode === "sample";
    const tag = isSample ? `<span class="badge-sample">Sample</span>` : "";
    const curRel = currentRelease(data.releases);

    const releaseRows = data.releases.map(r => {
      const isCurrent = r.id === curRel;
      return `<div class="releaserow ${isCurrent ? "current" : ""}">
        <div class="relid">${r.id}</div>
        <div class="relname">${escapeHtml(r.name)}</div>
        <div class="reldates">${fmtDate(r.start)} → ${fmtDate(r.end)}</div>
        ${isCurrent ? `<div class="relnow">Current</div>` : ""}
      </div>`;
    }).join("");

    const sysRows = data.systems.map(s => `
      <div class="sysrow">
        <span class="dot ${s.status}"></span>
        <span class="sysname">${escapeHtml(s.name)}</span>
        <span class="syslabel ${s.status}">${statusLabel(s.status)}</span>
        <span class="lastchecked">${fmtRelativeChecked(s.lastChecked)}</span>
      </div>`).join("");

    const doneCount = data.stories.filter(s => s.status === "done").length;
    const inProgCount = data.stories.filter(s => s.status === "in_progress").length;
    const total = data.stories.length;
    const pct = Math.round((doneCount / total) * 100);

    const guardrails = data.requirements.filter(r => data.guardrailIds.includes(r.id));
    const guardRows = guardrails.map(g => `
      <div class="grow">
        <span class="gid">${g.id}</span>
        <span class="gtext">${escapeHtml(g.text)}</span>
      </div>`).join("");

    return `
    <div class="pagehead">
      <h1>Overview</h1>
      <p class="sub">${escapeHtml(data.project.pitch)}</p>
    </div>

    <div class="grid2">
      <div class="card">
        <h2>Release timeline ${curRel ? "" : ""}</h2>
        <p class="cardsub">${curRel && curRel !== "done" ? `You are currently in <b>${curRel}</b>.` : curRel === "done" ? "All planned releases have reached their end date." : "The first release has not started yet."} Demo day is ${fmtDate(data.project.demoDate)}.</p>
        <div class="releasestrip">${releaseRows}</div>
      </div>

      <div class="card">
        <h2>What's live right now ${tag}</h2>
        <p class="cardsub">External systems this project depends on. None are connected on day one — that's expected, not a bug.</p>
        <div class="syslist">${sysRows}</div>
      </div>
    </div>

    <div class="grid2">
      <div class="card">
        <h2>Delivery status ${tag}</h2>
        <p class="cardsub">Stories complete across all releases.</p>
        <div class="progressstat"><span class="num">${doneCount}</span><span class="of">of ${total} stories done${inProgCount ? ` · ${inProgCount} in progress` : ""}</span></div>
        <div class="bar"><div style="width:${pct}%"></div></div>
      </div>

      <div class="card">
        <h2>Guardrails at a glance</h2>
        <p class="cardsub">The promises this system makes (SAFE requirements). None are enforced by working code yet on day one.</p>
        <div class="guardmini">${guardRows}</div>
      </div>
    </div>

    <p class="footnote">
      ${isSample ? `Sample snapshot generated ${fmtDate(data.generatedAt ? data.generatedAt.slice(0, 10) : null)}.` : "Real mode — reflects what this project has actually produced so far."}
      Remaining tabs (Outcomes, Users &amp; Use Case, Guardrails, Systems, Project Management, AI Agents, Knowledge Base, Data Model) are built next, after this Overview tab is reviewed.
    </p>`;
  }

  function render() {
    const mode = getMode();
    const data = window.CommandCenterData.getData(mode);
    document.getElementById("app").innerHTML =
      topbarHTML("overview") +
      `<div class="wrap">${sampleBannerHTML(mode)}${overviewHTML(data, mode)}</div>`;

    const sw = document.getElementById("modeSwitch");
    if (sw) sw.addEventListener("change", () => setMode(sw.checked ? "sample" : "real"));
  }

  document.addEventListener("DOMContentLoaded", render);
})();
