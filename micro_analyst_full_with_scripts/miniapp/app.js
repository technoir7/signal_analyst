// ===============================================================
// Signal-Analyst – Frontend Logic (Option A SAFE VERSION)
// Violent Pulse + Real Tool Usage Patch + Stable Layout
// ===============================================================

const API_URL = "http://localhost:8000/analyze";

// --- DOM HOOKS -------------------------------------------------------

const form = document.getElementById("analyze-form");
const companyNameInput = document.getElementById("company_name");
const companyUrlInput = document.getElementById("company_url");
const focusInput = document.getElementById("focus");
const reportStyleSelect = document.getElementById("report_style");
const demoModeCheckbox = document.getElementById("demo_mode");
const demoDatasetSelect = document.getElementById("demo_dataset");
const analyzeButton = document.getElementById("analyze-button");

const statusText = document.getElementById("status-text");
const cardStatusBadge = document.getElementById("card-status-badge");
const statusDot =
  document.querySelector(".form-footnote .dot") ||
  document.querySelector(".dot--idle") ||
  document.querySelector(".dot") ||
  null;

const latencyValue = document.getElementById("latency-value");
const modeValue = document.getElementById("mode-value");
const reportStatusBadge = document.getElementById("report-status-badge");
const reportMarkdown = document.getElementById("report-markdown");

const cotStatusBadge = document.getElementById("cot-status-badge");
const cotStream = document.getElementById("cot-stream");

const planGrid = document.getElementById("plan-grid");

// Agent pulse + pipeline
const agentPulseEl = document.getElementById("agent-pulse");
const agentPulseLabel = document.getElementById("agent-pulse-label");

const pipelineEl = document.getElementById("pipeline");
const pipelineProgressEl = document.getElementById("pipeline-progress");
const pipelineStepEls = Array.from(document.querySelectorAll(".pipeline-step"));

// MCP routing pills
const mcpPills = {
  web: document.getElementById("mcp-web"),
  seo: document.getElementById("mcp-seo"),
  tech: document.getElementById("mcp-tech"),
  reviews: document.getElementById("mcp-reviews"),
  social: document.getElementById("mcp-social"),
  careers: document.getElementById("mcp-careers"),
  ads: document.getElementById("mcp-ads"),
};

// Command palette
const cmdkBackdrop = document.getElementById("cmdk-backdrop");
const cmdkInput = document.getElementById("cmdk-input");
const cmdkList = document.getElementById("cmdk-list");
const openCommandPaletteBtn = document.getElementById("open-command-palette");

// --- STATUS HELPERS --------------------------------------------------

function setStatus(state, message) {
  if (statusText) statusText.textContent = message || "";

  if (statusDot) {
    statusDot.classList.remove("dot--idle", "dot--running", "dot--error");
    if (state === "idle") statusDot.classList.add("dot--idle");
    else if (state === "running") statusDot.classList.add("dot--running");
    else if (state === "error") statusDot.classList.add("dot--error");
  }

  if (cardStatusBadge) {
    cardStatusBadge.classList.remove(
      "badge-status--neutral",
      "badge-status--active",
      "badge-status--error"
    );
    if (state === "idle") {
      cardStatusBadge.classList.add("badge-status--neutral");
      cardStatusBadge.textContent = "IDLE";
    } else if (state === "running") {
      cardStatusBadge.classList.add("badge-status--active");
      cardStatusBadge.textContent = "RUNNING";
    } else if (state === "error") {
      cardStatusBadge.classList.add("badge-status--error");
      cardStatusBadge.textContent = "ERROR";
    }
  }
}

function setLoadingState(isLoading) {
  if (analyzeButton) analyzeButton.disabled = isLoading;
}

function setReportStatus(state, label) {
  if (!reportStatusBadge) return;
  reportStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--active",
    "badge-status--error"
  );
  if (state === "idle") reportStatusBadge.classList.add("badge-status--neutral");
  else if (state === "running") reportStatusBadge.classList.add("badge-status--active");
  else if (state === "error") reportStatusBadge.classList.add("badge-status--error");

  if (label) {
    reportStatusBadge.textContent = label;
  }
}

function setCotStatus(state, label) {
  if (!cotStatusBadge) return;
  cotStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--active",
    "badge-status--error"
  );
  if (state === "idle") cotStatusBadge.classList.add("badge-status--neutral");
  else if (state === "running") cotStatusBadge.classList.add("badge-status--active");
  else if (state === "error") cotStatusBadge.classList.add("badge-status--error");

  if (label) cotStatusBadge.textContent = label;
}

// --- MARKDOWN RENDERING ----------------------------------------------

function renderMarkdown(text) {
  if (!text) return `<p class="placeholder">No report returned.</p>`;

  const safe = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const lines = safe.split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      closeList();
      continue;
    }

    if (line.startsWith("# ")) {
      closeList();
      html += `<h1>${line.slice(2)}</h1>`;
    } else if (line.startsWith("## ")) {
      closeList();
      html += `<h2>${line.slice(3)}</h2>`;
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${line.slice(2)}</li>`;
    } else {
      closeList();
      html += `<p>${line}</p>`;
    }
  }

  closeList();
  return `<div class="markdown-body">${html}</div>`;
}

function renderReport(reportText) {
  if (!reportMarkdown) return;
  reportMarkdown.innerHTML = renderMarkdown(reportText);
}

// --- UTILITIES -------------------------------------------------------

function containsAny(text, keywords) {
  return keywords.some((kw) => text.includes(kw));
}

async function loadDemoProfile(key) {
  const all = window.DEMO_PROFILES || {};
  const entry = all[key];
  if (!entry) throw new Error(`Demo profile "${key}" not found`);
  return entry;
}

// ---------------------------------------------------------------------
// PLAN + MCP ROUTING
// ---------------------------------------------------------------------

function createPlanPreview({ hasUrl, focus, forceFullPlan = false }) {
  const plan = {
    use_web_scrape: false,
    use_seo_probe: false,
    use_tech_stack: false,
    use_reviews_snapshot: false,
    use_social_snapshot: false,
    use_careers_intel: false,
    use_ads_snapshot: false,
  };

  const lower = (focus || "").toLowerCase();

  if (hasUrl || forceFullPlan) {
    plan.use_web_scrape = true;
    plan.use_seo_probe = true;
    plan.use_tech_stack = true;
  }

  if (containsAny(lower, ["review", "reviews", "customer", "experience"])) {
    plan.use_reviews_snapshot = true;
  }
  if (containsAny(lower, ["social", "twitter", "instagram", "youtube", "tiktok"])) {
    plan.use_social_snapshot = true;
  }
  if (containsAny(lower, ["hiring", "org", "team", "talent", "recruit"])) {
    plan.use_careers_intel = true;
  }
  if (containsAny(lower, ["ads", "advertising", "campaign", "paid", "growth"])) {
    plan.use_ads_snapshot = true;
  }

  if (forceFullPlan) {
    plan.use_reviews_snapshot = true;
    plan.use_social_snapshot = true;
    plan.use_careers_intel = true;
    plan.use_ads_snapshot = true;
  }

  return plan;
}

function renderPlanGrid(plan) {
  if (!planGrid) return;

  const items = [
    ["WEB SCRAPE", "use_web_scrape"],
    ["SEO PROBE", "use_seo_probe"],
    ["TECH STACK", "use_tech_stack"],
    ["REVIEWS", "use_reviews_snapshot"],
    ["SOCIAL", "use_social_snapshot"],
    ["HIRING", "use_careers_intel"],
    ["ADS", "use_ads_snapshot"],
  ];

  planGrid.innerHTML = "";

  for (const [label, key] of items) {
    const pill = document.createElement("div");
    pill.classList.add("pill");
    if (plan[key]) pill.classList.add("pill--on");
    pill.textContent = label;
    planGrid.appendChild(pill);
  }
}

function resetMcpPills() {
  Object.values(mcpPills).forEach((el) => {
    if (!el) return;
    el.classList.remove("pill--on", "pill--error");
  });
}

let currentPlan = null;

function applyMcpPlan(plan) {
  currentPlan = plan || null;
  resetMcpPills();

  if (!plan) return;

  if (plan.use_web_scrape) mcpPills.web?.classList.add("pill--on");
  if (plan.use_seo_probe) mcpPills.seo?.classList.add("pill--on");
  if (plan.use_tech_stack) mcpPills.tech?.classList.add("pill--on");
  if (plan.use_reviews_snapshot) mcpPills.reviews?.classList.add("pill--on");
  if (plan.use_social_snapshot) mcpPills.social?.classList.add("pill--on");
  if (plan.use_careers_intel) mcpPills.careers?.classList.add("pill--on");
  if (plan.use_ads_snapshot) mcpPills.ads?.classList.add("pill--on");
}

function highlightMcpForStage(stageKey) {
  // Start from honest baseline
  applyMcpPlan(currentPlan);

  const map = {
    scrape: ["use_web_scrape", "use_reviews_snapshot"],
    seo: ["use_seo_probe", "use_ads_snapshot"],
    tech: ["use_tech_stack", "use_social_snapshot", "use_careers_intel"],
    synthesis: [],
  };

  const extras = map[stageKey] || [];

  for (const key of extras) {
    if (!currentPlan[key]) continue;
    if (key === "use_web_scrape") mcpPills.web?.classList.add("pill--on");
    if (key === "use_reviews_snapshot") mcpPills.reviews?.classList.add("pill--on");
    if (key === "use_seo_probe") mcpPills.seo?.classList.add("pill--on");
    if (key === "use_ads_snapshot") mcpPills.ads?.classList.add("pill--on");
    if (key === "use_tech_stack") mcpPills.tech?.classList.add("pill--on");
    if (key === "use_social_snapshot") mcpPills.social?.classList.add("pill--on");
    if (key === "use_careers_intel") mcpPills.careers?.classList.add("pill--on");
  }
}

// ---------------------------------------------------------------------
// AGENT PULSE + PIPELINE SIMULATION
// ---------------------------------------------------------------------

const STEP_ORDER = ["scrape", "seo", "tech", "synthesis"];
let pipelineSimTimer = null;
let pipelineSimStart = 0;
let pipelineSimTotalMs = 8000;
let pipelineStagesPlanned = STEP_ORDER.slice();

function derivePipelineStages(plan) {
  if (!plan) return STEP_ORDER.slice();

  const stages = [];

  if (plan.use_web_scrape || plan.use_reviews_snapshot) stages.push("scrape");
  if (plan.use_seo_probe || plan.use_ads_snapshot) stages.push("seo");
  if (
    plan.use_tech_stack ||
    plan.use_social_snapshot ||
    plan.use_careers_intel
  ) {
    stages.push("tech");
  }
  stages.push("synthesis");

  return stages.filter((s, i, arr) => arr.indexOf(s) === i);
}

function stopPipelineSimulation() {
  if (pipelineSimTimer) {
    clearInterval(pipelineSimTimer);
    pipelineSimTimer = null;
  }
}

function setAgentPulseState(state, label) {
  if (!agentPulseEl) return;
  agentPulseEl.classList.remove("idle", "active", "intense");
  agentPulseEl.classList.add(state);
  if (agentPulseLabel && label) agentPulseLabel.textContent = label;
}

function setPipelineRunning(isRunning) {
  if (!pipelineEl) return;
  pipelineEl.classList.toggle("pipeline--running", isRunning);
}

function resetPipeline() {
  for (const el of pipelineStepEls) {
    el.classList.remove("completed", "active", "pending", "error", "just-completed");
    el.classList.add("pending");
  }
  if (pipelineProgressEl) pipelineProgressEl.style.width = "0%";
}

function setPipelineStage(stageKey) {
  const idx = STEP_ORDER.indexOf(stageKey);
  if (idx === -1) return;

  const prevIdx = pipelineStepEls.findIndex((el) =>
    el.classList.contains("active")
  );

  pipelineStepEls.forEach((el, i) => {
    el.classList.remove("completed", "active", "pending", "error");
    if (i < idx) el.classList.add("completed");
    else if (i === idx) el.classList.add("active");
    else el.classList.add("pending");
  });

  const pct = ((idx) / (STEP_ORDER.length - 1)) * 100;
  if (pipelineProgressEl) pipelineProgressEl.style.width = `${pct}%`;

  // Pop effect
  if (prevIdx !== -1 && prevIdx < idx) {
    const completedEl = pipelineStepEls[prevIdx];
    completedEl.classList.add("just-completed");
    setTimeout(() => completedEl.classList.remove("just-completed"), 420);
  }

  highlightMcpForStage(stageKey);
}

function startPipelineSimulation(plan) {
  stopPipelineSimulation();
  resetPipeline();
  setPipelineRunning(true);

  pipelineStagesPlanned = derivePipelineStages(plan);
  const stageCount = pipelineStagesPlanned.length;

  const baseMs = 8000;
  const extraPerStage = 1400;
  pipelineSimTotalMs = baseMs + Math.max(0, stageCount - 2) * extraPerStage;

  pipelineSimStart = performance.now();

  setPipelineStage(pipelineStagesPlanned[0]);
  setAgentPulseState("active", "Scanning & enriching surface…");

  pipelineSimTimer = setInterval(() => {
    const elapsed = performance.now() - pipelineSimStart;
    const frac = Math.max(0, Math.min(0.98, elapsed / pipelineSimTotalMs));
    const idxFloat = frac * stageCount;
    const stageIdx = Math.min(stageCount - 1, Math.floor(idxFloat));
    const stageKey = pipelineStagesPlanned[stageIdx];

    setPipelineStage(stageKey);

    if (stageKey === "synthesis" || stageIdx >= stageCount - 2) {
      setAgentPulseState("intense", "Synthesizing intelligence…");
    } else {
      setAgentPulseState("active", "Scanning & enriching surface…");
    }

    if (elapsed >= pipelineSimTotalMs) {
      stopPipelineSimulation();
    }
  }, 160);
}

function finishAnalysisUI(success = true) {
  stopPipelineSimulation();
  setPipelineRunning(false);

  if (success) {
    setPipelineStage("synthesis");
    if (pipelineProgressEl) pipelineProgressEl.style.width = "100%";
    setAgentPulseState("idle", "Complete — ready for next target");
  } else {
    setAgentPulseState("idle", "Analysis failed — adjust target & retry");
  }

  // IMPORTANT PATCH:
  // Do NOT reapply predicted plan — show no tools until real usage arrives.
  applyMcpPlan({
    use_web_scrape: false,
    use_seo_probe: false,
    use_tech_stack: false,
    use_reviews_snapshot: false,
    use_social_snapshot: false,
    use_careers_intel: false,
    use_ads_snapshot: false,
  });
}

// ---------------------------------------------------------------------
// COT / TRACE
// ---------------------------------------------------------------------

function appendCotLine(role, text) {
  if (!cotStream) return;
  const li = document.createElement("li");
  li.classList.add("cot-line");

  if (role === "system") li.classList.add("cot-line--system");
  else if (role === "plan") li.classList.add("cot-line--plan");
  else if (role === "mcp") li.classList.add("cot-line--mcp");
  else if (role === "synth") li.classList.add("cot-line--synth");
  else if (role === "error") li.classList.add("cot-line--error");

  li.textContent = text;
  cotStream.appendChild(li);
  cotStream.scrollTop = cotStream.scrollHeight;
}

function resetCot() {
  if (cotStream) cotStream.innerHTML = "";
}

// ---------------------------------------------------------------------
// COMMAND PALETTE
// ---------------------------------------------------------------------

const COMMANDS = [
  {
    label: "load_blue_bottle — Load Blue Bottle demo profile",
    action: () => {
      companyNameInput.value = "Blue Bottle Coffee";
      companyUrlInput.value = "https://bluebottlecoffee.com";
      focusInput.value =
        "Assess brand, omni-channel presence, and operational maturity.";
      demoDatasetSelect.value = "blue_bottle";
      demoModeCheckbox.checked = true;
    },
  },
  {
    label: "load_sweetgreen — Load Sweetgreen demo profile",
    action: () => {
      companyNameInput.value = "Sweetgreen";
      companyUrlInput.value = "https://www.sweetgreen.com";
      focusInput.value =
        "Evaluate unit economics, digital ordering stack, and hiring posture.";
      demoDatasetSelect.value = "sweetgreen";
      demoModeCheckbox.checked = true;
    },
  },
  {
    label: "load_glossier — Load Glossier demo profile",
    action: () => {
      companyNameInput.value = "Glossier";
      companyUrlInput.value = "https://www.glossier.com";
      focusInput.value =
        "Understand DTC brand strength, retail footprint, and community.";
      demoDatasetSelect.value = "glossier";
      demoModeCheckbox.checked = true;
    },
  },
];

function renderCommandList(arr) {
  cmdkList.innerHTML = "";
  for (const [i, cmd] of arr.entries()) {
    const li = document.createElement("li");
    li.textContent = cmd.label;
    li.dataset.index = String(i);
    li.addEventListener("click", () => {
      cmd.action();
      closeCommandPalette();
    });
    cmdkList.appendChild(li);
  }
}

function openCommandPalette() {
  cmdkBackdrop.classList.add("cmdk-backdrop--visible");
  cmdkInput.value = "";
  cmdkInput.focus();
  renderCommandList(COMMANDS);
}

function closeCommandPalette() {
  cmdkBackdrop.classList.remove("cmdk-backdrop--visible");
}

cmdkInput?.addEventListener("input", () => {
  const q = cmdkInput.value.toLowerCase();
  renderCommandList(COMMANDS.filter((c) => c.label.toLowerCase().includes(q)));
});

cmdkBackdrop?.addEventListener("click", (e) => {
  if (e.target === cmdkBackdrop) closeCommandPalette();
});

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openCommandPalette();
  }
  if (e.key === "Escape") closeCommandPalette();
});

openCommandPaletteBtn?.addEventListener("click", openCommandPalette);

// ---------------------------------------------------------------------
// REAL TOOL USAGE PATCH
// ---------------------------------------------------------------------

function deriveActualPlanFromProfile(p) {
  if (!p) return {};

  function isUsed(section) {
    if (!section) return false;
    if (section.error) return true; // tool was actually invoked
    for (const v of Object.values(section)) {
      if (!v) continue;
      if (typeof v === "string" && v.trim()) return true;
      if (Array.isArray(v) && v.length > 0) return true;
      if (typeof v === "object" && Object.keys(v).length > 0) return true;
    }
    return false;
  }

  return {
    use_web_scrape: isUsed(p.web),
    use_seo_probe: isUsed(p.seo),
    use_tech_stack: isUsed(p.tech_stack),
    use_reviews_snapshot: isUsed(p.reviews),
    use_social_snapshot: isUsed(p.social),
    use_careers_intel: isUsed(p.hiring),
    use_ads_snapshot: isUsed(p.ads),
  };
}

function planToLabel(plan) {
  const map = {
    use_web_scrape: "WEB SCRAPE",
    use_seo_probe: "SEO PROBE",
    use_tech_stack: "TECH STACK",
    use_reviews_snapshot: "REVIEWS",
    use_social_snapshot: "SOCIAL",
    use_careers_intel: "HIRING",
    use_ads_snapshot: "ADS",
  };

  return Object.entries(plan)
    .filter(([, v]) => v)
    .map(([k]) => map[k])
    .filter(Boolean)
    .join(" · ");
}

// ---------------------------------------------------------------------
// MAIN FORM HANDLER
// ---------------------------------------------------------------------

form.addEventListener("submit", async (evt) => {
  evt.preventDefault();

  const companyName = companyNameInput.value.trim();
  const companyUrl = companyUrlInput.value.trim();
  let focus = focusInput.value.trim();
  const reportStyle = reportStyleSelect.value;
  const demoMode = demoModeCheckbox.checked;
  const demoKey = demoDatasetSelect.value;
  let startJobTime = 0; // Initialize start time tracker

  // Report style enrichments
  if (reportStyle === "red_team") {
    focus += " red team adversarial teardown of this company’s public surface.";
  }
  if (reportStyle === "narrative") {
    focus += " narrative human-readable OSINT case study.";
  }
  if (reportStyle === "investor_brief") {
    focus += " investor-focused brief: risk, moat, signals.";
  }
  if (reportStyle === "founder_playbook") {
    focus += " founder/operator playbook with prioritised actions.";
  }

  const plan = createPlanPreview({
    hasUrl: !!companyUrl,
    focus,
    forceFullPlan: demoMode,
  });

  renderPlanGrid(plan);
  applyMcpPlan(plan);

  resetCot();
  appendCotLine(
    "plan",
    `Mode: ${demoMode ? "demo" : "live"}. Deriving tool plan from surface + focus.`
  );
  appendCotLine(
    "plan",
    "Enabled tools → " +
    Object.entries(plan)
      .filter(([, v]) => v)
      .map(([k]) => planToLabel({ [k]: true }))
      .filter(Boolean)
      .join(" · ")
  );

  setStatus("running", demoMode ? "Loading demo…" : "Dispatching agent API…");
  setCotStatus("running", "RUNNING");
  setReportStatus("running", "Synthesizing");
  setLoadingState(true);
  if (modeValue) modeValue.textContent = demoMode ? "DEMO" : "LIVE";

  try {
    let data;

    if (demoMode) {
      // DEMO MODE: Keep existing simulation
      startPipelineSimulation(plan);
      data = await loadDemoProfile(demoKey);
      appendCotLine(
        "mcp",
        `Loaded demo profile: ${data.profile.company.name} (${data.profile.company.url})`
      );
    } else {
      // LIVE MODE: Real Async Polling

      // 1. Get API Key
      let apiKey = localStorage.getItem("signal_analyst_api_key");
      if (!apiKey) {
        apiKey = prompt("Please enter your API Key for Signal Analyst:");
        if (apiKey) localStorage.setItem("signal_analyst_api_key", apiKey);
      }
      if (!apiKey) throw new Error("API Key required for live analysis");

      // 2. Submit Job
      appendCotLine("system", "Submitting analysis job...");
      startJobTime = performance.now(); // Start timing
      const startResp = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey
        },
        body: JSON.stringify({
          company_name: companyName || null,
          company_url: companyUrl || "",
          focus: focus || null,
          report_style: reportStyle,
        }),
      });

      if (!startResp.ok) {
        if (startResp.status === 401) {
          localStorage.removeItem("signal_analyst_api_key");
          throw new Error("Invalid API Key. Please try again.");
        }
        throw new Error(`Agent API returned ${startResp.status}`);
      }

      const { job_id } = await startResp.json();
      appendCotLine("system", `Job started: ${job_id}`);

      // 3. Poll Job Status
      setPipelineRunning(true);
      setAgentPulseState("active", "Job queued...");

      let job = { status: "queued", progress: 0 };

      while (true) {
        const pollResp = await fetch(`http://localhost:8000/jobs/${job_id}`, {
          headers: { "X-API-Key": apiKey }
        });

        if (!pollResp.ok) throw new Error(`Polling failed: ${pollResp.status}`);
        job = await pollResp.json();

        // Update UI with real progress
        if (pipelineProgressEl) pipelineProgressEl.style.width = `${job.progress}%`;

        // Map backend progress to stages for UI highlighting
        let stageName = "scrape";
        if (job.progress > 20) stageName = "seo";
        if (job.progress > 50) stageName = "tech";
        if (job.progress > 80) stageName = "synthesis";
        setPipelineStage(stageName);

        setAgentPulseState("active", `Analyzing... ${job.progress}%`);
        if (job.status === "running") {
          // Keep polling
        } else if (job.status === "complete") {
          data = job.result;
          break;
        } else if (job.status === "failed") {
          throw new Error(job.error || "Job failed on server");
        }

        await new Promise(r => setTimeout(r, 1000));
      }

      appendCotLine("synth", "Job complete. Rendering report.");
    }

    // REAL TOOL USAGE APPLIED HERE:
    if (data && data.profile) {
      const actualPlan = deriveActualPlanFromProfile(data.profile);
      applyMcpPlan(actualPlan);
      appendCotLine(
        "mcp",
        "Final tool usage → " + (planToLabel(actualPlan) || "no tools produced data")
      );
    }

    const elapsed = Math.round(performance.now() - (demoMode ? pipelineSimStart : startJobTime));
    if (latencyValue) latencyValue.textContent = `${elapsed} ms`;

    renderReport(data.report_markdown);

    setStatus("idle", "Analysis complete.");
    setCotStatus("idle", "AWAITING INPUT");
    setReportStatus("idle", "Ready");
    finishAnalysisUI(true);
  } catch (err) {
    console.error(err);

    setStatus("error", "Failure during analysis: " + err.message);
    setCotStatus("error", "ERROR");
    setReportStatus("error", "Error");
    appendCotLine(
      "error",
      "Failure during analysis: " + err.message
    );
    finishAnalysisUI(false);
  } finally {
    setLoadingState(false);
  }
});

// ---------------------------------------------------------------------
// INITIALIZATION
// ---------------------------------------------------------------------

(function init() {
  demoModeCheckbox.checked = true;
  modeValue.textContent = "DEMO";
  latencyValue.textContent = "– ms";

  const initialPlan = createPlanPreview({
    hasUrl: false,
    focus: "",
    forceFullPlan: true,
  });
  renderPlanGrid(initialPlan);
  applyMcpPlan(initialPlan);

  resetCot();
  setStatus("idle", "Idle. Ready for new target.");
  setCotStatus("idle", "AWAITING INPUT");
  setReportStatus("idle", "Ready");

  setAgentPulseState("idle", "Idle — ready for next target");
  setPipelineRunning(false);
  resetPipeline();
})();
