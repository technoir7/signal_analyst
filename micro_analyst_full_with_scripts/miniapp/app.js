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
        apiKey = prompt("Enter API Key (or click OK to skip if Auth is disabled):");
        if (apiKey) {
          localStorage.setItem("signal_analyst_api_key", apiKey);
        } else {
          apiKey = "no_auth"; // Allow bypass
        }
      }
      // if (!apiKey) throw new Error("API Key required for live analysis"); // Removed strict check

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
// SETTINGS & API CONFIGURATION
// ---------------------------------------------------------------------

const DEFAULT_BASE_URL = "http://localhost:8000";

function getBaseUrl() {
  return localStorage.getItem("signal_analyst_base_url") || DEFAULT_BASE_URL;
}

function getApiKey() {
  return localStorage.getItem("signal_analyst_api_key") || "";
}

function setBaseUrl(url) {
  localStorage.setItem("signal_analyst_base_url", url);
}

function setApiKey(key) {
  localStorage.setItem("signal_analyst_api_key", key);
}

// Centralized API helper with auth injection and robust error handling
async function apiFetch(method, endpoint, body = null, options = {}) {
  const baseUrl = getBaseUrl();
  const apiKey = getApiKey();
  const fullUrl = `${baseUrl}${endpoint}`;

  const fetchOptions = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  };

  if (apiKey) {
    fetchOptions.headers["X-API-Key"] = apiKey;
  }

  if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
    fetchOptions.body = JSON.stringify(body);
  }

  // Log the request for debugging
  console.log(`[API] ${method} ${fullUrl}`, body ? body : "");

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || 300000); // 300s timeout for deep analysis
    fetchOptions.signal = controller.signal;

    const resp = await fetch(fullUrl, fetchOptions);
    clearTimeout(timeoutId);

    // Handle HTTP errors
    if (!resp.ok) {
      const text = await resp.text().catch(() => "(no response body)");
      console.error(`[API] HTTP ${resp.status}: ${text}`);

      if (resp.status === 401) {
        throw new ApiError("Unauthorized - check your API key in Settings", "AUTH", resp.status);
      }
      if (resp.status === 403) {
        throw new ApiError("Forbidden - API key lacks permissions", "AUTH", resp.status);
      }
      if (resp.status === 404) {
        throw new ApiError(`Endpoint not found: ${endpoint}`, "NOT_FOUND", resp.status);
      }
      if (resp.status === 429) {
        throw new ApiError("Rate limited - wait before retrying", "RATE_LIMIT", resp.status);
      }
      if (resp.status >= 500) {
        throw new ApiError(`Server error: ${text}`, "SERVER", resp.status);
      }
      throw new ApiError(`HTTP ${resp.status}: ${text}`, "HTTP", resp.status);
    }

    return resp.json();

  } catch (err) {
    // Classify the error type
    if (err instanceof ApiError) {
      throw err;
    }

    if (err.name === "AbortError") {
      console.error(`[API] Request timeout: ${fullUrl}`);
      throw new ApiError(
        `Request timed out after ${(options.timeout || 300000) / 1000}s. Deep analysis can take several minutes.`,
        "TIMEOUT"
      );
    }

    // Network errors (includes CORS blocks!)
    if (err instanceof TypeError && err.message === "Failed to fetch") {
      console.error(`[API] Network error: ${fullUrl}`, err);

      // Check if we're on file:// protocol
      const isFileProtocol = window.location.protocol === "file:";

      let hint = `Could not connect to ${baseUrl}.`;

      if (isFileProtocol) {
        hint += `\n\n⚠️ You're loading this page from file://. CORS blocks requests from file:// origins.\n\nFix: Serve the frontend via HTTP:\n  cd miniapp && python3 -m http.server 8080\nThen open http://localhost:8080`;
      } else {
        hint += `\n\nPossible causes:\n• Backend not running (start with: uvicorn agent.micro_analyst:app --reload)\n• Wrong base URL (check Settings)\n• CORS blocking the request`;
      }

      throw new ApiError(hint, "NETWORK");
    }

    console.error(`[API] Unexpected error: ${fullUrl}`, err);
    throw new ApiError(`Unexpected error: ${err.message}`, "UNKNOWN");
  }
}

// Custom error class for API errors
class ApiError extends Error {
  constructor(message, type, statusCode = null) {
    super(message);
    this.name = "ApiError";
    this.type = type; // CORS, NETWORK, TIMEOUT, AUTH, HTTP, SERVER, NOT_FOUND, RATE_LIMIT, UNKNOWN
    this.statusCode = statusCode;
  }
}

// Legacy wrapper for existing code
async function apiCall(method, endpoint, body = null) {
  return apiFetch(method, endpoint, body);
}

// Settings Modal
const settingsBackdrop = document.getElementById("settings-backdrop");
const settingsApiKeyInput = document.getElementById("settings-api-key");
const settingsBaseUrlInput = document.getElementById("settings-base-url");
const settingsSaveBtn = document.getElementById("settings-save-btn");
const settingsCloseBtn = document.getElementById("settings-close-btn");
const openSettingsBtn = document.getElementById("open-settings");
const healthCheckBtn = document.getElementById("health-check-btn");
const healthCheckResult = document.getElementById("health-check-result");
const fileProtocolWarning = document.getElementById("file-protocol-warning");
const dismissFileWarningBtn = document.getElementById("dismiss-file-warning");

function openSettings() {
  settingsApiKeyInput.value = getApiKey();
  settingsBaseUrlInput.value = getBaseUrl();
  settingsBackdrop.classList.add("cmdk-backdrop--visible");
}

function closeSettings() {
  settingsBackdrop.classList.remove("cmdk-backdrop--visible");
}

openSettingsBtn?.addEventListener("click", openSettings);
settingsCloseBtn?.addEventListener("click", closeSettings);
settingsSaveBtn?.addEventListener("click", () => {
  const key = settingsApiKeyInput.value.trim();
  const url = settingsBaseUrlInput.value.trim() || DEFAULT_BASE_URL;
  setApiKey(key);
  setBaseUrl(url);
  closeSettings();
});
settingsBackdrop?.addEventListener("click", (e) => {
  if (e.target === settingsBackdrop) closeSettings();
});

// Health Check
healthCheckBtn?.addEventListener("click", async () => {
  healthCheckResult.textContent = "Checking...";
  healthCheckResult.style.color = "var(--text-muted)";
  healthCheckBtn.disabled = true;

  try {
    const baseUrl = settingsBaseUrlInput.value.trim() || getBaseUrl();
    const start = performance.now();
    const resp = await fetch(`${baseUrl}/health`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    const elapsed = Math.round(performance.now() - start);

    if (resp.ok) {
      healthCheckResult.textContent = `✅ Connected (${elapsed}ms)`;
      healthCheckResult.style.color = "#22c55e";
    } else {
      healthCheckResult.textContent = `⚠️ HTTP ${resp.status}`;
      healthCheckResult.style.color = "#f59e0b";
    }
  } catch (err) {
    console.error("[Health Check] Failed:", err);
    if (window.location.protocol === "file:") {
      healthCheckResult.textContent = "❌ Failed (CORS from file://)";
    } else {
      healthCheckResult.textContent = "❌ Cannot connect";
    }
    healthCheckResult.style.color = "#ef4444";
  } finally {
    healthCheckBtn.disabled = false;
  }
});

// File Protocol Warning
function checkFileProtocol() {
  if (window.location.protocol === "file:" && fileProtocolWarning) {
    const dismissed = localStorage.getItem("file_protocol_warning_dismissed");
    if (!dismissed) {
      fileProtocolWarning.style.display = "block";
    }
  }
}

dismissFileWarningBtn?.addEventListener("click", () => {
  localStorage.setItem("file_protocol_warning_dismissed", "1");
  fileProtocolWarning.style.display = "none";
});

// ---------------------------------------------------------------------
// TAB CONTROLLER
// ---------------------------------------------------------------------

const tabBtns = document.querySelectorAll(".tab-btn");
const tabPanels = document.querySelectorAll(".tab-panel");

function setActiveTab(tabName) {
  tabBtns.forEach(btn => {
    btn.classList.toggle("tab-btn--active", btn.dataset.tab === tabName);
  });
  tabPanels.forEach(panel => {
    panel.classList.toggle("tab-panel--active", panel.id === `panel-${tabName}`);
  });
}

tabBtns.forEach(btn => {
  btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
});

// ---------------------------------------------------------------------
// COHORT WORKFLOW
// ---------------------------------------------------------------------

const cohortAnchorUrlInput = document.getElementById("cohort-anchor-url");
const cohortCategoryInput = document.getElementById("cohort-category");
const cohortIncludeAnchorCheckbox = document.getElementById("cohort-include-anchor");
const cohortProposeBtn = document.getElementById("cohort-propose-btn");
const cohortConfirmBtn = document.getElementById("cohort-confirm-btn");
const cohortAnalyzeBtn = document.getElementById("cohort-analyze-btn");
const cohortDriftBtn = document.getElementById("cohort-drift-btn");
const cohortResultsBtn = document.getElementById("cohort-results-btn");
const cohortStatusBadge = document.getElementById("cohort-status-badge");
const cohortProposalDiv = document.getElementById("cohort-proposal");
const cohortProposalList = document.getElementById("cohort-proposal-list");
const cohortConfirmedDiv = document.getElementById("cohort-confirmed");
const cohortConfirmedList = document.getElementById("cohort-confirmed-list");
const cohortIdDisplay = document.getElementById("cohort-id-display");
const cohortResultsDiv = document.getElementById("cohort-results");

let currentCohortId = null;
let proposedPeers = [];

function setCohortStatus(status, label) {
  cohortStatusBadge.classList.remove("badge-status--neutral", "badge-status--active", "badge-status--error");
  if (status === "idle") cohortStatusBadge.classList.add("badge-status--neutral");
  else if (status === "loading") cohortStatusBadge.classList.add("badge-status--active");
  else if (status === "error") cohortStatusBadge.classList.add("badge-status--error");
  cohortStatusBadge.textContent = label;
}

cohortProposeBtn?.addEventListener("click", async () => {
  const anchorUrl = cohortAnchorUrlInput.value.trim();
  if (!anchorUrl) {
    alert("Please enter an anchor URL");
    return;
  }

  setCohortStatus("loading", "PROPOSING...");
  cohortProposeBtn.disabled = true;

  try {
    const data = await apiCall("POST", "/cohorts/propose", {
      anchor_url: anchorUrl,
      category_hint: cohortCategoryInput.value.trim() || null,
    });

    currentCohortId = data.cohort_id;
    // Backend returns "candidates", not "proposed_peers"
    proposedPeers = data.candidates || data.proposed_peers || [];

    // Render proposed peers with checkboxes
    if (proposedPeers.length === 0) {
      cohortProposalList.innerHTML = `<p style="padding: 12px; color: var(--text-muted); font-style: italic;">
          No direct peers found for this target. You can proceed with just the anchor.
        </p>`;
    } else {
      cohortProposalList.innerHTML = proposedPeers.map((peer, i) => `
          <div class="cohort-item">
            <input type="checkbox" id="peer-${i}" checked data-url="${peer.url}">
            <label for="peer-${i}" class="cohort-item-url">${peer.url}</label>
            <span class="cohort-item-name">${peer.name || ""}</span>
          </div>
        `).join("");
    }

    cohortProposalDiv.style.display = "block";
    cohortConfirmedDiv.style.display = "none";
    setCohortStatus("idle", "PROPOSED");
  } catch (err) {
    setCohortStatus("error", "ERROR");
    cohortResultsDiv.innerHTML = `<p style="color: var(--danger);">Error: ${err.message}</p>`;
  } finally {
    cohortProposeBtn.disabled = false;
  }
});

cohortConfirmBtn?.addEventListener("click", async () => {
  if (!currentCohortId) {
    alert("No cohort proposed yet");
    return;
  }

  const checkboxes = cohortProposalList.querySelectorAll('input[type="checkbox"]:checked');
  const selectedUrls = Array.from(checkboxes).map(cb => cb.dataset.url);
  const includeAnchor = cohortIncludeAnchorCheckbox.checked;

  if (selectedUrls.length === 0 && !includeAnchor) {
    alert("Please select at least one peer (or include the anchor)");
    return;
  }

  setCohortStatus("loading", "CONFIRMING...");
  cohortConfirmBtn.disabled = true;

  try {
    const data = await apiCall("POST", `/cohorts/${currentCohortId}/confirm`, {
      final_urls: selectedUrls,
      include_anchor: cohortIncludeAnchorCheckbox.checked,
    });

    const confirmedUrls = data.confirmed_urls || selectedUrls;

    // Show confirmed cohort
    cohortConfirmedList.innerHTML = confirmedUrls.map(url => `
      <div class="cohort-item">
        <span class="cohort-item-url">${url}</span>
      </div>
    `).join("");

    cohortIdDisplay.textContent = currentCohortId.slice(0, 8);
    cohortProposalDiv.style.display = "none";
    cohortConfirmedDiv.style.display = "block";
    setCohortStatus("idle", "CONFIRMED");
  } catch (err) {
    setCohortStatus("error", "ERROR");
    cohortResultsDiv.innerHTML = `<p style="color: var(--danger);">Error: ${err.message}</p>`;
  } finally {
    cohortConfirmBtn.disabled = false;
  }
});

cohortAnalyzeBtn?.addEventListener("click", async () => {
  if (!currentCohortId) {
    alert("No cohort confirmed yet");
    return;
  }

  setCohortStatus("loading", "ANALYZING...");
  cohortAnalyzeBtn.disabled = true;

  try {
    await apiCall("POST", `/cohorts/${currentCohortId}/analyze`);
    setCohortStatus("idle", "ANALYZING");
    cohortResultsDiv.innerHTML = `<p class="pulse-text">Initiating analysis...</p>`;
    // Start polling automatically
    monitorCohortProgress("complete");
  } catch (err) {
    setCohortStatus("error", "ERROR");
    cohortResultsDiv.innerHTML = `<p style="color: var(--danger);">Error: ${err.message}</p>`;
  } finally {
    cohortAnalyzeBtn.disabled = false;
  }
});

cohortDriftBtn?.addEventListener("click", async () => {
  if (!currentCohortId) {
    alert("No cohort confirmed yet");
    return;
  }

  setCohortStatus("loading", "ANALYZING DRIFT...");
  cohortDriftBtn.disabled = true;

  try {
    await apiCall("POST", `/cohorts/${currentCohortId}/drift`);
    setCohortStatus("idle", "DRIFT STARTED");
    cohortResultsDiv.innerHTML += `<p class="pulse-text" style="color: #a855f7;">🌊 Starting drift analysis...</p>`;
    // Start polling for drift specifically
    monitorCohortProgress("drift");
  } catch (err) {
    setCohortStatus("error", "ERROR");
    cohortResultsDiv.innerHTML = `<p style="color: var(--danger);">Error: ${err.message}</p>`;
  } finally {
    cohortDriftBtn.disabled = false;
  }
});

// Polling Helper
async function monitorCohortProgress(targetStatus = "complete") {
  setCohortStatus("loading", "ANALYZING...");

  const pollInterval = 2000;
  let attempts = 0;

  while (true) {
    attempts++;
    try {
      const data = await apiCall("GET", `/cohorts/${currentCohortId}/results`);

      // Check completion based on target
      let isReady = false;
      if (targetStatus === "complete") {
        // Main analysis complete if status is "complete" OR we have a report
        isReady = (data.status === "complete") || !!data.report_markdown;
      } else if (targetStatus === "drift") {
        // Drift analysis complete if we have drift report
        isReady = !!data.drift_report_markdown;
      }

      // Also complete if we got an explicit error/message in report_markdown
      if (data.report_markdown && data.report_markdown.includes("⚠️")) {
        isReady = true; // Show warning message
      }

      if (isReady || attempts > 150) { // 5 min timeout
        renderCohortResults(data);
        setCohortStatus("idle", isReady ? "COMPLETE" : "TIMEOUT");
        break;
      } else {
        // Still running
        const statusMsg = data.status || "running";
        cohortResultsDiv.innerHTML = `<p class="pulse-text">analyzing... (${statusMsg})</p>`;
        await new Promise(r => setTimeout(r, pollInterval));
      }
    } catch (err) {
      console.error("Polling error:", err);
      // Don't crash loop on transient network err, but maybe stop if 404
      if (err.statusCode === 404) break;
      await new Promise(r => setTimeout(r, pollInterval));
    }
  }
}

function renderCohortResults(data) {
  let html = "";

  // 1. Show the markdown report first (this is what the user wants to see most)
  if (data.report_markdown) {
    html += `<div class="cohort-report-section">`;
    html += renderMarkdown(data.report_markdown);
    html += `</div>`;
  }

  // 2. Render matrix table
  const matrixObj = data.matrix || {};
  const targets = matrixObj.targets || [];

  if (targets.length > 0) {
    html += `<h3 style="margin-top: 24px; margin-bottom: 12px;">Signal Matrix</h3>`;

    const headers = [
      "url", "tech_confidence", "pricing_visible",
      "docs_visible", "jobs_visible", "seo_hygiene", "social_visibility"
    ];

    html += '<table class="cohort-matrix"><thead><tr>';
    headers.forEach(h => { html += `<th>${h.replace(/_/g, ' ')}</th>`; });
    html += '</tr></thead><tbody>';

    targets.forEach(row => {
      html += '<tr>';
      headers.forEach(h => {
        let val = row[h];
        if (typeof val === 'boolean') val = val ? '✓' : '-';
        if (val === null || val === undefined) val = '-';
        // Truncate long URLs
        if (h === 'url' && typeof val === 'string' && val.length > 30) {
          val = val.replace(/^https?:\/\//, '').slice(0, 25) + '…';
        }
        html += `<td>${val}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
  }

  // 3. Append Drift Report if available
  if (data.drift_report_markdown) {
    html += `<hr style="margin: 24px 0; border-top: 2px dashed var(--border-color);">`;
    html += `<h3 style="margin-bottom: 12px; color: #a855f7;">🌊 Temporal Drift Analysis</h3>`;
    html += renderMarkdown(data.drift_report_markdown);
  }

  // 4. Fallback message if nothing to show
  if (!data.report_markdown && targets.length === 0 && !data.drift_report_markdown) {
    html = `<p style="color: var(--text-muted);">Analysis in progress or no data available yet. Status: ${data.status || 'unknown'}</p>`;
  }

  // 5. Add collapsible raw JSON at the end
  html += `
    <details class="json-collapsible" style="margin-top: 16px;">
      <summary>View Raw JSON</summary>
      <pre>${JSON.stringify(data, null, 2)}</pre>
    </details>
  `;

  cohortResultsDiv.innerHTML = html;
}


cohortResultsBtn?.addEventListener("click", async () => {
  if (!currentCohortId) return;
  monitorCohortProgress("complete"); // Manual trigger if needed
});

// ---------------------------------------------------------------------
// WAYBACK WORKFLOW
// ---------------------------------------------------------------------

const waybackUrlInput = document.getElementById("wayback-url");
const waybackFocusInput = document.getElementById("wayback-focus");
const waybackAnalyzeBtn = document.getElementById("wayback-analyze-btn");
const waybackStatusBadge = document.getElementById("wayback-status-badge");
const waybackNotice = document.getElementById("wayback-notice");
const waybackReport = document.getElementById("wayback-report");

function setWaybackStatus(status, label) {
  waybackStatusBadge.classList.remove("badge-status--neutral", "badge-status--active", "badge-status--error");
  if (status === "idle") waybackStatusBadge.classList.add("badge-status--neutral");
  else if (status === "loading") waybackStatusBadge.classList.add("badge-status--active");
  else if (status === "error") waybackStatusBadge.classList.add("badge-status--error");
  waybackStatusBadge.textContent = label;
}

function highlightWaybackSection(html) {
  // Wrap Wayback section in highlight
  return html.replace(
    /(<h2[^>]*>.*?(?:Wayback|Change Over Time).*?<\/h2>)/gi,
    '<div class="wayback-highlight">$1'
  ).replace(
    /(<h2[^>]*>(?!.*(?:Wayback|Change Over Time)))/gi,
    '</div>$1'
  );
}

waybackAnalyzeBtn?.addEventListener("click", async () => {
  const url = waybackUrlInput.value.trim();
  if (!url) {
    alert("Please enter a company URL");
    return;
  }

  setWaybackStatus("loading", "ANALYZING...");
  waybackAnalyzeBtn.disabled = true;
  waybackNotice.style.display = "none";

  try {
    const data = await apiCall("POST", "/analyze", {
      company_url: url,
      focus: waybackFocusInput.value.trim() || "wayback change detection",
    });

    const reportMd = data.report_markdown || "";
    let reportHtml = renderMarkdown(reportMd);

    // Check if Wayback section exists
    if (reportMd.toLowerCase().includes("wayback") || reportMd.toLowerCase().includes("change over time")) {
      reportHtml = highlightWaybackSection(reportHtml);
    } else {
      // Show notice that Wayback may not be enabled
      waybackNotice.style.display = "block";
    }

    // Add collapsible profile JSON
    reportHtml += `
      <details class="json-collapsible">
        <summary>View Profile JSON</summary>
        <pre>${JSON.stringify(data.profile, null, 2)}</pre>
      </details>
    `;

    waybackReport.innerHTML = reportHtml;
    setWaybackStatus("idle", "COMPLETE");
  } catch (err) {
    setWaybackStatus("error", "ERROR");
    waybackReport.innerHTML = `<p style="color: var(--danger);">Error: ${err.message}</p>`;
  } finally {
    waybackAnalyzeBtn.disabled = false;
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

  // Initialize with Single tab active
  setActiveTab("single");

  // Check if running from file:// and show warning
  checkFileProtocol();

  // Load settings from localStorage
  if (!getApiKey()) {
    // Prompt for API key on first visit (optional)
    // openSettings();
  }
})();
