// Obsidian Command – Frontend Logic (wired + robust, fully inline demos)

// Live backend endpoint (same behavior as original miniapp)
const API_URL = "http://localhost:8000/analyze";

const form = document.getElementById("analyze-form");
const companyNameInput = document.getElementById("company_name");
const companyUrlInput = document.getElementById("company_url");
const focusInput = document.getElementById("focus");
const demoModeCheckbox = document.getElementById("demo_mode");
const demoDatasetSelect = document.getElementById("demo_dataset");
const analyzeButton = document.getElementById("analyze-button");

const statusText = document.getElementById("status-text");
const statusDot = document.querySelector(".dot");
const cardStatusBadge = document.getElementById("card-status-badge");
const planSummaryBadge = document.getElementById("plan-summary-badge");
const surfaceBadge = document.getElementById("surface-badge");
const cotStatusBadge = document.getElementById("cot-status-badge");

const planGrid = document.getElementById("plan-grid");
const reportOutput = document.getElementById("report-output");

const metaCompanyName = document.getElementById("meta-company-name");
const metaCompanyUrl = document.getElementById("meta-company-url");
const metaInference = document.getElementById("meta-inference");

const metricMetaIssues = document.getElementById("metric-meta-issues");
const metricKeywords = document.getElementById("metric-keywords");
const metricFrameworks = document.getElementById("metric-frameworks");
const metricHiring = document.getElementById("metric-hiring");

const latencyValue = document.getElementById("latency-value");
const modeValue = document.getElementById("mode-value");

const mcpWeb = document.getElementById("mcp-web");
const mcpSeo = document.getElementById("mcp-seo");
const mcpTech = document.getElementById("mcp-tech");
const mcpReviews = document.getElementById("mcp-reviews");
const mcpSocial = document.getElementById("mcp-social");
const mcpCareers = document.getElementById("mcp-careers");
const mcpAds = document.getElementById("mcp-ads");

const cotStream = document.getElementById("cot-stream");

// Command palette elements
const cmdkBackdrop = document.getElementById("cmdk-backdrop");
const cmdkInput = document.getElementById("cmdk-input");
const cmdkClose = document.getElementById("cmdk-close");
const openCommandPalette = document.getElementById("open-command-palette");
const cmdkList = document.querySelector(".cmdk-list");

/* -----------------------------
   INLINE DEMO PROFILES
   ----------------------------- */

const INLINE_DEMOS = {
  blue_bottle: {
    profile: {
      company: {
        name: "Blue Bottle Coffee",
        url: "https://bluebottlecoffee.com",
      },
      seo: {
        meta_issues: [
          "Some product pages missing meta descriptions",
          "Duplicate title tags on subscription flow pages",
        ],
        heading_issues: [],
        keyword_summary: [
          "single origin",
          "coffee subscription",
          "pour over",
          "espresso",
        ],
      },
      tech_stack: {
        frameworks: ["Next.js", "React"],
        analytics: ["Google Analytics", "Segment"],
        cdn: ["Fastly"],
      },
      hiring: {
        open_roles: [
          { title: "Director of Growth Marketing" },
          { title: "Senior Data Analyst, Lifecycle" },
          { title: "Frontend Engineer, E-commerce" },
          { title: "Retail Operations Manager" },
        ],
        inferred_focus:
          "Heavy emphasis on subscription growth, lifecycle optimization, and omni-channel retail.",
      },
      ads: {
        platforms: ["Meta", "Google", "TikTok"],
        themes: [
          "Third-wave craft credibility",
          "Subscription retention & churn reduction",
          "New cafe openings",
          "Seasonal product launches",
        ],
      },
    },
    report_markdown: `# Business Intelligence Report: Blue Bottle Coffee

## 1. Company Overview

**Company Name:** Blue Bottle Coffee  
**Primary URL:** https://bluebottlecoffee.com  

Blue Bottle is a third-wave coffee company operating a hybrid of retail cafes,
wholesale distribution, and a global e-commerce subscription business. The public
surface suggests a mature growth organization with strong brand control and
disciplined experimentation around DTC retention.

## 2. Web / SEO Surface

- Meta issues concentrated on long-tail product pages (missing descriptions).
- Core marketing pages are clean and structured; titles are coherent.
- Keyword field is dominated by:

  - *single origin*, *coffee subscription*, *pour over*, *espresso*

This reflects a balance of brand language (craft / story) and performance
language (subscription, delivery, convenience).

## 3. Tech Stack

- **Frameworks:** Next.js, React, custom components on top of a design system.
- **Analytics:** Google Analytics + Segment as routing layer.
- **Infra:** CDN via Fastly; misc marketing pixels integrated selectively.

This is the stack of a company that wants instrumentation and controlled
experimentation more than raw speed.

## 4. Hiring / Org Signals

Active roles include:

- Director of Growth Marketing
- Senior Data Analyst, Lifecycle
- Frontend Engineer, E-commerce
- Retail Operations Manager

The hiring pattern points to a subscription-driven growth engine with lifecycle
analytics at the center.

## 5. Ads & Growth Themes

Inferred themes from detected platforms and campaigns:

- Storytelling around third-wave craft and sourcing.
- Subscription retention, churn reduction, win-back flows.
- Grand openings and cafe experience campaigns.
- Seasonal launches to spike demand and reactivate dormant cohorts.

## 6. Analyst Summary

Blue Bottle operates as a mature DTC subscription business with real retail
gravity, not a simple cafe chain. The OSINT surface aligns with a growth
practice that cares deeply about:

- Cohort behavior over time.
- Subscription health and retention.
- Brand protection while still running performance marketing.
`,
  },

  sweetgreen: {
    profile: {
      company: {
        name: "Sweetgreen",
        url: "https://www.sweetgreen.com",
      },
      seo: {
        meta_issues: ["Location pages with thin content"],
        heading_issues: ["Non-semantic headings on menu pages"],
        keyword_summary: [
          "salad",
          "healthy lunch",
          "grain bowl",
          "restaurant near me",
        ],
      },
      tech_stack: {
        frameworks: ["React", "Next.js"],
        analytics: ["Segment", "Google Analytics"],
      },
      hiring: {
        open_roles: [
          { title: "Senior Product Manager, Marketplace" },
          { title: "Data Scientist, Growth" },
        ],
        inferred_focus:
          "Platformization of ordering and logistics; heavy experimentation around demand shaping.",
      },
      ads: {
        platforms: ["Meta", "Google"],
        themes: [
          "Healthy fast casual positioning",
          "Loyalty and app adoption",
          "Delivery & pickup convenience",
        ],
      },
    },
    report_markdown: `# Business Intelligence Report: Sweetgreen

The surface for Sweetgreen reads like a logistics + marketplace company wearing
a restaurant brand mask. Tech + hiring indicate a focus on:

- App-first ordering
- Loyalty, repeat purchase, CRM
- Demand shaping via promotions and placement
`,
  },

  glossier: {
    profile: {
      company: {
        name: "Glossier",
        url: "https://www.glossier.com",
      },
      seo: {
        meta_issues: ["Some legacy blog posts missing structured data"],
        heading_issues: [],
        keyword_summary: ["makeup", "skincare", "glowy skin", "beauty"],
      },
      tech_stack: {
        frameworks: ["Next.js", "React"],
        analytics: ["Google Analytics", "Hotjar"],
      },
      hiring: {
        open_roles: [{ title: "Brand Marketing Manager" }],
        inferred_focus:
          "Brand-led growth with selective performance marketing experiments.",
      },
      ads: {
        platforms: ["Meta", "Google"],
        themes: [
          "Hero SKU storytelling",
          "Influencer-adjacent social proof",
          "New product drops",
        ],
      },
    },
    report_markdown: `# Business Intelligence Report: Glossier

Glossier still leans heavily on brand and community, but the surface tech +
hiring signals show a careful layering of instrumentation and experimentation
on top of a visually rigid brand system.
`,
  },
};

// Fallback if some weird key is used
function loadDemoProfile(demoKey) {
  const key = demoKey in INLINE_DEMOS ? demoKey : "blue_bottle";
  const demo = INLINE_DEMOS[key];
  const name = demo.profile?.company?.name || key;
  appendCotLine("system", `Demo profile loaded: ${name}`);
  return Promise.resolve(demo);
}

/* -----------------------------
   Utility + Status
   ----------------------------- */

function setStatus(mode, text) {
  statusText.textContent = text;

  statusDot.classList.remove("dot--idle", "dot--running", "dot--error");
  cardStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--active",
    "badge-status--error"
  );

  if (mode === "idle") {
    statusDot.classList.add("dot--idle");
    cardStatusBadge.textContent = "IDLE";
    cardStatusBadge.classList.add("badge-status--neutral");
  } else if (mode === "running") {
    statusDot.classList.add("dot--running");
    cardStatusBadge.textContent = "ANALYZING";
    cardStatusBadge.classList.add("badge-status--active");
  } else if (mode === "error") {
    statusDot.classList.add("dot--error");
    cardStatusBadge.textContent = "ERROR";
    cardStatusBadge.classList.add("badge-status--error");
  }
}

function containsAny(text, keywords) {
  return keywords.some((k) => text.includes(k));
}

function createPlanPreview({ hasUrl, focus, forceFullPlan = false }) {
  const lowerFocus = (focus || "").toLowerCase();

  const plan = {
    use_web_scrape: false,
    use_seo_probe: false,
    use_tech_stack: false,
    use_reviews_snapshot: false,
    use_social_snapshot: false,
    use_careers_intel: false,
    use_ads_snapshot: false,
  };

  if (forceFullPlan) {
    Object.keys(plan).forEach((k) => {
      plan[k] = true;
    });
    return plan;
  }

  if (!hasUrl && !lowerFocus) {
    return plan;
  }

  if (hasUrl) {
    plan.use_web_scrape = true;
    plan.use_seo_probe = true;
    plan.use_tech_stack = true;
  }

  if (containsAny(lowerFocus, ["review", "brand", "reputation", "customer", "voice"])) {
    plan.use_reviews_snapshot = true;
    plan.use_social_snapshot = true;
  }

  if (containsAny(lowerFocus, ["social", "twitter", "instagram", "tiktok", "youtube", "community"])) {
    plan.use_social_snapshot = true;
  }

  if (containsAny(lowerFocus, ["hiring", "org", "team", "talent", "recruit", "headcount"])) {
    plan.use_careers_intel = true;
  }

  if (containsAny(lowerFocus, ["ads", "advertising", "campaign", "paid", "growth", "marketing"])) {
    plan.use_ads_snapshot = true;
  }

  return plan;
}

function renderPlanGrid(plan) {
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
  items.forEach(([label, key]) => {
    const active = !!plan[key];
    const div = document.createElement("div");
    div.className = "plan-item" + (active ? " plan-item--active" : "");
    div.innerHTML = `
      <span class="plan-dot ${active ? "plan-dot--active" : ""}"></span>
      <span class="plan-label">${label}</span>
    `;
    planGrid.appendChild(div);
  });

  toggleMcpPills(plan);
  updatePlanSummaryBadge(plan);
}

function toggleMcpPills(plan) {
  setPillActive(mcpWeb, plan.use_web_scrape);
  setPillActive(mcpSeo, plan.use_seo_probe);
  setPillActive(mcpTech, plan.use_tech_stack);
  setPillActive(mcpReviews, plan.use_reviews_snapshot);
  setPillActive(mcpSocial, plan.use_social_snapshot);
  setPillActive(mcpCareers, plan.use_careers_intel);
  setPillActive(mcpAds, plan.use_ads_snapshot);
}

function setPillActive(el, isActive) {
  if (!el) return;
  el.classList.toggle("status-pill--active", !!isActive);
}

function updatePlanSummaryBadge(plan) {
  const activeCount = Object.values(plan).filter(Boolean).length;
  planSummaryBadge.classList.remove("badge-status--neutral", "badge-status--active");
  if (activeCount === 0) {
    planSummaryBadge.textContent = "No tools selected (focus only)";
    planSummaryBadge.classList.add("badge-status--neutral");
  } else {
    planSummaryBadge.textContent = `${activeCount} tools enabled`;
    planSummaryBadge.classList.add("badge-status--active");
  }
}

/* -----------------------------
   CoT / Agent Mindstream
   ----------------------------- */

function appendCotLine(kind, text) {
  const line = document.createElement("div");
  line.className = "terminal-line terminal-line--" + kind;
  const tag = document.createElement("span");
  tag.className = "terminal-tag";
  tag.textContent = kind;
  const span = document.createElement("span");
  span.textContent = text;
  line.appendChild(tag);
  line.appendChild(span);
  cotStream.appendChild(line);
  cotStream.scrollTop = cotStream.scrollHeight;
}

function resetCot() {
  cotStream.innerHTML = "";
  appendCotLine("system", "Session reset. Awaiting new target surface…");
}

function setCotStatus(mode) {
  cotStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--active",
    "badge-status--error"
  );
  if (mode === "idle") {
    cotStatusBadge.textContent = "Standing by";
    cotStatusBadge.classList.add("badge-status--neutral");
  } else if (mode === "running") {
    cotStatusBadge.textContent = "Running analysis";
    cotStatusBadge.classList.add("badge-status--active");
  } else if (mode === "error") {
    cotStatusBadge.textContent = "Error";
    cotStatusBadge.classList.add("badge-status--error");
  }
}

function runCotSequence(plan, modeLabel) {
  setCotStatus("running");
  appendCotLine("plan", `Mode: ${modeLabel}. Deriving tool plan from surface…`);

  setTimeout(() => {
    const enabled = Object.entries(plan)
      .filter(([_, v]) => v)
      .map(([k]) => k.replace("use_", "").replace(/_/g, " ").toUpperCase());

    if (enabled.length === 0) {
      appendCotLine("plan", "No tools enabled; will still build an empty OSINT profile.");
    } else {
      appendCotLine("plan", `Enabled tools → ${enabled.join(" · ")}`);
    }
  }, 150);

  setTimeout(() => {
    if (plan.use_web_scrape) {
      appendCotLine("mcp", "Dispatching mcp_web_scrape → POST /run");
    } else {
      appendCotLine("mcp", "Skipping web scrape (no URL).");
    }
  }, 350);

  setTimeout(() => {
    if (plan.use_web_scrape) {
      if (plan.use_seo_probe) {
        appendCotLine("mcp", "Chaining mcp_seo_probe on scraped metadata.");
      }
      if (plan.use_tech_stack) {
        appendCotLine("mcp", "Fingerprinting stack via mcp_tech_stack.");
      }
    }
  }, 600);

  setTimeout(() => {
    if (plan.use_reviews_snapshot || plan.use_social_snapshot) {
      appendCotLine("mcp", "Optional surface probes → reviews / social snapshots.");
    }
    if (plan.use_careers_intel) {
      appendCotLine("mcp", "Scanning hiring signals via mcp_careers_intel.");
    }
    if (plan.use_ads_snapshot) {
      appendCotLine("mcp", "Inspecting ads themes / platforms via mcp_ads_snapshot.");
    }
  }, 900);
}

/* -----------------------------
   Render profile + report
   ----------------------------- */

function renderProfileAndReport(profile, reportMarkdown) {
  if (!profile || typeof profile !== "object") {
    surfaceBadge.textContent = "No profile";
    surfaceBadge.classList.add("badge-status--error");
    return;
  }

  reportOutput.textContent = reportMarkdown || "(No report_markdown in response.)";
  reportOutput.classList.remove("report-output--empty");

  const company = profile.company || {};
  metaCompanyName.textContent = company.name || "—";
  metaCompanyUrl.textContent = company.url || "—";

  const seo = profile.seo || {};
  const metaIssues = (seo.meta_issues || []).length;
  const headingIssues = (seo.heading_issues || []).length;
  metricMetaIssues.textContent = metaIssues + headingIssues;

  const keywordSummary = seo.keyword_summary || [];
  metricKeywords.textContent = keywordSummary.length || "0";

  const tech = profile.tech_stack || {};
  const frameworks = tech.frameworks || [];
  const analytics = tech.analytics || [];
  metricFrameworks.textContent = frameworks.length + analytics.length;

  const hiring = profile.hiring || {};
  const openRoles = (hiring.open_roles || []).length;
  const ads = profile.ads || {};
  const adPlatforms = ads.platforms || [];
  metricHiring.textContent = openRoles + adPlatforms.length;

  const inferred = hiring.inferred_focus || "";
  const themes = (ads.themes || []).slice(0, 3).join(" • ");
  if (inferred || themes) {
    metaInference.textContent = [inferred, themes].filter(Boolean).join(" | ");
  } else {
    metaInference.textContent =
      "No strong hiring or advertising signal detected by the agent.";
  }

  surfaceBadge.textContent = "Profile updated";
  surfaceBadge.classList.remove("badge-status--neutral", "badge-status--error");
  surfaceBadge.classList.add("badge-status--active");
}

/* -----------------------------
   Loading / Skeleton
   ----------------------------- */

function setLoadingState(isLoading) {
  document.body.classList.toggle("is-loading", isLoading);
  analyzeButton.disabled = isLoading;
}

/* -----------------------------
   Command Palette
   ----------------------------- */

function openCmdK() {
  cmdkBackdrop.classList.add("cmdk-backdrop--visible");
  cmdkInput.value = "";
  cmdkInput.focus();
}

function closeCmdK() {
  cmdkBackdrop.classList.remove("cmdk-backdrop--visible");
}

openCommandPalette.addEventListener("click", openCmdK);
cmdkClose.addEventListener("click", closeCmdK);
cmdkBackdrop.addEventListener("click", (e) => {
  if (e.target === cmdkBackdrop) closeCmdK();
});

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openCmdK();
  }
  if (e.key === "Escape") {
    closeCmdK();
  }
});

if (cmdkList) {
  cmdkList.addEventListener("click", (e) => {
    const item = e.target.closest(".cmdk-item");
    if (!item) return;
    const cmd = item.dataset.command;
    if (!cmd) return;
    runCommand(cmd);
  });
}

function runCommand(cmd) {
  switch (cmd) {
    case "load_blue_bottle":
      demoModeCheckbox.checked = true;
      demoDatasetSelect.value = "blue_bottle";
      syncDemoModeUI();
      closeCmdK();
      autoRunDemo();
      break;
    case "load_sweetgreen":
      demoModeCheckbox.checked = true;
      demoDatasetSelect.value = "sweetgreen";
      syncDemoModeUI();
      closeCmdK();
      autoRunDemo();
      break;
    case "load_glossier":
      demoModeCheckbox.checked = true;
      demoDatasetSelect.value = "glossier";
      syncDemoModeUI();
      closeCmdK();
      autoRunDemo();
      break;
    case "toggle_demo":
      demoModeCheckbox.checked = !demoModeCheckbox.checked;
      syncDemoModeUI();
      closeCmdK();
      break;
    case "clear_report":
      reportOutput.textContent =
        "No report yet. Run an analysis or load a demo profile.";
      reportOutput.classList.add("report-output--empty");
      metaCompanyName.textContent = "—";
      metaCompanyUrl.textContent = "—";
      metaInference.textContent =
        "Run an analysis to see how the agent reads this organization.";
      metricMetaIssues.textContent = "–";
      metricKeywords.textContent = "–";
      metricFrameworks.textContent = "–";
      metricHiring.textContent = "–";
      resetCot();
      closeCmdK();
      break;
    default:
      break;
  }
}

function autoRunDemo() {
  companyNameInput.value = "";
  companyUrlInput.value = "";
  focusInput.value = "";
  const ev = new Event("submit", { cancelable: true });
  form.dispatchEvent(ev);
}

/* -----------------------------
   Demo Mode UI
   ----------------------------- */

function syncDemoModeUI() {
  const demo = demoModeCheckbox.checked;
  modeValue.textContent = demo ? "Demo" : "Live";

  companyUrlInput.disabled = demo;
  companyNameInput.disabled = demo;
  focusInput.disabled = demo;

  setStatus(
    "idle",
    demo
      ? "Demo mode: use command palette or Run Analysis."
      : "Idle. Ready for live target."
  );
}

demoModeCheckbox.addEventListener("change", () => {
  syncDemoModeUI();
});

/* -----------------------------
   Main Submit Handler
   ----------------------------- */

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetSurfaceBadges();

  const companyName = companyNameInput.value.trim();
  const companyUrl = companyUrlInput.value.trim();
  const focus = focusInput.value.trim();
  const demoMode = demoModeCheckbox.checked;
  const demoKey = demoDatasetSelect.value;

  const plan = createPlanPreview({
    hasUrl: !!companyUrl,
    focus,
    forceFullPlan: demoMode,
  });
  renderPlanGrid(plan);

  const modeLabel = demoMode ? "demo" : "live";

  resetCot();
  runCotSequence(plan, modeLabel);

  setStatus(
    "running",
    demoMode ? "Loading demo profile…" : "Dispatching agent API…"
  );
  setCotStatus("running");
  setLoadingState(true);

  const startTime = performance.now();

  try {
    let data;

    if (demoMode) {
      data = await loadDemoProfile(demoKey);
    } else {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName || null,
          company_url: companyUrl || null,
          focus: focus || null,
        }),
      });
      if (!resp.ok) {
        throw new Error(`Agent API returned ${resp.status}`);
      }
      data = await resp.json();
      appendCotLine("synth", "Agent returned OSINT profile and markdown report.");
    }

    const elapsed = Math.round(performance.now() - startTime);
    latencyValue.textContent = `${elapsed} ms`;

    handleSuccess(data);
  } catch (err) {
    console.error(err);

    if (!demoMode) {
      appendCotLine(
        "system",
        "Live agent call failed. Loading embedded Blue Bottle demo profile…"
      );
      const data = INLINE_DEMOS.blue_bottle;
      const elapsed = Math.round(performance.now() - startTime);
      latencyValue.textContent = `${elapsed} ms (fallback demo)`;
      handleSuccess(data);
      setStatus(
        "error",
        "Live call failed, but demo profile loaded successfully for visualization."
      );
      setCotStatus("idle");
      appendCotLine(
        "error",
        `Live agent call failed (${String(
          err.message || err
        )}). Showing demo data instead.`
      );
    } else {
      handleError(err);
    }
  } finally {
    setLoadingState(false);
  }
});

function resetSurfaceBadges() {
  surfaceBadge.textContent = "Running…";
  surfaceBadge.classList.remove("badge-status--neutral", "badge-status--error");
  surfaceBadge.classList.add("badge-status--active");
}

function handleSuccess(data) {
  const profile = data && data.profile;
  const reportMarkdown = data && data.report_markdown;

  renderProfileAndReport(profile, reportMarkdown);

  setStatus("idle", "Analysis complete. You can refine focus or change target.");
  setCotStatus("idle");
  appendCotLine("synth", "Synthesis complete. Report ready for review.");
}

function handleError(err) {
  setStatus("error", "Request failed. Check backend or static paths.");
  setCotStatus("error");
  surfaceBadge.textContent = "Error";
  surfaceBadge.classList.remove("badge-status--neutral", "badge-status--active");
  surfaceBadge.classList.add("badge-status--error");
  appendCotLine("error", `Failure during analysis: ${String(err.message || err)}`);
}

/* -----------------------------
   Initial UI
   ----------------------------- */

(function init() {
  demoModeCheckbox.checked = true;
  syncDemoModeUI();

  const initialPlan = createPlanPreview({
    hasUrl: false,
    focus: "",
    forceFullPlan: true,
  });
  renderPlanGrid(initialPlan);

  latencyValue.textContent = "– ms";
})();
