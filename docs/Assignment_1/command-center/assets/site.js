(function () {
  const TABS = [
    { id: "overview", label: "Overview", href: "index.html" },
    { id: "outcomes", label: "Outcomes", href: "02-outcomes.html" },
    { id: "users", label: "Users & Use Case", href: "03-users.html" },
    { id: "guardrails", label: "Guardrails", href: "04-guardrails.html" },
    { id: "systems", label: "Systems", href: "05-systems.html" },
    { id: "pm", label: "Project Management", href: "06-pm.html" },
    { id: "agents", label: "AI Agents", href: "07-agents.html" },
    { id: "kb", label: "Knowledge Base", href: "08-kb.html" },
    { id: "datamodel", label: "Data Model", href: "09-datamodel.html" }
  ];

  const MODE_KEY = "cc-mode";
  const NOTES_KEY = "cc-kb-notes";

  function getMode() { return localStorage.getItem(MODE_KEY) === "sample" ? "sample" : "real"; }
  function setMode(m) { localStorage.setItem(MODE_KEY, m); location.reload(); }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmtDate(iso) {
    if (!iso) return "Not yet scheduled";
    return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }
  function fmtDateTime(iso) {
    if (!iso) return "unknown";
    return new Date(iso).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }
  function fmtRelativeChecked(iso) {
    if (!iso) return "never checked";
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    return Math.round(hrs / 24) + "d ago";
  }
  function currentRelease(releases) {
    if (!releases.length || !releases[0].start) return "unscheduled";
    const now = Date.now();
    for (const r of releases) {
      if (r.start && r.end && now >= new Date(r.start + "T00:00:00").getTime() && now < new Date(r.end + "T00:00:00").getTime()) return r.id;
    }
    if (now < new Date(releases[0].start + "T00:00:00").getTime()) return null;
    return "done";
  }
  const statusLabel = s => ({ unknown: "Unknown", connected: "Connected", not_connected: "Not connected", error: "Error" }[s] || s);
  const storyStatusLabel = s => ({ not_started: "Not started", in_progress: "In progress", done: "Done" }[s] || s);
  const byId = (arr, id) => arr.find(x => x.id === id);

  /* ============================== SHELL ============================== */
  function topbarHTML(currentId, mode) {
    const tabs = TABS.map(t => t.id === currentId
      ? `<a class="current" href="${t.href}">${t.label}</a>`
      : `<a href="${t.href}">${t.label}</a>`).join("");
    return `
    <div class="topbar">
      <div class="brand">PowerBI Blueprint<small>Command Center</small></div>
      <div class="tabbar">${tabs}</div>
      <div class="datatoggle">
        <span class="modelabel" data-real>Real</span>
        <label class="switch"><input type="checkbox" id="modeSwitch" ${mode === "sample" ? "checked" : ""}><span class="track"></span></label>
        <span class="modelabel" data-sample>Sample</span>
      </div>
    </div>`;
  }
  function sampleBannerHTML(mode) {
    if (mode !== "sample") return "";
    return `<div class="samplebanner"><b>SAMPLE DATA</b> — believable made-up data so you can see the shape of this tab. Switch to Real to see what the project has actually produced.</div>`;
  }
  function dataAgeHTML(mode, data) {
    if (mode === "sample") {
      return `<div class="samplebanner" style="background:var(--slate-bg); color:var(--muted); border-color:var(--border);">Sample data — not read from .colaberry/manifest.json, so it carries no live timestamp.</div>`;
    }
    if (!data.manifestGeneratedAt) {
      return `<div class="samplebanner" style="background:var(--red-bg); color:var(--red); border-color:var(--red);"><b>No data timestamp</b> — .colaberry/manifest.json did not provide generated_at.</div>`;
    }
    const ageMs = Date.now() - new Date(data.manifestGeneratedAt).getTime();
    const ageDays = ageMs / 86400000;
    const ageLabel = ageDays < 1 ? "less than a day old" : `${Math.floor(ageDays)} day${Math.floor(ageDays) === 1 ? "" : "s"} old`;
    if (ageDays > 7) {
      return `<div class="samplebanner" style="background:var(--red-bg); color:var(--red); border-color:var(--red);"><b>Data is stale</b> — generated ${fmtDateTime(data.manifestGeneratedAt)} (${ageLabel}), over the 7-day freshness limit.</div>`;
    }
    return `<div class="samplebanner" style="background:var(--slate-bg); color:var(--muted); border-color:var(--border);">Data as of ${fmtDateTime(data.manifestGeneratedAt)} (${ageLabel}) — from .colaberry/manifest.json.</div>`;
  }
  function loadErrorHTML(err) {
    const isFileProtocol = location.protocol === "file:";
    return `
    <div class="pagehead"><h1>Could not load project data</h1><p class="sub">Real mode reads .colaberry/plan.json, .colaberry/progress.json, and .colaberry/manifest.json at runtime. That read failed, so nothing below is fabricated to fill the gap.</p></div>
    <div class="card">
      <div class="samplebanner" style="background:var(--red-bg); color:var(--red); border-color:var(--red);"><b>Load error</b> — ${escapeHtml(err.message)}</div>
      ${isFileProtocol ? `
      <p style="font-size:13.5px;">This page was opened directly from disk (<code>file://</code>), and browsers block <code>fetch()</code> of local JSON files under that protocol. Serve this folder over HTTP instead:</p>
      <ol style="font-size:13.5px;">
        <li>Open a terminal at the repository root (<code>architect-workspace</code>, the folder containing <code>.colaberry/</code>).</li>
        <li>Run: <code>python -m http.server 8000</code></li>
        <li>Open: <code>http://localhost:8000/docs/Assignment_1/command-center/index.html</code></li>
      </ol>` : `<p style="font-size:13.5px;">Confirm the three files exist under <code>.colaberry/</code> at the repository root and that this page is being served over HTTP from that same repository.</p>`}
      <p style="font-size:13.5px;">Sample mode does not need these files — the toggle above still works.</p>
    </div>`;
  }
  function modalShellHTML() {
    return `<div class="modalbg" id="modalBg"><div class="modalpanel" id="modalPanel"></div></div>`;
  }
  function openModal(title, sub, bodyHtml) {
    document.getElementById("modalPanel").innerHTML =
      `<button class="modalclose" id="modalCloseBtn">✕</button><h2>${escapeHtml(title)}</h2>` +
      (sub ? `<p class="modalsub">${sub}</p>` : "") + bodyHtml;
    document.getElementById("modalBg").classList.add("open");
  }
  function closeModal() { document.getElementById("modalBg").classList.remove("open"); }

  /* ============================== DRILLDOWN DETAIL ============================== */
  function reqListHtml(ids, requirements) {
    return `<ul>${ids.map(id => { const r = byId(requirements, id); return `<li><code>${id}</code> — ${escapeHtml(r ? r.text : "")}</li>`; }).join("")}</ul>`;
  }
  function openDrill(key, data) {
    const [type, id] = key.split("::");
    if (type === "story") {
      const s = byId(data.stories, id);
      const rel = byId(data.releases, s.release);
      openModal(`${s.id} — ${s.title}`, `Owned by ${escapeHtml(s.owner)}`, `
        <dl>
          <dt>Release</dt><dd>${rel.id} — ${escapeHtml(rel.name)} (${fmtDate(rel.start)} → ${fmtDate(rel.end)})</dd>
          <dt>Due</dt><dd>${fmtDate(s.due)}</dd>
          <dt>Status</dt><dd><span class="statuspill ${s.status}">${storyStatusLabel(s.status)}</span></dd>
          <dt>Related requirements</dt><dd>${reqListHtml(s.reqRefs || [], data.requirements)}</dd>
        </dl>`);
    } else if (type === "req") {
      const r = byId(data.requirements, id);
      const stories = data.stories.filter(s => (s.reqRefs || []).includes(id));
      openModal(r.id, `${r.type} · ${r.priority}${data.guardrailIds.includes(r.id) ? " · GUARDRAIL" : ""}`, `
        <dl>
          <dt>Requirement</dt><dd>${escapeHtml(r.text)}</dd>
          <dt>Served by</dt><dd>${stories.length ? stories.map(s => `<code>${s.id}</code> ${escapeHtml(s.title)}`).join("<br>") : "No story currently references this requirement."}</dd>
        </dl>`);
    } else if (type === "system") {
      const s = byId(data.systems, id);
      openModal(s.name, "External system", `
        <dl>
          <dt>Status</dt><dd><span class="syslabel ${s.status}">${statusLabel(s.status)}</span></dd>
          <dt>Last checked</dt><dd>${fmtRelativeChecked(s.lastChecked)}</dd>
          <dt>Why it's here</dt><dd>REQ-009 — orchestration and storage of workflow inputs/outputs runs through Outlook, Power Automate, SharePoint, AI services, and Power BI.</dd>
        </dl>`);
    } else if (type === "release") {
      const r = byId(data.releases, id);
      const stories = data.stories.filter(s => s.release === id);
      openModal(`${r.id} — ${r.name}`, `${fmtDate(r.start)} → ${fmtDate(r.end)}`, `
        <dl><dt>Stories in this release</dt><dd>${stories.map(s => `<code>${s.id}</code> ${escapeHtml(s.title)} — <span class="statuspill ${s.status}">${storyStatusLabel(s.status)}</span>`).join("<br>")}</dd></dl>`);
    } else if (type === "entity") {
      const e = byId(data.dataModel, id);
      openModal(e.name, escapeHtml(e.purpose), `
        <dl>
          <dt>Fields</dt><dd><ul>${e.fields.map(f => `<li><code>${escapeHtml(f)}</code></li>`).join("")}</ul></dd>
          <dt>Relationships</dt><dd>${e.relates.length ? e.relates.map(r => `${r.phrase} <code>${r.to}</code>`).join("<br>") : "None yet."}</dd>
          <dt>From requirements</dt><dd>${reqListHtml(e.reqRefs, data.requirements)}</dd>
        </dl>`);
    } else if (type === "role") {
      const stories = data.stories.filter(s => s.owner === id);
      const skills = data.agentSkills[id] || [];
      openModal(id, "Story owner", `
        <dl>
          <dt>Owns</dt><dd>${stories.map(s => `<code>${s.id}</code> ${escapeHtml(s.title)}`).join("<br>")}</dd>
          <dt>Skills registered</dt><dd>${skills.length ? skills.map(escapeHtml).join(", ") : "No skills registered yet."}</dd>
        </dl>`);
    }
  }

  function initShell(currentId, data) {
    const sw = document.getElementById("modeSwitch");
    if (sw) sw.addEventListener("change", () => setMode(sw.checked ? "sample" : "real"));
    document.getElementById("modalBg").addEventListener("click", e => { if (e.target.id === "modalBg") closeModal(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
    document.addEventListener("click", e => {
      if (e.target.id === "modalCloseBtn") closeModal();
      const drill = e.target.closest("[data-drill]");
      if (drill) openDrill(drill.dataset.drill, data);
    });
  }

  /* ============================== GANTT ============================== */
  function ganttHTML(data) {
    if (!data.scheduleKnown) {
      // No starts_on/ends_on in the plan yet — position bars by relative week number
      // instead of inventing calendar dates.
      const maxWeek = Math.max(1, ...data.releases.map(r => r.weekEnd || 0));
      const rows = data.releases.map(r => {
        const left = ((r.weekStart || 0) / maxWeek) * 100;
        const width = (((r.weekEnd || 0) - (r.weekStart || 0)) / maxWeek) * 100;
        return `<div class="ganttrow">
          <div>${r.id} — ${escapeHtml(r.name)}</div>
          <div class="gantttrack"><div class="ganttbar" data-drill="release::${r.id}" style="left:${left}%; width:${Math.max(width, 4)}%;">${r.stories} stories</div></div>
        </div>`;
      }).join("");
      return `<div class="gantt" style="position:relative;">${rows}</div>
      <p class="cardsub" style="margin-top:2px;">Positioned by relative week number (week 0 = plan start) — <code>starts_on</code>/<code>ends_on</code> aren't set in .colaberry/plan.json yet, so no calendar dates are shown.</p>`;
    }
    const spanStart = new Date(data.releases[0].start + "T00:00:00").getTime();
    const spanEnd = new Date((data.project.demoDate || data.releases[data.releases.length - 1].end) + "T00:00:00").getTime();
    const total = spanEnd - spanStart;
    const pct = iso => Math.max(0, Math.min(100, ((new Date(iso + "T00:00:00").getTime() - spanStart) / total) * 100));
    const rows = data.releases.map(r => {
      const left = pct(r.start), width = pct(r.end) - pct(r.start);
      return `<div class="ganttrow">
        <div>${r.id} — ${escapeHtml(r.name)}</div>
        <div class="gantttrack"><div class="ganttbar" data-drill="release::${r.id}" style="left:${left}%; width:${width}%;">${r.stories} stories</div></div>
      </div>`;
    }).join("");
    let prepRow = "";
    if (data.project.buildEndDate && data.project.demoDate) {
      const prepLeft = pct(data.project.buildEndDate), prepWidth = pct(data.project.demoDate) - prepLeft;
      prepRow = `<div class="ganttrow">
        <div>Demo prep</div>
        <div class="gantttrack"><div class="ganttbar" style="left:${prepLeft}%; width:${prepWidth}%; background:var(--slate); color:var(--bg);">→ ${fmtDate(data.project.demoDate)}</div></div>
      </div>`;
    }
    const todayPct = pct(new Date().toISOString().slice(0, 10));
    const todayLine = todayPct >= 0 && todayPct <= 100 ? `<div class="gantttoday" style="left:${todayPct}%"></div>` : "";
    return `<div class="gantt" style="position:relative;">${rows}${prepRow}${todayLine}</div>`;
  }

  /* ============================== PAGE BUILDERS ============================== */
  const builders = {
    overview(data, mode) {
      const isSample = mode === "sample";
      const tag = isSample ? `<span class="badge-sample">Sample</span>` : "";
      const curRel = currentRelease(data.releases);
      const releaseRows = data.releases.map(r => `
        <div class="releaserow clickcard ${r.id === curRel ? "current" : ""}" data-drill="release::${r.id}">
          <div class="relid">${r.id}</div><div class="relname">${escapeHtml(r.name)}</div>
          <div class="reldates">${fmtDate(r.start)} → ${fmtDate(r.end)}</div>
          ${r.id === curRel ? `<div class="relnow">Current</div>` : ""}
        </div>`).join("");
      const sysRows = data.systems.map(s => `
        <div class="sysrow clickcard" data-drill="system::${s.name}">
          <span class="dot ${s.status}"></span><span class="sysname">${escapeHtml(s.name)}</span>
          <span class="syslabel ${s.status}">${statusLabel(s.status)}</span>
          <span class="lastchecked">${fmtRelativeChecked(s.lastChecked)}</span>
        </div>`).join("");
      const doneCount = data.stories.filter(s => s.status === "done").length;
      const inProgCount = data.stories.filter(s => s.status === "in_progress").length;
      const total = data.stories.length;
      const pct = Math.round((doneCount / total) * 100);
      const guardrails = data.requirements.filter(r => data.guardrailIds.includes(r.id));
      const guardRows = guardrails.map(g => `<div class="grow clickcard" data-drill="req::${g.id}"><span class="gid">${g.id}</span><span class="gtext">${escapeHtml(g.text)}</span></div>`).join("");
      let releaseStatusText;
      if (curRel === "unscheduled") releaseStatusText = "Release order is set (r0 → r4), but calendar dates aren't in the plan yet — this reads exactly what .colaberry/plan.json has.";
      else if (curRel === "done") releaseStatusText = "All planned releases have reached their end date.";
      else if (curRel === null) releaseStatusText = "The first release has not started yet.";
      else releaseStatusText = `You are currently in <b>${curRel}</b>.`;
      const demoText = data.project.demoDate ? `Demo day is ${fmtDate(data.project.demoDate)}.` : "No demo date is scheduled in the plan yet.";
      const selfCheckCard = data.selfCheck && data.selfCheck.length ? `
        <div class="card">
          <h2>This Command Center (STORY-000) ${tag}</h2>
          <p class="cardsub">Read live from .colaberry/progress.json.</p>
          <div class="guardmini">${data.selfCheck.map(c => `<div class="grow"><span class="gid" style="color:${c.passed ? "var(--green)" : "var(--red)"}; background:${c.passed ? "var(--green-bg)" : "var(--red-bg)"};">${c.passed ? "PASS" : "FAIL"}</span><span class="gtext">${escapeHtml(c.text)}</span></div>`).join("")}</div>
        </div>` : "";
      return `
      <div class="pagehead"><h1>Overview</h1><p class="sub">${escapeHtml(data.project.pitch)}</p></div>
      <div class="grid2">
        <div class="card">
          <h2>Release timeline</h2>
          <p class="cardsub">${releaseStatusText} ${demoText}</p>
          <div class="releasestrip">${releaseRows}</div>
        </div>
        <div class="card">
          <h2>What's live right now ${tag}</h2>
          <p class="cardsub">None are connected on day one — that's expected, not a bug.</p>
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
          <p class="cardsub">None are enforced by working code yet on day one.</p>
          <div class="guardmini">${guardRows}</div>
        </div>
      </div>
      ${selfCheckCard}
      <p class="footnote">${isSample ? "Sample snapshot — for shape only." : "Real mode — reflects what this project has actually produced so far."}</p>`;
    },

    outcomes(data) {
      return `
      <div class="pagehead"><h1>Outcomes</h1><p class="sub">The numbers this project has to move.</p></div>
      <div class="card">
        <div class="emptystate">
          <div class="big">—</div>
          No numeric target is defined in the plan yet.<br>
          This tab looks the same in Sample and Real mode — there's no number to fabricate a shape for.
          As soon as a measure is defined (e.g. "hours to turn a request into a draft"), it gets one card here.
        </div>
      </div>`;
    },

    users(data) {
      const cards = data.roles.map(role => {
        const stories = data.stories.filter(s => s.owner === role);
        return `<div class="card rolecard clickcard" data-drill="role::${role}">
          <h3>${escapeHtml(role)}</h3>
          <p class="rolestories">Appears in the plan as "As a ${escapeHtml(role.toLowerCase())}, I want …" — trying to get ${stories.length} stor${stories.length === 1 ? "y" : "ies"} done.</p>
          <div class="chiprow">${stories.map(s => `<span class="chip">${s.id}</span>`).join("")}</div>
        </div>`;
      }).join("");
      return `
      <div class="pagehead"><h1>Users &amp; Use Case</h1><p class="sub">Who this is for, taken directly from the roles in the user stories.</p></div>
      <div class="rolegrid">${cards}</div>`;
    },

    guardrails(data) {
      const guardrails = data.requirements.filter(r => data.guardrailIds.includes(r.id));
      const cards = guardrails.map(g => `
        <div class="card clickcard" data-drill="req::${g.id}">
          <h2><span class="gid">${g.id}</span> ${g.type} · ${g.priority}</h2>
          <p style="margin:10px 0 14px; font-size:13.5px;">${escapeHtml(g.text)}</p>
          <div class="samplebanner" style="background:var(--red-bg); color:var(--red); border-color:var(--red);">
            <b>Not enforced yet</b> — no code in this build currently checks this guardrail. This status doesn't change with the Sample/Real switch: it's a fact about the code, not a demo number.
          </div>
        </div>`).join("");
      return `
      <div class="pagehead"><h1>Guardrails</h1><p class="sub">The promises this system makes and never breaks.</p></div>
      ${cards || `<div class="card"><div class="emptystate">The plan has no SAFE requirement — that would be worth fixing before building further.</div></div>`}`;
    },

    systems(data) {
      const rows = data.systems.map(s => `
        <div class="sysrow clickcard" data-drill="system::${s.name}" style="padding:10px 0; border-bottom:1px solid var(--border);">
          <span class="dot ${s.status}"></span><span class="sysname">${escapeHtml(s.name)}</span>
          <span class="syslabel ${s.status}">${statusLabel(s.status)}</span>
          <span class="lastchecked">${fmtRelativeChecked(s.lastChecked)}</span>
        </div>`).join("");
      return `
      <div class="pagehead"><h1>Systems</h1><p class="sub">What this connects to. Grey means unknown — never fake green.</p></div>
      <div class="card"><div class="syslist">${rows}</div></div>`;
    },

    pm(data) {
      const sortKey = s => s.due || `zz-${s.release}-${s.id}`;
      const rows = data.stories.slice().sort((a, b) => sortKey(a).localeCompare(sortKey(b))).map(s => `
        <tr class="clickcard" data-drill="story::${s.id}">
          <td><code>${s.id}</code></td><td>${escapeHtml(s.title)}</td><td>${s.release}</td>
          <td>${fmtDate(s.due)}</td><td>${escapeHtml(s.owner)}</td>
          <td><span class="statuspill ${s.status}">${storyStatusLabel(s.status)}</span></td>
        </tr>`).join("");
      return `
      <div class="pagehead"><h1>Project Management</h1><p class="sub">${data.project.demoDate ? `Demo day is ${fmtDate(data.project.demoDate)}.` : "No demo date is scheduled in the plan yet."}</p></div>
      <div class="card">${ganttHTML(data)}</div>
      <div class="card">
        <h2>All tasks</h2>
        <table class="tasktable"><thead><tr><th>Story</th><th>Title</th><th>Release</th><th>Due</th><th>Owner</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>
      </div>`;
    },

    agents(data, mode) {
      const isSample = mode === "sample";
      const tag = isSample ? `<span class="badge-sample">Sample</span>` : "";
      const cards = data.roles.map(role => {
        const stories = data.stories.filter(s => s.owner === role);
        const skills = data.agentSkills[role] || [];
        return `<div class="card rolecard clickcard" data-drill="role::${role}">
          <h3>${escapeHtml(role)} ${tag}</h3>
          <div class="chiprow">${stories.map(s => `<span class="chip">${s.id}</span>`).join("")}</div>
          <div class="chiprow">${skills.length ? skills.map(sk => `<span class="chip">${escapeHtml(sk)}</span>`).join("") : `<span class="chip muted">No skills registered yet</span>`}</div>
        </div>`;
      }).join("");
      return `
      <div class="pagehead"><h1>AI Agents</h1><p class="sub">These are story <b>owners</b>, not scoped AI agents — the plan doesn't carry a scoped agent roster yet. A job title shown here is a placeholder for a future agent, not a claim that one exists.</p></div>
      <div class="rolegrid">${cards}</div>`;
    },

    kb(data) {
      const notes = JSON.parse(localStorage.getItem(NOTES_KEY) || "[]");
      const reqRows = data.requirements.map(r => `<div class="reqrow clickcard" data-drill="req::${r.id}" data-kb-item data-kb-text="${escapeHtml((r.id + " " + r.text).toLowerCase())}">
        <span class="reqid">${r.id}</span><span class="reqtag ${r.type}">${r.type}</span><span>${escapeHtml(r.text)}</span>
      </div>`).join("");
      const storyRows = data.stories.map(s => `<div class="reqrow clickcard" data-drill="story::${s.id}" data-kb-item data-kb-text="${escapeHtml((s.id + " " + s.title + " " + s.owner).toLowerCase())}">
        <span class="reqid">${s.id}</span><span>${escapeHtml(s.title)} — owned by ${escapeHtml(s.owner)}, release ${s.release}</span>
      </div>`).join("");
      const noteRows = notes.map(n => `<div class="kbnote"><div style="flex:1;">${escapeHtml(n.text)}</div><div class="kbnotewhen">${new Date(n.createdAt).toLocaleDateString()}</div></div>`).join("");
      return `
      <div class="pagehead"><h1>Knowledge Base</h1><p class="sub">Everything the project knows about itself — requirements, stories, decisions, and your own notes.</p></div>
      <div class="card">
        <h2>Ask the knowledge base</h2>
        <p class="cardsub">Keyword search over requirements and stories on this page — deterministic, not a guess.</p>
        <input class="kbsearch" id="kbAsk" placeholder="e.g. field mapping, approval, publication…">
        <div id="kbAnswer"></div>
      </div>
      <div class="card"><h2>Requirements (${data.requirements.length})</h2><div id="kbReqList">${reqRows}</div></div>
      <div class="card"><h2>Stories (${data.stories.length})</h2><div id="kbStoryList">${storyRows}</div></div>
      <div class="card">
        <h2>Decisions</h2>
        <div class="emptystate">No decisions logged yet.</div>
      </div>
      <div class="card">
        <h2>Notes</h2>
        <p class="cardsub">Stored in this browser. Add as you go — this list is never regenerated.</p>
        <div id="kbNotes">${noteRows || `<div class="emptystate">No notes yet.</div>`}</div>
        <form class="notesform" id="kbNoteForm"><input id="kbNoteInput" placeholder="Add a note…" required><button type="submit">Add</button></form>
      </div>`;
    },

    datamodel(data) {
      const cards = data.dataModel.map(e => `
        <div class="card entitycard clickcard" data-drill="entity::${e.id}">
          <h3>${e.name}</h3>
          <p class="entitypurpose">${escapeHtml(e.purpose)}</p>
          <div class="fieldcount">${e.fields.length} fields</div>
          <ul class="relatelist">${e.relates.map(r => `<li>${r.phrase} <code>${r.to}</code></li>`).join("")}</ul>
        </div>`).join("");
      return `
      <div class="pagehead"><h1>Data Model</h1><p class="sub">A starting point derived from the requirements — not created as real tables yet. Review before anything gets built.</p></div>
      <div class="samplebanner"><b>Nothing created yet</b> — this is a proposal for review, not a live schema.</div>
      <div class="entitygrid">${cards}</div>
      <p class="footnote">${escapeHtml(data.dataModelNote)}</p>`;
    }
  };

  function initKb() {
    const form = document.getElementById("kbNoteForm");
    if (form) form.addEventListener("submit", e => {
      e.preventDefault();
      const input = document.getElementById("kbNoteInput");
      const text = input.value.trim();
      if (!text) return;
      const notes = JSON.parse(localStorage.getItem(NOTES_KEY) || "[]");
      notes.push({ text, createdAt: new Date().toISOString() });
      localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
      location.reload();
    });
    const ask = document.getElementById("kbAsk");
    if (ask) ask.addEventListener("input", () => {
      const q = ask.value.trim().toLowerCase();
      const answer = document.getElementById("kbAnswer");
      if (!q) { answer.innerHTML = ""; return; }
      const reqItems = Array.from(document.querySelectorAll("#kbReqList [data-kb-item]"));
      const storyItems = Array.from(document.querySelectorAll("#kbStoryList [data-kb-item]"));
      const reqHit = reqItems.find(el => el.dataset.kbText.includes(q));
      const storyHit = storyItems.find(el => el.dataset.kbText.includes(q));
      if (reqHit) {
        answer.innerHTML = `<div class="kbanswer"><div class="kbsrc">From: Guardrails / Overview (requirements)</div>${reqHit.innerHTML}</div>`;
      } else if (storyHit) {
        answer.innerHTML = `<div class="kbanswer"><div class="kbsrc">From: Project Management (stories)</div>${storyHit.innerHTML}</div>`;
      } else {
        answer.innerHTML = `<div class="kbanswer">I can't answer that from the data on this page — try a different word, or add a note below.</div>`;
      }
    });
  }

  async function render(pageId) {
    const mode = getMode();
    let data, err = null;
    if (mode === "sample") {
      data = window.CommandCenterData.SAMPLE_DATA;
    } else {
      try {
        const { plan, progress, manifest } = await window.CommandCenterData.loadRuntimeFiles();
        data = window.CommandCenterData.buildRealData(plan, progress, manifest);
      } catch (e) {
        err = e;
      }
    }

    if (err) {
      document.getElementById("app").innerHTML =
        topbarHTML(pageId, mode) + `<div class="wrap">${loadErrorHTML(err)}</div>` + modalShellHTML();
      initShellChrome();
      return;
    }

    document.getElementById("app").innerHTML =
      topbarHTML(pageId, mode) +
      `<div class="wrap">${sampleBannerHTML(mode)}${dataAgeHTML(mode, data)}${builders[pageId](data, mode)}</div>` +
      modalShellHTML();
    initShell(pageId, data);
    if (pageId === "kb") initKb();
  }

  function initShellChrome() {
    const sw = document.getElementById("modeSwitch");
    if (sw) sw.addEventListener("change", () => setMode(sw.checked ? "sample" : "real"));
  }

  window.CC = { render };
})();
