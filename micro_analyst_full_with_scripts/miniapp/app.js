// Signal-Analyst – Frontend Logic (for original Micro-Analyst layout)

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
const statusDot = document.querySelector(".dot");
const cardStatusBadge = document.getElementById("card-status-badge");
const planSummaryBadge = document.getElementById("plan-summary-badge");

const metricMetaIssues = document.getElementById("metric-meta-issues");
const metricKeywords = document.getElementById("metric-keywords");
const metricFrameworks = document.getElementById("metric-frameworks");
const metricHiring = document.getElementById("metric-hiring");

const metaCompanyName = document.getElementById("meta-company-name");
const metaCompanyUrl = document.getElementById("meta-company-url");
const metaInference = document.getElementById("meta-inference");

const mcpWeb = document.getElementById("mcp-web");
const mcpSeo = document.getElementById("mcp-seo");
const mcpTech = document.getElementById("mcp-tech");
const mcpReviews = document.getElementById("mcp-reviews");
const mcpSocial = document.getElementById("mcp-social");
const mcpCareers = document.getElementById("mcp-careers");
const mcpAds = document.getElementById("mcp-ads");

const cotStatusBadge = document.getElementById("cot-status-badge");
const cotStream = document.getElementById("cot-stream");

const latencyValue = document.getElementById("latency-value");
const modeValue = document.getElementById("mode-value");
const reportStatusBadge = document.getElementById("report-status-badge");
const reportMarkdown = document.getElementById("report-markdown");

const planGrid = document.getElementById("plan-grid");

const cmdkBackdrop = document.getElementById("cmdk-backdrop");
const cmdkInput = document.getElementById("cmdk-input");
const cmdkList = document.getElementById("cmdk-list");
const openCommandPaletteBtn = document.getElementById("open-command-palette");

// --- STATUS HELPERS --------------------------------------------------

function setStatus(state, message) {
  statusText.textContent = message;

  statusDot.classList.remove("dot--idle", "dot--running", "dot--error");
  cardStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--running",
    "badge-status--error"
  );

  if (state === "idle") {
    statusDot.classList.add("dot--idle");
    cardStatusBadge.classList.add("badge-status--neutral");
  } else if (state === "running") {
    statusDot.classList.add("dot--running");
    cardStatusBadge.classList.add("badge-status--running");
  } else if (state === "error") {
    statusDot.classList.add("dot--error");
    cardStatusBadge.classList.add("badge-status--error");
  }
}

function setCotStatus(state, label) {
  cotStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--running",
    "badge-status--error"
  );
  if (state === "idle") {
    cotStatusBadge.classList.add("badge-status--neutral");
    cotStatusBadge.textContent = label || "READY";
  } else if (state === "running") {
    cotStatusBadge.classList.add("badge-status--running");
    cotStatusBadge.textContent = label || "RUNNING";
  } else if (state === "error") {
    cotStatusBadge.classList.add("badge-status--error");
    cotStatusBadge.textContent = label || "ERROR";
  }
}

function setReportStatus(state, label) {
  reportStatusBadge.classList.remove(
    "badge-status--neutral",
    "badge-status--running",
    "badge-status--error"
  );
  if (state === "idle") {
    reportStatusBadge.classList.add("badge-status--neutral");
    reportStatusBadge.textContent = label || "Ready";
  } else if (state === "running") {
    reportStatusBadge.classList.add("badge-status--running");
    reportStatusBadge.textContent = label || "Synthesizing";
  } else if (state === "error") {
    reportStatusBadge.classList.add("badge-status--error");
    reportStatusBadge.textContent = label || "Error";
  }
}

function setLoadingState(isLoading) {
  analyzeButton.disabled = isLoading;
  analyzeButton.textContent = isLoading ? "Running…" : "Run Analysis";
}

// --- COT / TRACE -----------------------------------------------------

function appendCotLine(role, text) {
  const li = document.createElement("li");
  li.classList.add("cot-line", `cot-line--${role}`);
  const label = document.createElement("span");
  label.classList.add("cot-tag");
  label.textContent = role;
  const body = document.createElement("span");
  body.classList.add("cot-text");
  body.textContent = text;
  li.appendChild(label);
  li.appendChild(body);
  cotStream.appendChild(li);
  cotStream.scrollTop = cotStream.scrollHeight;
}

function resetCot() {
  cotStream.innerHTML = "";
  appendCotLine("system", "Session reset. Awaiting new target surface…");
}

// --- PLAN PREVIEW (MIRRORS BACKEND HEURISTICS) -----------------------

function containsAny(text, keywords) {
  return keywords.some((kw) => text.includes(kw));
}

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

  const lowerFocus = (focus || "").toLowerCase();

  if (hasUrl || forceFullPlan) {
    plan.use_web_scrape = true;
    plan.use_seo_probe = true;
    plan.use_tech_stack = true;
  }

  if (
    containsAny(lowerFocus, [
      "review",
      "reviews",
      "brand",
      "reputation",
      "customer",
      "voice",
    ])
  ) {
    plan.use_reviews_snapshot = true;
    plan.use_social_snapshot = true;
  }

  if (
    containsAny(lowerFocus, [
      "social",
      "twitter",
      "instagram",
      "tiktok",
      "youtube",
      "community",
      "brand",
    ])
  ) {
    plan.use_social_snapshot = true;
  }

  if (containsAny(lowerFocus, ["hiring", "talent", "org", "team", "recruit"])) {
    plan.use_careers_intel = true;
  }

  if (
    containsAny(lowerFocus, [
      "ads",
      "advertising",
      "campaign",
      "paid",
      "growth",
      "marketing",
    ])
  ) {
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
    const pill = document.createElement("div");
    pill.classList.add("pill", "pill--plan");
    if (plan[key]) pill.classList.add("pill--on");
    pill.textContent = label;
    planGrid.appendChild(pill);
  });

  const activeLabels = items
    .filter(([_, key]) => plan[key])
    .map(([label]) => label);

  if (!activeLabels.length) {
    planSummaryBadge.textContent = "No tools selected yet";
  } else {
    planSummaryBadge.textContent = `Planned: ${activeLabels.join(" · ")}`;
  }
}

// --- DEMO PROFILES ---------------------------------------------------
// (These are simple placeholders; adjust to match your actual demo JSONs.)

const DEMO_PROFILES = {
  blue_bottle: {
    profile: {
      company: {
        name: "Blue Bottle Coffee",
        url: "https://bluebottlecoffee.com",
      },
      web: {
        url: "https://bluebottlecoffee.com",
        snapshot_summary:
          "Modern specialty coffee brand emphasizing quality, ritual, and subscription.",
        meta: {
          title: "Blue Bottle Coffee",
          description:
            "Thoughtfully sourced, carefully roasted coffee, delivered to your home or served in our cafes.",
          h1: ["Blue Bottle Coffee"],
          h2: ["Our Coffee", "Subscriptions", "Cafes"],
        },
      },
      seo: {
        meta_issues: [
          "Some collection pages with missing unique meta descriptions.",
        ],
        heading_issues: ["Multiple H1s detected on marketing pages."],
        keyword_summary: [
          "single origin coffee",
          "coffee subscription",
          "pour over",
        ],
      },
      tech_stack: {
        frameworks: ["Next.js", "React"],
        analytics: ["Google Analytics", "Segment"],
      },
      reviews: {
        summary:
          "High praise for flavor and design; recurring complaints on price and wait times.",
        top_complaints: ["Price sensitivity", "Long lines at peak hours"],
        top_praises: ["Coffee quality", "Store ambiance"],
      },
      social: {},
      hiring: {
        inferred_focus: "Retail operations & cafe expansion",
        open_roles: [{ title: "Cafe Manager" }, { title: "Barista" }],
      },
      ads: {
        platforms: ["Meta", "Google"],
        themes: ["subscription", "gift", "single origin"],
      },
    },
    report_markdown:
      "# OSINT Intelligence Report: Blue Bottle Coffee\n\n_Focus: Demo profile_\n\n## 1. Web Presence\n\n- Modern, minimalist landing experience with clear brand and subscription emphasis.\n\n## 2. SEO Diagnostics\n\n- Mostly solid SEO; some metadata duplication and missing descriptions.\n\n## 3. Tech Stack Fingerprint\n\n- Next.js/React with standard analytics and tracking.\n\n## 4. Customer Voice & Reviews\n\n- Strong affinity; complaints on price and lines.\n\n## 5. Social Footprint\n\n- Active visual storytelling around product and ritual.\n\n## 6. Hiring & Org Signals\n\n- Retail-heavy roles suggest focus on cafe footprint.\n\n## 7. Ads & Growth Motions\n\n- Paid spend around subscription and gifting.\n\n## 8. Strategic Recommendations\n\n- Tighten metadata on key pages and align campaigns with review language.\n",
  },
  sweetgreen: {
    profile: {
      company: {
        name: "Sweetgreen",
        url: "https://www.sweetgreen.com",
      },
      web: {
        url: "https://www.sweetgreen.com",
        snapshot_summary:
          "Fast-casual salad chain foregrounding health, speed, and digital ordering.",
        meta: {
          title: "Sweetgreen",
          description:
            "Real food, freshly prepared, delivered or picked up from our restaurants.",
          h1: ["Sweetgreen"],
          h2: ["Our Menu", "Order", "Locations"],
        },
      },
      seo: {
        meta_issues: ["Thin location page content."],
        heading_issues: [],
        keyword_summary: ["salad", "healthy lunch", "delivery", "pickup"],
      },
      tech_stack: {
        frameworks: ["React"],
        analytics: ["Google Analytics"],
      },
      reviews: {
        summary:
          "Customers balance convenience and health against price and portion size.",
      },
      social: {},
      hiring: {
        inferred_focus: "Store operations & digital product",
        open_roles: [
          { title: "General Manager" },
          { title: "Product Manager, Digital Ordering" },
        ],
      },
      ads: {
        platforms: ["Meta"],
        themes: ["healthy lunch", "delivery"],
      },
    },
    report_markdown:
      "# OSINT Intelligence Report: Sweetgreen\n\n_Focus: Demo profile_\n\n## 1. Web Presence\n\n- Clean, food-centric layout optimized for ordering.\n\n## 2. SEO Diagnostics\n\n- Location pages could carry more unique content.\n\n## 3. Tech Stack Fingerprint\n\n- React-based frontend with standard analytics.\n\n## 4. Customer Voice & Reviews\n\n- Positive sentiment on convenience; pricing and portions are friction points.\n\n## 5. Social Footprint\n\n- Strong visuals around ingredients and sourcing.\n\n## 6. Hiring & Org Signals\n\n- Emphasis on in-store ops and digital product.\n\n## 7. Ads & Growth Motions\n\n- Campaigns around lunch, delivery, and healthy eating.\n\n## 8. Strategic Recommendations\n\n- Use review language more directly in paid and onsite copy.\n",
  },
  glossier: {
    profile: {
      company: {
        name: "Glossier",
        url: "https://www.glossier.com",
      },
      web: {
        url: "https://www.glossier.com",
        snapshot_summary:
          "DTC beauty brand with editorial-style product pages and heavy community voice.",
        meta: {
          title: "Glossier",
          description:
            "Skincare and makeup inspired by real life. Skin first. Makeup second.",
          h1: ["Glossier"],
          h2: ["New", "Bestsellers", "Skincare", "Makeup"],
        },
      },
      seo: {
        meta_issues: ["Some product pages lack unique descriptions."],
        heading_issues: [],
        keyword_summary: ["skincare", "makeup", "glowy", "everyday"],
      },
      tech_stack: {
        frameworks: ["React"],
        analytics: ["Google Analytics", "Klaviyo"],
      },
      reviews: {
        summary:
          "High brand affinity; common complaints on shipping and product availability.",
      },
      social: {},
      hiring: {
        inferred_focus: "Omnichannel retail & marketing",
        open_roles: [
          { title: "Retail Associate" },
          { title: "Growth Marketing Manager" },
        ],
      },
      ads: {
        platforms: ["Meta", "Google"],
        themes: ["new launches", "everyday staples"],
      },
    },
    report_markdown:
      "# OSINT Intelligence Report: Glossier\n\n_Focus: Demo profile_\n\n## 1. Web Presence\n\n- Editorial storytelling and heavy emphasis on brand voice.\n\n## 2. SEO Diagnostics\n\n- Mostly strong; a few metadata gaps.\n\n## 3. Tech Stack Fingerprint\n\n- Modern DTC stack with marketing automation.\n\n## 4. Customer Voice & Reviews\n\n- Love for the brand; logistics and availability are weak points.\n\n## 5. Social Footprint\n\n- High engagement, strong UGC.\n\n## 6. Hiring & Org Signals\n\n- Investment in retail + marketing.\n\n## 7. Ads & Growth Motions\n\n- Launch-driven plus evergreen brand campaigns.\n\n## 8. Strategic Recommendations\n\n- Address recurring friction areas to protect loyalty.\n",
  },
};

function loadDemoProfile(key) {
  const demo = DEMO_PROFILES[key] || DEMO_PROFILES.blue_bottle;
  // Simulate latency so the UI feels alive
  return new Promise((resolve) => {
    setTimeout(() => resolve(demo), 500);
  });
}

// --- MCP PILL RENDERING ----------------------------------------------

function setMcpPills(plan) {
  const mapping = [
    [mcpWeb, "use_web_scrape"],
    [mcpSeo, "use_seo_probe"],
    [mcpTech, "use_tech_stack"],
    [mcpReviews, "use_reviews_snapshot"],
    [mcpSocial, "use_social_snapshot"],
    [mcpCareers, "use_careers_intel"],
    [mcpAds, "use_ads_snapshot"],
  ];

  mapping.forEach(([el, key]) => {
    if (!el) return;
    el.classList.remove("pill--on");
    el.classList.add("pill--off");
    if (plan[key]) {
      el.classList.remove("pill--off");
      el.classList.add("pill--on");
    }
  });
}

// --- REPORT RENDERING ------------------------------------------------

function safeList(x) {
  return Array.isArray(x) ? x : [];
}

function renderProfileAndReport(profile, markdown) {
  const company = profile.company || {};
  const web = profile.web || {};
  const seo = profile.seo || {};
  const tech = profile.tech_stack || {};
  const hiring = profile.hiring || {};

  metaCompanyName.textContent = company.name || "—";
  metaCompanyUrl.textContent = company.url || "—";

  const snapshot = web.snapshot_summary || "";
  metaInference.textContent =
    snapshot || "Surface read will appear here after a run.";

  metricMetaIssues.textContent = safeList(seo.meta_issues).length.toString();
  metricKeywords.textContent = safeList(seo.keyword_summary).length.toString();
  metricFrameworks.textContent = safeList(tech.frameworks).length.toString();
  metricHiring.textContent = safeList(hiring.open_roles).length.toString();

  // very simple markdown → HTML
  reportMarkdown.innerHTML = "";
  const lines = markdown.split("\n");
  lines.forEach((line) => {
    if (line.startsWith("# ")) {
      const h1 = document.createElement("h2");
      h1.textContent = line.replace(/^#\s+/, "");
      reportMarkdown.appendChild(h1);
    } else if (line.startsWith("## ")) {
      const h2 = document.createElement("h3");
      h2.textContent = line.replace(/^##\s+/, "");
      reportMarkdown.appendChild(h2);
    } else if (line.startsWith("- ")) {
      const p = document.createElement("p");
      p.textContent = line.replace(/^-+\s*/, "• ");
      reportMarkdown.appendChild(p);
    } else if (line.trim().length === 0) {
      // skip blank lines
    } else {
      const p = document.createElement("p");
      p.textContent = line;
      reportMarkdown.appendChild(p);
    }
  });
}

// --- COMMAND PALETTE -------------------------------------------------

function openCmdk() {
  cmdkBackdrop.classList.add("cmdk-backdrop--open");
  cmdkInput.value = "";
  cmdkInput.focus();
}

function closeCmdk() {
  cmdkBackdrop.classList.remove("cmdk-backdrop--open");
}

openCommandPaletteBtn.addEventListener("click", () => {
  openCmdk();
});

cmdkBackdrop.addEventListener("click", (e) => {
  if (e.target === cmdkBackdrop) closeCmdk();
});

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openCmdk();
  } else if (e.key === "Escape") {
    closeCmdk();
  }
});

cmdkInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const cmd = cmdkInput.value.trim();
    if (cmd) {
      applyCommand(cmd);
    }
  }
});

cmdkList.addEventListener("click", (e) => {
  if (e.target.tagName === "LI") {
    const text = e.target.textContent || "";
    const cmd = text.split("—")[0].trim();
    applyCommand(cmd);
  }
});

function applyCommand(cmd) {
  const c = cmd.toLowerCase();
  if (c === "load_blue_bottle") {
    demoModeCheckbox.checked = true;
    demoDatasetSelect.value = "blue_bottle";
    modeValue.textContent = "DEMO";
  } else if (c === "load_sweetgreen") {
    demoModeCheckbox.checked = true;
    demoDatasetSelect.value = "sweetgreen";
    modeValue.textContent = "DEMO";
  } else if (c === "load_glossier") {
    demoModeCheckbox.checked = true;
    demoDatasetSelect.value = "glossier";
    modeValue.textContent = "DEMO";
  } else if (c === "toggle_demo") {
    demoModeCheckbox.checked = !demoModeCheckbox.checked;
    modeValue.textContent = demoModeCheckbox.checked ? "DEMO" : "LIVE";
  } else if (c === "focus_growth") {
    focusInput.value =
      "Focus on growth funnel, paid acquisition, and where spend is likely wasted or fragile.";
  } else if (c === "focus_reputation") {
    focusInput.value =
      "Focus on brand, reputation, and where customer trust is strongest or weakest.";
  } else if (c === "focus_hiring") {
    focusInput.value =
      "Focus on hiring patterns and what they reveal about the real company strategy.";
  }
  closeCmdk();
}

// --- FORM SUBMIT / MAIN FLOW ----------------------------------------

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const companyName = companyNameInput.value.trim();
  const companyUrl = companyUrlInput.value.trim();
  let focus = focusInput.value.trim();
  const reportStyle = reportStyleSelect.value;
  const demoMode = demoModeCheckbox.checked;
  const demoKey = demoDatasetSelect.value;

  // Enrich focus so backend can flip modes.
  if (reportStyle === "red_team") {
    focus =
      (focus ? focus + " " : "") +
      "red team opfor adversarial teardown of this company's public surface and web presence";
  } else if (reportStyle === "narrative") {
    focus =
      (focus ? focus + " " : "") +
      "narrative article case study essay-style human-readable report";
  }

  const plan = createPlanPreview({
    hasUrl: !!companyUrl,
    focus,
    forceFullPlan: demoMode,
  });
  renderPlanGrid(plan);
  setMcpPills(plan);

  resetCot();
  appendCotLine(
    "plan",
    `Mode: ${demoMode ? "demo" : "live"}. Deriving tool plan from surface and focus.`
  );
  appendCotLine(
    "plan",
    "Enabled tools → " +
      Object.entries(plan)
        .filter(([, v]) => v)
        .map(([k]) => {
          switch (k) {
            case "use_web_scrape":
              return "WEB SCRAPE";
            case "use_seo_probe":
              return "SEO PROBE";
            case "use_tech_stack":
              return "TECH STACK";
            case "use_reviews_snapshot":
              return "REVIEWS";
            case "use_social_snapshot":
              return "SOCIAL";
            case "use_careers_intel":
              return "HIRING";
            case "use_ads_snapshot":
              return "ADS";
            default:
              return "";
          }
        })
        .filter(Boolean)
        .join(" · ")
  );

  setStatus(
    "running",
    demoMode ? "Loading demo profile…" : "Dispatching agent API…"
  );
  setCotStatus("running", "RUNNING");
  setReportStatus("running", "Synthesizing");
  setLoadingState(true);
  modeValue.textContent = demoMode ? "DEMO" : "LIVE";

  const startTime = performance.now();

  try {
    let data;

    if (demoMode) {
      data = await loadDemoProfile(demoKey);
      appendCotLine(
        "demo",
        `Loaded demo profile: ${data.profile.company.name} (${data.profile.company.url}).`
      );
    } else {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName || null,
          company_url: companyUrl || null,
          focus: focus || null,
          report_style: reportStyle,
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

    renderProfileAndReport(data.profile, data.report_markdown);
    setStatus("idle", "Analysis complete. Refine focus or change target.");
    setCotStatus("idle", "READY");
    setReportStatus("idle", "Complete");
  } catch (err) {
    console.error(err);
    setStatus(
      "error",
      "Failure during analysis: " + (err && err.message ? err.message : "Unknown error")
    );
    setCotStatus("error", "ERROR");
    setReportStatus("error", "Error");
    appendCotLine(
      "error",
      "Failure during analysis. Check console logs or backend trace for details."
    );
  } finally {
    setLoadingState(false);
  }
});

// --- INITIALIZATION --------------------------------------------------

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
  setMcpPills(initialPlan);
  resetCot();
  setStatus("idle", "Idle. Ready for new target.");
  setCotStatus("idle", "AWAITING INPUT");
  setReportStatus("idle", "Ready");
})();
